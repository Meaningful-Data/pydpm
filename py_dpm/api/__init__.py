"""
PyDPM Public API

Main entry point for the PyDPM library.
Provides both DPM-XL specific and general DPM functionality.
"""

# Import from DPM-XL API
from py_dpm.api.dpm_xl import (
    SyntaxAPI,
    SemanticAPI,
    ASTGenerator,
    CompleteASTAPI,
)

# Import from general DPM API
from py_dpm.api.dpm import (
    DataDictionaryAPI,
    DPMExplorer,
    OperationScopesAPI,
    MigrationAPI,
)

# Import convenience functions and types from DPM API
from py_dpm.api.dpm.operation_scopes import (
    calculate_scopes_from_expression,
    get_existing_scopes,
)
from py_dpm.api.dpm.types import (
    ModuleVersionInfo,
    TableVersionInfo,
    HeaderVersionInfo,
    OperationScopeDetailedInfo,
    OperationScopeResult,
)

# Import AST generator convenience functions
from py_dpm.api.dpm_xl.ast_generator import (
    parse_expression,
    validate_expression,
    parse_batch,
)

# Import complete AST functions
from py_dpm.api.dpm_xl.complete_ast import (
    generate_complete_ast,
    generate_complete_batch,
    generate_enriched_ast,
    enrich_ast_with_metadata,
)

# Legacy imports for backward compatibility
from antlr4 import CommonTokenStream, InputStream
from py_dpm.dpm_xl.grammar.generated.dpm_xlLexer import dpm_xlLexer
from py_dpm.dpm_xl.grammar.generated.dpm_xlParser import dpm_xlParser
from py_dpm.dpm_xl.grammar.generated.listeners import DPMErrorListener
from py_dpm.dpm_xl.ast.constructor import ASTVisitor
from py_dpm.dpm_xl.ast.nodes import TemporaryAssignment
from py_dpm.dpm_xl.ast.ml_generation import MLGeneration
from py_dpm.dpm_xl.ast.module_analyzer import ModuleAnalyzer
from py_dpm.dpm_xl.ast.module_dependencies import ModuleDependencies
from py_dpm.dpm_xl.ast.operands import OperandsChecking
from py_dpm.dpm_xl.validation.variants import (
    VariantsProcessor,
    VariantsProcessorChecker,
)
from py_dpm.dpm_xl.validation.property_constraints import (
    PropertiesConstraintsChecker,
    PropertiesConstraintsProcessor,
)
from py_dpm.dpm.db.utils import get_session, get_engine

# Semantic analyzer - need to check if this exists
try:
    from py_dpm.semantics import SemanticAnalyzer
except ImportError:
    SemanticAnalyzer = None

# Export the main API classes
__all__ = [
    # Complete AST API (recommended - includes data fields)
    'generate_complete_ast',
    'generate_complete_batch',

    # Enriched AST API (engine-ready with framework structure)
    'generate_enriched_ast',
    'enrich_ast_with_metadata',

    # Simple AST API
    'ASTGenerator',
    'parse_expression',
    'validate_expression',
    'parse_batch',

    # Advanced APIs
    'MigrationAPI',
    'SyntaxAPI',
    'SemanticAPI',
    'DataDictionaryAPI',
    'OperationScopesAPI',
    'DPMExplorer',

    # Operation Scopes Convenience Functions
    'calculate_scopes_from_expression',
    'get_existing_scopes',

    # Operation Scopes Data Classes
    'ModuleVersionInfo',
    'TableVersionInfo',
    'HeaderVersionInfo',
    'OperationScopeDetailedInfo',
    'OperationScopeResult',

    'API'  # Keep for backward compatibility
]


class API:
    """
    Legacy API class for backward compatibility.

    Note: This class is maintained for backward compatibility.
    New code should use the specific API classes:
    - SyntaxAPI for syntax validation
    - SemanticAPI for semantic validation
    - ASTGenerator for AST generation
    - DataDictionaryAPI for database queries
    """
    error_listener = DPMErrorListener()
    visitor = ASTVisitor()

    def __init__(self, database_path=None, connection_url=None):
        """
        Initialize the API.

        Args:
            database_path: Path to SQLite database (optional)
            connection_url: SQLAlchemy connection URL for PostgreSQL (optional)
        """
        if connection_url:
            # Create isolated engine and session for the provided connection URL
            from sqlalchemy.orm import sessionmaker
            from py_dpm.dpm.db.utils import create_engine_from_url

            # Create engine for the connection URL (supports SQLite, PostgreSQL, MySQL, etc.)
            self.engine = create_engine_from_url(connection_url)
            session_maker = sessionmaker(bind=self.engine)
            self.session = session_maker()
        elif database_path:
            # Create isolated engine and session for this specific database
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            import os

            # Create the database directory if it doesn't exist
            db_dir = os.path.dirname(database_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)

            # Create engine for specific database path
            db_connection_url = f"sqlite:///{database_path}"
            self.engine = create_engine(db_connection_url, pool_pre_ping=True)
            session_maker = sessionmaker(bind=self.engine)
            self.session = session_maker()
        else:
            # Use default global connection
            get_engine()
            self.session = get_session()
            self.engine = None

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

    def semantic_validation(self, expression, release_id=None):
        self.create_ast(expression=expression)

        oc = OperandsChecking(session=self.session, expression=expression, ast=self.AST, release_id=release_id)

        if SemanticAnalyzer:
            semanticAnalysis = SemanticAnalyzer.InputAnalyzer(expression)
            semanticAnalysis.data = oc.data
            semanticAnalysis.key_components = oc.key_components
            semanticAnalysis.open_keys = oc.open_keys
            semanticAnalysis.preconditions = oc.preconditions
            results = semanticAnalysis.visit(self.AST)
            return results
        else:
            raise ImportError("SemanticAnalyzer not available")

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
