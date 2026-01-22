from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import date

from antlr4 import CommonTokenStream, InputStream
from py_dpm.dpm_xl.grammar.generated.dpm_xlLexer import dpm_xlLexer
from py_dpm.dpm_xl.grammar.generated.dpm_xlParser import dpm_xlParser
from py_dpm.dpm_xl.grammar.generated.listeners import DPMErrorListener
from py_dpm.dpm_xl.ast.constructor import ASTVisitor
from py_dpm.dpm_xl.ast.operands import OperandsChecking
from py_dpm.dpm_xl.ast.nodes import PreconditionItem
from py_dpm.dpm_xl.utils.scopes_calculator import OperationScopeService
from py_dpm.dpm.models import (
    ModuleVersion,
    OperationScope,
    TableVersion,
    HeaderVersion,
    TableVersionHeader,
    Framework,
    Module,
)
from py_dpm.dpm.utils import get_session, get_engine
from py_dpm.exceptions.exceptions import SemanticError


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


@dataclass
class FrameworkInfo:
    """
    Framework information.

    Attributes:
        framework_id (int): Framework ID
        code (str): Framework code
        name (str): Framework name
        description (str): Framework description
    """

    framework_id: int
    code: str
    name: str
    description: str


@dataclass
class OperationScopeDetailedInfo:
    """
    Operation scope with detailed module metadata.

    Attributes:
        operation_scope_id (int): Operation scope ID
        operation_vid (int): Operation version ID
        is_active (int): Active status
        severity (str): Severity level
        from_submission_date (Optional[date]): Start date for submission
        module_versions (List[ModuleVersionInfo]): List of modules with metadata
    """

    operation_scope_id: int
    operation_vid: int
    is_active: int
    severity: str
    from_submission_date: Optional[date]
    module_versions: List[Dict[str, Any]] = field(default_factory=list)


