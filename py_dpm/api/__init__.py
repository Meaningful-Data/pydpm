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
)

# Import from general DPM API
from py_dpm.api.dpm import (
    DataDictionaryAPI,
    ExplorerQueryAPI,
    OperationScopesAPI,
    MigrationAPI,
    HierarchicalQueryAPI,
)

# Import convenience functions and types from DPM API
from py_dpm.api.dpm.operation_scopes import (
    calculate_scopes_from_expression,
    get_existing_scopes,
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


# Export the main API classes
__all__ = [
    # Complete AST API (recommended - includes data fields)
    "generate_complete_ast",
    "generate_complete_batch",
    # Enriched AST API (engine-ready with framework structure)
    "generate_enriched_ast",
    "enrich_ast_with_metadata",
    # Simple AST API
    "ASTGenerator",
    "parse_expression",
    "validate_expression",
    "parse_batch",
    # Advanced APIs
    "MigrationAPI",
    "SyntaxAPI",
    "SemanticAPI",
    "DataDictionaryAPI",
    "OperationScopesAPI",
    "ExplorerQueryAPI",
    # Operation Scopes Convenience Functions
    "calculate_scopes_from_expression",
    "get_existing_scopes",
    # Operation Scopes Data Classes
    "ModuleVersionInfo",
    "TableVersionInfo",
    "HeaderVersionInfo",
    "OperationScopeDetailedInfo",
    "OperationScopeResult",
]
