"""Integration test configuration.

This module provides:
- Automatic marking of integration tests
- Database fixtures with proper cleanup
- Session management with nested transaction rollback pattern
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def pytest_collection_modifyitems(items):
    """Automatically mark all tests in this directory as integration tests."""
    for item in items:
        if "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(autouse=True)
def cleanup_global_state():
    """Reset global utils state after each test to prevent state leakage.

    This fixture runs automatically for all integration tests and ensures
    that the global database connection state in py_dpm.dpm.utils is
    properly cleaned up after each test.
    """
    yield

    # Import utils module to access global state
    import py_dpm.dpm.utils as utils
    from sqlalchemy.orm import close_all_sessions

    # Close all sessions first
    if utils.sessionMakerObject is not None:
        close_all_sessions()

    # Dispose engine if it exists
    if utils.engine is not None:
        utils.engine.dispose()

    # Reset all global state
    utils.engine = None
    utils.connection = None
    utils.sessionMakerObject = None
    utils._current_engine_url = None


@pytest.fixture
def memory_engine():
    """Create an in-memory SQLite engine with StaticPool.

    Using StaticPool ensures the same connection is reused across the session,
    which is necessary for in-memory SQLite to maintain data between operations.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    engine.dispose()


@pytest.fixture
def memory_session(memory_engine):
    """Create a session with nested transaction rollback pattern.

    This fixture creates all tables, starts a transaction, and rolls back
    after the test completes. This ensures each test starts with a clean
    database state.
    """
    from py_dpm.dpm.models import Base

    # Create all tables
    Base.metadata.create_all(memory_engine)

    # Create a connection and begin a transaction
    connection = memory_engine.connect()
    transaction = connection.begin()

    # Create session bound to the connection
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    # Cleanup: close session, rollback transaction, close connection
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def data_dict_api_memory():
    """Create a DataDictionaryAPI instance with in-memory SQLite.

    This fixture provides a fully configured DataDictionaryAPI with
    proper lifecycle management.
    """
    from py_dpm.api.dpm.data_dictionary import DataDictionaryAPI
    from py_dpm.dpm.models import Base

    db_url = "sqlite:///:memory:"
    api = DataDictionaryAPI(connection_url=db_url)
    Base.metadata.create_all(api.session.bind)

    yield api

    api.session.close()
