from py_dpm.api.migration import MigrationAPI
from py_dpm.api.syntax import SyntaxAPI
from py_dpm.api.semantic import SemanticAPI
from py_dpm.api.ast_generator import ASTGenerator, parse_expression, validate_expression, parse_batch
from py_dpm.api.complete_ast import generate_complete_ast, generate_complete_batch

from antlr4 import CommonTokenStream, InputStream

from py_dpm.grammar.dist.dpm_xlLexer import dpm_xlLexer
from py_dpm.grammar.dist.dpm_xlParser import dpm_xlParser
from py_dpm.grammar.dist.listeners import DPMErrorListener
from py_dpm.AST.ASTConstructor import ASTVisitor
from py_dpm.AST.ASTObjects import TemporaryAssignment
from py_dpm.AST.MLGeneration import MLGeneration
from py_dpm.AST.ModuleAnalyzer import ModuleAnalyzer
from py_dpm.AST.ModuleDependencies import ModuleDependencies
from py_dpm.AST.check_operands import OperandsChecking
from py_dpm.semantics import SemanticAnalyzer

from py_dpm.ValidationsGeneration.VariantsProcessor import (
    VariantsProcessor,
    VariantsProcessorChecker,
)
from py_dpm.ValidationsGeneration.PropertiesConstraintsProcessor import (
    PropertiesConstraintsChecker,
    PropertiesConstraintsProcessor,
)

from py_dpm.db_utils import get_session, get_engine

# Export the main API classes
__all__ = [
    # Complete AST API (recommended - includes data fields)
    'generate_complete_ast',
    'generate_complete_batch',

    # Simple AST API
    'ASTGenerator',
    'parse_expression',
    'validate_expression',
    'parse_batch',

    # Advanced APIs
    'MigrationAPI',
    'SyntaxAPI',
    'SemanticAPI',
    'API'  # Keep for backward compatibility
]


class API:
    error_listener = DPMErrorListener()
    visitor = ASTVisitor()

    def __init__(self):
        get_engine()
        self.session = get_session()

    @classmethod
    def lexer(cls, text: str):
        """
        Extracts the tokens from the input expression
        :param text: Expression to be analyzed
        """
        lexer = dpm_xlLexer(InputStream(text))
        lexer._listeners = [cls.error_listener]
        cls.stream = CommonTokenStream(lexer)

    @classmethod
    def parser(cls):
        """
        Parses the token from the lexer stream
        """
        parser = dpm_xlParser(cls.stream)
        parser._listeners = [cls.error_listener]
        cls.CST = parser.start()

        if parser._syntaxErrors == 0:
            return True

    @classmethod
    def syntax_validation(cls, expression):
        """
        Validates that the input expression is syntactically correct by applying the ANTLR lexer and parser
        :param expression: Expression to be analyzed
        """
        cls.lexer(expression)
        cls.parser()

    @classmethod
    def create_ast(cls, expression):
        """
        Generates the AST from the expression
        :param expression: Expression to be analyzed
        """
        cls.lexer(expression)
        if cls.parser():
            cls.visitor = ASTVisitor()
            cls.AST = cls.visitor.visit(cls.CST)

    def semantic_validation(self, expression):
        self.create_ast(expression=expression)

        oc = OperandsChecking(session=self.session, expression=expression, ast=self.AST, release_id=None)
        semanticAnalysis = SemanticAnalyzer.InputAnalyzer(expression)

        semanticAnalysis.data = oc.data
        semanticAnalysis.key_components = oc.key_components
        semanticAnalysis.open_keys = oc.open_keys

        semanticAnalysis.preconditions = oc.preconditions

        results = semanticAnalysis.visit(self.AST)
        return results

    def _check_property_constraints(self, ast):
        """
        Method to check property constraints
        :return: Boolean value indicating if the ast has property constraints
        """
        pcc = PropertiesConstraintsChecker(ast=ast, session=self.session)
        return pcc.is_property_constraint

    def _check_property_constraints_from_expression(self, expression):
        """
        Method to check property constraints
        :return: Boolean value indicating if the ast has property constraints
        """
        self.create_ast(expression=expression)
        pcc = PropertiesConstraintsChecker(ast=self.AST, session=self.session)
        return pcc.is_property_constraint

    def _check_variants(self, expression):
        """
        Method to check table groups
        :return: Boolean value indicating if the ast has table groups
        """
        self.create_ast(expression=expression)
        tgc = VariantsProcessorChecker(ast=self.AST)
        return tgc.is_variant
