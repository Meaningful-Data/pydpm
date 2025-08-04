import pandas as pd

from py_dpm.AST.ASTObjects import AggregationOp, BinOp, ComplexNumericOp, CondExpr, FilterOp, GetOp, PropertyReference, RenameOp, Scalar, \
    TimeShiftOp, UnaryOp, VarID, WhereClauseOp
from py_dpm.AST.ASTTemplate import ASTTemplate
from py_dpm.Exceptions import exceptions
from py_dpm.models import ItemCategory, ViewDatapoints
from py_dpm.Utils.ValidationsGenerationUtils import ValidationsGenerationUtils
from py_dpm.Utils.tokens import *

ALLOWED_OPERATORS = [MATCH, IN, EQ, NEQ, GT, GTE, LT, LTE, LENGTH, CONCATENATE]


def _check_property_constraint_exists(signature: str, session):
    if ":" in signature:
        property_query = ItemCategory.get_property_from_signature(signature, session)
    else:
        property_query = ItemCategory.get_property_from_code(signature, session)
    if property_query is None:
        return False
    return True


class PropertiesConstraintsChecker(ASTTemplate):
    def __init__(self, ast, session):
        super().__init__()
        self.has_property = False
        self.has_table = False
        self.session = session
        self.visit(ast)

    @property
    def is_property_constraint(self):
        if self.has_table:
            return False
        return self.has_property

    def visit_PropertyReference(self, node: PropertyReference):
        # Optional
        if not ":" in node.code:
            pass  # signature should have : to be a property constraint
        signature = node.code
        # look for property in models
        property_query = ItemCategory.get_property_from_signature(signature, self.session)
        if property_query is None:
            raise exceptions.SemanticError("5-1-4", ref=signature)
        self.has_property = True

    def visit_VarID(self, node: VarID):
        if node.table:
            self.has_table = True

    def visit_Scalar(self, node: Scalar):
        signature = node.item
        if not self.has_property:
            if getattr(node, "scalar_type", None) == "Item":
                # go to models and check if item exists and is a property
                property_query = ItemCategory.get_property_from_signature(signature, self.session)
                if property_query:
                    self.has_property = True
                # other assumption could be always first scalar is a property but this is not true
                # self.has_property = True
        else:
            other_property_query = ItemCategory.get_property_from_signature(signature, self.session)
            if other_property_query:
                raise exceptions.SemanticError("5-1-2")


class PropertiesConstraintsProcessor(ASTTemplate):
    """
    Class to generate individual validations from properties constraints

    :parameter expression: DPM-XL expression.
    :parameter ast: Abstract Syntax Tree of expression.
    :parameter validation_code: Code of parent validation.
    :parameter session: SQLAlchemy Session to be used to connect to the DB.
    """

    def __init__(self, expression, ast, validation_code, session, release_id):
        super().__init__()
        self.expression = expression
        self.AST = ast
        self.validation_code = validation_code
        self.session = session
        self.current_validation = 1
        self.property_constraint = None
        self.release_id = release_id
        self.new_expressions = []
        self.visit(self.AST)

    def generate_validations(self):
        """
        Generates individual validations using the extracted property constraint in the Abstract Syntax Tree
        """
        if not self.property_constraint:
            raise exceptions.SemanticError("5-1-1")

        item_category = ItemCategory.get_property_from_signature(
                signature=self.property_constraint, session=self.session, release_id=self.release_id)
        if item_category is None:
            raise exceptions.SemanticError("1-7", property_code=self.property_constraint)
        variables: pd.DataFrame = ViewDatapoints.get_from_property(self.session, item_category.ItemID, self.release_id)
        for table_code, group_df in variables.groupby(['table_code']):
            datapoints = ViewDatapoints.get_table_data(session=self.session, table=str(table_code))
            self.generate_expressions(table_code, group_df, datapoints)

    def generate_expressions(self, table_code, data, datapoints_table):
        """
        Generates new expressions getting their operands by grouping the cells
        :param table_code: code of the operand table
        :param data: dataframe with operand datapoints
        :param datapoints_table: table datapoints
        """
        groups = ValidationsGenerationUtils.group_cells(datapoints_variable=data,
                                                        datapoints_table=datapoints_table)
        for rows, cols, sheets in groups:
            operand = ValidationsGenerationUtils.write_cell(table_code, rows, cols, sheets)
            new_expression = self.expression
            new_expression = new_expression.replace(f"[{self.property_constraint}]", operand)
            self.new_expressions.append(new_expression)

    def create_validation(self, expression, status):
        """
        Creates a dictionary to represent a validation from expression and status information
        :param expression: Expression of validation
        :param status: Status of validation
        :return a dictionary with validation_code, expression and status
        """
        validation_code = None
        if status == STATUS_CORRECT:
            validation_code = f"{self.validation_code}-{self.current_validation}"
            self.current_validation += 1
        return {
            VALIDATION_CODE: validation_code,
            EXPRESSION: expression,
            STATUS: status
        }

    def visit_PropertyReference(self, node: PropertyReference):
        if not self.property_constraint:
            self.property_constraint = node.code
            signature = node.code
            if not _check_property_constraint_exists(signature, self.session):
                raise exceptions.SemanticError("5-1-4", ref=signature)
        else:
            raise exceptions.SemanticError("5-1-2")

    def visit_Scalar(self, node: Scalar):
        if getattr(node, "scalar_type", None) == "Item":
            signature = node.item
            property_query = ItemCategory.get_property_from_signature(signature, self.session)
            if property_query:
                if not self.property_constraint:
                    self.property_constraint = signature

    def visit_BinOp(self, node: BinOp):
        if node.op not in ALLOWED_OPERATORS:
            raise exceptions.SemanticError("5-1-3", operator=node.op)

        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryOp(self, node: UnaryOp):
        if node.op not in ALLOWED_OPERATORS:
            raise exceptions.SemanticError("5-1-3", operator=node.op)
        self.visit(node.operand)

    def visit_CondExpr(self, node: CondExpr):
        raise exceptions.SemanticError("5-1-3", operator=IF)

    def visit_AggregationOp(self, node: AggregationOp):
        raise exceptions.SemanticError("5-1-3", operator=node.op)

    def visit_RenameOp(self, node: RenameOp):
        raise exceptions.SemanticError("5-1-3", operator=RENAME)

    def visit_TimeShiftOp(self, node: TimeShiftOp):
        raise exceptions.SemanticError("5-1-3", operator=TIME_SHIFT)

    def visit_FilterOp(self, node: FilterOp):
        raise exceptions.SemanticError("5-1-3", operator=FILTER)

    def visit_WhereClauseOp(self, node: WhereClauseOp):
        raise exceptions.SemanticError("5-1-3", operator=WHERE)

    def visit_GetOp(self, node: GetOp):
        raise exceptions.SemanticError("5-1-3", operator=GET)

    def visit_ComplexNumericOp(self, node: ComplexNumericOp):
        raise exceptions.SemanticError("5-1-3", operator=node.op)
