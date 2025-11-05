from typing import List, Optional, Any
from dataclasses import dataclass, field

from antlr4 import CommonTokenStream, InputStream
from py_dpm.grammar.dist.dpm_xlLexer import dpm_xlLexer
from py_dpm.grammar.dist.dpm_xlParser import dpm_xlParser
from py_dpm.grammar.dist.listeners import DPMErrorListener
from py_dpm.AST.ASTConstructor import ASTVisitor
from py_dpm.AST.check_operands import OperandsChecking
from py_dpm.AST.ASTObjects import VarID, PreconditionItem
from py_dpm.OperationScopes.OperationScopeService import OperationScopeService
from py_dpm.models import ModuleVersion, OperationScope, OperationScopeComposition
from py_dpm.db_utils import get_session, get_engine
from py_dpm.Exceptions.exceptions import SemanticError


@dataclass
class OperationScopeResult:
    """
    Result of operation scope calculation.

    Attributes:
        existing_scopes (List[OperationScope]): List of existing scopes in database
        new_scopes (List[OperationScope]): List of newly created scopes
        total_scopes (int): Total number of scopes (existing + new)
        is_cross_module (bool): Whether any scope spans multiple modules
        module_versions (List[int]): List of unique module version IDs involved
        has_error (bool): Whether an error occurred during calculation
        error_message (Optional[str]): Error message if calculation failed
        release_id (Optional[int]): Release ID used for filtering
        expression (Optional[str]): Original expression if calculated from expression
    """
    existing_scopes: List[OperationScope] = field(default_factory=list)
    new_scopes: List[OperationScope] = field(default_factory=list)
    total_scopes: int = 0
    is_cross_module: bool = False
    module_versions: List[int] = field(default_factory=list)
    has_error: bool = False
    error_message: Optional[str] = None
    release_id: Optional[int] = None
    expression: Optional[str] = None


