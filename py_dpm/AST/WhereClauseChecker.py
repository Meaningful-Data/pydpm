from py_dpm.AST.ASTObjects import Dimension
from py_dpm.AST.ASTTemplate import ASTTemplate


class WhereClauseChecker(ASTTemplate):

    def __init__(self):
        super().__init__()
        self.key_components = []

    def visit_Dimension(self, node: Dimension):
        self.key_components.append(node.dimension_code)
