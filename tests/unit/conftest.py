"""Unit test configuration.

This module automatically marks all tests in the unit/ directory
as unit tests using the pytest_collection_modifyitems hook.
"""

import pytest


def pytest_collection_modifyitems(items):
    """Automatically mark all tests in this directory as unit tests."""
    for item in items:
        if "/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
