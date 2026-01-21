#!/usr/bin/env python3
"""
Complete AST API - Generate ASTs exactly like the JSON examples

This module provides backwards-compatible standalone functions that delegate to ASTGeneratorAPI.
All AST-related functionality is now consolidated in the ASTGeneratorAPI class.

For new code, prefer using ASTGeneratorAPI directly:
    from py_dpm.api.dpm_xl import ASTGeneratorAPI

    generator = ASTGeneratorAPI(database_path="data.db")
    result = generator.generate_complete_ast(expression)
"""

from typing import Dict, Any, Optional, List, Union, Tuple
from py_dpm.api.dpm_xl.ast_generator import ASTGeneratorAPI


def generate_complete_ast(
    expression: str,
    database_path: str = None,
    connection_url: str = None,
    release_id: Optional[int] = None,
):
    """
    Generate complete AST with all data fields, exactly like json_scripts examples.

    This function delegates to ASTGeneratorAPI for backwards compatibility.

    Args:
        expression: DPM-XL expression string
        database_path: Path to SQLite database file (e.g., "./database.db")
        connection_url: SQLAlchemy connection URL for PostgreSQL (optional)
        release_id: Optional release ID to filter database lookups by specific release.
            If None, uses all available data (release-agnostic).

    Returns:
        dict with keys:
            success, ast, context, error, data_populated, semantic_result
    """
    generator = ASTGeneratorAPI(
        database_path=database_path,
        connection_url=connection_url,
        enable_semantic_validation=True
    )
    return generator.generate_complete_ast(expression, release_id=release_id)


# Convenience function with cleaner interface
def parse_with_data_fields(
    expression: str,
    database_path: str = None,
    connection_url: str = None,
    release_id: Optional[int] = None,
):
    """
    Simple function to parse expression and get AST with data fields.

    This function delegates to ASTGeneratorAPI for backwards compatibility.

    Args:
        expression: DPM-XL expression string
        database_path: Path to SQLite database file
        connection_url: SQLAlchemy connection URL for PostgreSQL (optional)
        release_id: Optional release ID to filter database lookups by specific release.
            If None, uses all available data (release-agnostic).

    Returns:
        dict: AST dictionary with data fields, or None if failed
    """
    result = generate_complete_ast(
        expression, database_path, connection_url, release_id=release_id
    )
    return result["ast"] if result["success"] else None


# ============================================================================
# AST Enrichment Functions - Create engine-ready ASTs
# ============================================================================


def generate_enriched_ast(
    expressions: Union[str, List[Tuple[str, str, Optional[str]]]],
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    release_code: Optional[str] = None,
    table_context: Optional[Dict[str, Any]] = None,
    release_id: Optional[int] = None,
    primary_module_vid: Optional[int] = None,
    module_code: Optional[str] = None,
    preferred_module_dependencies: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate enriched, engine-ready AST from DPM-XL expression(s).

    This function delegates to ASTGeneratorAPI for backwards compatibility.

    Supports both single expressions (for backward compatibility) and multiple
    expression/operation/precondition tuples for generating scripts with multiple operations.

    Args:
        expressions: Either a single DPM-XL expression string (backward compatible),
            or a list of tuples: [(expression, operation_code, precondition), ...].
            Each tuple contains:
            - expression (str): The DPM-XL expression (required)
            - operation_code (str): The operation code (required)
            - precondition (Optional[str]): Optional precondition reference (e.g., {v_F_44_04})
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

    Returns:
        dict: {
            'success': bool,
            'enriched_ast': dict,  # Engine-ready AST with framework structure
            'error': str           # Error message if failed
        }

    Example:
        >>> # Single expression (backward compatible)
        >>> result = generate_enriched_ast(
        ...     "{tF_01.00, r0010, c0010}",
        ...     database_path="data.db",
        ...     release_code="4.2",
        ... )
        >>>
        >>> # Multiple expressions
        >>> result = generate_enriched_ast(
        ...     [
        ...         ("{tF_01.00, r0010, c0010} = 0", "v1234_m", None),
        ...         ("{tF_01.00, r0020, c0010} > 0", "v1235_m", "{v_F_44_04}"),
        ...     ],
        ...     database_path="data.db",
        ...     release_code="4.2",
        ...     module_code="FINREP9",
        ... )
    """
    generator = ASTGeneratorAPI(
        database_path=database_path,
        connection_url=connection_url,
        enable_semantic_validation=True
    )
    return generator.generate_enriched_ast(
        expressions=expressions,
        release_code=release_code,
        table_context=table_context,
        release_id=release_id,
        primary_module_vid=primary_module_vid,
        module_code=module_code,
        preferred_module_dependencies=preferred_module_dependencies,
    )


def enrich_ast_with_metadata(
    ast_dict: Dict[str, Any],
    expression: str,
    context: Optional[Dict[str, Any]],
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    release_code: Optional[str] = None,
    operation_code: Optional[str] = None,
    precondition: Optional[str] = None,
    release_id: Optional[int] = None,
    primary_module_vid: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Add framework structure (operations, variables, tables, preconditions) to complete AST.

    This function delegates to ASTGeneratorAPI for backwards compatibility.

    Args:
        ast_dict: Complete AST dictionary (from generate_complete_ast)
        expression: Original DPM-XL expression
        context: Context dict with table, rows, columns, sheets, default, interval
        database_path: Path to SQLite database
        connection_url: PostgreSQL connection URL (takes precedence)
        release_code: DPM release code (e.g., "4.2")
        operation_code: Operation code (defaults to "default_code")
        precondition: Precondition variable reference (e.g., {v_F_44_04})
        release_id: Optional release ID to filter database lookups
        primary_module_vid: Optional module VID of the module being exported

    Returns:
        dict: Engine-ready AST with framework structure
    """
    generator = ASTGeneratorAPI(
        database_path=database_path,
        connection_url=connection_url,
        enable_semantic_validation=True
    )
    return generator._enrich_ast_with_metadata(
        ast_dict=ast_dict,
        expression=expression,
        context=context,
        release_code=release_code,
        operation_code=operation_code,
        precondition=precondition,
        release_id=release_id,
        primary_module_vid=primary_module_vid,
    )
