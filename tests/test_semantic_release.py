import os

import pytest
from dotenv import load_dotenv
from urllib.parse import quote_plus

from py_dpm.api.dpm_xl.semantic import validate_expression


load_dotenv()


def _semantic_db_kwargs():
    """
    Build DB configuration for semantic validation from environment/.env.

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

    # Legacy PostgreSQL configuration
    use_postgres = os.getenv("USE_POSTGRES", "false").lower() == "true"
    use_sqlite = os.getenv("USE_SQLITE", "true").lower() == "true"

    if use_postgres:
        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASS")

        if all([host, db, user, password]):
            connection_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
            return {"connection_url": connection_url}

    if use_sqlite:
        db_path = os.getenv("SQLITE_DB_PATH", "database.db")
        return {"database_path": db_path}

    # No DB configuration found; let underlying defaults apply
    return {}


def test_validate_expression_release_1():
    # Test for release_id=1 (Should be VALID)
    expression = """
    with {tC_09.02}:
    if
        sum({(r0042, r0050), c0105} group by CEG) > 0
    then
        not(isnull({r0030, c0080}))
    endif
    """
    result_r1 = validate_expression(
        expression, release_id=1, **_semantic_db_kwargs()
    )
    assert (
        result_r1.is_valid
    ), f"Expected valid for release_id=1, but got error: {result_r1.error_message}"


def test_validate_expression_release_5():
    # Test for release_id=5 (Should be INVALID)
    expression = """
    with {tC_09.02}:
    if
        sum({(r0042, r0050), c0105} group by CEG) > 0
    then
        not(isnull({r0030, c0080}))
    endif
    """
    result_r5 = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert not result_r5.is_valid, "Expected invalid for release_id=5, but it was valid"


def test_EGDQ_0022_1_release_5():
    """Test EGDQ_0022_1 expression validation for release_id=5"""
    expression = """with {tC_17.01.a, c0010-0080}:
    if {tC_17.01.b, r0020, c0090, default: 0} < 1000 and {r0050} = {r0060} then {r0010}  in {0, 1} endif"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert (
        result.is_valid
    ), f"EGDQ_0022_1 failed for release_id=5: {result.error_message}"


def test_EGDQ_0052_1_release_5():
    """Test EGDQ_0052_1 expression validation for release_id=5"""
    expression = """if {tF_32.04.b, r0010-0110, c0030} > 0 then {tF_32.04.a, r0010-0110, c0010} > 0 endif"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert (
        result.is_valid
    ), f"EGDQ_0052_1 failed for release_id=5: {result.error_message}"


def test_EGDQ_0058_release_5():
    """Test EGDQ_0058 expression validation for release_id=5"""
    expression = """if not({tC_27.00,c050} in {[eba_CT:x598], [eba_CT:x20]}) then isnull({tC_27.00, c060}) else not(isnull({tC_27.00, c060})) endif"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert result.is_valid, f"EGDQ_0058 failed for release_id=5: {result.error_message}"


def test_EGDQ_0059_release_5():
    """Test EGDQ_0059 expression validation for release_id=5"""
    expression = (
        """if {tC_27.00, c050} = [eba_CT:x598] then len({tC_27.00, c060}) > 8  endif"""
    )
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert result.is_valid, f"EGDQ_0059 failed for release_id=5: {result.error_message}"


