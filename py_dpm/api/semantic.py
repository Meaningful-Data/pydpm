from typing import Optional

from py_dpm.api.dpm_xl.semantic import (
    SemanticAPI as _SemanticAPI,
    SemanticValidationResult,
    validate_expression as _validate_expression,
    is_valid_semantics as _is_valid_semantics,
)


SemanticAPI = _SemanticAPI


def validate_expression(
    expression: str,
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    release_id: Optional[int] = None,
) -> SemanticValidationResult:
    """
    Backwards-compatible wrapper for semantic validation.

    This delegates to the DPM-XL SemanticAPI implementation.
    """
    return _validate_expression(
        expression,
        database_path=database_path,
        connection_url=connection_url,
        release_id=release_id,
    )


def is_valid_semantics(
    expression: str,
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    release_id: Optional[int] = None,
) -> bool:
    """
    Backwards-compatible wrapper to check semantic validity.
    """
    return _is_valid_semantics(
        expression,
        database_path=database_path,
        connection_url=connection_url,
        release_id=release_id,
    )


__all__ = [
    "SemanticAPI",
    "SemanticValidationResult",
    "validate_expression",
    "is_valid_semantics",
]

