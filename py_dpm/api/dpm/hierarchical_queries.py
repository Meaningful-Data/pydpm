"""
Hierarchical Queries API

This module provides ORM-based query methods for accessing t    he data dictionary.
All methods use SQLAlchemy ORM instead of raw SQL for PostgreSQL compatibility.
"""

from typing import Optional, Dict, Any

from py_dpm.dpm.utils import get_session, get_engine
from py_dpm.dpm.queries.hierarchical_queries import HierarchicalQuery


class HierarchicalQueryAPI:
    """
    Main API for querying the data dictionary using ORM.

    This class provides methods for:
    - Table/row/column reference lookups
    - Wildcard resolution
    - Item and sheet validation
    - Open key queries
    - Metadata retrieval

    All methods use SQLAlchemy ORM for database-agnostic queries.
    """

    def __init__(
        self,
        database_path: Optional[str] = None,
        connection_url: Optional[str] = None,
    ):
        """
        Initialize the Data Dictionary API.

        Args:
            database_path: Path to SQLite database (optional)
            connection_url: SQLAlchemy connection URL for PostgreSQL (optional)
        """
        # engine is created but not stored since it's used globally/per-session
        get_engine(database_path=database_path, connection_url=connection_url)
        self.session = get_session()

    def close(self):
        """
        Explicitly close the underlying SQLAlchemy session.
        """
        if hasattr(self, "session") and self.session:
            try:
                self.session.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_module_version(
        self,
        module_code: str,
        release_id: Optional[int] = None,
        date: Optional[str] = None,
        release_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch list of available releases from database.

        Returns:
            List of dictionaries containing release info
        """
        # Use ReleaseQuery
        return HierarchicalQuery.get_module_version(
            self.session,
            module_code=module_code,
            release_id=release_id,
            date=date,
            release_code=release_code,
        )

    def get_all_frameworks(
        self,
        release_id: Optional[int] = None,
        date: Optional[str] = None,
        release_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch list of available releases from database.

        Returns:
            List of dictionaries containing release info
        """
        # Use ReleaseQuery
        return HierarchicalQuery.get_all_frameworks(
            self.session,
            release_id=release_id,
            date=date,
            release_code=release_code,
        )

    def get_table_details(
        self,
        table_code: str,
        release_id: Optional[int] = None,
        date: Optional[str] = None,
        release_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch table structure and cell data from database.

        Returns:
            Dictionary with DPM JSON structure
        """
        return HierarchicalQuery.get_table_details(
            self.session,
            table_code=table_code,
            release_id=release_id,
            date=date,
            release_code=release_code,
        )

    def get_table_modelling(
        self,
        table_code: str,
        release_id: Optional[int] = None,
        date: Optional[str] = None,
        release_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Placeholder API for table modelling metadata.

        Mirrors the signature of get_table_details; the underlying query and
        output format will be provided later.
        """
        return HierarchicalQuery.get_table_modelling(
            self.session,
            table_code=table_code,
            release_id=release_id,
            date=date,
            release_code=release_code,
        )
