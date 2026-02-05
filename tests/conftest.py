"""Root test configuration for pytest.

This module sets up the Python path and registers pytest markers.
"""

import sys
import os

# Get the directory containing this file (tests/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory (project root)
project_root = os.path.dirname(current_dir)

# Add the project root to sys.path if it's not already there
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: unit tests (no DB, fast)"
    )
    config.addinivalue_line(
        "markers", "integration: integration tests (require DB)"
    )
