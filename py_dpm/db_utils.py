import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import close_all_sessions, sessionmaker

env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
server = os.getenv("DATABASE_SERVER", None)
username = os.getenv("DATABASE_USER", None)
password = os.getenv("DATABASE_PASS", None)
database_name = os.getenv("DATABASE_NAME", None)

if not (server and username and password):
    raise Exception(f'Missing Database credentials')

# Handling special characters in password
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
    engine = create_engine(url, pool_size=20, max_overflow=10,
                           pool_recycle=180, pool_pre_ping=True)
    global sessionMakerObject
    if sessionMakerObject is not None:
        close_all_sessions()
    sessionMakerObject = sessionmaker(bind=engine)
    return engine


def get_engine(owner):
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
    views = [f for f in os.listdir(path)]
    cnxn = get_connection(owner)
    for query_file in views:
        with open(os.path.join(path, query_file), 'r') as f:
            cnxn.execute(f.read())
    cnxn.close()
    global engine
    engine = None
    global connection
    connection = None
    global sessionMakerObject
    sessionMakerObject = None
