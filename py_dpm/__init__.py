"""
PyDPM - Python Data Processing and Migration
============================================

A Python library for DPM-XL data processing, migration, and analysis.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

Main Features:
- Database migration from Access to SQLite
- DPM-XL syntax validation and parsing
- DPM-XL semantic analysis

Quick Start:
    >>> import pydpm
    >>>
    >>> # Migration
    >>> migration = pydpm.api.MigrationAPI()
    >>> engine = migration.migrate_access_to_sqlite("data.mdb", "output.db")
    >>>
    >>> # Syntax validation
    >>> syntax = pydpm.api.SyntaxAPI()
    >>> result = syntax.validate_expression("{tC_01.00, r0100, c0010}")
    >>>
    >>> # Semantic analysis
    >>> semantic = pydpm.api.SemanticAPI()
    >>> result = semantic.validate_expression("{tC_01.00, r0100, c0010}")

Available packages:
- pydpm.api: Main APIs for migration, syntax, and semantic analysis
"""

__version__ = "0.2.12"
__author__ = "MeaningfulData S.L."
__email__ = "info@meaningfuldata.eu"
__license__ = "GPL-3.0-or-later"

# Import main API modules for convenient access
from py_dpm import api

# Import main classes for direct usage
from py_dpm.api import MigrationAPI, SyntaxAPI, SemanticAPI

__all__ = ["api", "MigrationAPI", "SyntaxAPI", "SemanticAPI", "__version__"]
