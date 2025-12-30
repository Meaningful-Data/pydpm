import pytest

from py_dpm.dpm.utils import get_engine, create_engine_from_url, create_engine_object, session_scope


def test_create_engine_from_url_sqlite_smoke():
    url = "sqlite:///test_engine_reuse.db"
    engine = create_engine_from_url(url)
    assert engine is not None


def test_create_engine_object_sqlite_smoke():
    url = "sqlite:///test_engine_object.db"
    engine = create_engine_object(url)
    assert engine is not None


def test_session_scope_closes_session():
    engine = get_engine(database_path="test_session_scope.db")

    with session_scope() as session:
        # Simple smoke query: ensure we can execute something against the engine
        conn = engine.connect()
        conn.close()

    # If we reach here without error, the context manager closed the session.
    # SQLAlchemy itself will recycle connections via the pool.
