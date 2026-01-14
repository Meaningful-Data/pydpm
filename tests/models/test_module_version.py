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


# Tests for get_from_release_id classmethod
class TestGetFromReleaseId:
    """Integration tests for ModuleVersion.get_from_release_id()"""

    @pytest.fixture
    def setup_releases(self, session):
        """Create releases for testing, using high IDs to avoid conflicts."""
        release_ids = [101, 102, 103, 104]
        releases = []
        for rid in release_ids:
            existing = session.query(Release).filter(Release.releaseid == rid).first()
            if not existing:
                releases.append(Release(releaseid=rid, code=f"R{rid}"))
        if releases:
            session.add_all(releases)
            session.flush()
        return session.query(Release).filter(Release.releaseid.in_(release_ids)).all()

    def test_get_from_release_id_requires_module_identifier(self, session):
        """Test that ValueError is raised when no module identifier is provided."""
        with pytest.raises(ValueError, match="Either module_id or module_code must be provided"):
            ModuleVersion.get_from_release_id(session, release_id=1)

    def test_get_from_release_id_rejects_both_identifiers(self, session):
        """Test that ValueError is raised when both module identifiers are provided."""
        with pytest.raises(ValueError, match="Specify only one of module_id or module_code"):
            ModuleVersion.get_from_release_id(
                session, release_id=1, module_id=1, module_code="TEST"
            )

    def test_get_from_release_id_returns_none_when_not_found(
        self, session, setup_releases
    ):
        """Test that None is returned when no matching module version is found."""
        result = ModuleVersion.get_from_release_id(
            session, release_id=101, module_code="NONEXISTENT"
        )
        assert result is None

    def test_get_from_release_id_by_module_code(self, session, setup_releases):
        """Test getting module version by module_code."""
        from datetime import date

        # Use unique module ID for this test
        module = Module(moduleid=201)
        session.add(module)
        session.flush()

        mv = ModuleVersion(
            modulevid=1000,
            moduleid=201,
            code="TESTMOD_CODE",
            startreleaseid=101,
            endreleaseid=None,
            fromreferencedate=date(2020, 1, 1),
            toreferencedate=date(2025, 12, 31),
        )
        session.add(mv)
        session.commit()

        result = ModuleVersion.get_from_release_id(
            session, release_id=102, module_code="TESTMOD_CODE"
        )

        assert result is not None
        assert result.modulevid == 1000
        assert result.code == "TESTMOD_CODE"

    def test_get_from_release_id_by_module_id(self, session, setup_releases):
        """Test getting module version by module_id."""
        from datetime import date

        # Use unique module ID for this test
        module = Module(moduleid=202)
        session.add(module)
        session.flush()

        mv = ModuleVersion(
            modulevid=1001,
            moduleid=202,
            code="TESTMOD_ID",
            startreleaseid=101,
            endreleaseid=None,
            fromreferencedate=date(2020, 1, 1),
            toreferencedate=date(2025, 12, 31),
        )
        session.add(mv)
        session.commit()

        result = ModuleVersion.get_from_release_id(
            session, release_id=102, module_id=202
        )

        assert result is not None
        assert result.modulevid == 1001

    def test_get_from_release_id_returns_previous_when_dates_equal(
        self, session, setup_releases
    ):
        """Test that previous module version is returned when fromreferencedate == toreferencedate."""
        from datetime import date

        # Use unique module ID for this test
        module = Module(moduleid=203)
        session.add(module)
        session.flush()

        # Create the "previous" module version (startreleaseid=101)
        mv_previous = ModuleVersion(
            modulevid=1002,
            moduleid=203,
            code="FINREP9_PREV",
            startreleaseid=101,
            endreleaseid=103,  # Ended at release 103
            fromreferencedate=date(2020, 1, 1),
            toreferencedate=date(2023, 12, 31),
        )

        # Create the "current" module version (startreleaseid=103)
        # with fromreferencedate == toreferencedate
        mv_current = ModuleVersion(
            modulevid=1003,
            moduleid=203,
            code="FINREP9_PREV",
            startreleaseid=103,
            endreleaseid=None,  # Current/live version
            fromreferencedate=date(2024, 1, 1),
            toreferencedate=date(2024, 1, 1),  # Same as fromreferencedate
        )

        session.add_all([mv_previous, mv_current])
        session.commit()

        # Query for release_id=104, which should match mv_current
        # But since fromreferencedate == toreferencedate, it should return mv_previous
        result = ModuleVersion.get_from_release_id(
            session, release_id=104, module_code="FINREP9_PREV"
        )

        assert result is not None
        assert result.modulevid == 1002  # Should be the previous version
        assert result.start_release.releaseid == 101

    def test_get_from_release_id_finrep9_integration(self, session, setup_releases):
        """
        Integration test: FINREP9 module with release_id=104 should return
        module version with start_release.releaseid=101 when current version
        has equal fromreferencedate and toreferencedate.
        """
        from datetime import date

        # Use unique module ID for this test
        module = Module(moduleid=204)
        session.add(module)
        session.flush()

        # Setup: Module version 1 (the one that should be returned)
        mv1 = ModuleVersion(
            modulevid=2000,
            moduleid=204,
            code="FINREP9",
            startreleaseid=101,
            endreleaseid=103,
            fromreferencedate=date(2020, 1, 1),
            toreferencedate=date(2023, 12, 31),
        )

        # Setup: Module version 2 (valid for release 104 but has equal dates)
        mv2 = ModuleVersion(
            modulevid=2001,
            moduleid=204,
            code="FINREP9",
            startreleaseid=103,
            endreleaseid=None,
            fromreferencedate=date(2024, 1, 1),
            toreferencedate=date(2024, 1, 1),  # Equal dates triggers fallback
        )

        session.add_all([mv1, mv2])
        session.commit()

        # Act
        module_version = ModuleVersion.get_from_release_id(
            session, module_code="FINREP9", release_id=104
        )

        # Assert
        assert module_version is not None
        assert module_version.start_release.releaseid == 101

    def test_get_from_release_id_does_not_fallback_when_dates_differ(
        self, session, setup_releases
    ):
        """Test that current version is returned when fromreferencedate != toreferencedate."""
        from datetime import date

        # Use unique module ID for this test
        module = Module(moduleid=205)
        session.add(module)
        session.flush()

        mv_previous = ModuleVersion(
            modulevid=3000,
            moduleid=205,
            code="TESTMOD_NOFALLBACK",
            startreleaseid=101,
            endreleaseid=102,
            fromreferencedate=date(2020, 1, 1),
            toreferencedate=date(2021, 12, 31),
        )

        mv_current = ModuleVersion(
            modulevid=3001,
            moduleid=205,
            code="TESTMOD_NOFALLBACK",
            startreleaseid=102,
            endreleaseid=None,
            fromreferencedate=date(2022, 1, 1),
            toreferencedate=date(2025, 12, 31),  # Different from fromreferencedate
        )

        session.add_all([mv_previous, mv_current])
        session.commit()

        result = ModuleVersion.get_from_release_id(
            session, release_id=103, module_code="TESTMOD_NOFALLBACK"
        )

        assert result is not None
        assert result.modulevid == 3001  # Should be the current version
        assert result.start_release.releaseid == 102