def test_EGDQ_0063_release_5():
    """Test EGDQ_0063 expression validation for release_id=5"""
    expression = """if {tC_27.00, c070} = [eba_ZZ:x662] then ((({tC_27.00, c050} = [eba_CT:x598]) or (isnull({tC_27.00, c050}))) or {tC_27.00, c050} in {[eba_CT:x12], [eba_CT:x599]} and (not ({tC_27.00, c040} in {[eba_GA:AT], [eba_GA:BE], [eba_GA:BG], [eba_GA:CY], [eba_GA:CZ], [eba_GA:DE], [eba_GA:DK], [eba_GA:EE], [eba_GA:ES], [eba_GA:FI], [eba_GA:FR], [eba_GA:GR], [eba_GA:HR], [eba_GA:HU], [eba_GA:IE], [eba_GA:IT], [eba_GA:LT], [eba_GA:LU], [eba_GA:LV], [eba_GA:MT], [eba_GA:NL], [eba_GA:PL], [eba_GA:PT], [eba_GA:RO], [eba_GA:SE], [eba_GA:SI], [eba_GA:SK]}))) endif"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert result.is_valid, f"EGDQ_0063 failed for release_id=5: {result.error_message}"


def test_EGDQ_0084a_release_5():
    """Test EGDQ_0084a expression validation for release_id=5"""
    expression = """({tC_17.01.a, r0910, c0010} >= max_aggr({tC_17.01.a, (r0010, r0110, r0210, r0310, r0410, r0510, r0610, r0710, r0810), c0010})) and ({tC_17.01.a, r0910, c0020} >= max_aggr({tC_17.01.a, (r0010, r0110, r0210, r0310, r0410, r0510, r0610, r0710, r0810), c0020})) and ({tC_17.01.a, r0910, c0030} >= max_aggr({tC_17.01.a, (r0010, r0110, r0210, r0310, r0410, r0510, r0610, r0710, r0810), c0030})) and ({tC_17.01.a, r0910, c0040} >= max_aggr({tC_17.01.a, (r0010, r0110, r0210, r0310, r0410, r0510, r0610, r0710, r0810), c0040})) and ({tC_17.01.a, r0910, c0050} >= max_aggr({tC_17.01.a, (r0010, r0110, r0210, r0310, r0410, r0510, r0610, r0710, r0810), c0050})) and ({tC_17.01.a, r0910, c0060} >= max_aggr({tC_17.01.a, (r0010, r0110, r0210, r0310, r0410, r0510, r0610, r0710, r0810), c0060})) and ({tC_17.01.a, r0910, c0070} >= max_aggr({tC_17.01.a, (r0010, r0110, r0210, r0310, r0410, r0510, r0610, r0710, r0810), c0070})) and ({tC_17.01.a, r0910, c0080} >= max_aggr({tC_17.01.a, (r0010, r0110, r0210, r0310, r0410, r0510, r0610, r0710, r0810), c0080}))"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert (
        result.is_valid
    ), f"EGDQ_0084a failed for release_id=5: {result.error_message}"


def test_EGDQ_0362e_release_5():
    """Test EGDQ_0362e expression validation for release_id=5"""
    expression = """with {tC_14.00}:
    if {c0110} = [eba_RS:x2] and not({c0160} in {[eba_UE:x3], [eba_UE:x9]}) then
    not(isnull({c0060})) endif"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert (
        result.is_valid
    ), f"EGDQ_0362e failed for release_id=5: {result.error_message}"


def test_EGDQ_0532_release_5():
    """Test EGDQ_0532 expression validation for release_id=5"""
    expression = """with {tC_22.00, c0080, default: 0}: {r0010} = {r0020}"""
    result = validate_expression(expression, release_id=5, **_semantic_db_kwargs())
    assert result.is_valid, f"EGDQ_0532 failed for release_id=5: {result.error_message}"


def test_EGDQ_0774_release_5():
    """Test EGDQ_0774 expression validation for release_id=5"""
    expression = """if {tC_47.00, r0300, c0010} > 0 then {tC_47.00, r0440, c0010} = {tC_47.00, r0420, c0010} + {tC_47.00, r0370, c0010} / {tC_47.00, r0300, c0010} endif"""
    result = validate_expression(expression, release_id=5, **_semantic_db_kwargs())
    assert result.is_valid, f"EGDQ_0774 failed for release_id=5: {result.error_message}"


def test_EGDQ_0921a_release_5():
    """Test EGDQ_0921a expression validation for release_id=5"""
    expression = """with {tJ_05.00.b, (r0010, r0030, r0040, r0050, r0060, r0070, r0090, r0100, r0110, r0120, r0180, r0190, r0200, r0220, r0230, r0240, r0260, r0270, r0290, r0300, r0310, r0330, r0340, r0350, r0370, r0380, r0390, r0410, r0420, r0440, r0450, r0460, r0510, r0520)}:
    if {c0010, default:0} != 0 then not(isnull({c0050})) and {c0050} < 0.5 endif"""
    result = validate_expression(expression, release_id=5, **_semantic_db_kwargs())
    assert (
        result.is_valid
    ), f"EGDQ_0921a failed for release_id=5: {result.error_message}"


def test_EGDQ_C199_release_5():
    """Test EGDQ_C199 expression validation for release_id=5"""
    expression = """with {tC_33.00.a, default: 0}:
    sum({c0290, r0010}[where RCP = [eba_GA:qx2014]]) > 0 and
    sum({c0290, r0010}[where not(RCP in {[eba_GA:qx2014], [eba_GA:qx2000]})]) > 0"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert result.is_valid, f"EGDQ_C199 failed for release_id=5: {result.error_message}"


