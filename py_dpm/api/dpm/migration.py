import os
from typing import Optional
from sqlalchemy.engine import Engine

from py_dpm.dpm.migration import run_migration as _run_migration


class MigrationAPI:
    """
    API for database migration operations.

    This class provides methods to migrate data from Access databases to SQLite.
    """

    def __init__(self):
        """Initialize the Migration API."""
        pass

    def migrate_access_to_sqlite(
        self, access_file_path: str, sqlite_db_path: Optional[str] = None
    ) -> Engine:
        """
        Migrate data from an Access database to SQLite.

        Args:
            access_file_path (str): Path to the Access database file (.mdb or .accdb)
            sqlite_db_path (Optional[str]): Path for the SQLite database.
                                          If None, defaults to "database.db"

        Returns:
            Engine: SQLAlchemy engine for the created SQLite database

        Raises:
            FileNotFoundError: If the Access file doesn't exist
            Exception: If migration fails

        Example:
            >>> from pydpm.api import MigrationAPI
            >>> migration = MigrationAPI()
            >>> engine = migration.migrate_access_to_sqlite("data.mdb", "output.db")
        """
        if not os.path.exists(access_file_path):
            raise FileNotFoundError(f"Access file not found: {access_file_path}")

        if sqlite_db_path is None:
            sqlite_db_path = os.getenv("SQLITE_DB_PATH", "database.db")

        try:
            engine = _run_migration(access_file_path, sqlite_db_path)
            return engine
        except Exception as e:
            raise Exception(f"Migration failed: {str(e)}") from e


# Convenience function for direct usage
def migrate_access_to_sqlite(
    access_file_path: str, sqlite_db_path: Optional[str] = None
) -> Engine:
    """
    Convenience function to migrate Access database to SQLite.

    Args:
        access_file_path (str): Path to the Access database file
        sqlite_db_path (Optional[str]): Path for the SQLite database

    Returns:
        Engine: SQLAlchemy engine for the created SQLite database

    Example:
        >>> from pydpm.api.migration import migrate_access_to_sqlite
        >>> engine = migrate_access_to_sqlite("data.mdb", "output.db")
    """
    api = MigrationAPI()
    return api.migrate_access_to_sqlite(access_file_path, sqlite_db_path)
