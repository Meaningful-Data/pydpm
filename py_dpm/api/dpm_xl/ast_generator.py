#!/usr/bin/env python3
"""
AST Generator API - Simplified interface for external packages

This module provides a clean, abstracted interface for generating ASTs from DPM-XL expressions
without exposing internal complexity or version compatibility issues.
"""

from typing import Dict, Any, Optional, List, Union, Tuple
from pathlib import Path
import json
from datetime import datetime
from py_dpm.api.dpm_xl.syntax import SyntaxAPI
from py_dpm.api.dpm_xl.semantic import SemanticAPI



class ASTGeneratorAPI:
    """
    Simplified AST Generator for external packages.

    Provides three levels of AST generation:

    1. **Basic AST** (parse_expression):
       - Syntax parsing only, no database required
       - Returns: Clean AST dictionary with version compatibility normalization
       - Use for: Syntax validation, basic AST analysis

    2. **Complete AST** (generate_complete_ast):
       - Requires database connection
       - Performs full semantic validation and operand checking
       - Returns: AST with data fields populated (datapoint IDs, operand references)
       - Use for: AST analysis with complete metadata, matching json_scripts/*.json format

    3. **Validations Script** (generate_validations_script):
       - Requires database connection
       - Extends complete AST with framework structure for execution engines
       - Returns: Engine-ready AST with operations, variables, tables, preconditions sections
       - Use for: Business rule execution engines, validation frameworks

    Handles all internal complexity including:
    - Version compatibility
    - Context processing
    - Database integration
    - Error handling
    - JSON serialization
    """

    def __init__(self, database_path: Optional[str] = None,
                 connection_url: Optional[str] = None,
                 pool_config: Optional[Dict[str, Any]] = None,
                 compatibility_mode: str = "auto",
                 enable_semantic_validation: bool = False):
        """
        Initialize AST Generator.

        Args:
            database_path: Optional path to SQLite data dictionary database
            connection_url: Optional SQLAlchemy connection URL for PostgreSQL
            pool_config: Connection pool configuration for PostgreSQL/MySQL
            compatibility_mode: "auto", "3.1.0", "4.0.0", or "current"
            enable_semantic_validation: Enable semantic validation (requires database)
        """
        self.syntax_api = SyntaxAPI()
        self.semantic_api = SemanticAPI(
            database_path=database_path,
            connection_url=connection_url,
            pool_config=pool_config
        ) if enable_semantic_validation else None
        self.database_path = database_path
        self.connection_url = connection_url
        self.pool_config = pool_config
        self.compatibility_mode = compatibility_mode
        self.enable_semantic = enable_semantic_validation

        # Internal version handling
        self._version_normalizers = self._setup_version_normalizers()

    def parse_expression(self, expression: str) -> Dict[str, Any]:
        """
        Parse DPM-XL expression into clean AST format (Level 1 - Basic AST).

        Performs syntax parsing only, no database required. Returns a clean AST dictionary
        with version compatibility normalization applied.

        **What you get:**
        - Clean AST structure (syntax tree)
        - Context information (if WITH clause present)
        - Version compatibility normalization

        **What you DON'T get:**
        - Data fields (datapoint IDs, operand references) - use generate_complete_ast()
        - Framework structure - use generate_validations_script()

        Args:
            expression: DPM-XL expression string

        Returns:
            Dictionary containing:
            - success (bool): Whether parsing succeeded
            - ast (dict): Clean AST dictionary
            - context (dict): Context information (if WITH clause present)
            - error (str): Error message (if failed)
            - metadata (dict): Additional information (expression type, compatibility mode)
        """
        try:
            # Parse with syntax API
            raw_ast = self.syntax_api.parse_expression(expression)

            # Extract context and expression
            context, expr_ast = self._extract_components(raw_ast)

            # Convert to clean JSON format
            ast_dict = self._to_clean_json(expr_ast, context)

            # Apply version normalization
            normalized_ast = self._normalize_for_compatibility(ast_dict)

            # Optional semantic validation
            semantic_info = None
            if self.enable_semantic and self.semantic_api:
                semantic_info = self._validate_semantics(expression)

            return {
                'success': True,
                'ast': normalized_ast,
                'context': self._serialize_context(context),
                'error': None,
                'metadata': {
                    'has_context': context is not None,
                    'expression_type': normalized_ast.get('class_name', 'Unknown'),
                    'semantic_info': semantic_info,
                    'compatibility_mode': self.compatibility_mode
                }
            }

        except Exception as e:
            return {
                'success': False,
                'ast': None,
                'context': None,
                'error': str(e),
                'metadata': {
                    'error_type': type(e).__name__,
                    'original_expression': expression[:100] + "..." if len(expression) > 100 else expression
                }
            }

    def validate_expression(self, expression: str) -> Dict[str, Any]:
        """
        Validate expression syntax without full parsing.

        Args:
            expression: DPM-XL expression string

        Returns:
            Dictionary containing validation result
        """
        try:
            self.syntax_api.parse_expression(expression)
            return {
                'valid': True,
                'error': None,
                'expression': expression
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'expression': expression
            }

    def get_expression_info(self, expression: str) -> Dict[str, Any]:
        """
        Get comprehensive information about an expression.

        Args:
            expression: DPM-XL expression string

        Returns:
            Dictionary with expression analysis
        """
        result = self.parse_expression(expression)
        if not result['success']:
            return result

        ast = result['ast']
        context = result['context']

        # Analyze AST structure
        analysis = {
            'variable_references': self._extract_variables(ast),
            'constants': self._extract_constants(ast),
            'operations': self._extract_operations(ast),
            'has_aggregations': self._has_aggregations(ast),
            'has_conditionals': self._has_conditionals(ast),
            'complexity_score': self._calculate_complexity(ast),
            'context_info': context
        }

        result['analysis'] = analysis
        return result

    # ============================================================================
    # Complete AST Generation (requires database)
    # ============================================================================

    def generate_complete_ast(
        self,
        expression: str,
        release_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete AST with all data fields populated (Level 2).

        This method performs full semantic validation and operand checking using the database,
        populating datapoint IDs and operand references in the AST. The result matches the
        format found in json_scripts/*.json files.

        **What you get:**
        - Pure AST with data fields (datapoint IDs, operand references)
        - Semantic validation results
        - Context information

        **What you DON'T get:**
        - Framework structure (operations, variables, tables, preconditions)
        - For that, use generate_enriched_ast() instead

        Args:
            expression: DPM-XL expression string
            release_id: Optional release ID to filter database lookups by specific release.
                If None, uses all available data (release-agnostic).

        Returns:
            dict with keys:
                - success (bool): Whether generation succeeded
                - ast (dict): Complete AST with data fields
                - context (dict): Context information (table, rows, columns, etc.)
                - error (str): Error message if failed
                - data_populated (bool): Whether data fields were populated
                - semantic_result: Semantic validation result object
        """
        try:
            from py_dpm.dpm.utils import get_engine
            from py_dpm.dpm_xl.utils.serialization import ASTToJSONVisitor

            # Initialize database connection if explicitly provided, to surface connection errors early
            try:
                get_engine(database_path=self.database_path, connection_url=self.connection_url)
            except Exception as e:
                return {
                    "success": False,
                    "ast": None,
                    "context": None,
                    "error": f"Database connection failed: {e}",
                    "data_populated": False,
                }

            # Create or reuse semantic API for validation
            if not self.semantic_api:
                self.semantic_api = SemanticAPI(
                    database_path=self.database_path,
                    connection_url=self.connection_url
                )

            semantic_result = self.semantic_api.validate_expression(
                expression, release_id=release_id
            )

            # If semantic validation failed, return structured error
            if not semantic_result.is_valid:
                return {
                    "success": False,
                    "ast": None,
                    "context": None,
                    "error": semantic_result.error_message,
                    "data_populated": False,
                    "semantic_result": semantic_result,
                }

            ast_root = getattr(self.semantic_api, "ast", None)

            if ast_root is None:
                return {
                    "success": False,
                    "ast": None,
                    "context": None,
                    "error": "Semantic validation did not generate AST",
                    "data_populated": False,
                    "semantic_result": semantic_result,
                }

            # Extract components
            actual_ast, context = self._extract_complete_components(ast_root)

            # Convert to JSON using the ASTToJSONVisitor
            visitor = ASTToJSONVisitor(context)
            ast_dict = visitor.visit(actual_ast)

            # Check if data fields were populated
            data_populated = self._check_data_fields_populated(ast_dict)

            # Serialize context
            context_dict = self._serialize_context(context)

            return {
                "success": True,
                "ast": ast_dict,
                "context": context_dict,
                "error": None,
                "data_populated": data_populated,
                "semantic_result": semantic_result,
            }

        except Exception as e:
            return {
                "success": False,
                "ast": None,
                "context": None,
                "error": f"API error: {str(e)}",
                "data_populated": False,
            }

    # ============================================================================
    # Enriched AST Generation (requires database)
    # ============================================================================

    def _normalize_expressions_input(
        self,
        expressions: Union[str, List[Tuple[str, str, Optional[str]]]]
    ) -> List[Tuple[str, str, Optional[str]]]:
        """
        Normalize input to list of (expression, operation_code, precondition) tuples.

        Supports:
        - Single expression string: "expr" -> [("expr", "default_code", None)]
        - List of tuples: [("expr1", "op1", "precond1"), ("expr2", "op2", None)]

        Args:
            expressions: Either a single expression string or a list of tuples

        Returns:
            List of (expression, operation_code, precondition) tuples
        """
        if isinstance(expressions, str):
            return [(expressions, "default_code", None)]
        return expressions

    def generate_validations_script(
        self,
        expressions: Union[str, List[Tuple[str, str, Optional[str]]]],
        release_code: Optional[str] = None,
        table_context: Optional[Dict[str, Any]] = None,
        release_id: Optional[int] = None,
        output_path: Optional[Union[str, Path]] = None,
        primary_module_vid: Optional[int] = None,
        module_code: Optional[str] = None,
        preferred_module_dependencies: Optional[List[str]] = None,
        module_version_number: Optional[str] = None,
        add_all_tables: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate validations script with engine-ready AST and framework structure.

        This method generates the complete validations script by wrapping ASTs in an engine-ready
        framework structure with operations, variables, tables, and preconditions sections.
        This is the format required by business rule execution engines.

        Supports both single expressions (for backward compatibility) and multiple
        expression/operation/precondition tuples for generating scripts with multiple operations.

        **What you get:**
        - Complete AST with data fields PLUS:
        - Framework structure: operations, variables, tables, preconditions
        - Module metadata: version, release info, dates
        - Dependency information (including cross-module dependencies)
        - Coordinates (x/y/z) added to data entries

        **Typical use case:**
        - Feeding AST to business rule execution engines
        - Validation framework integration
        - Production rule processing
        - Module exports with cross-module dependency tracking

        Args:
            expressions: Either a single DPM-XL expression string (backward compatible),
                or a list of tuples: [(expression, operation_code, precondition), ...].
                Each tuple contains:
                - expression (str): The DPM-XL expression (required)
                - operation_code (str): The operation code (required)
                - precondition (Optional[str]): Optional precondition reference (e.g., {v_F_44_04})
            release_code: Optional release code (e.g., "4.0", "4.1", "4.2").
                Mutually exclusive with release_id and module_version_number.
            table_context: Optional table context dict with keys: 'table', 'columns', 'rows', 'sheets', 'default', 'interval'
            release_id: Optional release ID to filter database lookups by specific release.
                Mutually exclusive with release_code and module_version_number.
            output_path: Optional path (string or Path) to save the enriched_ast as JSON file.
                If provided, the enriched_ast will be automatically saved to this location.
            primary_module_vid: Optional module version ID of the module being exported.
                When provided, enables detection of cross-module dependencies - tables from
                other modules will be identified and added to dependency_modules and
                cross_instance_dependencies fields. If None, cross-module detection uses
                the first table's module as the primary module.
            module_code: Optional module code (e.g., "FINREP9") to specify the main module.
                The main module's URL will be used as the root key of the output.
                If provided, this takes precedence over primary_module_vid for determining
                the main module.
            preferred_module_dependencies: Optional list of module codes to prefer when
                multiple dependency scopes are possible. If a table belongs to multiple modules,
                the module in this list will be selected as the dependency.
            module_version_number: Optional module version number (e.g., "4.1.0") to specify
                which version of the module to use. Requires module_code to be specified.
                Mutually exclusive with release_code and release_id.
                If none of release_code, release_id, or module_version_number are provided,
                the latest (active) module version is used.
            add_all_tables: If True (default), include all tables and variables from the
                module version in the output, regardless of whether they are referenced in
                the validations. If False, only include tables and variables that are
                actually referenced in the expressions.

        Returns:
            dict: {
                'success': bool,
                'enriched_ast': dict,  # Engine-ready AST with framework structure
                'error': str           # Error message if failed
            }

        Raises:
            ValueError: If more than one of release_id, release_code, or module_version_number
                are specified; if module_version_number is specified without module_code; or if
                no operation scope belongs to the specified module.

        Example:
            >>> generator = ASTGeneratorAPI(database_path="data.db")
            >>> # Single expression
            >>> result = generator.generate_validations_script(
            ...     "{tF_01.00, r0010, c0010}",
            ...     release_code="4.2",
            ... )
            >>>
            >>> # Multiple expressions with operations and preconditions
            >>> result = generator.generate_validations_script(
            ...     [
            ...         ("{tF_01.00, r0010, c0010} = 0", "v1234_m", None),
            ...         ("{tF_01.00, r0020, c0010} > 0", "v1235_m", "{v_F_44_04}"),
            ...         ("{tF_01.00, r0030, c0010} >= 0", "v1236_m", "{v_F_44_04}"),  # Same precondition, deduplicated
            ...     ],
            ...     release_code="4.2",
            ...     module_code="FINREP9",
            ... )
        """
        # Validate mutually exclusive parameters
        version_params = [release_id, release_code, module_version_number]
        if sum(p is not None for p in version_params) > 1:
            raise ValueError(
                "Specify a maximum of one of release_id, release_code, or module_version_number."
            )

        # Validate module_version_number requires module_code
        if module_version_number is not None and module_code is None:
            raise ValueError(
                "module_version_number requires module_code to be specified."
            )

        # Resolve version parameters to release_id
        effective_release_id = release_id
        effective_release_code = release_code

        if release_code is not None:
            effective_release_id = self._resolve_release_code(release_code)
        elif module_version_number is not None:
            # Resolve module_version_number to release_id
            effective_release_id, effective_release_code = self._resolve_module_version(
                module_code, module_version_number
            )

        # Normalize input to list of tuples
        expression_tuples = self._normalize_expressions_input(expressions)

        try:
            # Enrich with framework structure for multiple expressions
            enriched_ast = self._enrich_ast_with_metadata_multi(
                expression_tuples=expression_tuples,
                table_context=table_context,
                release_code=effective_release_code,
                release_id=effective_release_id,
                primary_module_vid=primary_module_vid,
                module_code=module_code,
                preferred_module_dependencies=preferred_module_dependencies,
                add_all_tables=add_all_tables,
            )

            # Save to file if output_path is provided
            if output_path is not None:
                path = Path(output_path) if isinstance(output_path, str) else output_path
                # Create parent directories if they don't exist
                path.parent.mkdir(parents=True, exist_ok=True)
                # Save enriched_ast as JSON
                with open(path, "w") as f:
                    json.dump(enriched_ast, f, indent=4)

            return {"success": True, "enriched_ast": enriched_ast, "error": None}

        except Exception as e:
            return {
                "success": False,
                "enriched_ast": None,
                "error": f"Enrichment error: {str(e)}",
            }

    # Internal helper methods

    def _extract_components(self, raw_ast):
        """Extract context and expression from raw AST."""
        if hasattr(raw_ast, 'children') and len(raw_ast.children) > 0:
            child = raw_ast.children[0]
            if hasattr(child, 'expression') and hasattr(child, 'partial_selection'):
                return child.partial_selection, child.expression
            else:
                return None, child
        return None, raw_ast

    def _to_clean_json(self, ast_node, context=None):
        """Convert AST node to clean JSON format."""
        # Import the serialization function from utils
        from py_dpm.dpm_xl.utils.serialization import serialize_ast

        # Use the serialize_ast function which handles all AST node types properly
        return serialize_ast(ast_node)

    def _serialize_context(self, context):
        """Serialize context to clean dictionary."""
        if not context:
            return None

        return {
            'table': getattr(context, 'table', None),
            'rows': getattr(context, 'rows', None),
            'columns': getattr(context, 'cols', None),
            'sheets': getattr(context, 'sheets', None),
            'default': getattr(context, 'default', None),
            'interval': getattr(context, 'interval', None)
        }

    def _normalize_for_compatibility(self, ast_dict):
        """Apply version compatibility normalization."""
        if self.compatibility_mode == "auto":
            # Auto-detect and normalize
            return self._auto_normalize(ast_dict)
        elif self.compatibility_mode in self._version_normalizers:
            normalizer = self._version_normalizers[self.compatibility_mode]
            return normalizer(ast_dict)
        else:
            return ast_dict

    def _setup_version_normalizers(self):
        """Setup version-specific normalizers."""
        return {
            "3.1.0": self._normalize_v3_1_0,
            "4.0.0": self._normalize_v4_0_0,
            "current": lambda x: x
        }

    def _normalize_v3_1_0(self, ast_dict):
        """Normalize AST for version 3.1.0 compatibility."""
        if not isinstance(ast_dict, dict):
            return ast_dict

        normalized = {}
        for key, value in ast_dict.items():
            # Handle Scalar item naming for v3.1.0
            if key == 'item' and isinstance(value, str) and ':' in value:
                namespace, code = value.split(':', 1)
                if namespace.endswith('_qEC'):
                    namespace = namespace.replace('_qEC', '_EC')
                if code.startswith('qx'):
                    code = code[1:]
                normalized[key] = f"{namespace}:{code}"

            # Handle TimeShiftOp field mapping
            elif ast_dict.get('class_name') == 'TimeShiftOp':
                if key == 'component':
                    normalized['reference_period'] = value
                    continue
                elif key == 'shift_number' and not isinstance(value, dict):
                    # Convert to Constant format for v3.1.0
                    normalized[key] = {
                        'class_name': 'Constant',
                        'type_': 'Integer',
                        'value': int(value)
                    }
                    continue
                elif key == 'period_indicator' and not isinstance(value, dict):
                    # Convert to Constant format for v3.1.0
                    period_map = {'A': 'Q'}  # Map known differences
                    actual_value = period_map.get(value, value)
                    normalized[key] = {
                        'class_name': 'Constant',
                        'type_': 'String',
                        'value': actual_value
                    }
                    continue

            # Recursively normalize nested structures
            if isinstance(value, dict):
                normalized[key] = self._normalize_v3_1_0(value)
            elif isinstance(value, list):
                normalized[key] = [self._normalize_v3_1_0(item) if isinstance(item, dict) else item for item in value]
            else:
                normalized[key] = value

        return normalized

    def _normalize_v4_0_0(self, ast_dict):
        """Normalize AST for version 4.0.0 compatibility."""
        if not isinstance(ast_dict, dict):
            return ast_dict

        normalized = {}
        for key, value in ast_dict.items():
            # Handle Scalar item naming for v4.0.0
            if key == 'item' and isinstance(value, str) and ':' in value:
                namespace, code = value.split(':', 1)
                if namespace.endswith('_EC') and not namespace.endswith('_qEC'):
                    namespace = namespace.replace('_EC', '_qEC')
                if code.startswith('x') and not code.startswith('qx'):
                    code = 'q' + code
                normalized[key] = f"{namespace}:{code}"

            # Handle TimeShiftOp field mapping
            elif ast_dict.get('class_name') == 'TimeShiftOp':
                if key == 'reference_period':
                    normalized['component'] = value
                    continue

            # Recursively normalize nested structures
            if isinstance(value, dict):
                normalized[key] = self._normalize_v4_0_0(value)
            elif isinstance(value, list):
                normalized[key] = [self._normalize_v4_0_0(item) if isinstance(item, dict) else item for item in value]
            else:
                normalized[key] = value

        return normalized

    def _auto_normalize(self, ast_dict):
        """Auto-detect version and normalize accordingly."""
        # Simple heuristic: check for version-specific patterns
        ast_str = json.dumps(ast_dict) if ast_dict else ""

        if 'eba_qEC' in ast_str or 'qx' in ast_str:
            # Looks like v4.0.0 format, normalize to current
            return self._normalize_v4_0_0(ast_dict)
        elif 'eba_EC' in ast_str and 'reference_period' in ast_str:
            # Looks like v3.1.0 format
            return ast_dict
        else:
            # Default to current format
            return ast_dict

    def _validate_semantics(self, expression):
        """Perform semantic validation if enabled."""
        try:
            # This would integrate with semantic API when available
            return {'semantic_valid': True, 'operands_checked': False}
        except Exception as e:
            return {'semantic_valid': False, 'error': str(e)}

    def _extract_variables(self, ast_dict):
        """Extract variable references from AST."""
        variables = []
        self._traverse_for_type(ast_dict, 'VarID', variables)
        return variables

    def _extract_constants(self, ast_dict):
        """Extract constants from AST."""
        constants = []
        self._traverse_for_type(ast_dict, 'Constant', constants)
        return constants

    def _extract_operations(self, ast_dict):
        """Extract operations from AST."""
        operations = []
        for op_type in ['BinOp', 'UnaryOp', 'AggregationOp', 'CondExpr']:
            self._traverse_for_type(ast_dict, op_type, operations)
        return operations

    def _traverse_for_type(self, ast_dict, target_type, collector):
        """Traverse AST collecting nodes of specific type."""
        if isinstance(ast_dict, dict):
            if ast_dict.get('class_name') == target_type:
                collector.append(ast_dict)
            for value in ast_dict.values():
                if isinstance(value, (dict, list)):
                    self._traverse_for_type(value, target_type, collector)
        elif isinstance(ast_dict, list):
            for item in ast_dict:
                self._traverse_for_type(item, target_type, collector)

    def _has_aggregations(self, ast_dict):
        """Check if AST contains aggregation operations."""
        aggregations = []
        self._traverse_for_type(ast_dict, 'AggregationOp', aggregations)
        return len(aggregations) > 0

    def _has_conditionals(self, ast_dict):
        """Check if AST contains conditional expressions."""
        conditionals = []
        self._traverse_for_type(ast_dict, 'CondExpr', conditionals)
        return len(conditionals) > 0

    def _calculate_complexity(self, ast_dict):
        """Calculate complexity score for AST."""
        score = 0
        if isinstance(ast_dict, dict):
            score += 1
            for value in ast_dict.values():
                if isinstance(value, (dict, list)):
                    score += self._calculate_complexity(value)
        elif isinstance(ast_dict, list):
            for item in ast_dict:
                score += self._calculate_complexity(item)
        return score

    # ============================================================================
    # Helper methods for complete and enriched AST generation
    # ============================================================================

    def _extract_complete_components(self, ast_obj):
        """Extract context and expression from complete AST object."""
        if hasattr(ast_obj, "children") and len(ast_obj.children) > 0:
            child = ast_obj.children[0]
            if hasattr(child, "expression"):
                return child.expression, child.partial_selection
            else:
                return child, None
        return ast_obj, None

    def _check_data_fields_populated(self, ast_dict):
        """Check if any VarID nodes have data fields populated."""
        if not isinstance(ast_dict, dict):
            return False

        if ast_dict.get("class_name") == "VarID" and "data" in ast_dict:
            return True

        # Recursively check nested structures
        for value in ast_dict.values():
            if isinstance(value, dict):
                if self._check_data_fields_populated(value):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and self._check_data_fields_populated(item):
                        return True

        return False

    def _enrich_ast_with_metadata(
        self,
        ast_dict: Dict[str, Any],
        expression: str,
        context: Optional[Dict[str, Any]],
        release_code: Optional[str] = None,
        operation_code: Optional[str] = None,
        precondition: Optional[str] = None,
        release_id: Optional[int] = None,
        primary_module_vid: Optional[int] = None,
        module_code: Optional[str] = None,
        preferred_module_dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Add framework structure (operations, variables, tables, preconditions) to complete AST.

        This creates the engine-ready format with all metadata sections.

        Args:
            ast_dict: Complete AST dictionary
            expression: Original DPM-XL expression
            context: Context dict with table, rows, columns, sheets, default, interval
            release_code: Release code (e.g., "4.2")
            operation_code: Operation code (defaults to "default_code")
            precondition: Precondition variable reference (e.g., {v_F_44_04})
            release_id: Optional release ID to filter database lookups
            primary_module_vid: Module VID being exported (to identify external dependencies)
        """
        from py_dpm.dpm.utils import get_engine
        import copy

        # Initialize database connection
        engine = get_engine(database_path=self.database_path, connection_url=self.connection_url)

        # Generate operation code if not provided
        if not operation_code:
            operation_code = "default_code"

        # Get current date for framework structure
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Detect primary module from the expression (or use provided module_code)
        primary_module_info = self._get_primary_module_info(
            expression=expression,
            primary_module_vid=primary_module_vid,
            release_id=release_id,
            module_code=module_code,
        )

        # Query database for release information
        release_info = self._get_release_info(release_code, engine)

        # Build module info using detected primary module or defaults
        module_info = {
            "module_code": primary_module_info.get("module_code", "default"),
            "module_version": primary_module_info.get("module_version", "1.0.0"),
            "framework_code": primary_module_info.get("framework_code", "default"),
            "dpm_release": {
                "release": release_info["release"],
                "publication_date": release_info["publication_date"],
            },
            "dates": {
                "from": primary_module_info.get("from_date", "2001-01-01"),
                "to": primary_module_info.get("to_date"),
            },
        }

        # Add coordinates to AST data entries
        ast_with_coords = self._add_coordinates_to_ast(ast_dict, context)

        # Build operations section
        # Use module's from_date for from_submission_date (fallback to current date)
        submission_date = primary_module_info.get("from_date", current_date)
        operations = {
            operation_code: {
                "version_id": hash(expression) % 10000,
                "code": operation_code,
                "expression": expression,
                "root_operator_id": 24,  # Default for now
                "ast": ast_with_coords,
                "from_submission_date": submission_date,
                "severity": "Error",
            }
        }

        # Build variables section by extracting from the complete AST
        # This gives us the tables referenced in the expression
        _, variables_by_table = self._extract_variables_from_ast(ast_with_coords)

        # Clean extra fields from data entries (after extraction, as it uses data_type)
        self._clean_ast_data_entries(ast_with_coords)

        all_variables = {}
        tables = {}

        # Get tables_with_modules to filter tables by primary module
        tables_with_modules = primary_module_info.get("tables_with_modules", [])
        primary_module_vid = primary_module_info.get("module_vid")

        # Build mapping of table_code -> module_vid for filtering
        table_to_module = {}
        for table_info in tables_with_modules:
            table_code = table_info.get("code", "")
            module_vid = table_info.get("module_vid")
            if table_code and module_vid:
                table_to_module[table_code] = module_vid

        # Initialize DataDictionaryAPI to query open keys and all variables
        from py_dpm.api.dpm import DataDictionaryAPI
        data_dict_api = DataDictionaryAPI(
            database_path=self.database_path,
            connection_url=self.connection_url
        )

        # Build tables with ALL variables from database (not just from expression)
        # Only include tables belonging to the primary module
        for table_code in variables_by_table.keys():
            # Check if this table belongs to the primary module
            table_module_vid = table_to_module.get(table_code)
            if table_module_vid and table_module_vid != primary_module_vid:
                # This table belongs to a different module, skip it for the main tables section
                continue

            # Get table version info to get table_vid
            table_info = data_dict_api.get_table_version(table_code, release_id)

            if table_info and table_info.get("table_vid"):
                table_vid = table_info["table_vid"]
                # Get ALL variables for this table from database
                table_variables = data_dict_api.get_all_variables_for_table(table_vid)
            else:
                # Fallback to expression variables if table not found
                table_variables = variables_by_table[table_code]

            # Query open keys for this table
            open_keys_list = data_dict_api.get_open_keys_for_table(table_code, release_id)
            open_keys = {item["property_code"]: item["data_type_code"] for item in open_keys_list}

            tables[table_code] = {"variables": table_variables, "open_keys": open_keys}

            # Add table variables to all_variables
            all_variables.update(table_variables)

        data_dict_api.close()

        # Build preconditions
        preconditions = {}
        precondition_variables = {}

        if precondition:
            preconditions, precondition_variables = self._build_preconditions(
                precondition=precondition,
                context=context,
                operation_code=operation_code,
                release_id=release_id,
            )

        # Detect cross-module dependencies
        # Use ALL variables from tables (not just expression variables)
        full_variables_by_table = {
            table_code: table_data["variables"]
            for table_code, table_data in tables.items()
        }
        # Use module_vid from primary_module_info (may have been resolved from module_code)
        resolved_primary_module_vid = primary_module_info.get("module_vid") or primary_module_vid
        dependency_modules, cross_instance_dependencies = self._detect_cross_module_dependencies(
            expression=expression,
            variables_by_table=full_variables_by_table,
            primary_module_vid=resolved_primary_module_vid,
            operation_code=operation_code,
            release_id=release_id,
            preferred_module_dependencies=preferred_module_dependencies,
        )

        # Build dependency information
        # intra_instance_validations should be empty for cross-module operations
        # (operations that have cross_instance_dependencies)
        is_cross_module = bool(cross_instance_dependencies)
        dependency_info = {
            "intra_instance_validations": [] if is_cross_module else [operation_code],
            "cross_instance_dependencies": cross_instance_dependencies,
        }

        # Build complete structure
        # Use module URI as namespace if available, otherwise use "default_module"
        namespace = primary_module_info.get("module_uri", "default_module")

        return {
            namespace: {
                **module_info,
                "operations": operations,
                "variables": all_variables,
                "tables": tables,
                "preconditions": preconditions,
                "precondition_variables": precondition_variables,
                "dependency_information": dependency_info,
                "dependency_modules": dependency_modules,
            }
        }

    def _enrich_ast_with_metadata_multi(
        self,
        expression_tuples: List[Tuple[str, str, Optional[str]]],
        table_context: Optional[Dict[str, Any]],
        release_code: Optional[str] = None,
        release_id: Optional[int] = None,
        primary_module_vid: Optional[int] = None,
        module_code: Optional[str] = None,
        preferred_module_dependencies: Optional[List[str]] = None,
        add_all_tables: bool = True,
    ) -> Dict[str, Any]:
        """
        Add framework structure for multiple expressions (operations, variables, tables, preconditions).

        This creates the engine-ready format with all metadata sections, aggregating
        multiple expressions into a single script structure.

        Args:
            expression_tuples: List of (expression, operation_code, precondition) tuples
            table_context: Context dict with table, rows, columns, sheets, default, interval
            release_code: Release code (e.g., "4.2")
            release_id: Optional release ID to filter database lookups
            primary_module_vid: Module VID being exported (to identify external dependencies)
            module_code: Optional module code to specify the main module
            preferred_module_dependencies: Optional list of module codes to prefer for dependencies
            add_all_tables: If True, include all tables and variables from the module version.
                If False, only include tables referenced in expressions.

        Returns:
            Dict with the enriched AST structure

        Raises:
            ValueError: If no operation scope belongs to the specified module
        """
        from py_dpm.dpm.utils import get_engine
        from py_dpm.api.dpm import DataDictionaryAPI
        from py_dpm.api.dpm_xl.operation_scopes import OperationScopesAPI

        # Initialize database connection
        engine = get_engine(database_path=self.database_path, connection_url=self.connection_url)

        # Get current date for framework structure
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Aggregated structures
        all_operations = {}
        all_variables = {}
        all_tables = {}
        all_preconditions = {}
        all_precondition_variables = {}
        all_dependency_modules = {}
        all_cross_instance_deps = []
        all_intra_instance_ops = []

        # Track processed preconditions to avoid duplicates
        # Maps precondition string -> list of precondition keys generated from it
        processed_preconditions: Dict[str, List[str]] = {}

        # Track all tables with their modules for validation
        all_tables_with_modules = []

        # Flag to track if at least one operation belongs to the primary module
        has_primary_module_operation = False

        # Initialize DataDictionaryAPI once for all expressions
        data_dict_api = DataDictionaryAPI(
            database_path=self.database_path,
            connection_url=self.connection_url
        )

        # Initialize OperationScopesAPI once for all expressions (performance optimization)
        scopes_api = OperationScopesAPI(
            database_path=self.database_path,
            connection_url=self.connection_url
        )

        # Primary module info will be determined from the first expression or module_code
        primary_module_info = None
        namespace = None

        try:
            for idx, (expression, operation_code, precondition) in enumerate(expression_tuples):
                # Generate complete AST for this expression
                complete_result = self.generate_complete_ast(expression, release_id=release_id)

                if not complete_result["success"]:
                    raise ValueError(
                        f"Failed to generate complete AST for expression {idx + 1} "
                        f"(operation '{operation_code}'): {complete_result['error']}"
                    )

                complete_ast = complete_result["ast"]
                context = complete_result.get("context") or table_context

                # Get tables with modules for this expression FIRST (reuse scopes_api from outer scope)
                # This is done before _get_primary_module_info to pass precomputed values
                tables_with_modules = scopes_api.get_tables_with_metadata_from_expression(
                    expression=expression,
                    release_id=release_id
                )

                # Calculate scope_result once (avoid duplicate calls in other methods)
                scope_result = scopes_api.calculate_scopes_from_expression(
                    expression=expression,
                    release_id=release_id,
                    read_only=True
                )
                all_tables_with_modules.extend(tables_with_modules)

                # Get primary module info from first expression (or use module_code)
                if primary_module_info is None:
                    primary_module_info = self._get_primary_module_info(
                        expression=expression,
                        primary_module_vid=primary_module_vid,
                        release_id=release_id,
                        module_code=module_code,
                        # Performance optimization: pass precomputed values
                        tables_with_modules=tables_with_modules,
                        scopes_api=scopes_api,
                    )
                    namespace = primary_module_info.get("module_uri", "default_module")

                # Add coordinates to AST data entries
                ast_with_coords = self._add_coordinates_to_ast(complete_ast, context)

                # Build operation entry
                submission_date = primary_module_info.get("from_date", current_date)
                all_operations[operation_code] = {
                    "version_id": hash(expression) % 10000,
                    "code": operation_code,
                    "expression": expression,
                    "root_operator_id": 24,
                    "ast": ast_with_coords,
                    "from_submission_date": submission_date,
                    "severity": "Error",
                }

                # Extract variables from this expression's AST
                _, variables_by_table = self._extract_variables_from_ast(ast_with_coords)

                # Clean extra fields from data entries
                self._clean_ast_data_entries(ast_with_coords)

                # Build mapping of table_code -> module_vid
                # Prefer the module VID that matches the detected primary module
                table_to_module = {}
                primary_module_code = primary_module_info.get("module_code")

                # First pass: record mappings for tables belonging to the primary module (by code)
                if primary_module_code:
                    for table_info in tables_with_modules:
                        table_code = table_info.get("code", "")
                        table_module_vid = table_info.get("module_vid")
                        table_module_code = table_info.get("module_code")
                        if (
                            table_code
                            and table_module_vid
                            and table_module_code == primary_module_code
                        ):
                            table_to_module[table_code] = table_module_vid

                # Second pass: fill in any remaining tables with the first available module VID
                for table_info in tables_with_modules:
                    table_code = table_info.get("code", "")
                    table_module_vid = table_info.get("module_vid")
                    if table_code and table_module_vid and table_code not in table_to_module:
                        table_to_module[table_code] = table_module_vid

                resolved_primary_module_vid = primary_module_info.get("module_vid") or primary_module_vid

                # Process tables from this expression
                for table_code in variables_by_table.keys():
                    # Check if this table belongs to the primary module
                    table_module_vid = table_to_module.get(table_code)

                    if table_module_vid and table_module_vid != resolved_primary_module_vid:
                        # This table belongs to a different module, skip for main tables
                        continue

                    # Skip if we already have this table
                    if table_code in all_tables:
                        # Table already added, it passed the module filter before
                        has_primary_module_operation = True
                        continue

                    # Get table version info
                    table_info = data_dict_api.get_table_version(table_code, release_id)

                    if table_info and table_info.get("table_vid"):
                        table_vid = table_info["table_vid"]
                        table_variables = data_dict_api.get_all_variables_for_table(table_vid)
                    else:
                        table_variables = variables_by_table[table_code]

                    # Query open keys for this table
                    open_keys_list = data_dict_api.get_open_keys_for_table(table_code, release_id)
                    open_keys = {item["property_code"]: item["data_type_code"] for item in open_keys_list}

                    all_tables[table_code] = {"variables": table_variables, "open_keys": open_keys}
                    all_variables.update(table_variables)

                    # We successfully added a table that passed the module filter
                    # This means at least one operation references the primary module
                    has_primary_module_operation = True

                # Handle precondition (deduplicate by precondition string)
                if precondition and precondition not in processed_preconditions:
                    preconds, precond_vars = self._build_preconditions(
                        precondition=precondition,
                        context=context,
                        operation_code=operation_code,
                        release_id=release_id,
                    )
                    # Track which keys were generated for this precondition string
                    processed_preconditions[precondition] = list(preconds.keys())
                    # Merge preconditions
                    for precond_key, precond_data in preconds.items():
                        if precond_key not in all_preconditions:
                            all_preconditions[precond_key] = precond_data
                        else:
                            # Add this operation to affected_operations if not already there
                            if operation_code not in all_preconditions[precond_key]["affected_operations"]:
                                all_preconditions[precond_key]["affected_operations"].append(operation_code)
                    all_precondition_variables.update(precond_vars)
                elif precondition and precondition in processed_preconditions:
                    # Precondition already processed, add this operation ONLY to the matching precondition(s)
                    matching_keys = processed_preconditions[precondition]
                    for precond_key in matching_keys:
                        if precond_key in all_preconditions:
                            if operation_code not in all_preconditions[precond_key]["affected_operations"]:
                                all_preconditions[precond_key]["affected_operations"].append(operation_code)

                # Detect cross-module dependencies for this expression
                full_variables_by_table = {
                    table_code: table_data["variables"]
                    for table_code, table_data in all_tables.items()
                }
                dep_modules, cross_deps = self._detect_cross_module_dependencies(
                    expression=expression,
                    variables_by_table=full_variables_by_table,
                    primary_module_vid=resolved_primary_module_vid,
                    operation_code=operation_code,
                    release_id=release_id,
                    preferred_module_dependencies=preferred_module_dependencies,
                    # Performance optimization: pass precomputed values to avoid redundant work
                    tables_with_modules=tables_with_modules,
                    scopes_api=scopes_api,
                    scope_result=scope_result,
                )

                # Merge dependency modules (avoid table duplicates)
                self._merge_dependency_modules(all_dependency_modules, dep_modules)

                # Merge cross-instance dependencies (avoid duplicates)
                self._merge_cross_instance_dependencies(all_cross_instance_deps, cross_deps)

                # Track intra-instance operations
                if not cross_deps:
                    all_intra_instance_ops.append(operation_code)

            # After processing all expressions, add remaining tables from the module if requested
            if add_all_tables and primary_module_info:
                resolved_module_vid = primary_module_info.get("module_vid")
                if resolved_module_vid:
                    # Get all tables belonging to the primary module
                    module_tables = data_dict_api.get_all_tables_for_module(resolved_module_vid)

                    for table_info in module_tables:
                        table_code = table_info.get("table_code")
                        table_vid = table_info.get("table_vid")

                        # Skip if already added from expressions
                        if table_code in all_tables:
                            continue

                        # Get all variables for this table
                        table_variables = data_dict_api.get_all_variables_for_table(table_vid)

                        # Query open keys for this table
                        open_keys_list = data_dict_api.get_open_keys_for_table(table_code, release_id)
                        open_keys = {item["property_code"]: item["data_type_code"] for item in open_keys_list}

                        all_tables[table_code] = {"variables": table_variables, "open_keys": open_keys}
                        all_variables.update(table_variables)

                    # If we added any tables, mark that we have primary module operations
                    if module_tables:
                        has_primary_module_operation = True

        finally:
            data_dict_api.close()

        # Validate: at least one operation must belong to the primary module
        if not has_primary_module_operation and module_code:
            raise ValueError(
                f"No operation scope belongs to the specified module '{module_code}'. "
                "At least one expression must reference tables from the primary module."
            )

        # Query database for release information
        release_info = self._get_release_info(release_code, engine)

        # Build module info
        module_info = {
            "module_code": primary_module_info.get("module_code", "default"),
            "module_version": primary_module_info.get("module_version", "1.0.0"),
            "framework_code": primary_module_info.get("framework_code", "default"),
            "dpm_release": {
                "release": release_info["release"],
                "publication_date": release_info["publication_date"],
            },
            "dates": {
                "from": primary_module_info.get("from_date", "2001-01-01"),
                "to": primary_module_info.get("to_date"),
            },
        }

        # Build dependency information
        dependency_info = {
            "intra_instance_validations": all_intra_instance_ops,
            "cross_instance_dependencies": all_cross_instance_deps,
        }

        return {
            namespace: {
                **module_info,
                "operations": all_operations,
                "variables": all_variables,
                "tables": all_tables,
                "preconditions": all_preconditions,
                "precondition_variables": all_precondition_variables,
                "dependency_information": dependency_info,
                "dependency_modules": all_dependency_modules,
            }
        }

    def _merge_dependency_modules(
        self,
        existing: Dict[str, Any],
        new: Dict[str, Any]
    ) -> None:
        """
        Merge new dependency_modules into existing, avoiding table duplicates.

        Args:
            existing: Existing dependency_modules dict (modified in place)
            new: New dependency_modules dict to merge
        """
        for uri, module_data in new.items():
            if uri not in existing:
                existing[uri] = module_data
            else:
                # Merge tables (avoid duplicates)
                for table_code, table_data in module_data.get("tables", {}).items():
                    if table_code not in existing[uri].get("tables", {}):
                        existing[uri].setdefault("tables", {})[table_code] = table_data
                # Merge variables
                existing[uri].setdefault("variables", {}).update(
                    module_data.get("variables", {})
                )

    def _merge_cross_instance_dependencies(
        self,
        existing: List[Dict[str, Any]],
        new: List[Dict[str, Any]]
    ) -> None:
        """
        Merge new cross_instance_dependencies into existing, avoiding duplicates.

        Duplicates are identified by the set of module URIs involved.

        Args:
            existing: Existing list (modified in place)
            new: New list to merge
        """
        def get_module_uris(dep: Dict[str, Any]) -> tuple:
            """Extract sorted URIs from modules list for deduplication."""
            modules = dep.get("modules", [])
            uris = []
            for m in modules:
                if isinstance(m, dict):
                    uris.append(m.get("URI", ""))
                else:
                    uris.append(str(m))
            return tuple(sorted(uris))

        # Build a set of existing module URI combinations for deduplication
        existing_module_sets = set()
        for dep in existing:
            existing_module_sets.add(get_module_uris(dep))

        for dep in new:
            dep_uris = get_module_uris(dep)
            if dep_uris not in existing_module_sets:
                existing.append(dep)
                existing_module_sets.add(dep_uris)
            else:
                # Merge affected_operations for existing dependency
                for existing_dep in existing:
                    if get_module_uris(existing_dep) == dep_uris:
                        for op in dep.get("affected_operations", []):
                            if op not in existing_dep.get("affected_operations", []):
                                existing_dep.setdefault("affected_operations", []).append(op)
                        break

    def _get_primary_module_info(
        self,
        expression: str,
        primary_module_vid: Optional[int],
        release_id: Optional[int],
        module_code: Optional[str] = None,
        tables_with_modules: Optional[List[Dict[str, Any]]] = None,
        scopes_api: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Detect and return metadata for the primary module from the expression.

        Args:
            expression: DPM-XL expression
            primary_module_vid: Optional module VID (if known)
            release_id: Optional release ID for filtering
            module_code: Optional module code (e.g., "FINREP9") - takes precedence over
                primary_module_vid if provided
            tables_with_modules: Optional precomputed tables with module metadata
                (performance optimization to avoid redundant database queries)
            scopes_api: Optional precomputed OperationScopesAPI instance
                (performance optimization to reuse database connections)

        Returns:
            Dict with module_uri, module_code, module_version, framework_code,
            from_date, to_date, module_vid
        """
        from py_dpm.api.dpm_xl.operation_scopes import OperationScopesAPI
        from py_dpm.dpm.queries.explorer_queries import ExplorerQuery

        default_info = {
            "module_uri": "default_module",
            "module_code": "default",
            "module_version": "1.0.0",
            "framework_code": "default",
            "from_date": "2001-01-01",
            "to_date": None,
            "module_vid": None,
        }

        # Track if we created the scopes_api locally (need to close it)
        local_scopes_api = False

        try:
            # Reuse provided scopes_api or create a new one
            if scopes_api is None:
                scopes_api = OperationScopesAPI(
                    database_path=self.database_path,
                    connection_url=self.connection_url
                )
                local_scopes_api = True

            # Reuse provided tables_with_modules or fetch if not available
            if tables_with_modules is None:
                tables_with_modules = scopes_api.get_tables_with_metadata_from_expression(
                    expression=expression,
                    release_id=release_id
                )

            if not tables_with_modules:
                if local_scopes_api:
                    scopes_api.close()
                return default_info

            # Determine primary module
            # Priority: module_code (param) > primary_module_vid > first table
            primary_table = None

            if module_code:
                # Find table matching the provided module_code
                for table_info in tables_with_modules:
                    if table_info.get("module_code") == module_code:
                        primary_table = table_info
                        break
            elif primary_module_vid:
                # Find table matching the provided module VID
                for table_info in tables_with_modules:
                    if table_info.get("module_vid") == primary_module_vid:
                        primary_table = table_info
                        break

            # If no match found, use first table
            if not primary_table:
                primary_table = tables_with_modules[0]

            resolved_module_code = primary_table.get("module_code")
            module_vid = primary_table.get("module_vid")

            # Get module URI
            try:
                module_uri = ExplorerQuery.get_module_url(
                    scopes_api.session,
                    module_code=resolved_module_code,
                    release_id=release_id,
                )
                # Remove .json extension if present
                if module_uri and module_uri.endswith(".json"):
                    module_uri = module_uri[:-5]
            except Exception:
                module_uri = "default_module"

            # Get module version dates from scopes metadata
            from_date = "2001-01-01"
            to_date = None
            scopes_metadata = scopes_api.get_scopes_with_metadata_from_expression(
                expression=expression,
                release_id=release_id
            )
            for scope_info in scopes_metadata:
                for module in scope_info.module_versions:
                    if module.get("module_vid") == module_vid:
                        from_date = module.get("from_reference_date", from_date)
                        to_date = module.get("to_reference_date", to_date)
                        break

            if local_scopes_api:
                scopes_api.close()

            return {
                "module_uri": module_uri or "default_module",
                "module_code": resolved_module_code or "default",
                "module_version": primary_table.get("module_version", "1.0.0"),
                "framework_code": resolved_module_code or "default",  # Framework code typically matches module code
                "from_date": str(from_date) if from_date else "2001-01-01",
                "to_date": str(to_date) if to_date else None,
                "module_vid": module_vid,
                "tables_with_modules": tables_with_modules,  # Include table-to-module mapping
            }

        except Exception as e:
            import logging
            logging.warning(f"Failed to detect primary module info: {e}")
            return {**default_info, "tables_with_modules": []}

    def _resolve_release_code(self, release_code: str) -> Optional[int]:
        """
        Resolve a release code (e.g., "4.2") to its release ID.

        Args:
            release_code: The release code string (e.g., "4.2")

        Returns:
            The release ID if found, None otherwise.
        """
        from py_dpm.dpm.utils import get_engine
        from py_dpm.dpm.models import Release
        from sqlalchemy.orm import sessionmaker

        engine = get_engine(database_path=self.database_path, connection_url=self.connection_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            release = (
                session.query(Release)
                .filter(Release.code == release_code)
                .first()
            )
            if release:
                return release.releaseid
            return None
        except Exception:
            return None
        finally:
            session.close()

    def _resolve_module_version(
        self, module_code: str, module_version_number: str
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Resolve a module version number to its release ID and release code.

        Args:
            module_code: The module code (e.g., "COREP_LR")
            module_version_number: The module version number (e.g., "4.1.0")

        Returns:
            Tuple of (release_id, release_code) if found, (None, None) otherwise.
        """
        from py_dpm.dpm.utils import get_engine
        from py_dpm.dpm.models import ModuleVersion, Release
        from sqlalchemy.orm import sessionmaker

        engine = get_engine(database_path=self.database_path, connection_url=self.connection_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Find the module version by code and version number
            module_version = (
                session.query(ModuleVersion)
                .filter(
                    ModuleVersion.code == module_code,
                    ModuleVersion.versionnumber == module_version_number
                )
                .first()
            )
            if not module_version:
                raise ValueError(
                    f"Module version '{module_version_number}' not found for module '{module_code}'."
                )

            # Get the release code from the start release
            release = (
                session.query(Release)
                .filter(Release.releaseid == module_version.startreleaseid)
                .first()
            )
            release_code = release.code if release else None

            return module_version.startreleaseid, release_code
        finally:
            session.close()

    def _get_release_info(self, release_code: Optional[str], engine) -> Dict[str, Any]:
        """Get release information from database using SQLAlchemy."""
        from py_dpm.dpm.models import Release
        from sqlalchemy.orm import sessionmaker

        def format_date(date_value) -> str:
            """Format date whether it's a string or datetime object."""
            if date_value is None:
                return "2001-01-01"
            if isinstance(date_value, str):
                return date_value
            # Assume it's a datetime-like object
            return date_value.strftime("%Y-%m-%d")

        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            if release_code:
                # Query for specific version
                release = (
                    session.query(Release)
                    .filter(Release.code == release_code)
                    .first()
                )

                if release:
                    return {
                        "release": str(release.code) if release.code else release_code,
                        "publication_date": format_date(release.date),
                    }

            # Fallback: get latest released version
            release = (
                session.query(Release)
                .filter(Release.status == "released")
                .order_by(Release.code.desc())
                .first()
            )

            if release:
                return {
                    "release": str(release.code) if release.code else "4.1",
                    "publication_date": format_date(release.date),
                }

            # Final fallback
            return {"release": "4.1", "publication_date": "2001-01-01"}

        except Exception:
            # Fallback on any error
            return {"release": "4.1", "publication_date": "2001-01-01"}
        finally:
            session.close()

    def _get_table_info(self, table_code: str, engine) -> Optional[Dict[str, Any]]:
        """Get table information from database using SQLAlchemy."""
        from py_dpm.dpm.models import TableVersion
        from sqlalchemy.orm import sessionmaker
        import re

        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Try exact match first
            table = (
                session.query(TableVersion).filter(TableVersion.code == table_code).first()
            )

            if table:
                return {"table_vid": table.tablevid, "code": table.code}

            # Handle precondition parser format: F_25_01 -> F_25.01
            if re.match(r"^[A-Z]_\d+_\d+", table_code):
                parts = table_code.split("_", 2)
                if len(parts) >= 3:
                    table_code_with_dot = f"{parts[0]}_{parts[1]}.{parts[2]}"
                    table = (
                        session.query(TableVersion)
                        .filter(TableVersion.code == table_code_with_dot)
                        .first()
                    )

                    if table:
                        return {"table_vid": table.tablevid, "code": table.code}

            # Try LIKE pattern as last resort (handles sub-tables like F_25.01.a)
            table = (
                session.query(TableVersion)
                .filter(TableVersion.code.like(f"{table_code}%"))
                .order_by(TableVersion.code)
                .first()
            )

            if table:
                return {"table_vid": table.tablevid, "code": table.code}

            return None

        except Exception:
            return None
        finally:
            session.close()

    def _build_preconditions(
        self,
        precondition: Optional[str],
        context: Optional[Dict[str, Any]],
        operation_code: str,
        release_id: Optional[int] = None,
    ) -> tuple:
        """Build preconditions and precondition_variables sections.

        Handles both simple preconditions like {v_C_47.00} and compound
        preconditions like {v_C_01.00} and {v_C_05.01} and {v_C_47.00}.

        For compound preconditions, generates a full AST with BinOp nodes
        for 'and' operators connecting PreconditionItem nodes.

        Uses ExplorerQueryAPI to fetch actual variable_id and variable_vid
        from the database based on variable codes.

        Args:
            precondition: Precondition string like "{v_C_01.00}" or
                "{v_C_01.00} and {v_C_05.01} and {v_C_47.00}"
            context: Optional context dict
            operation_code: Operation code to associate with this precondition
            release_id: Optional release ID for filtering variable versions
        """
        import re
        from py_dpm.api.dpm.explorer import ExplorerQueryAPI

        preconditions = {}
        precondition_variables = {}

        if not precondition:
            return preconditions, precondition_variables

        # Extract all variable codes from precondition (handles both simple and compound)
        # Pattern matches {v_VARIABLE_CODE} references
        var_matches = re.findall(r"\{v_([^}]+)\}", precondition)

        if not var_matches:
            return preconditions, precondition_variables

        # Normalize variable codes (F_44_04 -> F_44.04)
        variable_codes = [self._normalize_table_code(v) for v in var_matches]

        # Batch lookup variable IDs from database (single query for efficiency)
        explorer_api = ExplorerQueryAPI()
        try:
            variables_info = explorer_api.get_variables_by_codes(
                variable_codes=variable_codes,
                release_id=release_id,
            )
        finally:
            explorer_api.close()

        # Build variable infos list preserving order from precondition
        var_infos = []
        for var_code in variable_codes:
            if var_code in variables_info:
                info = variables_info[var_code]
                var_infos.append({
                    "variable_code": var_code,
                    "variable_id": info["variable_id"],
                    "variable_vid": info["variable_vid"],
                })
                # Add to precondition_variables
                precondition_variables[str(info["variable_vid"])] = "b"

        if not var_infos:
            return preconditions, precondition_variables

        # Build the AST based on number of variables
        if len(var_infos) == 1:
            # Simple precondition - single PreconditionItem
            info = var_infos[0]
            precondition_code = f"p_{info['variable_vid']}"

            preconditions[precondition_code] = {
                "ast": {
                    "class_name": "PreconditionItem",
                    "variable_id": info["variable_id"],
                    "variable_code": info["variable_code"],
                },
                "affected_operations": [operation_code],
                "version_id": info["variable_vid"],
                "code": precondition_code,
            }
        else:
            # Compound precondition - build BinOp tree with 'and' operators
            # Create a unique key based on sorted variable VIDs
            sorted_var_vids = sorted([info["variable_vid"] for info in var_infos])
            precondition_code = "p_" + "_".join(str(vid) for vid in sorted_var_vids)

            # Build AST: left-associative chain of BinOp 'and' nodes
            # E.g., for [A, B, C]: ((A and B) and C)
            ast = self._build_precondition_item_ast(var_infos[0])
            for info in var_infos[1:]:
                right_ast = self._build_precondition_item_ast(info)
                ast = {
                    "class_name": "BinOp",
                    "op": "and",
                    "left": ast,
                    "right": right_ast,
                }

            # Use the first variable's VID as version_id
            preconditions[precondition_code] = {
                "ast": ast,
                "affected_operations": [operation_code],
                "version_id": sorted_var_vids[0],
                "code": precondition_code,
            }

        return preconditions, precondition_variables

    def _build_precondition_item_ast(self, var_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build a PreconditionItem AST node for a single variable."""
        return {
            "class_name": "PreconditionItem",
            "variable_id": var_info["variable_id"],
            "variable_code": var_info["variable_code"],
        }

    def _normalize_table_code(self, table_code: str) -> str:
        """Normalize table/variable code format (e.g., F_44_04 -> F_44.04)."""
        import re
        # Handle format like C_01_00 -> C_01.00 or F_44_04 -> F_44.04
        match = re.match(r"([A-Z]+)_(\d+)_(\d+)", table_code)
        if match:
            return f"{match.group(1)}_{match.group(2)}.{match.group(3)}"
        # Already in correct format or different format
        return table_code

    def _extract_variables_from_ast(self, ast_dict: Dict[str, Any]) -> tuple:
        """
        Extract variables from complete AST by table.

        Returns:
            tuple: (all_variables_dict, variables_by_table_dict)
        """
        variables_by_table = {}
        all_variables = {}

        def extract_from_node(node):
            if isinstance(node, dict):
                # Check if this is a VarID node with data
                if node.get("class_name") == "VarID" and "data" in node:
                    table = node.get("table")
                    if table:
                        if table not in variables_by_table:
                            variables_by_table[table] = {}

                        # Extract variable IDs and data types from AST data array
                        for data_item in node["data"]:
                            if "datapoint" in data_item:
                                var_id = str(int(data_item["datapoint"]))
                                data_type = data_item.get("data_type", "e")
                                variables_by_table[table][var_id] = data_type
                                all_variables[var_id] = data_type

                # Recursively process nested nodes
                for value in node.values():
                    if isinstance(value, (dict, list)):
                        extract_from_node(value)
            elif isinstance(node, list):
                for item in node:
                    extract_from_node(item)

        extract_from_node(ast_dict)
        return all_variables, variables_by_table

    def _extract_time_shifts_by_table(self, expression: str) -> Dict[str, str]:
        """
        Extract time shift information for each table in the expression.

        Uses the AST to properly parse the expression and find TimeShiftOp nodes
        to determine the ref_period for each table reference.

        Args:
            expression: DPM-XL expression

        Returns:
            Dict mapping table codes to ref_period values (e.g., {"C_01.00": "T-1Q"})
            Tables without time shifts default to "T".
        """
        from py_dpm.dpm_xl.ast.template import ASTTemplate

        time_shifts = {}
        current_period = ["t"]  # Use list to allow mutation in nested function

        class TimeShiftExtractor(ASTTemplate):
            """Lightweight AST visitor that extracts time shifts for each table."""

            def visit_TimeShiftOp(self, node):
                # Save current time period and compute new one
                previous_period = current_period[0]

                period_indicator = node.period_indicator
                shift_number = node.shift_number

                # Compute time period (same logic as ModuleDependencies)
                if "-" in str(shift_number):
                    current_period[0] = f"t+{period_indicator}{shift_number}"
                else:
                    current_period[0] = f"t-{period_indicator}{shift_number}"

                # Visit operand (which contains the VarID)
                self.visit(node.operand)

                # Restore previous time period
                current_period[0] = previous_period

            def visit_VarID(self, node):
                if node.table and current_period[0] != "t":
                    time_shifts[node.table] = current_period[0]

        def convert_to_ref_period(internal_period: str) -> str:
            """Convert internal time period format to ref_period format.

            Internal format: "t+Q-1" or "t-Q1"
            Output format: "T-1Q" for one quarter back
            """
            if internal_period.startswith("t+"):
                # e.g., "t+Q-1" -> "T-1Q"
                indicator = internal_period[2]
                number = internal_period[3:]
                if number.startswith("-"):
                    return f"T{number}{indicator}"
                return f"T+{number}{indicator}"
            elif internal_period.startswith("t-"):
                # e.g., "t-Q1" -> "T-1Q"
                indicator = internal_period[2]
                number = internal_period[3:]
                return f"T-{number}{indicator}"
            return "T"

        try:
            ast = self.syntax_api.parse_expression(expression)
            extractor = TimeShiftExtractor()
            extractor.visit(ast)

            return {table: convert_to_ref_period(period) for table, period in time_shifts.items()}

        except Exception:
            return {}

    def _detect_cross_module_dependencies(
        self,
        expression: str,
        variables_by_table: Dict[str, Dict[str, str]],
        primary_module_vid: Optional[int],
        operation_code: str,
        release_id: Optional[int] = None,
        preferred_module_dependencies: Optional[List[str]] = None,
        tables_with_modules: Optional[List[Dict[str, Any]]] = None,
        scopes_api: Optional[Any] = None,
        scope_result: Optional[Any] = None,
    ) -> tuple:
        """
        Detect cross-module dependencies for a single expression.

        Uses existing OperationScopesAPI and ExplorerQuery to detect external module
        references in cross-module expressions.

        Args:
            expression: DPM-XL expression
            variables_by_table: Variables by table code (from _extract_variables_from_ast)
            primary_module_vid: The module being exported (if known)
            operation_code: Current operation code
            release_id: Optional release ID for filtering
            preferred_module_dependencies: Optional list of module codes to prefer when
                a table belongs to multiple modules
            tables_with_modules: Optional precomputed tables with module metadata
                (performance optimization to avoid redundant database queries)
            scopes_api: Optional precomputed OperationScopesAPI instance
                (performance optimization to reuse database connections)
            scope_result: Optional precomputed scope result from calculate_scopes_from_expression
                (performance optimization to avoid redundant computation)

        Returns:
            Tuple of (dependency_modules, cross_instance_dependencies)
            - dependency_modules: {uri: {tables: {...}, variables: {...}}}
            - cross_instance_dependencies: [{modules: [...], affected_operations: [...], ...}]
        """
        from py_dpm.api.dpm_xl.operation_scopes import OperationScopesAPI
        from py_dpm.dpm.queries.explorer_queries import ExplorerQuery
        import logging

        # Reuse provided scopes_api or create a new one
        if scopes_api is None:
            scopes_api = OperationScopesAPI(
                database_path=self.database_path,
                connection_url=self.connection_url
            )

        try:
            # Reuse provided tables_with_modules or fetch if not available
            if tables_with_modules is None:
                tables_with_modules = scopes_api.get_tables_with_metadata_from_expression(
                    expression=expression,
                    release_id=release_id
                )

            # Reuse provided scope_result or compute if not available
            if scope_result is None:
                scope_result = scopes_api.calculate_scopes_from_expression(
                    expression=expression,
                    release_id=release_id,
                    read_only=True
                )

            if scope_result.has_error or not scope_result.is_cross_module:
                return {}, []

            # Extract time shifts for each table from expression
            time_shifts_by_table = self._extract_time_shifts_by_table(expression)

            # Determine primary module from first table if not provided
            if primary_module_vid is None and tables_with_modules:
                primary_module_vid = tables_with_modules[0].get("module_vid")

            # Helper to normalize table code (remove 't' prefix if present)
            def normalize_table_code(code: str) -> str:
                return code[1:] if code and code.startswith('t') else code

            # Helper to lookup ref_period for a table
            def get_ref_period(table_code: str) -> str:
                if not table_code:
                    return "T"
                ref = time_shifts_by_table.get(table_code)
                if not ref:
                    ref = time_shifts_by_table.get(normalize_table_code(table_code))
                return ref or "T"

            # Helper to lookup variables for a table
            # For external module tables, fetch from database if not in variables_by_table
            from py_dpm.api.dpm import DataDictionaryAPI
            data_dict_api = DataDictionaryAPI(
                database_path=self.database_path,
                connection_url=self.connection_url
            )

            def get_table_variables(table_code: str, table_vid: int = None) -> dict:
                if not table_code:
                    return {}
                # First try from passed variables_by_table
                variables = variables_by_table.get(table_code)
                if not variables:
                    variables = variables_by_table.get(f"t{table_code}", {})
                # If still empty and table_vid is provided, fetch from database
                if not variables and table_vid:
                    variables = data_dict_api.get_all_variables_for_table(table_vid)
                return variables or {}

            # Group external tables by module
            # If preferred_module_dependencies is set, only include those modules
            external_modules = {}

            # TEMPORARY WORKAROUND: Also collect primary module tables to add to dependency_modules
            # This is conceptually wrong but required for current implementation.
            # See /docs/dependency_modules_main_tables_workaround.md for how to revert this.
            primary_module_tables = []

            for table_info in tables_with_modules:
                module_vid = table_info.get("module_vid")
                if module_vid == primary_module_vid:
                    # Collect primary module tables for later inclusion in dependency_modules
                    primary_module_tables.append(table_info)
                    continue  # Skip for now, will add later

                ext_module_code = table_info.get("module_code")
                if not ext_module_code:
                    continue

                # If preferred_module_dependencies is set, only include preferred modules
                if preferred_module_dependencies and ext_module_code not in preferred_module_dependencies:
                    continue

                # Get module URI
                try:
                    module_uri = ExplorerQuery.get_module_url(
                        scopes_api.session,
                        module_code=ext_module_code,
                        release_id=release_id,
                    )
                    if module_uri.endswith(".json"):
                        module_uri = module_uri[:-5]
                except Exception:
                    continue

                table_code = table_info.get("code")
                ref_period = get_ref_period(table_code)

                if module_uri not in external_modules:
                    external_modules[module_uri] = {
                        "module_vid": module_vid,
                        "module_version": table_info.get("module_version"),  # Already in table_info
                        "ref_period": ref_period,
                        "tables": {},
                        "variables": {},
                        "from_date": None,
                        "to_date": None
                    }
                elif ref_period != "T":
                    # Keep most specific ref_period (non-T takes precedence)
                    external_modules[module_uri]["ref_period"] = ref_period

                # Add table and variables
                if table_code:
                    table_vid = table_info.get("table_vid")
                    table_variables = get_table_variables(table_code, table_vid)
                    external_modules[module_uri]["tables"][table_code] = {
                        "variables": table_variables,
                        "open_keys": {}
                    }
                    external_modules[module_uri]["variables"].update(table_variables)

            # TEMPORARY WORKAROUND: Add primary module tables to each dependency module entry
            # This includes main module tables/variables in dependency_modules for cross-module validations
            # See /docs/dependency_modules_main_tables_workaround.md for how to revert this.
            for uri in external_modules:
                for table_info in primary_module_tables:
                    table_code = table_info.get("code")
                    if table_code:
                        table_vid = table_info.get("table_vid")
                        table_variables = get_table_variables(table_code, table_vid)
                        external_modules[uri]["tables"][table_code] = {
                            "variables": table_variables,
                            "open_keys": {}
                        }
                        external_modules[uri]["variables"].update(table_variables)

            # Get date info from scopes metadata
            scopes_metadata = scopes_api.get_scopes_with_metadata_from_expression(
                expression=expression,
                release_id=release_id
            )
            for scope_info in scopes_metadata:
                for module in scope_info.module_versions:
                    mvid = module.get("module_vid")
                    for uri, data in external_modules.items():
                        if data["module_vid"] == mvid:
                            data["from_date"] = module.get("from_reference_date")
                            data["to_date"] = module.get("to_reference_date")

            # Build output structures
            dependency_modules = {}
            cross_instance_dependencies = []

            for uri, data in external_modules.items():
                # dependency_modules entry
                dependency_modules[uri] = {
                    "tables": data["tables"],
                    "variables": data["variables"]
                }

                # cross_instance_dependencies entry (one per external module)
                from_date = data["from_date"]
                to_date = data["to_date"]
                module_entry = {
                    "URI": uri,
                    "ref_period": data["ref_period"]
                }
                # Add module_version if available
                if data["module_version"]:
                    module_entry["module_version"] = data["module_version"]

                cross_instance_dependencies.append({
                    "modules": [module_entry],
                    "affected_operations": [operation_code],
                    "from_reference_date": str(from_date) if from_date else "",
                    "to_reference_date": str(to_date) if to_date else ""
                })

            # Close data_dict_api before returning
            data_dict_api.close()
            return dependency_modules, cross_instance_dependencies

        except Exception as e:
            logging.warning(f"Failed to detect cross-module dependencies: {e}")
            return {}, []
        finally:
            scopes_api.close()

    def _add_coordinates_to_ast(
        self, ast_dict: Dict[str, Any], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Add x/y/z coordinates to data entries in AST.

        Coordinates are assigned based on:
        - x: row position (1-indexed)
        - y: column position (1-indexed)
        - z: sheet position (1-indexed)

        If context provides column/row/sheet lists, those are used for ordering.
        Otherwise, the order is extracted from the data entries themselves.
        """
        import copy

        def add_coords_to_node(node):
            if isinstance(node, dict):
                # Handle VarID nodes with data arrays
                if node.get("class_name") == "VarID" and "data" in node:
                    data_entries = node["data"]
                    if not data_entries:
                        return

                    # Get context lists (may be empty)
                    context_cols = []
                    context_rows = []
                    context_sheets = []
                    if context:
                        context_cols = context.get("columns") or []
                        context_rows = context.get("rows") or []
                        context_sheets = context.get("sheets") or []

                    # Extract unique rows, columns, sheets from data entries
                    # Use these if context doesn't provide them
                    data_rows = []
                    data_cols = []
                    data_sheets = []
                    seen_rows = set()
                    seen_cols = set()
                    seen_sheets = set()

                    for entry in data_entries:
                        row = entry.get("row", "")
                        col = entry.get("column", "")
                        sheet = entry.get("sheet", "")
                        if row and row not in seen_rows:
                            data_rows.append(row)
                            seen_rows.add(row)
                        if col and col not in seen_cols:
                            data_cols.append(col)
                            seen_cols.add(col)
                        if sheet and sheet not in seen_sheets:
                            data_sheets.append(sheet)
                            seen_sheets.add(sheet)

                    # Sort for consistent ordering
                    data_rows.sort()
                    data_cols.sort()
                    data_sheets.sort()

                    # Use context lists if provided, otherwise use extracted lists
                    rows = context_rows if context_rows else data_rows
                    cols = context_cols if context_cols else data_cols
                    sheets = context_sheets if context_sheets else data_sheets

                    # Assign coordinates to each data entry
                    for entry in data_entries:
                        row_code = entry.get("row", "")
                        col_code = entry.get("column", "")
                        sheet_code = entry.get("sheet", "")

                        # Calculate x coordinate (row position)
                        if rows and row_code in rows:
                            x_index = rows.index(row_code) + 1
                            # Only add x if there are multiple rows
                            if len(rows) > 1:
                                entry["x"] = x_index

                        # Calculate y coordinate (column position)
                        # Only add y if there are multiple columns
                        if cols and col_code in cols:
                            y_index = cols.index(col_code) + 1
                            if len(cols) > 1:
                                entry["y"] = y_index

                        # Calculate z coordinate (sheet position)
                        if sheets and sheet_code in sheets:
                            z_index = sheets.index(sheet_code) + 1
                            # Only add z if there are multiple sheets
                            if len(sheets) > 1:
                                entry["z"] = z_index

                # Recursively process child nodes
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        add_coords_to_node(value)
            elif isinstance(node, list):
                for item in node:
                    add_coords_to_node(item)

        # Create a deep copy to avoid modifying the original
        result = copy.deepcopy(ast_dict)
        add_coords_to_node(result)
        return result

    def _clean_ast_data_entries(self, ast_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove extra fields from data entries in the AST.

        Keeps only the fields required by the engine:
        - datapoint, operand_reference_id (always)
        - x and row (only if multiple rows - rows are variable)
        - y and column (only if multiple columns - columns are variable)
        - z and sheet (only if multiple sheets - sheets are variable)

        Removes internal/debug fields:
        - data_type, cell_code, table_code, table_vid
        """
        # Base fields to always keep in data entries
        BASE_FIELDS = {"datapoint", "operand_reference_id"}

        def clean_node(node):
            if isinstance(node, dict):
                # Handle VarID nodes with data arrays
                if node.get("class_name") == "VarID" and "data" in node:
                    cleaned_data = []
                    for data_entry in node["data"]:
                        # Build allowed fields based on which coordinates are present
                        # Only keep row/column/sheet if the corresponding x/y/z coordinate exists
                        allowed = set(BASE_FIELDS)
                        if "x" in data_entry:
                            allowed.add("x")
                            allowed.add("row")
                        if "y" in data_entry:
                            allowed.add("y")
                            allowed.add("column")
                        if "z" in data_entry:
                            allowed.add("z")
                            allowed.add("sheet")

                        # Keep only allowed fields
                        cleaned_entry = {
                            k: v for k, v in data_entry.items() if k in allowed
                        }
                        cleaned_data.append(cleaned_entry)
                    node["data"] = cleaned_data

                # Recursively process child nodes
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        clean_node(value)
            elif isinstance(node, list):
                for item in node:
                    clean_node(item)

        # Modify in place (ast_dict is already a copy from _add_coordinates_to_ast)
        clean_node(ast_dict)
        return ast_dict


# Convenience functions for simple usage

def parse_expression(expression: str, compatibility_mode: str = "auto") -> Dict[str, Any]:
    """
    Simple function to parse a single expression.

    Args:
        expression: DPM-XL expression string
        compatibility_mode: Version compatibility mode

    Returns:
        Parse result dictionary
    """
    generator = ASTGeneratorAPI(compatibility_mode=compatibility_mode)
    return generator.parse_expression(expression)


def validate_expression(expression: str) -> bool:
    """
    Simple function to validate expression syntax.

    Args:
        expression: DPM-XL expression string

    Returns:
        True if valid, False otherwise
    """
    generator = ASTGeneratorAPI()
    result = generator.validate_expression(expression)
    return result['valid']