class OperationScopesAPI:
    """
    API for calculating and managing operation scopes.

    This class provides methods to calculate which module versions are involved
    in a DPM-XL operation based on table references and precondition items.
    """

    def __init__(self, database_path: Optional[str] = None, connection_url: Optional[str] = None):
        """
        Initialize the Operation Scopes API.

        Args:
            database_path (Optional[str]): Path to SQLite database. If None, uses default from environment.
            connection_url (Optional[str]): Full SQLAlchemy connection URL (e.g., postgresql://user:pass@host:port/db).
                                          Takes precedence over database_path.
        """
        self.database_path = database_path
        self.connection_url = connection_url

        if connection_url:
            # Create isolated engine and session for the provided connection URL
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            # Create engine for the connection URL (PostgreSQL, MySQL, etc.)
            self.engine = create_engine(connection_url, pool_pre_ping=True,
                                       pool_size=20, max_overflow=10, pool_recycle=180)
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

    def calculate_scopes_from_expression(
        self,
        expression: str,
        operation_version_id: Optional[int] = None,
        release_id: Optional[int] = None,
        read_only: bool = False
    ) -> OperationScopeResult:
        """
        Calculate operation scopes from a DPM-XL expression.

        This is the recommended method for calculating scopes as it automatically
        extracts table VIDs and precondition items from the expression.

        Args:
            expression (str): The DPM-XL expression to analyze
            operation_version_id (Optional[int]): Operation version ID to use for querying existing scopes.
                                                 Used only for comparison, not for persistence unless read_only=False.
            release_id (Optional[int]): Specific release ID to filter modules.
                                       If None, defaults to last release.
            read_only (bool): If True, never commit to database (default: False for backward compatibility).
                            When True, operation_version_id is only used to query existing scopes.

        Returns:
            OperationScopeResult: Result containing existing and new scopes

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> result = api.calculate_scopes_from_expression(
            ...     "{tC_01.00, r0100, c0010} + {tC_02.00, r0200, c0020}",
            ...     operation_version_id=1,
            ...     release_id=42
            ... )
            >>> print(f"Total scopes: {result.total_scopes}")
            >>> print(f"Cross-module: {result.is_cross_module}")
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
                return OperationScopeResult(
                    has_error=True,
                    error_message="Syntax errors detected in expression",
                    expression=expression,
                    release_id=release_id
                )

            # Generate AST
            ast = self.visitor.visit(parse_tree)

            # Perform operands checking to get data
            oc = OperandsChecking(session=self.session, expression=expression, ast=ast, release_id=release_id)

            # Extract table VIDs, precondition items, and table codes from AST
            # Always extract table codes for cross-version scope calculation
            # (release_id will be determined later if None)
            table_vids, precondition_items, table_codes = self._extract_vids_from_ast(ast, oc.data, extract_codes=True)

            # Calculate scopes using the low-level API
            return self.calculate_scopes(
                operation_version_id=operation_version_id,
                tables_vids=table_vids,
                precondition_items=precondition_items,
                release_id=release_id,
                expression=expression,
                table_codes=table_codes,
                read_only=read_only
            )

        except SemanticError as e:
            return OperationScopeResult(
                has_error=True,
                error_message=str(e),
                expression=expression,
                release_id=release_id
            )
        except Exception as e:
            return OperationScopeResult(
                has_error=True,
                error_message=f"Unexpected error: {str(e)}",
                expression=expression,
                release_id=release_id
            )

    def _extract_vids_from_ast(self, ast, data, extract_codes=False) -> tuple[List[int], List[str], List[str]]:
        """
        Extract table VIDs, table codes, and precondition items from OperandsChecking data.

        The OperandsChecking process already extracts all table information,
        so we get it directly from the data DataFrame rather than walking the AST.

        IMPORTANT: When extract_codes is True, this method also returns the table CODES
        so that the scope calculation can find all module versions containing those table codes,
        not just the specific table VIDs from the expression.

        Args:
            ast: The abstract syntax tree (not used, kept for compatibility)
            data: DataFrame with table information from OperandsChecking
            extract_codes: If True, also extract table codes for cross-version scope calculation

        Returns:
            tuple: (list of table VIDs, list of precondition item codes, list of table codes)
        """
        table_vids = []
        table_codes = []
        precondition_items = []

        # Extract unique table VIDs from the data DataFrame
        if 'table_vid' in data.columns:
            table_vids = data['table_vid'].dropna().unique().astype(int).tolist()

            # If requested, also extract table codes for cross-version scope calculation
            if extract_codes and table_vids:
                from py_dpm.models import TableVersion

                # Get table codes for the VIDs
                table_codes_query = (
                    self.session.query(TableVersion.code)
                    .filter(TableVersion.tablevid.in_(table_vids))
                    .distinct()
                )
                table_codes = [row[0] for row in table_codes_query.all()]

        # Note: Precondition items would need to be extracted from the AST
        # or from a separate field in OperandsChecking if available
        # For now, we walk the AST only for precondition items
        def walk_ast(node):
            """Recursively walk the AST to find PreconditionItem nodes."""
            if isinstance(node, PreconditionItem):
                # Extract precondition code
                precondition_code = node.code
                if precondition_code not in precondition_items:
                    precondition_items.append(precondition_code)

            # Recursively process child nodes
            if hasattr(node, '__dict__'):
                for attr_value in vars(node).values():
                    if hasattr(attr_value, '__class__') and hasattr(attr_value.__class__, '__module__'):
                        if 'ASTObjects' in attr_value.__class__.__module__:
                            walk_ast(attr_value)
                    elif isinstance(attr_value, list):
                        for item in attr_value:
                            if hasattr(item, '__class__') and hasattr(item.__class__, '__module__'):
                                if 'ASTObjects' in item.__class__.__module__:
                                    walk_ast(item)

        walk_ast(ast)
        return table_vids, precondition_items, table_codes

    def calculate_scopes(
        self,
        operation_version_id: Optional[int] = None,
        tables_vids: Optional[List[int]] = None,
        precondition_items: Optional[List[str]] = None,
        release_id: Optional[int] = None,
        expression: Optional[str] = None,
        table_codes: Optional[List[str]] = None,
        read_only: bool = False
    ) -> OperationScopeResult:
        """
        Calculate operation scopes from table VIDs and precondition items.

        This is the low-level API for scope calculation. Use calculate_scopes_from_expression
        for expression-based calculation.

        Args:
            operation_version_id (Optional[int]): Operation version ID to use for querying existing scopes.
                                                 Used only for comparison, not for persistence unless read_only=False.
            tables_vids (Optional[List[int]]): List of table version IDs
            precondition_items (Optional[List[str]]): List of precondition item codes
            release_id (Optional[int]): Specific release ID to filter modules.
                                       If None, defaults to last release.
            expression (Optional[str]): Original expression (for result metadata)
            read_only (bool): If True, never commit to database (default: False for backward compatibility).
                            When True, operation_version_id is only used to query existing scopes.

        Returns:
            OperationScopeResult: Result containing existing and new scopes

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> result = api.calculate_scopes(
            ...     operation_version_id=1,
            ...     tables_vids=[101, 102],
            ...     release_id=42
            ... )
        """
        try:
            tables_vids = tables_vids or []
            precondition_items = precondition_items or []

            # Use a temporary operation version ID if not provided
            temp_operation_version_id = operation_version_id or -1

            # Create service and calculate scopes
            service = OperationScopeService(
                operation_version_id=temp_operation_version_id,
                session=self.session
            )

            # Use no_autoflush when not persisting to avoid premature flush attempts
            with self.session.no_autoflush:
                existing_scopes, new_scopes = service.calculate_operation_scope(
                    tables_vids=tables_vids,
                    precondition_items=precondition_items,
                    release_id=release_id,
                    table_codes=table_codes
                )

                # Analyze results
                all_scopes = existing_scopes + new_scopes
                is_cross_module = any(
                    len(scope.operation_scope_compositions) > 1
                    for scope in all_scopes
                )

                # Collect unique module versions
                module_versions = set()
                for scope in all_scopes:
                    for comp in scope.operation_scope_compositions:
                        module_versions.add(comp.modulevid)

            # Commit only if not in read-only mode and operation_version_id was provided
            if not read_only and operation_version_id is not None:
                self.session.commit()
            else:
                # Rollback if read-only or no operation version ID (temp calculation)
                self.session.rollback()

            return OperationScopeResult(
                existing_scopes=existing_scopes,
                new_scopes=new_scopes,
                total_scopes=len(all_scopes),
                is_cross_module=is_cross_module,
                module_versions=sorted(list(module_versions)),
                has_error=False,
                error_message=None,
                release_id=release_id,
                expression=expression
            )

        except SemanticError as e:
            self.session.rollback()
            return OperationScopeResult(
                has_error=True,
                error_message=str(e),
                release_id=release_id,
                expression=expression
            )
        except Exception as e:
            self.session.rollback()
            return OperationScopeResult(
                has_error=True,
                error_message=f"Unexpected error: {str(e)}",
                release_id=release_id,
                expression=expression
            )

    def get_existing_scopes(self, operation_version_id: int) -> List[OperationScope]:
        """
        Query existing operation scopes for a specific operation version.

        Args:
            operation_version_id (int): Operation version ID

        Returns:
            List[OperationScope]: List of existing scopes

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> scopes = api.get_existing_scopes(operation_version_id=1)
            >>> for scope in scopes:
            ...     print(f"Scope {scope.OperationScopeID}: {len(scope.composition)} modules")
        """
        return (
            self.session.query(OperationScope)
            .filter(OperationScope.operationvid == operation_version_id)
            .all()
        )

    def validate_scope_consistency(self, operation_version_id: int) -> bool:
        """
        Validate that all scopes for an operation are consistent.

        Args:
            operation_version_id (int): Operation version ID

        Returns:
            bool: True if scopes are consistent, False otherwise

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> is_valid = api.validate_scope_consistency(operation_version_id=1)
        """
        try:
            scopes = self.get_existing_scopes(operation_version_id)

            if not scopes:
                return True  # No scopes to validate

            # Check that all scopes have at least one module
            for scope in scopes:
                if not scope.operation_scope_compositions:
                    return False

            # Check that all module versions exist
            for scope in scopes:
                for comp in scope.operation_scope_compositions:
                    module = (
                        self.session.query(ModuleVersion)
                        .filter(ModuleVersion.modulevid == comp.modulevid)
                        .first()
                    )
                    if not module:
                        return False

            return True

        except Exception:
            return False

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session'):
            self.session.close()
        if hasattr(self, 'engine') and self.engine is not None:
            self.engine.dispose()


# Convenience functions for direct usage
def calculate_scopes_from_expression(
    expression: str,
    operation_version_id: Optional[int] = None,
    release_id: Optional[int] = None,
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    read_only: bool = True
) -> OperationScopeResult:
    """
    Convenience function to calculate operation scopes from expression.

    Args:
        expression (str): The DPM-XL expression to analyze
        operation_version_id (Optional[int]): Operation version ID to use for querying existing scopes
        release_id (Optional[int]): Specific release ID to filter modules. If None, uses last release.
        database_path (Optional[str]): Path to SQLite database
        connection_url (Optional[str]): Full SQLAlchemy connection URL
        read_only (bool): If True (default), never commit to database

    Returns:
        OperationScopeResult: Result containing existing and new scopes

    Example:
        >>> from py_dpm.api.operation_scopes import calculate_scopes_from_expression
        >>> result = calculate_scopes_from_expression(
        ...     "{tC_01.00, r0100, c0010}",
        ...     release_id=4,
        ...     database_path="./database.db"
        ... )
        >>> print(f"Total scopes: {result.total_scopes}")
    """
    api = OperationScopesAPI(database_path=database_path, connection_url=connection_url)
    return api.calculate_scopes_from_expression(expression, operation_version_id, release_id, read_only=read_only)


def get_existing_scopes(
    operation_version_id: int,
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None
) -> List[OperationScope]:
    """
    Convenience function to get existing scopes for an operation.

    Args:
        operation_version_id (int): Operation version ID
        database_path (Optional[str]): Path to SQLite database
        connection_url (Optional[str]): Full SQLAlchemy connection URL

    Returns:
        List[OperationScope]: List of existing scopes

    Example:
        >>> from py_dpm.api.operation_scopes import get_existing_scopes
        >>> scopes = get_existing_scopes(operation_version_id=1, database_path="./database.db")
    """
    api = OperationScopesAPI(database_path=database_path, connection_url=connection_url)
    return api.get_existing_scopes(operation_version_id)
