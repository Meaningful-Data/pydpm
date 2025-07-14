import copy
import re

import pandas as pd

from py_dpm.AST.ASTObjects import VarID, WithExpression
from py_dpm.AST.ASTTemplate import ASTTemplate
from py_dpm.Exceptions import exceptions
from py_dpm.models import ModuleVersionComposition, TableGroup, TableGroupComposition, TableVersion, ViewDatapoints
from py_dpm.Utils.tokens import EXPRESSION, STATUS, STATUS_CORRECT, STATUS_INCOMPLETE, STATUS_INCORRECT, VALIDATION_CODE
from py_dpm.data_handlers import filter_all_data

cell_components = ['table', 'rows', 'cols', 'sheets']
TABLE_ID = 'TableID'
MODULE_VID = 'ModuleVID'
TABLE_CODE = 'Code'
GROUP = 'group'
MODULE_VERSION_ID = 'module_version_id'
MODULE_CODE = 'module_code'


class VariantsProcessorChecker(ASTTemplate):
    def __init__(self, ast):
        super().__init__()
        self._is_variant = False
        self.visit(ast)

    @property
    def is_variant(self):
        return self._is_variant

    def visit_VarID(self, node: VarID):
        if node.is_table_group:
            self._is_variant = True


class VariantsProcessor(ASTTemplate):
    """
    Class to generate individual validations from a validation defined on groups.

    :parameter expression: DPM-XL expression.
    :parameter ast: Abstract Syntax Tree of expression.
    :parameter session: SQLAlchemy Session to be used to connect to the DB.
    :parameter validation_code: Code of parent validation.
    """

    def __init__(self, expression, ast, session, validation_code, release_id):
        super().__init__()
        self.expression = expression
        self.AST = ast
        self.session = session
        self.validation_code = validation_code
        self.current_validation = 1
        self.partial_selection = None
        self.release_id = release_id

        self.table_data = {}
        self.group_tables = []
        self.table_groups_compositions = {}
        self.tables_without_cells = []
        self.children_suffix = None
        self.equal_children_suffix = True

        self.visit(self.AST)

    def check_if_table_has_cells(self, table_code, rows, cols, sheets):
        """
        Method to check if an individual table has cells for rows, columns and sheets of validation.
        :param table_code: code of table.
        :param rows: rows.
        :param cols: columns.
        :param sheets: sheets.
        :return: True if table has cells, False otherwise.
        """
        if table_code not in self.table_data:
            datapoints = ViewDatapoints.get_table_data(session=self.session, table=table_code, release_id=self.release_id)
            self.table_data[table_code] = datapoints
        else:
            datapoints = self.table_data[table_code]
        data = filter_all_data(data=datapoints, table_code=table_code, rows=rows, cols=cols, sheets=sheets)
        return not data.empty

    def check_table_from_module(self, node, table_module_id, is_abstract):
        """
        Method to get table_versions of a table group when there are cells for those tables.
        :param node: var_id node
        :param table_module_id: module id
        :param is_abstract: flag that represents if table is abstract
        :return: table version if table version has cells, None otherwise.
        """

        table_versions = TableVersion.get_tables_versions_of_table_group_compositions(session=self.session,
                                                                                      table_id=table_module_id,
                                                                                      is_abstract=is_abstract,
                                                                                      release_id=self.release_id)

        for table_version in table_versions:
            table_with_cells = self.check_if_table_has_cells(table_version.Code, node.rows, node.cols, node.sheets)
            if table_with_cells:
                return table_version
            else:
                if table_version.TableID not in self.tables_without_cells:
                    self.tables_without_cells.append(table_version.TableID)
        return None

    def generate_child_expression(self, group_code, table_code):
        """
        Method to replace group_code by table_code in order to generate new validations.
        :param group_code: Group code.
        :param table_code: Table code.
        """
        groups = re.search("(" + re.escape(group_code) + '[^.$]' + ")", self.expression)
        if f"g{group_code}" in self.expression and groups:
            group = groups.group(0)
            suffix = table_code[-(len(table_code)-len(group_code)):]
            if group:
                if not self.children_suffix:
                    self.children_suffix = suffix
                else:
                    if self.children_suffix != suffix:
                        self.equal_children_suffix = False
                        return
                self.expression = re.sub(re.escape(f"g{group_code}") + '[^.$]', f"t{table_code}" + group[-1], self.expression)

    def generate_child_expressions(self):
        """
        Method to generate all the individual validations.
        :return: Expressions and expressions with errors.
        """
        if self.group_tables:
            final_expressions = []
            final_expressions_with_errors = []
            df_tables = pd.DataFrame.from_records(self.group_tables)
            df_tables = df_tables[~df_tables[TABLE_ID].isin(self.tables_without_cells)]
            df_tables.drop_duplicates(inplace=True)

            table_ids = df_tables[TABLE_ID].tolist()
            modules_df = ModuleVersionComposition.get_modules_from_table_ids(session=self.session, table_ids=table_ids,
                                                                             release_id=self.release_id)

            data = pd.merge(df_tables, modules_df, on=[TABLE_ID])

            expression = copy.deepcopy(self.expression)
            for module, modules_tables in data.groupby(MODULE_VID):
                modules_tables.apply(lambda x: self.generate_child_expression(x[GROUP], x[TABLE_CODE]), axis=1)
                module_code = modules_tables[MODULE_CODE].unique().tolist()[0]
                if len(modules_tables) < len(self.table_groups_compositions):
                    final_expressions_with_errors.append(
                        {EXPRESSION: self.expression, MODULE_VERSION_ID: module, MODULE_CODE: module_code})
                else:
                    if self.equal_children_suffix:
                        final_expressions.append(
                            {EXPRESSION: self.expression, MODULE_VERSION_ID: module, MODULE_CODE: module_code})
                    else:
                        final_expressions_with_errors.append(
                            {EXPRESSION: self.expression, MODULE_VERSION_ID: module, MODULE_CODE: module_code})
                        self.equal_children_suffix = True
                self.expression = copy.deepcopy(expression)
                self.children_suffix = None

            return final_expressions, final_expressions_with_errors
        else:
            raise exceptions.SemanticError("5-2-1")

    def create_validation(self, expression_info, status):
        """
        Method to centralize creation of validations given expression and status of new validation
        :param expression_info: Dictionary with information about expression, module_vid and module_code of validation
        :param status: Status of validation
        :return: Validation with code, expression and status
        """

        validation_code = self.generate_child_validation_code() if status == STATUS_CORRECT else None

        validation = {VALIDATION_CODE: validation_code,
                      EXPRESSION: expression_info[EXPRESSION],
                      STATUS: status,
                      MODULE_VERSION_ID: expression_info[MODULE_VERSION_ID],
                      MODULE_CODE: expression_info[MODULE_CODE]}
        return validation

    def create_validation_new_format(self, expressions_dict):
        """
        Method to centralize creation of validations given expression and status of new validation
        :param expression_info: Dictionary with information about expression, module_vid and module_code of validation
        :param status: Status of validation
        :return: Validation with code, expression and status
        """

        correct_expressions = expressions_dict[STATUS_CORRECT]
        incomplete_expressions = expressions_dict[STATUS_INCOMPLETE]
        incorrect_expressions = expressions_dict[STATUS_INCORRECT]
        unique_correct_expressions = pd.DataFrame.from_records(correct_expressions)['expression'].unique().tolist() if correct_expressions else []
        unique_incomplete_expressions = pd.DataFrame.from_records(incomplete_expressions)['expression'].unique().tolist() if incomplete_expressions else []
        unique_incorrect_expressions = pd.DataFrame.from_records(incorrect_expressions)['expression'].unique().tolist() if incorrect_expressions else []
        validations = []
        if correct_expressions:
            v = self._aux_create_validation_new_format(correct_expressions, unique_correct_expressions, STATUS_CORRECT)
            validations.extend(v)
        if incomplete_expressions:
            v = self._aux_create_validation_new_format(incomplete_expressions, unique_incomplete_expressions, STATUS_INCOMPLETE)
            validations.extend(v)
        if incorrect_expressions:
            v = self._aux_create_validation_new_format(incorrect_expressions, unique_incorrect_expressions, STATUS_INCORRECT)
            validations.extend(v)

        return validations

    def _aux_create_validation_new_format(self, expressions, unique_expressions, status):
        validations = []
        for expr in unique_expressions:
            aux = {}
            aux[EXPRESSION] = expr
            aux[STATUS] = status
            if status == STATUS_CORRECT:
                aux[VALIDATION_CODE] = self.generate_child_validation_code()
            else:
                aux[VALIDATION_CODE] = None
            aux['scopes'] = []
            for elto in expressions:
                if elto[EXPRESSION] == aux[EXPRESSION]:
                    aux['scopes'].append(
                        {"module_versions_ids": [elto[MODULE_VERSION_ID]],
                        "module_code": elto[MODULE_CODE]
                        }
                    )
            validations.append(aux)
        return validations

    def generate_child_validation_code(self):
        """
        Method to calculate validation codes for new validations.
        :return: New code for the individual validation.
        """
        child_code = f"{self.validation_code}-{self.current_validation}"
        self.current_validation += 1
        return child_code

    def visit_WithExpression(self, node: WithExpression):
        self.partial_selection = node.partial_selection
        self.visit(node.partial_selection)
        self.visit(node.expression)

    def visit_VarID(self, node: VarID):
        if self.partial_selection:
            for attribute in cell_components:
                if not getattr(node, attribute, False) and hasattr(self.partial_selection, attribute):
                    setattr(node, attribute, getattr(self.partial_selection, attribute))

        if node.is_table_group or self.partial_selection.is_table_group:
            if node.table:
                if node.table not in self.table_groups_compositions:
                    group: TableGroup = TableGroup.get_group_from_code(session=self.session, group_code=node.table)
                    if not group:
                        raise exceptions.SemanticError("1-6", table_group=node.table)
                    table_groups_compositions = TableGroupComposition.get_from_parent_table_code(code=node.table, session=self.session)
                    self.table_groups_compositions[node.table] = table_groups_compositions
                else:
                    table_groups_compositions = self.table_groups_compositions[node.table]

                for table_id, is_abstract in table_groups_compositions:
                    table_version = self.check_table_from_module(node, table_id, is_abstract)
                    if table_version:
                        self.group_tables.append(
                            {GROUP: node.table, TABLE_CODE: table_version.Code, TABLE_ID: table_version.TableID})
