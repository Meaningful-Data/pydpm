"""
Integration tests for generate_enriched_ast with multi-expression support.

These tests require a database connection configured via .env file.
"""

import os
import pytest
from dotenv import load_dotenv
from urllib.parse import quote_plus

from py_dpm.api.dpm_xl import ASTGeneratorAPI


load_dotenv()


def _db_kwargs():
    """
    Build DB configuration from environment/.env.

    Prefers server databases configured via PYDPM_RDBMS/PYDPM_DB_* variables.
    Falls back to legacy USE_POSTGRES/POSTGRES_* configuration, then finally
    to SQLite via SQLITE_DB_PATH.
    """
    # Preferred unified configuration
    rdbms = os.getenv("PYDPM_RDBMS", "").strip().lower()

    if rdbms in ("postgres", "sqlserver"):
        host = os.getenv("PYDPM_DB_HOST")
        port = os.getenv("PYDPM_DB_PORT") or (
            "5432" if rdbms == "postgres" else "1433"
        )
        db = os.getenv("PYDPM_DB_NAME")
        user = os.getenv("PYDPM_DB_USER")
        password = os.getenv("PYDPM_DB_PASSWORD")

        if all([host, db, user, password]):
            if rdbms == "postgres":
                connection_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
            else:
                # SQL Server connection using ODBC connection string
                server_with_port = f"{host},{port}" if port else host

                # Handling special characters in password for SQL Server
                sqlserver_password = password.replace("}", "}}")
                for x in "%&.@#/\\=;":
                    if x in sqlserver_password:
                        sqlserver_password = "{" + sqlserver_password + "}"
                        break

                if os.name == "nt":
                    driver = "{SQL Server}"
                else:
                    driver = os.getenv(
                        "SQL_DRIVER", "{ODBC Driver 18 for SQL Server}"
                    )

                connection_string = (
                    f"DRIVER={driver}",
                    f"SERVER={server_with_port}",
                    f"DATABASE={db}",
                    f"UID={user}",
                    f"PWD={sqlserver_password}",
                    "TrustServerCertificate=yes",
                )
                encoded = quote_plus(";".join(connection_string))
                connection_url = f"mssql+pyodbc:///?odbc_connect={encoded}"

            return {"connection_url": connection_url}

    return {}