def test_EGDQ_0735_release_5():
    """Test EGDQ_0735 expression validation for release_id=5"""
    expression = """with {tC_66.01.a, (c0020, c0030, c0040, c0050, c0060, c0070, c0080, c0090, c0100, c0110, c0120, c0130, c0140, c0150, c0160, c0170, c0180, c0190, c0200, c0210, c0220), default:0, interval:true}: (sum({r0380, s*})) - (sum({r0350, s*})) - (sum({r0360, s*})) >=
    0.9 * ({tF_01.02,r0040,c0010}+{tF_01.02,r0050,c0010}+{tF_01.02,r0060,c0010}+{tF_01.02,r0064,c0010}+{tF_01.02,r0065,c0010}+{tF_01.02,r0066,c0010}+{tF_01.02,r0070,c0010}+{tF_01.02,r0110,c0010}+{tF_01.02,r0141,c0010}+{tF_01.02,r0240,c0010})"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert result.is_valid, f"EGDQ_0735 failed for release_id=5: {result.error_message}"


def test_EGDQ_0861_2_release_5():
    """Test EGDQ_0861_2 expression validation for release_id=5"""
    expression = """with {default:0, interval:true}: {tP_04.01,r010,c020} >= 0.5 *
   ({tP_02.04,r010,c020}*{tP_01.01,r030,c030} + {tP_02.04,r050,c020}*{tP_01.01,r100,c030} + {tP_02.04,r085,c020}*{tP_01.01,r180,c030}
   + {tP_02.04,r120,c020}*{tP_01.01,r190,c030} + {tP_02.04,r160,c020}*{tP_01.01,r195,c030} + {tP_02.04,r170,c020}*{tP_01.01,r197,c030})"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert (
        result.is_valid
    ), f"EGDQ_0861_2 failed for release_id=5: {result.error_message}"


def test_EGDQ_0865_3_release_5():
    """Test EGDQ_0865_3 expression validation for release_id=5"""
    expression = """with {(r010, r090, r200, r210), default:0, interval:true}:
    (abs({tP_04.01, c040} - {tP_04.01, c030})) / max(abs({tP_04.01, c040}), abs({tP_04.01, c030})) < 0.8"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert (
        result.is_valid
    ), f"EGDQ_0865_3 failed for release_id=5: {result.error_message}"


def test_EGDQ_0454b_1_release_5():
    """Test EGDQ_0454b_1 expression validation for release_id=5"""
    expression = """with {tC_66.01.a, s*, default: 0}:
    {r1080, c0030} = {r1080, c0020} + {r1070, c0030}"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert (
        result.is_valid
    ), f"EGDQ_0454b_1 failed for release_id=5: {result.error_message}"


def test_EGDQ_0678_11_release_5():
    """Test EGDQ_0678_11 expression validation for release_id=5"""
    expression = """with {tF_18.00.a, r0195}:
    {tF_04.03.1, r0150, c0030} = {c0057} + {c0109}"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert (
        result.is_valid
    ), f"EGDQ_0678_11 failed for release_id=5: {result.error_message}"


def test_EGDQ_0480_5_release_5():
    """Test EGDQ_0480_5 expression validation for release_id=5"""
    expression = """with {default: 0}:
    sum({tF_18.00.a, (r0050, r0185), (c0080, c0090, c0101, c0102, c0106, c0107)}) +
    sum({tF_18.00.b, (r0050, r0185), (c0170, c0180, c0191, c0192, c0196, c0197)})
    <=
    sum({tF_07.01, r0100, (c0030, c0060, c0090, c0120)}) +
    sum({tF_07.02, r0100, (c0030, c0060)})"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert (
        result.is_valid
    ), f"EGDQ_0480_5 failed for release_id=5: {result.error_message}"


def test_EGDQ_0455a_11_release_5():
    """Test EGDQ_0455a_11 expression validation for release_id=5"""
    expression = """with {tC_66.01.a, s*, default: 0}:
    {r0720, c0130} = {r0720, c0120} + {r0710, c0130}"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert (
        result.is_valid
    ), f"EGDQ_0455a_11 failed for release_id=5: {result.error_message}"


def test_item_versioning_release_3():
    """Test item versioning expression validation for release_id=3 (Should be INVALID)"""
    expression = """
with {tF_40.01}:
    if {c0095} = [eba_CT:x12] and {c0130} = [eba_RP:x1]
    then {tF_40.01, c0095}[get qCIN] = [eba_qCO:qx2010] endif
"""
    result = validate_expression(
        expression, release_id=3, **_semantic_db_kwargs()
    )
    assert not result.is_valid, f"Expected invalid for release_id=3, but it was valid"


def test_item_versioning_release_5():
    """Test item versioning expression validation for release_id=5 (Should be VALID)"""
    expression = """
with {tF_40.01}:
    if {c0095} = [eba_CT:x12] and {c0130} = [eba_RP:x1]
    then {tF_40.01, c0095}[get qCIN] = [eba_qCO:qx2010] endif
"""
    result = validate_expression(
        expression, release_id=5, **_semantic_db_kwargs()
    )
    assert (
        result.is_valid
    ), f"Expected valid for release_id=5, but got error: {result.error_message}"