class OperationScopesAPI:
    """
    API for calculating and managing operation scopes.

    This class provides methods to calculate which module versions are involved
    in a DPM-XL operation based on table references and precondition items.
    """

    def __init__(
        self,
        database_path: Optional[str] = None,
        connection_url: Optional[str] = None,
        pool_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the Operation Scopes API.

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

    def calculate_scopes_from_expression(
        self,
        expression: str,
        operation_version_id: Optional[int] = None,
        release_id: Optional[int] = None,
        read_only: bool = False,
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
                    release_id=release_id,
                )

            # Generate AST
            ast = self.visitor.visit(parse_tree)

            # Perform operands checking to get data
            oc = OperandsChecking(
                session=self.session,
                expression=expression,
                ast=ast,
                release_id=release_id,
            )

            # Extract table VIDs, precondition items, and table codes from AST
            # Always extract table codes for cross-version scope calculation
            # (release_id will be determined later if None)
            table_vids, precondition_items, table_codes = self._extract_vids_from_ast(
                ast, oc.data, extract_codes=True
            )

            # Calculate scopes using the low-level API
            return self.calculate_scopes(
                operation_version_id=operation_version_id,
                tables_vids=table_vids,
                precondition_items=precondition_items,
                release_id=release_id,
                expression=expression,
                table_codes=table_codes,
                read_only=read_only,
            )

        except SemanticError as e:
            return OperationScopeResult(
                has_error=True,
                error_message=str(e),
                expression=expression,
                release_id=release_id,
            )
        except Exception as e:
            return OperationScopeResult(
                has_error=True,
                error_message=f"Unexpected error: {str(e)}",
                expression=expression,
                release_id=release_id,
            )

    def _extract_vids_from_ast(
        self, ast, data, extract_codes=False
    ) -> tuple[List[int], List[str], List[str]]:
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
        if "table_vid" in data.columns:
            table_vids = data["table_vid"].dropna().unique().astype(int).tolist()

            # If requested, also extract table codes for cross-version scope calculation
            if extract_codes and table_vids:
                from py_dpm.dpm.models import TableVersion

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
            if hasattr(node, "__dict__"):
                for attr_value in vars(node).values():
                    if hasattr(attr_value, "__class__") and hasattr(
                        attr_value.__class__, "__module__"
                    ):
                        if "ASTObjects" in attr_value.__class__.__module__:
                            walk_ast(attr_value)
                    elif isinstance(attr_value, list):
                        for item in attr_value:
                            if hasattr(item, "__class__") and hasattr(
                                item.__class__, "__module__"
                            ):
                                if "ASTObjects" in item.__class__.__module__:
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
        read_only: bool = False,
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
                operation_version_id=temp_operation_version_id, session=self.session
            )

            # Use no_autoflush when not persisting to avoid premature flush attempts
            with self.session.no_autoflush:
                existing_scopes, new_scopes = service.calculate_operation_scope(
                    tables_vids=tables_vids,
                    precondition_items=precondition_items,
                    release_id=release_id,
                    table_codes=table_codes,
                )

                # Analyze results
                all_scopes = existing_scopes + new_scopes
                is_cross_module = any(
                    len(scope.operation_scope_compositions) > 1 for scope in all_scopes
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
                expression=expression,
            )

        except SemanticError as e:
            self.session.rollback()
            return OperationScopeResult(
                has_error=True,
                error_message=str(e),
                release_id=release_id,
                expression=expression,
            )
        except Exception as e:
            self.session.rollback()
            return OperationScopeResult(
                has_error=True,
                error_message=f"Unexpected error: {str(e)}",
                release_id=release_id,
                expression=expression,
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

    def get_scopes_with_metadata(
        self, operation_version_id: int
    ) -> List[OperationScopeDetailedInfo]:
        """
        Get operation scopes with detailed module metadata.

        Args:
            operation_version_id (int): Operation version ID

        Returns:
            List[OperationScopeDetailedInfo]: List of scopes with enriched module information

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> scopes = api.get_scopes_with_metadata(operation_version_id=1)
            >>> for scope in scopes:
            ...     print(f"Scope {scope.operation_scope_id}:")
            ...     for module in scope.module_versions:
            ...         print(f"  - {module.code}: {module.name}")
        """
        scopes = self.get_existing_scopes(operation_version_id)
        result = []

        for scope in scopes:
            # Get module metadata for each scope
            module_infos = []
            for comp in scope.operation_scope_compositions:
                module = (
                    self.session.query(ModuleVersion)
                    .filter(ModuleVersion.modulevid == comp.modulevid)
                    .first()
                )
                if module:
                    module_infos.append(
                        {
                            "module_vid": module.modulevid,
                            "code": module.code or "",
                            "name": module.name or "",
                            "description": module.description or "",
                            "version_number": module.versionnumber or "",
                            "from_reference_date": module.fromreferencedate,
                            "to_reference_date": module.toreferencedate,
                        }
                    )

            result.append(
                OperationScopeDetailedInfo(
                    operation_scope_id=scope.operationscopeid,
                    operation_vid=scope.operationvid,
                    is_active=scope.isactive,
                    severity=scope.severity or "",
                    from_submission_date=scope.fromsubmissiondate,
                    module_versions=module_infos,
                )
            )

        return result

    def get_scopes_with_metadata_from_expression(
        self, expression: str, release_id: Optional[int] = None
    ) -> List[OperationScopeDetailedInfo]:
        """
        Calculate operation scopes from expression and return with detailed metadata.

        This method calculates scopes from the expression without persisting to database.

        Args:
            expression (str): The DPM-XL expression to analyze
            release_id (Optional[int]): Specific release ID to filter modules.
                                       If None, defaults to last release.

        Returns:
            List[OperationScopeDetailedInfo]: List of calculated scopes with metadata

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> scopes = api.get_scopes_with_metadata_from_expression(
            ...     "{tC_01.00, r0100, c0010} + {tC_02.00, r0200, c0020}",
            ...     release_id=42
            ... )
        """
        # Calculate scopes in read-only mode
        scope_result = self.calculate_scopes_from_expression(
            expression=expression, release_id=release_id, read_only=True
        )

        if scope_result.has_error:
            return []

        # Convert to detailed info
        result = []
        all_scopes = scope_result.existing_scopes + scope_result.new_scopes

        for scope in all_scopes:
            module_infos = []
            for comp in scope.operation_scope_compositions:
                module = (
                    self.session.query(ModuleVersion)
                    .filter(ModuleVersion.modulevid == comp.modulevid)
                    .first()
                )
                if module:
                    module_infos.append(
                        {
                            "module_vid": module.modulevid,
                            "code": module.code or "",
                            "name": module.name or "",
                            "description": module.description or "",
                            "version_number": module.versionnumber or "",
                            "from_reference_date": module.fromreferencedate,
                            "to_reference_date": module.toreferencedate,
                        }
                    )

            result.append(
                OperationScopeDetailedInfo(
                    operation_scope_id=scope.operationscopeid,
                    operation_vid=scope.operationvid,
                    is_active=scope.isactive,
                    severity=scope.severity or "",
                    from_submission_date=scope.fromsubmissiondate,
                    module_versions=module_infos,
                )
            )

        return result

    def get_tables_with_metadata(
        self, operation_version_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get all tables involved in operation scopes with metadata.

        Args:
            operation_version_id (int): Operation version ID

        Returns:
            List[Dict[str, Any]]: List of unique tables with metadata

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> tables = api.get_tables_with_metadata(operation_version_id=1)
            >>> for table in tables:
            ...     print(f"{table['code']}: {table['name']}")
        """
        scopes = self.get_existing_scopes(operation_version_id)

        # Collect unique module VIDs
        module_vids = set()
        for scope in scopes:
            for comp in scope.operation_scope_compositions:
                module_vids.add(comp.modulevid)

        if not module_vids:
            return []

        # Query tables from these modules
        from py_dpm.dpm.models import ModuleVersionComposition

        tables_query = (
            self.session.query(
                TableVersion,
                ModuleVersionComposition.modulevid,
                ModuleVersion.code,
                ModuleVersion.name,
                ModuleVersion.versionnumber,
            )
            .join(
                ModuleVersionComposition,
                ModuleVersionComposition.tablevid == TableVersion.tablevid,
            )
            .join(
                ModuleVersion,
                ModuleVersion.modulevid == ModuleVersionComposition.modulevid,
            )
            .filter(ModuleVersionComposition.modulevid.in_(module_vids))
            .distinct()
            .order_by(TableVersion.code)
        )

        result = []
        for (
            table,
            module_vid,
            module_code,
            module_name,
            module_version,
        ) in tables_query.all():
            result.append(
                {
                    "table_vid": table.tablevid,
                    "code": table.code or "",
                    "name": table.name or "",
                    "description": table.description or "",
                    "module_vid": module_vid,
                    "module_code": module_code or "",
                    "module_name": module_name or "",
                    "module_version": module_version or "",
                }
            )

        return result

    def get_tables_with_metadata_from_expression(
        self, expression: str, release_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tables from expression with metadata.

        This method parses the expression and returns ONLY the tables that are
        actually referenced in the expression, not all tables from the modules.

        Args:
            expression (str): The DPM-XL expression to analyze
            release_id (Optional[int]): Specific release ID to filter modules

        Returns:
            List[Dict[str, Any]]: List of tables referenced in the expression with metadata

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> tables = api.get_tables_with_metadata_from_expression(
            ...     "{tC_01.00, r0100, c0010} + {tC_02.00, r0200, c0020}"
            ... )
            >>> # Returns only tables C_01.00 and C_02.00, not all module tables
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
                return []

            # Generate AST
            ast = self.visitor.visit(parse_tree)

            # Perform operands checking to get data
            oc = OperandsChecking(
                session=self.session,
                expression=expression,
                ast=ast,
                release_id=release_id,
            )

            # Extract table VIDs referenced in the expression
            table_vids, _, _ = self._extract_vids_from_ast(
                ast, oc.data, extract_codes=False
            )

            if not table_vids:
                return []

            # Query only the specific tables referenced in the expression
            from py_dpm.dpm.models import ModuleVersionComposition

            tables_query = (
                self.session.query(
                    TableVersion,
                    ModuleVersionComposition.modulevid,
                    ModuleVersion.code,
                    ModuleVersion.name,
                    ModuleVersion.versionnumber,
                )
                .join(
                    ModuleVersionComposition,
                    ModuleVersionComposition.tablevid == TableVersion.tablevid,
                )
                .join(
                    ModuleVersion,
                    ModuleVersion.modulevid == ModuleVersionComposition.modulevid,
                )
                .filter(TableVersion.tablevid.in_(table_vids))
                .distinct()
                .order_by(TableVersion.code)
            )

            result = []
            for (
                table,
                module_vid,
                module_code,
                module_name,
                module_version,
            ) in tables_query.all():
                result.append(
                    {
                        "table_vid": table.tablevid,
                        "code": table.code or "",
                        "name": table.name or "",
                        "description": table.description or "",
                        "module_vid": module_vid,
                        "module_code": module_code or "",
                        "module_name": module_name or "",
                        "module_version": module_version or "",
                    }
                )

            return result

        except SemanticError:
            return []
        except Exception:
            return []

    def get_headers_with_metadata(
        self, operation_version_id: int, table_vid: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get headers from tables in operation scopes with metadata.

        Args:
            operation_version_id (int): Operation version ID
            table_vid (Optional[int]): Filter by specific table VID. If None, returns all headers.

        Returns:
            List[Dict[str, Any]]: List of headers with metadata

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> # Get all headers
            >>> headers = api.get_headers_with_metadata(operation_version_id=1)
            >>> # Get headers for specific table
            >>> headers = api.get_headers_with_metadata(operation_version_id=1, table_vid=101)
        """
        scopes = self.get_existing_scopes(operation_version_id)

        # Collect unique module VIDs
        module_vids = set()
        for scope in scopes:
            for comp in scope.operation_scope_compositions:
                module_vids.add(comp.modulevid)

        if not module_vids:
            return []

        # Get table VIDs from modules
        from py_dpm.dpm.models import ModuleVersionComposition, Header

        table_vids_query = (
            self.session.query(ModuleVersionComposition.tablevid)
            .filter(ModuleVersionComposition.modulevid.in_(module_vids))
            .distinct()
        )

        if table_vid is not None:
            # Filter by specific table
            table_vids_query = table_vids_query.filter(
                ModuleVersionComposition.tablevid == table_vid
            )

        table_vids = [row[0] for row in table_vids_query.all()]

        if not table_vids:
            return []

        # Query headers for these tables with table information
        headers_query = (
            self.session.query(
                HeaderVersion,
                TableVersionHeader.tablevid,
                Header.direction,
                TableVersion.code,
                TableVersion.name,
            )
            .join(
                TableVersionHeader,
                TableVersionHeader.headervid == HeaderVersion.headervid,
            )
            .join(Header, Header.headerid == TableVersionHeader.headerid)
            .join(TableVersion, TableVersion.tablevid == TableVersionHeader.tablevid)
            .filter(TableVersionHeader.tablevid.in_(table_vids))
            .order_by(TableVersionHeader.tablevid, HeaderVersion.code)
            .distinct()
        )

        result = []
        for (
            header_version,
            table_vid_val,
            direction,
            table_code,
            table_name,
        ) in headers_query.all():
            # Map direction to readable type (DPM uses X=Row, Y=Column, Z=Sheet)
            header_type_map = {"X": "Row", "Y": "Column", "Z": "Sheet"}
            header_type = header_type_map.get(direction, direction or "Unknown")

            result.append(
                result.append(
                    {
                        "header_vid": header_version.headervid,
                        "code": header_version.code or "",
                        "label": header_version.label or "",
                        "header_type": header_type,
                        "table_vid": table_vid_val,
                        "table_code": table_code or "",
                        "table_name": table_name or "",
                    }
                )
            )

        return result

    def get_headers_with_metadata_from_expression(
        self,
        expression: str,
        table_vid: Optional[int] = None,
        release_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get headers from expression with metadata.

        This method parses the expression and returns ONLY the headers (rows, columns, sheets)
        that are actually referenced in the expression, not all headers from the tables.
        Wildcards (r*, c*, s*) are expanded to the actual header codes they reference.

        Args:
            expression (str): The DPM-XL expression to analyze
            table_vid (Optional[int]): Filter by specific table VID
            release_id (Optional[int]): Specific release ID to filter modules

        Returns:
            List[Dict[str, Any]]: List of headers referenced in the expression with metadata

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> headers = api.get_headers_with_metadata_from_expression(
            ...     "{tC_01.00, r0100, c0010}",
            ...     table_vid=101
            ... )
            >>> # Returns only headers r0100 and c0010, not all table headers
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
                return []

            # Generate AST
            ast = self.visitor.visit(parse_tree)

            # Perform operands checking to get data
            oc = OperandsChecking(
                session=self.session,
                expression=expression,
                ast=ast,
                release_id=release_id,
            )

            # Extract table VIDs referenced in the expression
            table_vids, _, _ = self._extract_vids_from_ast(
                ast, oc.data, extract_codes=False
            )

            if not table_vids:
                return []

            # Apply table_vid filter if specified
            if table_vid is not None:
                table_vids = [vid for vid in table_vids if vid == table_vid]
                if not table_vids:
                    return []

            # Extract header codes from the data DataFrame
            # oc.data contains the resolved codes (wildcards already expanded)
            # IMPORTANT: The row_code, column_code, sheet_code in oc.data reflect how headers
            # are USED in the expression syntax (r=Row, c=Column, s=Sheet), which may differ
            # from the Header.direction field in the database (some tables may be transposed).
            # We return headers based on their USAGE in the expression, not their catalog definition.
            row_codes = set(oc.data["row_code"].dropna().unique().tolist())
            column_codes = set(oc.data["column_code"].dropna().unique().tolist())
            sheet_codes = set(oc.data["sheet_code"].dropna().unique().tolist())

            # Create mapping: code -> usage dimension(s) in the expression
            # The same code might be used in multiple dimensions
            code_usage = {}
            for code in row_codes:
                if code not in code_usage:
                    code_usage[code] = set()
                code_usage[code].add("Row")
            for code in column_codes:
                if code not in code_usage:
                    code_usage[code] = set()
                code_usage[code].add("Column")
            for code in sheet_codes:
                if code not in code_usage:
                    code_usage[code] = set()
                code_usage[code].add("Sheet")

            if not code_usage:
                return []

            all_header_codes = set(code_usage.keys())

            # Query headers - get all headers with matching codes
            # Query headers - get all headers with matching codes
            # Note: We don't filter by Header.direction because tables may be transposed
            from py_dpm.dpm.models import Header
            from sqlalchemy import and_

            headers_query = (
                self.session.query(
                    HeaderVersion,
                    TableVersionHeader.tablevid,
                    Header.direction,
                    TableVersion.code,
                    TableVersion.name,
                )
                .join(
                    TableVersionHeader,
                    TableVersionHeader.headervid == HeaderVersion.headervid,
                )
                .join(Header, Header.headerid == HeaderVersion.headerid)
                .join(
                    TableVersion, TableVersion.tablevid == TableVersionHeader.tablevid
                )
                .filter(
                    and_(
                        TableVersionHeader.tablevid.in_(table_vids),
                        HeaderVersion.code.in_(all_header_codes),
                    )
                )
                .distinct()
            )

            result = []
            seen = set()  # Track (code, usage_type, table_vid) to avoid duplicates

            for (
                header_version,
                table_vid_val,
                direction,
                table_code,
                table_name,
            ) in headers_query.all():
                code = header_version.code or ""

                # For each usage dimension of this code in the expression
                if code in code_usage:
                    for usage_type in code_usage[code]:
                        # Avoid duplicates
                        key = (code, usage_type, table_vid_val)
                        if key in seen:
                            continue
                        seen.add(key)

                        # Return header with usage type from expression, not catalog direction
                        # Return header with usage type from expression, not catalog direction
                        result.append(
                            {
                                "header_vid": header_version.headervid,
                                "code": code,
                                "label": header_version.label or "",
                                "header_type": usage_type,  # Usage in expression: Row, Column, or Sheet
                                "table_vid": table_vid_val,
                                "table_code": table_code or "",
                                "table_name": table_name or "",
                            }
                        )
                        break  # Only add each header once per code (we'll get multiple if used in multiple dims)

            return result

        except SemanticError:
            return []
        except Exception:
            return []

    def get_frameworks_with_metadata(
        self, operation_version_id: int
    ) -> List[FrameworkInfo]:
        """
        Get frameworks from operation scopes with metadata.

        Args:
            operation_version_id (int): Operation version ID

        Returns:
            List[FrameworkInfo]: List of frameworks with metadata

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> frameworks = api.get_frameworks_with_metadata(operation_version_id=1)
            >>> for fw in frameworks:
            ...     print(f"{fw.code}: {fw.name}")
        """
        scopes = self.get_existing_scopes(operation_version_id)

        # Collect unique module VIDs
        module_vids = set()
        for scope in scopes:
            for comp in scope.operation_scope_compositions:
                module_vids.add(comp.modulevid)

        if not module_vids:
            return []

        # Query frameworks via modules
        frameworks_query = (
            self.session.query(Framework)
            .join(Module, Module.frameworkid == Framework.frameworkid)
            .join(ModuleVersion, ModuleVersion.moduleid == Module.moduleid)
            .filter(ModuleVersion.modulevid.in_(module_vids))
            .distinct()
            .order_by(Framework.code)
        )

        result = []
        for framework in frameworks_query.all():
            result.append(
                FrameworkInfo(
                    framework_id=framework.frameworkid,
                    code=framework.code or "",
                    name=framework.name or "",
                    description=framework.description or "",
                )
            )

        return result

    def get_frameworks_with_metadata_from_expression(
        self, expression: str, release_id: Optional[int] = None
    ) -> List[FrameworkInfo]:
        """
        Get frameworks from expression with metadata.

        Args:
            expression (str): The DPM-XL expression to analyze
            release_id (Optional[int]): Specific release ID to filter modules

        Returns:
            List[FrameworkInfo]: List of frameworks with metadata

        Example:
            >>> from py_dpm.api import OperationScopesAPI
            >>> api = OperationScopesAPI()
            >>> frameworks = api.get_frameworks_with_metadata_from_expression(
            ...     "{tC_01.00, r0100, c0010}"
            ... )
        """
        # Calculate scopes in read-only mode
        scope_result = self.calculate_scopes_from_expression(
            expression=expression, release_id=release_id, read_only=True
        )

        if scope_result.has_error:
            return []

        # Collect module VIDs
        module_vids = set(scope_result.module_versions)

        if not module_vids:
            return []

        # Query frameworks via modules
        frameworks_query = (
            self.session.query(Framework)
            .join(Module, Module.frameworkid == Framework.frameworkid)
            .join(ModuleVersion, ModuleVersion.moduleid == Module.moduleid)
            .filter(ModuleVersion.modulevid.in_(module_vids))
            .distinct()
            .order_by(Framework.code)
        )

        result = []
        for framework in frameworks_query.all():
            result.append(
                FrameworkInfo(
                    framework_id=framework.frameworkid,
                    code=framework.code or "",
                    name=framework.name or "",
                    description=framework.description or "",
                )
            )

        return result

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, "session"):
            self.session.close()
        if hasattr(self, "engine") and self.engine is not None:
            self.engine.dispose()

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
def calculate_scopes_from_expression(
    expression: str,
    operation_version_id: Optional[int] = None,
    release_id: Optional[int] = None,
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    read_only: bool = True,
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
        >>> from py_dpm.api.dpm_xl.operation_scopes import calculate_scopes_from_expression
        >>> result = calculate_scopes_from_expression(
        ...     "{tC_01.00, r0100, c0010}",
        ...     release_id=4,
        ...     database_path="./database.db"
        ... )
        >>> print(f"Total scopes: {result.total_scopes}")
    """
    api = OperationScopesAPI(database_path=database_path, connection_url=connection_url)
    return api.calculate_scopes_from_expression(
        expression, operation_version_id, release_id, read_only=read_only
    )


def get_existing_scopes(
    operation_version_id: int,
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
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
        >>> from py_dpm.api.dpm_xl.operation_scopes import get_existing_scopes
        >>> scopes = get_existing_scopes(operation_version_id=1, database_path="./database.db")
    """
    api = OperationScopesAPI(database_path=database_path, connection_url=connection_url)
    return api.get_existing_scopes(operation_version_id)
