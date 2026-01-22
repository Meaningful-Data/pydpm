import pytest

from py_dpm.api.dpm_xl.ast_generator import parse_expression
from py_dpm.api.dpm_xl import complete_ast as complete_ast_module
from py_dpm.api.dpm_xl.semantic import SemanticValidationResult
from py_dpm.dpm_xl.ast import nodes as ast_nodes


def test_parse_expression_does_not_use_undefined_astobjects():
    """
    Regression test for NameError: ASTObjects not defined in serialization.

    Ensures that parse_expression runs successfully and returns a structured result.
    """
    expression = "{tC_01.00, r0100, c0010}"

    result = parse_expression(expression)

    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["ast"] is not None
    assert result["error"] is None


def test_generate_complete_ast_uses_semantic_api_without_legacy_api(monkeypatch):
    """
    Regression test for generate_complete_ast importing non-existent API class.

    We patch SemanticAPI inside the module to avoid hitting the real database
    and to control the AST returned, verifying that generate_complete_ast
    successfully produces an AST and context dictionary.
    """
    expression = "{tC_01.00, r0100, c0010}"

    # Build a minimal AST: Start(WithExpression(context, expression))
    context_varid = ast_nodes.VarID(
        table="C_01.00",
        rows=["0100"],
        cols=["0010"],
        sheets=None,
        interval=None,
        default=None,
    )
    expr_varid = ast_nodes.VarID(
        table="C_01.00",
        rows=["0100"],
        cols=["0010"],
        sheets=None,
        interval=None,
        default=None,
    )
    with_expr = ast_nodes.WithExpression(
        partial_selection=context_varid, expression=expr_varid
    )
    start_ast = ast_nodes.Start(children=[with_expr])

    class DummySemanticAPI:
        def __init__(self, database_path=None, connection_url=None, pool_config=None):
            self.database_path = database_path
            self.connection_url = connection_url
            self.pool_config = pool_config
            # Expose the AST as SemanticAPI.validate_expression would
            self.ast = start_ast

        def validate_expression(self, expression: str, release_id=None):
            return SemanticValidationResult(
                is_valid=True,
                error_message=None,
                error_code=None,
                expression=expression,
                validation_type="SEMANTIC",
            )

    # Patch SemanticAPI in both the semantic module and ast_generator module
    # since generate_complete_ast now uses ASTGeneratorAPI which imports SemanticAPI
    monkeypatch.setattr(
        "py_dpm.api.dpm_xl.semantic.SemanticAPI", DummySemanticAPI
    )
    monkeypatch.setattr(
        "py_dpm.api.dpm_xl.ast_generator.SemanticAPI", DummySemanticAPI
    )

    # Mock get_engine to avoid database connection issues
    def mock_get_engine(database_path=None, connection_url=None):
        return None  # Return a dummy engine

    monkeypatch.setattr(
        "py_dpm.dpm.utils.get_engine", mock_get_engine
    )

    # Provide a dummy database path to satisfy the check
    result = complete_ast_module.generate_complete_ast(
        expression, database_path="dummy.db"
    )

    assert isinstance(result, dict)
    assert result["success"] is True, f"Expected success=True, got error: {result.get('error')}"
    assert result["ast"] is not None
    assert result["context"] is not None
    # Context should reflect the partial_selection VarID
    assert result["context"]["table"] == "C_01.00"
    assert result["context"]["rows"] == ["0100"]
    assert result["context"]["columns"] == ["0010"]
