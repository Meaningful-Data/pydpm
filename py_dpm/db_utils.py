import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import close_all_sessions, sessionmaker
from rich.console import Console

console = Console()

env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

# SQLite configuration
sqlite_db_path = os.getenv("SQLITE_DB_PATH", "database.db")

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

if use_postgres and not (postgres_host and postgres_user and postgres_pass and postgres_db):
    console.print(f"Warning: PostgreSQL credentials not provided", style="bold yellow")
elif not use_sqlite and not use_postgres and not (server and username and password):
    console.print(f"Warning: Database credentials not provided", style="bold yellow")
elif not use_sqlite and not use_postgres:
    # Handling special characters in password for SQL Server
    password = password.replace('}', '}}')
    for x in '%&.@#/\\=;':
        if x in password:
            password = '{' + password + '}'
            break

engine = None
connection = None
sessionMakerObject = None


def create_engine_from_url(connection_url):
    """
    Create SQLAlchemy engine from a connection URL with appropriate pooling parameters.

    Detects database type from URL scheme and applies pooling parameters conditionally:
    - SQLite: Only pool_pre_ping=True (no connection pooling)
    - PostgreSQL/MySQL/others: Full connection pooling parameters

    Also initializes the global sessionMakerObject for use by get_session().

    Args:
        connection_url (str): SQLAlchemy connection URL (e.g., 'sqlite:///path.db', 'postgresql://user:pass@host/db')

    Returns:
        sqlalchemy.engine.Engine: Configured database engine

    Examples:
        >>> engine = create_engine_from_url('sqlite:///database.db')
        >>> engine = create_engine_from_url('postgresql://user:pass@localhost/mydb')
    """
    global engine, sessionMakerObject

    # Detect database type from URL scheme
    is_sqlite = connection_url.startswith('sqlite://')

    if is_sqlite:
        # SQLite doesn't support connection pooling
        engine = create_engine(connection_url, pool_pre_ping=True)
    else:
        # Server-based databases (PostgreSQL, MySQL, etc.) with connection pooling
        engine = create_engine(
            connection_url,
            pool_size=20,
            max_overflow=10,
            pool_recycle=180,
            pool_pre_ping=True
        )

    # Initialize global sessionMakerObject
    if sessionMakerObject is not None:
        close_all_sessions()
    sessionMakerObject = sessionmaker(bind=engine)

    return engine


def create_engine_object(url):
    global engine
    if use_sqlite:
        engine = create_engine(url, pool_pre_ping=True)
    elif use_postgres:
        # PostgreSQL with connection pooling
        engine = create_engine(url, pool_size=20, max_overflow=10,
                               pool_recycle=180, pool_pre_ping=True)
    else:
        # SQL Server with connection pooling
        engine = create_engine(url, pool_size=20, max_overflow=10,
                               pool_recycle=180, pool_pre_ping=True)

    global sessionMakerObject
    if sessionMakerObject is not None:
        close_all_sessions()
    sessionMakerObject = sessionmaker(bind=engine)
    return engine


def get_engine(owner=None, database_path=None, connection_url=None):
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

    Returns:
        SQLAlchemy Engine
    """
    # Priority 1: If explicit connection URL is provided, use it directly
    if connection_url:
        return create_engine_from_url(connection_url)

    # Priority 2: If explicit database_path is provided, use SQLite with that path
    if database_path:
        connection_url = f"sqlite:///{database_path}"
        return create_engine_object(connection_url)

    # Priority 3: Check environment variable USE_POSTGRES
    if use_postgres:
        # PostgreSQL connection
        connection_url = f"postgresql://{postgres_user}:{postgres_pass}@{postgres_host}:{postgres_port}/{postgres_db}"
        return create_engine_object(connection_url)

    # Priority 4: Check environment variable USE_SQLITE
    elif use_sqlite:
        # For SQLite, create the database path if it doesn't exist
        db_dir = os.path.dirname(sqlite_db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        # If owner is specified, append it to the filename
        if owner:
            base_name = os.path.splitext(sqlite_db_path)[0]
            extension = os.path.splitext(sqlite_db_path)[1] or '.db'
            db_path = f"{base_name}_{owner}{extension}"
        else:
            db_path = sqlite_db_path

        connection_url = f"sqlite:///{db_path}"
        return create_engine_object(connection_url)
    else:
        # Legacy SQL Server logic
        if owner is None:
            raise Exception("Cannot generate engine. No owner used.")

        if owner not in ('EBA', 'EIOPA'):
            raise Exception("Invalid owner, must be EBA or EIOPA")

        if database_name is None:
            database = "DPM_" + owner
        else:
            database = database_name

        if os.name == 'nt':
            driver = "{SQL Server}"
        else:
            driver = os.getenv('SQL_DRIVER', "{ODBC Driver 18 for SQL Server}")

        connection_string = (
            f"DRIVER={driver}", f"SERVER={server}",
            f"DATABASE={database}", f"UID={username}",
            f"PWD={password}",
            "TrustServerCertificate=yes")
        connection_string = ';'.join(connection_string)
        connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": quote_plus(connection_string)})
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
