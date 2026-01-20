"""
PyDPM Public API

Main entry point for the PyDPM library.
Provides both DPM-XL specific and general DPM functionality.
"""

# Import from DPM-XL API
from py_dpm.api.dpm_xl import (
    SyntaxAPI,
    SemanticAPI,
    ASTGeneratorAPI,
    OperationScopesAPI,
    generate_complete_ast,
    generate_enriched_ast,
    enrich_ast_with_metadata,
    parse_with_data_fields,
)

# Import from general DPM API
from py_dpm.api.dpm import (
    MigrationAPI,
    DataDictionaryAPI,
    ExplorerQueryAPI,
    HierarchicalQueryAPI,
    InstanceAPI,
)


# Export the main API classes and functions
__all__ = [
    # General DPM APIs
    "MigrationAPI",
    "DataDictionaryAPI",
    "ExplorerQueryAPI",
    "HierarchicalQueryAPI",
    "InstanceAPI",
    # DPM-XL APIs
    "SyntaxAPI",
    "SemanticAPI",
    "ASTGeneratorAPI",
    "OperationScopesAPI",
    # Complete AST functions (backwards compatibility)
    "generate_complete_ast",
    "generate_enriched_ast",
    "enrich_ast_with_metadata",
    "parse_with_data_fields",
]
