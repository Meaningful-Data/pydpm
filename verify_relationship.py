import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append("/home/aolle/pydpm")

from py_dpm.dpm.models import (
    Base,
    ModuleVersion,
    TableVersion,
    ModuleVersionComposition,
    Table,
    Module,
)

# Setup DB
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Create dummy dependencies (keys, etc. might be needed if nullable=False, checking models.py)
# ModuleVersion needs: ModuleID, StartReleaseID (unique constraint), etc.
# But for sqlite in memory and just testing relationship, simple inserts might work if constraints aren't strict or we fill them.

# Looking at models.py:
# ModuleVersion: moduleid (FK), globalkeyid (FK), startreleaseid (FK), endreleaseid (FK)
# TableVersion: tableid (FK), etc.
# ModuleVersionComposition: modulevid (PK, FK), tableid (PK, FK), tablevid (FK)

# Let's try to be minimal but sufficient.

try:
    # Create parent objects to satisfy FKs if enforced (SQLite enforces FKs only if PRAGMA foreign_keys=ON, usually OFF by default)
    # But SQLAlchemy might issue INSERTs.

    m = Module(moduleid=10)
    t = Table(tableid=20)
    session.add(m)
    session.add(t)
    session.commit()

    mv = ModuleVersion(modulevid=1, moduleid=10, code="M1")
    tv = TableVersion(tablevid=1, tableid=20, code="T1")
    session.add(mv)
    session.add(tv)
    session.commit()

    mvc = ModuleVersionComposition(modulevid=1, tablevid=1, tableid=20, order=1)
    session.add(mvc)
    session.commit()

    # Test relationship
    mv_query = session.query(ModuleVersion).filter(ModuleVersion.modulevid == 1).first()
    print(f"Table Versions: {mv_query.table_versions}")

    assert len(mv_query.table_versions) == 1
    assert mv_query.table_versions[0].code == "T1"
    print("Verification successful!")

except Exception as e:
    print(f"Verification failed: {e}")
    import traceback

    traceback.print_exc()
