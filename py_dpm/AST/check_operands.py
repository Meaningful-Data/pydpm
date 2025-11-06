from abc import ABC

import pandas as pd

from py_dpm.AST.ASTObjects import Dimension, OperationRef, PersistentAssignment, PreconditionItem, \
    Scalar, TemporaryAssignment, VarID, VarRef, WhereClauseOp, WithExpression
from py_dpm.AST.ASTTemplate import ASTTemplate
from py_dpm.AST.WhereClauseChecker import WhereClauseChecker
from py_dpm.DataTypes.ScalarTypes import Integer, Mixed, Number, ScalarFactory
from py_dpm.Exceptions import exceptions
from py_dpm.Exceptions.exceptions import SemanticError
from py_dpm.models import ItemCategory, Operation, VariableVersion, ViewDatapoints, \
    ViewKeyComponents, ViewOpenKeys
from py_dpm.Utils.operands_mapping import generate_new_label, set_operand_label
from py_dpm.data_handlers import filter_all_data

operand_elements = ['table', 'rows', 'cols', 'sheets', 'default', 'interval']


def _create_operand_label(node):
    label = generate_new_label()
    node.label = label


def _modify_element_info(new_data, element, table_info):
    if new_data is None and table_info[element] is None:
        pass
    elif table_info[element] == ['*']:
        pass
    elif new_data is not None and table_info[element] is None:
        table_info[element] = new_data

    elif new_data == ['*']:
        # We have already all data available
        table_info[element] = new_data

    else:
        # We get only the elements that are not already in the info and sort them
        new_list = [x for x in new_data if x not in table_info[element]]
        new_list += table_info[element]
        new_list = sorted(new_list)
        table_info[element] = new_list


def _modify_table(node, table_info):
    for element in table_info:
        _modify_element_info(getattr(node, element), element, table_info)


def format_missing_data(node):
    rows = ', '.join([f"r{x}" for x in node.rows]) if node.rows else None
    cols = ', '.join([f"c{x}" for x in node.cols]) if node.cols else None
    sheets = ', '.join([f"s{x}" for x in node.sheets]) if node.sheets else None
    op_pos = [node.table, rows, cols, sheets]
    cell_exp = ", ".join(x for x in op_pos if x is not None)
    raise exceptions.SemanticError("1-2", cell_expression=cell_exp)


