from typing import Dict, Any, Optional
from dataclasses import dataclass

# Import directly to avoid circular imports
from antlr4 import CommonTokenStream, InputStream
from py_dpm.dpm_xl.grammar.generated.dpm_xlLexer import dpm_xlLexer
from py_dpm.dpm_xl.grammar.generated.dpm_xlParser import dpm_xlParser
from py_dpm.dpm_xl.grammar.generated.listeners import DPMErrorListener
from py_dpm.dpm_xl.ast.constructor import ASTVisitor
from py_dpm.dpm_xl.ast.operands import OperandsChecking
from py_dpm.dpm_xl import semantic_analyzer as SemanticAnalyzer
from py_dpm.dpm.utils import get_session, get_engine
from py_dpm.exceptions.exceptions import SemanticError


@dataclass
class SemanticValidationResult:
    """
    Result of semantic validation.

    Attributes:
        is_valid (bool): Whether the semantic validation passed
        error_message (Optional[str]): Error message if validation failed
        error_code (Optional[str]): Error code if validation failed
        expression (str): The original expression that was validated
        validation_type (str): Type of validation performed
        results (Optional[Any]): Additional results from semantic analysis
    """

    is_valid: bool
    error_message: Optional[str]
    error_code: Optional[str]
    expression: str
    validation_type: str
    results: Optional[Any] = None


