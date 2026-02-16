#!/usr/bin/env python3
"""
Validations Script API - Generate engine-ready ASTs for validation frameworks.

This module provides a standalone function that delegates to ASTGeneratorAPI.

For direct class usage:
    from py_dpm.api.dpm_xl import ASTGeneratorAPI

    generator = ASTGeneratorAPI(database_path="data.db")
    result = generator.generate_validations_script(expressions)
"""

from typing import Dict, Any, Optional, List, Union, Tuple
from py_dpm.api.dpm_xl.ast_generator import ASTGeneratorAPI


def generate_validations_script(
    expressions: Union[str, List[Union[Tuple[str, str, Optional[str]], Tuple[str, str, Optional[str], str]]]],
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    release_code: Optional[str] = None,
    table_context: Optional[Dict[str, Any]] = None,
    release_id: Optional[int] = None,
    primary_module_vid: Optional[int] = None,
    module_code: Optional[str] = None,
    preferred_module_dependencies: Optional[List[str]] = None,
    severity: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate validations script with engine-ready AST from DPM-XL expression(s).

    This function delegates to ASTGeneratorAPI.generate_validations_script().

    Supports both single expressions and multiple expression/operation/precondition
    tuples for generating scripts with multiple operations.

    Args:
        expressions: Either a single DPM-XL expression string,
            or a list of tuples: [(expression, operation_code, precondition[, severity]), ...].
            Each tuple contains:
            - expression (str): The DPM-XL expression (required)
            - operation_code (str): The operation code (required)
            - precondition (Optional[str]): Optional precondition reference (e.g., {v_F_44_04})
            - severity (str, optional): Per-operation severity override ('error', 'warning', 'info').
                If omitted (3-element tuple) or None, uses the global severity parameter.
        database_path: Path to SQLite database (or None for PostgreSQL)
        connection_url: PostgreSQL connection URL (takes precedence over database_path)
        release_code: DPM release code (e.g., "4.0", "4.1", "4.2")
        table_context: Optional table context dict with keys: 'table', 'columns', 'rows', 'sheets', 'default', 'interval'
        release_id: Optional release ID to filter database lookups by specific release.
            If None, uses all available data (release-agnostic).
        primary_module_vid: Optional module version ID of the module being exported.
            When provided, enables detection of cross-module dependencies.
        module_code: Optional module code (e.g., "FINREP9") to specify the main module.
        preferred_module_dependencies: Optional list of module codes to prefer when
            multiple dependency scopes are possible.
        severity: Default severity level for operations. Must be one of:
            'error', 'warning', or 'info'. Defaults to 'error' if not specified.
            Per-operation severity in 4-element tuples takes precedence.

    Returns:
        dict: {
            'success': bool,
            'enriched_ast': dict,  # Engine-ready AST with framework structure
            'error': str           # Error message if failed
        }

    Example:
        >>> # Single expression
        >>> result = generate_validations_script(
        ...     "{tF_01.00, r0010, c0010}",
        ...     database_path="data.db",
        ...     release_code="4.2",
        ... )
        >>>
        >>> # Multiple expressions with per-operation severity
        >>> result = generate_validations_script(
        ...     [
        ...         ("{tF_01.00, r0010, c0010} = 0", "v1234_m", None, "error"),
        ...         ("{tF_01.00, r0020, c0010} > 0", "v1235_m", "{v_F_44_04}", "warning"),
        ...         ("{tF_01.00, r0030, c0010} >= 0", "v1236_m", None),  # uses global severity
        ...     ],
        ...     database_path="data.db",
        ...     release_code="4.2",
        ...     module_code="FINREP9",
        ...     severity="error",
        ... )
    """
    generator = ASTGeneratorAPI(
        database_path=database_path,
        connection_url=connection_url,
        enable_semantic_validation=True
    )
    return generator.generate_validations_script(
        expressions=expressions,
        release_code=release_code,
        table_context=table_context,
        release_id=release_id,
        primary_module_vid=primary_module_vid,
        module_code=module_code,
        preferred_module_dependencies=preferred_module_dependencies,
        severity=severity,
    )
