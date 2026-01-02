"""
DPM-XL API

Public APIs for DPM-XL expression parsing, validation, and AST generation.
"""

from py_dpm.api.dpm_xl.syntax import SyntaxAPI
from py_dpm.api.dpm_xl.semantic import SemanticAPI
from py_dpm.api.dpm_xl.ast_generator import ASTGeneratorAPI
from py_dpm.api.dpm_xl.operation_scopes import OperationScopesAPI

# Backwards-compatible standalone functions (delegate to ASTGeneratorAPI)
from py_dpm.api.dpm_xl.complete_ast import (
    generate_complete_ast,
    generate_complete_batch,
    generate_enriched_ast,
    enrich_ast_with_metadata,
    parse_with_data_fields,
)

__all__ = [
    # Class-based APIs
    "SyntaxAPI",
    "SemanticAPI",
    "ASTGeneratorAPI",
    "OperationScopesAPI",
    # Standalone functions (backwards compatibility)
    "generate_complete_ast",
    "generate_complete_batch",
    "generate_enriched_ast",
    "enrich_ast_with_metadata",
    "parse_with_data_fields",
]