class SemanticAPI:
    """
    API for DPM-XL semantic validation and analysis.

    This class provides methods to perform semantic analysis on DPM-XL expressions,
    including operand checking, data type validation, and structure validation.
    """

    def __init__(
        self,
        database_path: Optional[str] = None,
        connection_url: Optional[str] = None,
        pool_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the Semantic API.

        Args:
            database_path (Optional[str]): Path to SQLite database. If None, uses default from environment.
            connection_url (Optional[str]): Full SQLAlchemy connection URL (e.g., postgresql://user:pass@host:port/db).
                                          Takes precedence over database_path.
            pool_config (Optional[Dict[str, Any]]): Connection pool configuration for PostgreSQL/MySQL.
                Supported keys: pool_size, max_overflow, pool_timeout, pool_recycle, pool_pre_ping.
        """
        self.database_path = database_path
        self.connection_url = connection_url
        self.pool_config = pool_config
        # Store last parsed AST for consumers that need it (e.g. complete AST generation)
        self.ast = None

        if connection_url:
            # Create isolated engine and session for the provided connection URL
            from sqlalchemy.orm import sessionmaker
            from py_dpm.dpm.utils import create_engine_from_url

            # Create engine for the connection URL (supports SQLite, PostgreSQL, MySQL, etc.)
            self.engine = create_engine_from_url(connection_url, pool_config=pool_config)
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

        self.error_listener = DPMErrorListener()
        self.visitor = ASTVisitor()

    def validate_expression(
        self, expression: str, release_id: Optional[int] = None
    ) -> SemanticValidationResult:
        """
        Perform semantic validation on a DPM-XL expression.

        This includes syntax validation, operands checking, data type validation,
        and structure validation.

        Args:
            expression (str): The DPM-XL expression to validate
            release_id (Optional[int]): Specific release ID for component filtering.
                                       If None, uses live/latest release (EndReleaseID IS NULL).

        Returns:
            SemanticValidationResult: Result containing validation status and details

        Example:
            >>> from pydpm.api import SemanticAPI
            >>> semantic = SemanticAPI()
            >>> result = semantic.validate_expression("{tC_01.00, r0100, c0010} + {tC_01.00, r0200, c0010}")
            >>> print(result.is_valid)
            True

            >>> # Validate for specific release
            >>> result = semantic.validate_expression("{tC_01.00, r0100, c0010}", release_id=5)
        """
        try:
            # Parse expression to AST
            input_stream = InputStream(expression)
            lexer = dpm_xlLexer(input_stream)
            lexer._listeners = [self.error_listener]
            token_stream = CommonTokenStream(lexer)

            parser = dpm_xlParser(token_stream)
            parser._listeners = [self.error_listener]
            parse_tree = parser.start()

            if parser._syntaxErrors > 0:
                return SemanticValidationResult(
                    is_valid=False,
                    error_message="Syntax errors detected",
                    error_code="SYNTAX_ERROR",
                    expression=expression,
                    validation_type="SEMANTIC",
                )

            # Generate AST
            ast = self.visitor.visit(parse_tree)
            # Expose AST on the instance for downstream consumers
            self.ast = ast

            # Perform semantic analysis
            oc = OperandsChecking(
                session=self.session,
                expression=expression,
                ast=ast,
                release_id=release_id,
            )
            semanticAnalysis = SemanticAnalyzer.InputAnalyzer(expression)

            semanticAnalysis.data = oc.data
            semanticAnalysis.key_components = oc.key_components
            semanticAnalysis.open_keys = oc.open_keys
            semanticAnalysis.preconditions = oc.preconditions

            results = semanticAnalysis.visit(ast)

            return SemanticValidationResult(
                is_valid=True,
                error_message=None,
                error_code=None,
                expression=expression,
                validation_type="SEMANTIC",
                results=results,
            )

        except SemanticError as e:
            return SemanticValidationResult(
                is_valid=False,
                error_message=str(e),
                error_code=getattr(e, "code", None),
                expression=expression,
                validation_type="SEMANTIC",
            )
        except Exception as e:
            return SemanticValidationResult(
                is_valid=False,
                error_message=str(e),
                error_code="UNKNOWN",
                expression=expression,
                validation_type="SEMANTIC",
            )

    def analyze_expression(
        self, expression: str, release_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform detailed semantic analysis on a DPM-XL expression.

        Args:
            expression (str): The DPM-XL expression to analyze
            release_id (Optional[int]): Specific release ID for component filtering.
                                       If None, uses live/latest release.

        Returns:
            Dict[str, Any]: Detailed analysis results

        Raises:
            Exception: If analysis fails

        Example:
            >>> from pydpm.api import SemanticAPI
            >>> semantic = SemanticAPI()
            >>> analysis = semantic.analyze_expression("{tC_01.00, r0100, c0010}")
            >>> # Analyze for specific release
            >>> analysis = semantic.analyze_expression("{tC_01.00, r0100, c0010}", release_id=5)
        """
        result = self.validate_expression(expression, release_id=release_id)

        if not result.is_valid:
            raise Exception(f"Semantic analysis failed: {result.error_message}")

        # Extract additional analysis information
        analysis = {
            "expression": expression,
            "is_valid": True,
            "results": result.results,
            "data_types": (
                getattr(result.results, "type", None) if result.results else None
            ),
            "components": (
                getattr(result.results, "components", None) if result.results else None
            ),
        }

        return analysis

    def is_valid_semantics(
        self, expression: str, release_id: Optional[int] = None
    ) -> bool:
        """
        Quick check if expression has valid semantics.

        Args:
            expression (str): The DPM-XL expression to check
            release_id (Optional[int]): Specific release ID for component filtering.
                                       If None, uses live/latest release.

        Returns:
            bool: True if semantics are valid, False otherwise

        Example:
            >>> from pydpm.api import SemanticAPI
            >>> semantic = SemanticAPI()
            >>> is_valid = semantic.is_valid_semantics("{tC_01.00, r0100, c0010}")
            >>> # Check for specific release
            >>> is_valid = semantic.is_valid_semantics("{tC_01.00, r0100, c0010}", release_id=5)
        """
        result = self.validate_expression(expression, release_id=release_id)
        return result.is_valid

    def __del__(self):
        """Clean up resources."""
        try:
            if hasattr(self, "session") and self.session:
                self.session.close()
        except Exception:
            pass

        try:
            if hasattr(self, "engine") and self.engine is not None:
                self.engine.dispose()
        except Exception:
            pass

    def close(self):
        """
        Explicitly close the underlying SQLAlchemy session and dispose any private engine.
        """
        try:
            if hasattr(self, "session") and self.session:
                self.session.close()
        except Exception:
            pass

        try:
            if hasattr(self, "engine") and self.engine is not None:
                self.engine.dispose()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience functions for direct usage
def validate_expression(
    expression: str,
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    release_id: Optional[int] = None,
) -> SemanticValidationResult:
    """
    Convenience function to validate DPM-XL expression semantics.

    Args:
        expression (str): The DPM-XL expression to validate
        database_path (Optional[str]): Path to SQLite database. If None, uses default from environment.
        connection_url (Optional[str]): Full SQLAlchemy connection URL (e.g., postgresql://user:pass@host:port/db).
        release_id (Optional[int]): Specific release ID for component filtering.
                                   If None, uses live/latest release.

    Returns:
        SemanticValidationResult: Result containing validation status and details

    Example:
        >>> from pydpm.api.semantic import validate_expression
        >>> result = validate_expression("{tC_01.00, r0100, c0010}", database_path="./database.db")
        >>> # Using PostgreSQL
        >>> result = validate_expression("{tC_01.00, r0100, c0010}",
        ...     connection_url="postgresql://user:pass@host:5432/db")
        >>> # Validate for specific release
        >>> result = validate_expression("{tC_01.00, r0100, c0010}", database_path="./database.db", release_id=5)
    """
    api = SemanticAPI(database_path=database_path, connection_url=connection_url)
    return api.validate_expression(expression, release_id=release_id)


def is_valid_semantics(
    expression: str,
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    release_id: Optional[int] = None,
) -> bool:
    """
    Convenience function to check if expression has valid semantics.

    Args:
        expression (str): The DPM-XL expression to check
        database_path (Optional[str]): Path to SQLite database. If None, uses default from environment.
        connection_url (Optional[str]): Full SQLAlchemy connection URL (e.g., postgresql://user:pass@host:port/db).
        release_id (Optional[int]): Specific release ID for component filtering.
                                   If None, uses live/latest release.

    Returns:
        bool: True if semantics are valid, False otherwise

    Example:
        >>> from pydpm.api.semantic import is_valid_semantics
        >>> is_valid = is_valid_semantics("{tC_01.00, r0100, c0010}", database_path="./database.db")
        >>> # Using PostgreSQL
        >>> is_valid = is_valid_semantics("{tC_01.00, r0100, c0010}",
        ...     connection_url="postgresql://user:pass@host:5432/db")
        >>> # Check for specific release
        >>> is_valid = is_valid_semantics("{tC_01.00, r0100, c0010}", database_path="./database.db", release_id=5)
    """
    api = SemanticAPI(database_path=database_path, connection_url=connection_url)
    return api.is_valid_semantics(expression, release_id=release_id)