class OperandsChecking(ASTTemplate, ABC):
    def __init__(self, session, expression, ast, release_id, is_scripting=False):
        self.expression = expression
        self.release_id = release_id
        self.AST = ast
        self.tables = {}
        self.operands = {}
        self.key_components = {}
        self.partial_selection = None
        self.data = None
        self.items = []
        self.preconditions = False
        self.dimension_codes = []
        self.open_keys = None

        self.operations = []
        self.operations_data = None
        self.is_scripting = is_scripting

        self.session = session

        super().__init__()
        self.visit(self.AST)
        self.check_headers()
        self.check_items()
        self.check_tables()
        self.check_dimensions()

        self.check_operations()

    def _check_header_present(self, table, header):
        if (self.partial_selection is not None and self.partial_selection.table == table and
                getattr(self.partial_selection, header) is not None):
            return
        for node in self.operands[table]:
            if getattr(node, header) is None:
                if header == 'cols':
                    header = 'columns'
                raise exceptions.SemanticError("1-20", header=header, table=table)

    def check_headers(self):
        table_codes = list(self.tables.keys())
        if len(table_codes) == 0:
            return
        query = """
        SELECT DISTINCT tv."Code", tv."StartReleaseID", tv."EndReleaseID", h."Direction", t."HasOpenRows", t."HasOpenColumns", t."HasOpenSheets"
        FROM "Table" AS t
        INNER JOIN "TableVersion" tv ON t."TableID" = tv."TableID"
        INNER JOIN "TableVersionHeader" tvh ON tv."TableVID" = tvh."TableVID"
        INNER JOIN "Header" h ON h."HeaderID" = tvh."HeaderID"
        """
        codes = [f"{code!r}" for code in table_codes]
        query += f"WHERE tv.\"Code\" IN ({', '.join(codes)}) "
        query += "AND tv.\"EndReleaseID\" is null"
        df_headers = pd.read_sql(query, self.session.connection())
        for table in table_codes:
            table_headers = df_headers[df_headers['Code'] == table]
            if table_headers.empty:
                continue
            open_rows = table_headers['HasOpenRows'].values[0]
            open_cols = table_headers['HasOpenColumns'].values[0]
            open_sheets = table_headers['HasOpenSheets'].values[0]
            if "Y" in table_headers['Direction'].values and not open_rows:
                self._check_header_present(table, 'rows')
            if "X" in table_headers['Direction'].values and not open_cols:
                self._check_header_present(table, 'cols')
            if "Z" in table_headers['Direction'].values and not open_sheets:
                self._check_header_present(table, 'sheets')


    def check_items(self):
        if len(self.items) == 0:
            return
        df_items = ItemCategory.get_items(self.session, self.items, self.release_id)
        if len(df_items.iloc[:, 0].values) < len(set(self.items)):
            not_found_items = list(set(self.items).difference(set(df_items['Signature'])))
            raise exceptions.SemanticError("1-1", items=not_found_items)

    def check_dimensions(self):
        if len(self.dimension_codes) == 0:
            return
        self.open_keys = ViewOpenKeys.get_keys(self.session, self.dimension_codes, self.release_id)
        if len(self.open_keys) < len(self.dimension_codes):
            not_found_dimensions = list(set(self.dimension_codes).difference(self.open_keys['property_code']))
            raise exceptions.SemanticError("1-5", open_keys=not_found_dimensions)

    def check_tables(self):
        for table, value in self.tables.items():
            # Extract all data and filter to get only necessary data
            table_info = value
            df_table = ViewDatapoints.get_table_data(self.session, table, table_info['rows'],
                                                table_info['cols'], table_info['sheets'], self.release_id)
            # Insert data type on each node by selecting only data required by node
            for node in self.operands[table]:
                node_data = filter_all_data(df_table, table, node.rows, node.cols, node.sheets)
                # Checking grey cells (no variable ID in data for that cell)
                grey_cells_data = node_data[node_data['variable_id'].isnull()]
                if not grey_cells_data.empty:
                    if len(grey_cells_data) > 10:
                        list_cells = grey_cells_data["cell_code"].values[:10]
                    else:
                        list_cells = grey_cells_data["cell_code"].values
                    cell_expression = ', '.join(list_cells)
                    raise exceptions.SemanticError("1-17", cell_expression=cell_expression)
                if node_data.empty:
                    format_missing_data(node)
                extract_data_types(node, node_data['data_type'])

                # Check for invalid sheet wildcards
                if df_table['sheet_code'].isnull().all() and node.sheets is not None and '*' in node.sheets:
                    # Check if s* is required to avoid duplicate (row, column) combinations
                    # Group by (row_code, column_code) and check for duplicates
                    # IMPORTANT: Include NA/NULL values in grouping (dropna=False)
                    df_without_sheets = df_table.groupby(['row_code', 'column_code'], dropna=False).size()
                    has_duplicates = (df_without_sheets > 1).any()

                    if not has_duplicates:
                        # Only raise error if sheets are truly not needed (no duplicates without them)
                        raise SemanticError("1-18")
                    # else: s* is required even though sheet_code is NULL, so allow it

                # Check for invalid row wildcards
                if df_table['row_code'].isnull().all() and node.rows is not None and '*' in node.rows:
                    # Check if r* is required to avoid duplicate (column, sheet) combinations
                    # IMPORTANT: Include NA/NULL values in grouping (dropna=False)
                    df_without_rows = df_table.groupby(['column_code', 'sheet_code'], dropna=False).size()
                    has_duplicates = (df_without_rows > 1).any()

                    if not has_duplicates:
                        # Only raise error if rows are truly not needed
                        raise SemanticError("1-19")
                    # else: r* is required even though row_code is NULL, so allow it
            del node_data

            # Adding data to self.data
            if self.data is None:
                self.data = df_table
            else:
                self.data: pd.DataFrame = pd.concat([self.data, df_table], axis=0).reset_index(drop=True)


            self.key_components[table] = ViewKeyComponents.get_by_table(self.session, table, self.release_id)

    # Start of visiting nodes
    def visit_WithExpression(self, node: WithExpression):
        if node.partial_selection.is_table_group:
            raise exceptions.SemanticError("1-10", table=node.partial_selection.table)
        self.partial_selection: VarID = node.partial_selection
        self.visit(node.expression)

    def visit_VarID(self, node: VarID):

        if node.is_table_group:
            raise exceptions.SemanticError("1-10", table=node.table)

        if self.partial_selection:
            for attribute in operand_elements:
                if getattr(node, attribute, None) is None and not getattr(self.partial_selection, attribute, None) is None:
                    setattr(node, attribute, getattr(self.partial_selection, attribute))

        if not node.table:
            raise exceptions.SemanticError("1-4", table=node.table)

        _create_operand_label(node)
        set_operand_label(node.label, node)

        table_info = {
            'rows': node.rows,
            'cols': node.cols,
            'sheets': node.sheets
        }

        if node.table not in self.tables:
            self.tables[node.table] = table_info
            self.operands[node.table] = [node]
        else:
            self.operands[node.table].append(node)
            _modify_table(node, self.tables[node.table])

    def visit_Dimension(self, node: Dimension):
        if node.dimension_code not in self.dimension_codes:
            self.dimension_codes.append(node.dimension_code)

    def visit_VarRef(self, node: VarRef):
        if not VariableVersion.check_variable_exists(self.session, node.variable, self.release_id):
            raise exceptions.SemanticError('1-3', variable=node.variable)

    def visit_PreconditionItem(self, node: PreconditionItem):

        if self.is_scripting:
            raise exceptions.SemanticError('6-3', precondition=node.variable_code)

        if not VariableVersion.check_variable_exists(self.session, node.variable_code, self.release_id):
            raise exceptions.SemanticError("1-3", variable=node.variable_code)

        self.preconditions = True
        _create_operand_label(node)
        set_operand_label(node.label, node)

    def visit_Scalar(self, node: Scalar):
        if node.item and node.scalar_type == 'Item':
            if node.item not in self.items:
                self.items.append(node.item)

    def visit_WhereClauseOp(self, node: WhereClauseOp):
        self.visit(node.operand)
        checker = WhereClauseChecker()
        checker.visit(node.condition)
        node.key_components = checker.key_components
        self.visit(node.condition)

    def visit_OperationRef(self, node: OperationRef):
        if not self.is_scripting:
            raise exceptions.SemanticError("6-2", operation_code=node.operation_code)

    def visit_PersistentAssignment(self, node: PersistentAssignment):
        # TODO: visit node.left when there are calculations variables in database
        self.visit(node.right)

    def visit_TemporaryAssignment(self, node: TemporaryAssignment):
        temporary_identifier = node.left
        self.operations.append(temporary_identifier.value)
        self.visit(node.right)

    def check_operations(self):
        if len(self.operations):
            df_operations = Operation.get_operations_from_codes(session=self.session, operation_codes=self.operations,
                                                                release_id=self.release_id)
            if len(df_operations.values) < len(self.operations):
                not_found_operations = list(set(self.operations).difference(set(df_operations['Code'])))
                raise exceptions.SemanticError('1-8', operations=not_found_operations)
            self.operations_data = df_operations


def extract_data_types(node: VarID, database_types: pd.Series) -> None:
    """
    Extract data type of var ids from database information
    :param node: Var id
    :param database_types: Series that contains the data types of node elements
    :return: None
    """
    unique_types = database_types.unique()
    scalar_factory = ScalarFactory()
    if len(unique_types) == 1:
        data_type = scalar_factory.database_types_mapping(unique_types[0])
        if node.interval and isinstance(data_type(), Number):
            setattr(node, "type", data_type(node.interval))
        else:
            setattr(node, "type", data_type())
    else:
        data_types = {scalar_factory.database_types_mapping(data_type) for data_type in unique_types}
        if len(data_types) == 1:
            data_type = data_types.pop()
            setattr(node, "type", data_type())
        elif len(data_types) == 2 and Number in data_types and Integer in data_types:
            setattr(node, "type", Number())
        else:
            setattr(node, "type", Mixed())
