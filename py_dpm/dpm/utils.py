import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import close_all_sessions, sessionmaker
from contextlib import contextmanager
from rich.console import Console

console = Console()

# Try to load .env from parent directories
current_dir = os.path.dirname(os.path.abspath(__file__))
while current_dir != os.path.dirname(current_dir):  # Stop at root
    env_path = os.path.join(current_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break
    current_dir = os.path.dirname(current_dir)

# SQLite configuration
sqlite_db_path = os.getenv("SQLITE_DB_PATH", "database.db")

# Unified RDBMS configuration (preferred)
#
# These environment variables provide a single, backend-agnostic way to
# configure a server-based database for pyDPM. `PYDPM_RDBMS` selects the
# backend and the remaining variables provide connection details:
#   - PYDPM_RDBMS: "postgres" or "sqlserver"
#   - PYDPM_DB_HOST: hostname or IP
#   - PYDPM_DB_PORT: port number (optional; defaults per backend)
#   - PYDPM_DB_NAME: database name
#   - PYDPM_DB_USER: username
#   - PYDPM_DB_PASSWORD: password
pydpm_rdbms = os.getenv("PYDPM_RDBMS", "").strip().lower()
db_host = os.getenv("PYDPM_DB_HOST", None)
db_port = os.getenv("PYDPM_DB_PORT", None)
db_name = os.getenv("PYDPM_DB_NAME", None)
db_user = os.getenv("PYDPM_DB_USER", None)
db_password = os.getenv("PYDPM_DB_PASSWORD", None)

if pydpm_rdbms == "postgres" and not db_port:
    db_port = "5432"
elif pydpm_rdbms == "sqlserver" and not db_port:
    db_port = "1433"



# PostgreSQL configuration
postgres_host = os.getenv("POSTGRES_HOST", None)
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", None)
postgres_user = os.getenv("POSTGRES_USER", None)
postgres_pass = os.getenv("POSTGRES_PASS", None)

# Legacy SQL Server configuration (kept for backward compatibility)
server = os.getenv("DATABASE_SERVER", None)
username = os.getenv("DATABASE_USER", None)
password = os.getenv("DATABASE_PASS", None)
database_name = os.getenv("DATABASE_NAME", None)

# Determine database type
use_postgres = os.getenv("USE_POSTGRES", "false").lower() == "true"
use_sqlite = os.getenv("USE_SQLITE", "true").lower() == "true" and not use_postgres

if use_postgres and not (
    postgres_host and postgres_user and postgres_pass and postgres_db
):
    console.print(f"Warning: PostgreSQL credentials not provided", style="bold yellow")
elif not use_sqlite and not use_postgres and not (server and username and password):
    console.print(f"Warning: Database credentials not provided", style="bold yellow")
elif not use_sqlite and not use_postgres:
    # Handling special characters in password for SQL Server
    password = password.replace("}", "}}")
    for x in "%&.@#/\\=;":
        if x in password:
            password = "{" + password + "}"
            break

engine = None
connection = None
sessionMakerObject = None
_current_engine_url = None


def create_engine_from_url(connection_url, pool_config=None):
    """
    Create SQLAlchemy engine from a connection URL with appropriate pooling parameters.

    Detects database type from URL scheme and applies pooling parameters conditionally:
    - SQLite: Only pool_pre_ping=True (no connection pooling)
    - PostgreSQL/MySQL/others: Full connection pooling parameters

    Also initializes the global sessionMakerObject for use by get_session().

    Args:
        connection_url (str): SQLAlchemy connection URL (e.g., 'sqlite:///path.db', 'postgresql://user:pass@host/db')
        pool_config (dict, optional): Custom pool configuration. Supported keys:
            - pool_size (int): Maximum number of connections to maintain in the pool (default: 20)
            - max_overflow (int): Maximum overflow connections beyond pool_size (default: 10)
            - pool_timeout (int): Seconds to wait before giving up on getting a connection (default: 30)
            - pool_recycle (int): Seconds before recycling connections (default: 180)
            - pool_pre_ping (bool): Health check connections before using from pool (default: True)

    Returns:
        sqlalchemy.engine.Engine: Configured database engine

    Examples:
        >>> engine = create_engine_from_url('sqlite:///database.db')
        >>> engine = create_engine_from_url('postgresql://user:pass@localhost/mydb')
        >>> engine = create_engine_from_url('postgresql://user:pass@localhost/mydb',
        ...                                   pool_config={'pool_size': 5, 'max_overflow': 10})
    """
    global engine, sessionMakerObject, _current_engine_url

    # Detect database type from URL scheme
    is_sqlite = connection_url.startswith("sqlite://")

    # For PostgreSQL, ensure ISO datestyle if not already set
    # This prevents date parsing errors when PostgreSQL returns dates in locale format
    is_postgres = connection_url.startswith("postgresql://")
    if is_postgres and "datestyle" not in connection_url.lower():
        separator = "&" if "?" in connection_url else "?"
        connection_url = f"{connection_url}{separator}options=-c%20datestyle%3DISO"

    # For SQLite URLs, always create a fresh engine to avoid
    # surprising cross-test or cross-call state sharing, especially
    # for in-memory databases. For server-based databases, reuse the
    # engine when the URL has not changed.
    if not is_sqlite and engine is not None and _current_engine_url == str(
        connection_url
    ):
        return engine

    if is_sqlite:
        # SQLite doesn't support connection pooling
        engine = create_engine(connection_url, pool_pre_ping=True)
    else:
        # Server-based databases (PostgreSQL, MySQL, etc.) with connection pooling
        # Default pool configuration
        default_pool_config = {
            'pool_size': 20,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 180,
            'pool_pre_ping': True,
        }

        # Merge custom pool_config with defaults
        if pool_config:
            default_pool_config.update(pool_config)

        engine = create_engine(
            connection_url,
            **default_pool_config
        )

    # Initialize global sessionMakerObject
    if sessionMakerObject is not None:
        close_all_sessions()
    sessionMakerObject = sessionmaker(bind=engine)
    _current_engine_url = str(connection_url)

    return engine


def create_engine_object(url):
    global engine, _current_engine_url

    # Convert URL to string for type detection if needed
    url_str = str(url)

    # Detect database type from URL scheme (not from environment variables)
    is_sqlite = url_str.startswith("sqlite://")

    # For PostgreSQL, ensure ISO datestyle if not already set
    # This prevents date parsing errors when PostgreSQL returns dates in locale format
    is_postgres = url_str.startswith("postgresql://")
    if is_postgres and "datestyle" not in url_str.lower():
        separator = "&" if "?" in url_str else "?"
        url_str = f"{url_str}{separator}options=-c%20datestyle%3DISO"
        url = url_str  # Use modified URL for engine creation

    # Only reuse engines for non-SQLite URLs. SQLite (especially in-memory)
    # should create independent engines to avoid leaking state between calls.
    if not is_sqlite and engine is not None and _current_engine_url == url_str:
        return engine

    if is_sqlite:
        engine = create_engine(url, pool_pre_ping=True)
    else:
        # Server-based databases (PostgreSQL, MySQL, SQL Server, etc.) with connection pooling
        engine = create_engine(
            url, pool_size=20, max_overflow=10, pool_recycle=180, pool_pre_ping=True
        )

    global sessionMakerObject
    if sessionMakerObject is not None:
        close_all_sessions()
    sessionMakerObject = sessionmaker(bind=engine)
    _current_engine_url = url_str
    return engine


def get_engine(owner=None, database_path=None, connection_url=None, pool_config=None):
    """
    Get database engine based on configuration or explicit parameters.

    Priority order:
    1. Explicit connection_url parameter (for PostgreSQL or other databases)
    2. Explicit database_path parameter (for SQLite)
    3. Environment variable USE_POSTGRES (from .env)
    4. Environment variable USE_SQLITE (from .env)

    Args:
        owner: Owner for SQL Server databases (EBA/EIOPA) - legacy support
        database_path: Explicit SQLite database path
        connection_url: Explicit SQLAlchemy connection URL (e.g., for PostgreSQL)
        pool_config: Connection pool configuration dict (for PostgreSQL/MySQL)

    Returns:
        SQLAlchemy Engine
    """
    # Priority 1: If explicit connection URL is provided, use it directly
    if connection_url:
        return create_engine_from_url(connection_url, pool_config=pool_config)

    # Priority 2: If explicit database_path is provided, use SQLite with that path
    if database_path:
        connection_url = f"sqlite:///{database_path}"
        return create_engine_object(connection_url)

    # Priority 3: Check unified PYDPM_RDBMS configuration
    if pydpm_rdbms in ("postgres", "sqlserver"):
        if not (db_host and db_name and db_user and db_password):
            console.print(
                "Warning: PYDPM_RDBMS is set but PYDPM_DB_* variables are incomplete; "
                "falling back to legacy configuration",
                style="bold yellow",
            )
        else:
            if pydpm_rdbms == "postgres":
                # PostgreSQL via unified PYDPM_* configuration
                port = db_port or "5432"
                connection_url = (
                    f"postgresql://{db_user}:{db_password}@{db_host}:{port}/{db_name}"
                    "?options=-c%20datestyle%3DISO"
                )
                return create_engine_object(connection_url)
            else:
                # SQL Server via unified PYDPM_* configuration
                port = db_port or "1433"
                server_with_port = f"{db_host},{port}" if port else db_host

                # Handling special characters in password for SQL Server
                sqlserver_password = db_password.replace("}", "}}")
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
                    f"DATABASE={db_name}",
                    f"UID={db_user}",
                    f"PWD={sqlserver_password}",
                    "TrustServerCertificate=yes",
                )
                connection_url = URL.create(
                    "mssql+pyodbc",
                    query={"odbc_connect": quote_plus(';'.join(connection_string))},
                )
                return create_engine_object(connection_url)

    # Priority 4: Check legacy PostgreSQL configuration
    if use_postgres:
        if not (postgres_host and postgres_user and postgres_pass and postgres_db):
            console.print(
                "Warning: USE_POSTGRES is true but PostgreSQL credentials are incomplete; "
                "falling back to SQLite or SQL Server defaults",
                style="bold yellow",
            )
        else:
            connection_url = (
                f"postgresql://{postgres_user}:{postgres_pass}@"
                f"{postgres_host}:{postgres_port}/{postgres_db}"
                "?options=-c%20datestyle%3DISO"
            )
            return create_engine_object(connection_url)

    # Priority 5: Check environment variable USE_SQLITE
    if use_sqlite:
        # For SQLite, create the database path if it doesn't exist
        db_dir = os.path.dirname(sqlite_db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        # If owner is specified, append it to the filename
        if owner:
            base_name = os.path.splitext(sqlite_db_path)[0]
            extension = os.path.splitext(sqlite_db_path)[1] or ".db"
            db_path = f"{base_name}_{owner}{extension}"
        else:
            db_path = sqlite_db_path

        connection_url = f"sqlite:///{db_path}"
        return create_engine_object(connection_url)

    # Priority 6: Legacy SQL Server logic
    if owner is None:
        raise Exception("Cannot generate engine. No owner used.")

    if owner not in ("EBA", "EIOPA"):
        raise Exception("Invalid owner, must be EBA or EIOPA")

    if database_name is None:
        database = "DPM_" + owner
    else:
        database = database_name

    if os.name == "nt":
        driver = "{SQL Server}"
    else:
        driver = os.getenv("SQL_DRIVER", "{ODBC Driver 18 for SQL Server}")

    # Handling special characters in password for legacy SQL Server configuration
    sqlserver_password = password.replace("}", "}}") if password else ""
    for x in "%&.@#/\\=;":
        if x in sqlserver_password:
            sqlserver_password = "{" + sqlserver_password + "}"
            break

    connection_string = (
        f"DRIVER={driver}",
        f"SERVER={server}",
        f"DATABASE={database}",
        f"UID={username}",
        f"PWD={sqlserver_password}",
        "TrustServerCertificate=yes",
    )
    connection_string = ";".join(connection_string)
    connection_url = URL.create(
        "mssql+pyodbc", query={"odbc_connect": quote_plus(connection_string)}
    )
    return create_engine_object(connection_url)


def get_connection(owner=None):
    global engine
    if engine is None:
        engine = get_engine(owner)
    connection = engine.connect()
    return connection


def get_session():
    global sessionMakerObject
    """Returns as session on the connection string"""
    if sessionMakerObject is None:
        raise Exception("Not found Session Maker")
    session = sessionMakerObject()
    return session


@contextmanager
def session_scope():
    """
    Provide a transactional scope around a series of operations.

    This helper is intended for short-lived, one-off operations where
    explicit session closing is desired. It does not commit automatically,
    leaving transaction control to the caller, but always closes the
    session in a finally block.
    """
    session = get_session()
    try:
        yield session
    finally:
        try:
            session.close()
        except Exception:
            # Best-effort close; suppress errors on shutdown paths
            pass
