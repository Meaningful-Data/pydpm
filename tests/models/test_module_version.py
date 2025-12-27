import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from py_dpm.dpm.models import (
    Base,
    ModuleVersion,
    TableVersion,
    ModuleVersionComposition,
    Table,
    Module,
    Release,
    CompoundKey,
    Concept,
    DpmClass,
    Organisation,
)


from sqlalchemy.pool import StaticPool


# Setup in-memory SQLite database
@pytest.fixture(scope="module")
def engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(scope="module")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def session(engine, tables):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_module_version_table_versions_relationship(session):
    # 1. Setup Data
    # Identify minimal required fields based on models.py (which I saw earlier)
    # Organization, Concept, DpmClass might be needed if triggers/constraints exist, but usually standard inserts are fine.

    # We need a Module, a Table, a Release (constraints)

    release = Release(releaseid=1, code="1.0")
    session.add(release)
    session.flush()

    module_obj = Module(moduleid=10)
    table_obj = Table(tableid=20)
    session.add_all([module_obj, table_obj])
    session.flush()

    # Create Module Version
    mv = ModuleVersion(modulevid=100, moduleid=10, code="MV_TEST", startreleaseid=1)

    # Create Table Version
    tv = TableVersion(tablevid=200, tableid=20, code="TV_TEST", startreleaseid=1)

    session.add_all([mv, tv])
    session.flush()

    # Link them
    mvc = ModuleVersionComposition(modulevid=100, tablevid=200, tableid=20, order=1)
    session.add(mvc)
    session.commit()

    # 2. Verify Relationship
    # Fetch ModuleVersion back
    fetched_mv = (
        session.query(ModuleVersion).filter(ModuleVersion.modulevid == 100).one()
    )

    assert len(fetched_mv.table_versions) == 1
    assert fetched_mv.table_versions[0].code == "TV_TEST"
    assert fetched_mv.table_versions[0].tablevid == 200


def test_module_version_table_versions_is_viewonly(session):
    # Verify we can't easily add to it directly because it's viewonly
    # (Though SQLAlchemy python-side might allow append, commit won't persist the association properly if it's viewonly
    #  WITHOUT the association object, but here we assert behavior).

    # Actually, for viewonly=True, SQLAlchemy typically does not persist changes made to the collection.
    # We can test that adding to it doesn't create a ModuleVersionComposition.

    mv = session.query(
        ModuleVersion
    ).first()  # From previous test if connection reused, or new setup
    if not mv:
        # Setup if needed (session fixture usually effectively cleans or rolls back?
        # Wait, session fixture yields session, but engine fixture is module scope, so data persists unless tables dropped or transaction rollback used.
        # My session fixture closes but doesn't auto-rollback unless configured.
        # SQLite memory persists across connections only if shared cache or same connection.
        # create_engine(":memory:") creates a new DB per connection unless specific URL used.
        # Actually, default pool with :memory: is StaticPool? No, default is NullPool?
        # For :memory:, usually need StaticPool to share data across sessions if checking persistence.
        # But simpler: just create new data.)
        pass

    # Create another table version
    # Use different tableid to avoid UNIQUE(TableID, StartReleaseID) violation if tableid=20, startreleaseid=1 already exists
    table_obj_2 = Table(tableid=21)
    session.add(table_obj_2)
    session.flush()

    tv2 = TableVersion(tablevid=201, tableid=21, code="TV2", startreleaseid=1)
    session.add(tv2)
    session.flush()

    # Check current count
    initial_count = len(mv.table_versions)

    # Try to append
    # Since viewonly=True, this operation on the python object may succeed in memory,
    # but it won't trigger the INSERT into ModuleVersionComposition upon flush/commit.
    mv.table_versions.append(tv2)
    session.commit()

    # Clear session to force reload
    session.expire_all()
    fetched_mv = (
        session.query(ModuleVersion)
        .filter(ModuleVersion.modulevid == mv.modulevid)
        .one()
    )

    # Should NOT have the new table_version because we didn't create the Association object
    assert len(fetched_mv.table_versions) == initial_count
