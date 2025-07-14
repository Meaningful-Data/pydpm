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

# Legacy SQL Server configuration (kept for backward compatibility)
server = os.getenv("DATABASE_SERVER", None)
username = os.getenv("DATABASE_USER", None)
password = os.getenv("DATABASE_PASS", None)
database_name = os.getenv("DATABASE_NAME", None)

# Determine database type
use_sqlite = os.getenv("USE_SQLITE", "true").lower() == "true"

if not use_sqlite and not (server and username and password):
    console.print(f"Warning: Database credentials not provided", style="bold yellow")
elif not use_sqlite:
    # Handling special characters in password for SQL Server
    password = password.replace('}', '}}')
    for x in '%&.@#/\\=;':
        if x in password:
            password = '{' + password + '}'
            break

engine = None
connection = None
sessionMakerObject = None


def create_engine_object(url):
    global engine
    if use_sqlite:
        engine = create_engine(url, pool_pre_ping=True)
    else:
        engine = create_engine(url, pool_size=20, max_overflow=10,
                               pool_recycle=180, pool_pre_ping=True)

    global sessionMakerObject
    if sessionMakerObject is not None:
        close_all_sessions()
    sessionMakerObject = sessionmaker(bind=engine)
    return engine


def get_engine(owner=None):
    if use_sqlite:
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
    connection = engine.connect(close_with_result=False)
    return connection


def get_session():
    global sessionMakerObject
    """Returns as session on the connection string"""
    if sessionMakerObject is None:
        raise Exception("Not found Session Maker")
    session = sessionMakerObject()
    return session


def create_views(owner):
    """Creates the database tables in the DB connected to by the engine."""
    path = os.path.dirname(__file__)
    path = os.path.join(os.path.join(path, 'data'), 'views')

    if not os.path.exists(path):
        console.print(f"Views directory not found: {path}", style="bold red")
        return

    views = [f for f in os.listdir(path) if f.endswith('.sql')]

    if not views:
        console.print(f"No SQL files found in: {path}", style="bold yellow")
        return

    cnxn = get_connection(owner)

    for query_file in views:
        try:
            with open(os.path.join(path, query_file), 'r') as f:
                query = f.read()
                # SQLite doesn't support some SQL Server specific syntax
                # You might need to modify queries for SQLite compatibility
                cnxn.execute(query)
            console.print(f"Successfully executed: {query_file}", style="green")
        except Exception as e:
            console.print(f"Error executing {query_file}: {str(e)}", style="bold red")

    cnxn.close()

    # Reset global variables
    global engine
    engine = None
    global connection
    connection = None
    global sessionMakerObject
    sessionMakerObject = None