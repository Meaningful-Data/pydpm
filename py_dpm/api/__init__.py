"""
PyDPM Public API

Main entry point for the PyDPM library.
Provides both DPM-XL specific and general DPM functionality.
"""

# Import from DPM-XL API
from py_dpm.api.dpm_xl import (
    SyntaxAPI,
    SemanticAPI,
)

# Import from general DPM API
from py_dpm.api.dpm import (
    MigrationAPI,
    DataDictionaryAPI,
    ExplorerQueryAPI,
    HierarchicalQueryAPI,
)


# Export the main API classes
__all__ = [
    "MigrationAPI",
    "SyntaxAPI",
    "SemanticAPI",
    "DataDictionaryAPI",
    "ExplorerQueryAPI",
    "HierarchicalQueryAPI",
]
