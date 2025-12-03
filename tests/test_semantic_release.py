import pytest
from py_dpm.api.semantic import validate_expression

EXPRESSION = """
with {tC_09.02}:
    if
        sum({(r0042, r0050), c0105} group by CEG) > 0 
    then
        not(isnull({r0030, c0080}))
    endif
"""


def test_validate_expression_release_1():
    # Test for release_id=1 (Should be VALID)
    result_r1 = validate_expression(EXPRESSION, release_id=1)
    assert (
        result_r1.is_valid
    ), f"Expected valid for release_id=1, but got error: {result_r1.error_message}"


def test_validate_expression_release_5():
    # Test for release_id=5 (Should be INVALID)
    result_r5 = validate_expression(EXPRESSION, release_id=5)
    assert not result_r5.is_valid, "Expected invalid for release_id=5, but it was valid"