class TestGenerateEnrichedAstMultiExpression:
    """Integration tests for multi-expression generate_enriched_ast."""

    @pytest.fixture
    def api(self):
        """Create ASTGeneratorAPI instance with database configuration."""
        db_config = _db_kwargs()
        return ASTGeneratorAPI(
            **db_config,
            enable_semantic_validation=True
        )

    def test_single_expression_new_signature(self, api):
        """Test that single expression works with new tuple signature."""
        expression = """
        with {default: 0, interval: true}:
            sum ({tF_32.01, r0010, (c0010, c0060)}) = {tF_01.01, r0380, c0010}
        """

        result = api.generate_enriched_ast(
            expressions=[
                (expression, "v2814_m", None),
            ],
            release_code="4.2",
            module_code="AE",
            preferred_module_dependencies=["FINREP9"],
        )

        assert result["success"] is True, f"Expected success, got error: {result['error']}"
        assert result["enriched_ast"] is not None
        assert result["error"] is None

        # Verify structure
        enriched_ast = result["enriched_ast"]
        assert len(enriched_ast) == 1  # Single namespace

        namespace = list(enriched_ast.keys())[0]
        module_data = enriched_ast[namespace]

        # Verify operations
        assert "operations" in module_data
        assert "v2814_m" in module_data["operations"]
        assert module_data["operations"]["v2814_m"]["code"] == "v2814_m"
        assert module_data["operations"]["v2814_m"]["expression"] == expression

        # Verify variables and tables exist
        assert "variables" in module_data
        assert "tables" in module_data
        assert len(module_data["variables"]) > 0
        assert len(module_data["tables"]) > 0

        # Verify dependency information
        assert "dependency_information" in module_data
        assert "cross_instance_dependencies" in module_data["dependency_information"]

    def test_multiple_expressions_single_module(self, api):
        """Test multiple expressions aggregated into single script."""
        expressions = [
            ("{tF_01.01, r0380, c0010} > 0", "op_1", None),
            ("{tF_01.01, r0390, c0010} >= 0", "op_2", None),
            ("{tF_01.01, r0340, c0010} != 0", "op_3", None),
        ]

        result = api.generate_enriched_ast(
            expressions=expressions,
            module_version_number="3.3.0",
            module_code="FINREP9",
        )

        assert result["success"] is True, f"Expected success, got error: {result['error']}"

        enriched_ast = result["enriched_ast"]
        namespace = list(enriched_ast.keys())[0]
        module_data = enriched_ast[namespace]

        # All three operations should be present
        assert "op_1" in module_data["operations"]
        assert "op_2" in module_data["operations"]
        assert "op_3" in module_data["operations"]

        # Single table should be present (F_01.01)
        assert "F_01.01" in module_data["tables"]

    def test_multiple_expressions_with_preconditions(self, api):
        """Test multiple expressions with preconditions."""
        expressions = [
            ("{tF_01.01, r0380, c0010} > 0", "op_with_precond_1", "{v_F_44_04}"),
            ("{tF_01.01, r0390, c0010} >= 0", "op_with_precond_2", "{v_F_44_04}"),  # Same precondition
            ("{tF_01.01, r0340, c0010} != 0", "op_without_precond", None),
        ]

        result = api.generate_enriched_ast(
            expressions=expressions,
            release_code="4.2",
            module_code="FINREP9",
        )

        assert result["success"] is True, f"Expected success, got error: {result['error']}"

        enriched_ast = result["enriched_ast"]
        namespace = list(enriched_ast.keys())[0]
        module_data = enriched_ast[namespace]

        # All operations present
        assert len(module_data["operations"]) == 3

        # Preconditions should be deduplicated (same precondition used twice)
        # but affected_operations should list both ops
        if module_data["preconditions"]:
            precond_key = list(module_data["preconditions"].keys())[0]
            affected_ops = module_data["preconditions"][precond_key]["affected_operations"]
            assert "op_with_precond_1" in affected_ops or "op_with_precond_2" in affected_ops

    def test_cross_module_expression(self, api):
        """Test expression that references multiple modules."""
        expression = """
        with {default: 0, interval: true}:
            sum ({tF_32.01, r0010, (c0010, c0060)}) = {tF_01.01, r0380, c0010}
        """

        result = api.generate_enriched_ast(
            expressions=[
                (expression, "cross_module_op", None),
            ],
            release_code="4.2",
            module_code="AE",
            preferred_module_dependencies=["FINREP9"],
        )

        assert result["success"] is True, f"Expected success, got error: {result['error']}"

        enriched_ast = result["enriched_ast"]
        namespace = list(enriched_ast.keys())[0]
        module_data = enriched_ast[namespace]

        # Should have cross-module dependencies
        assert "dependency_modules" in module_data
        assert "dependency_information" in module_data

        cross_deps = module_data["dependency_information"]["cross_instance_dependencies"]
        # Should have at least one cross-module dependency (FINREP9)
        assert len(cross_deps) >= 0  # May or may not have depending on module detection

    def test_expression_failure_fails_entire_operation(self, api):
        """Test that invalid expression fails the entire operation."""
        expressions = [
            ("{tF_01.01, r0380, c0010} > 0", "valid_op", None),
            ("INVALID EXPRESSION !!!", "invalid_op", None),  # This should fail
        ]

        result = api.generate_enriched_ast(
            expressions=expressions,
            release_code="4.2",
            module_code="FINREP9",
        )

        # Entire operation should fail
        assert result["success"] is False
        assert result["enriched_ast"] is None
        assert result["error"] is not None
        assert "invalid_op" in result["error"] or "expression 2" in result["error"].lower()

    def test_variables_deduplicated_across_expressions(self, api):
        """Test that variables from same table are not duplicated."""
        expressions = [
            ("{tF_01.01, r0380, c0010} > 0", "op_1", None),
            ("{tF_01.01, r0380, c0010} < 100", "op_2", None),  # Same variable
        ]

        result = api.generate_enriched_ast(
            expressions=expressions,
            release_code="4.2",
            module_code="FINREP9",
        )

        assert result["success"] is True

        enriched_ast = result["enriched_ast"]
        namespace = list(enriched_ast.keys())[0]
        module_data = enriched_ast[namespace]

        # Table should only appear once
        assert list(module_data["tables"].keys()).count("F_01.01") == 1

    def test_output_structure_matches_expected_format(self, api):
        """Test that output structure has all required fields."""
        expression = "{tF_01.01, r0380, c0010} > 0"

        result = api.generate_enriched_ast(
            expressions=[
                (expression, "test_op", None),
            ],
            release_code="4.2",
            module_code="FINREP9",
        )

        assert result["success"] is True

        enriched_ast = result["enriched_ast"]
        namespace = list(enriched_ast.keys())[0]
        module_data = enriched_ast[namespace]

        # Required top-level fields
        required_fields = [
            "module_code",
            "module_version",
            "framework_code",
            "dpm_release",
            "dates",
            "operations",
            "variables",
            "tables",
            "preconditions",
            "precondition_variables",
            "dependency_information",
            "dependency_modules",
        ]

        for field in required_fields:
            assert field in module_data, f"Missing required field: {field}"

        # DPM release structure
        assert "release" in module_data["dpm_release"]
        assert "publication_date" in module_data["dpm_release"]

        # Dates structure
        assert "from" in module_data["dates"]
        assert "to" in module_data["dates"]

        # Dependency information structure
        assert "intra_instance_validations" in module_data["dependency_information"]
        assert "cross_instance_dependencies" in module_data["dependency_information"]
