import sys
import os
from datetime import date

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from py_dpm.api.dpm.data_dictionary import DataDictionaryAPI
from py_dpm.api.dpm.types import ReleaseInfo
from py_dpm.dpm.db.models import Release, Base


def verify_releases():
    print("Setting up in-memory database...")

    # Create valid SQLite URL
    db_url = "sqlite:///:memory:"

    # Initialize API with this URL
    try:
        api = DataDictionaryAPI(connection_url=db_url)
        print("API initialized with in-memory DB.")
    except Exception as e:
        print(f"Failed to initialize API: {e}")
        return

    # Create tables
    print("Creating tables...")
    try:
        # Use the engine from the API instance
        Base.metadata.create_all(api.session.bind)
        print("Tables created.")
    except Exception as e:
        print(f"Failed to create tables: {e}")
        return

    # Insert test data
    print("Inserting test data...")
    try:
        release1 = Release(
            releaseid=1,
            code="R1",
            date=date(2023, 1, 1),
            description="Release 1",
            status="released",
            iscurrent=False,
        )
        release2 = Release(
            releaseid=2,
            code="R2",
            date=date(2023, 2, 1),
            description="Release 2",
            status="active",
            iscurrent=True,
        )

        api.session.add(release1)
        api.session.add(release2)
        api.session.commit()
        print("Test data inserted.")
    except Exception as e:
        print(f"Failed to insert test data: {e}")
        return

    print("Fetching releases...")
    try:
        releases = api.get_releases()
        print(f"Found {len(releases)} releases.")

        for release in releases:
            print(
                f"- Release: {release.code} (ID: {release.release_id}, Date: {release.date}, Current: {release.is_current})"
            )

            # Verify type
            if not isinstance(release, ReleaseInfo):
                print(f"ERROR: Release is not of type ReleaseInfo, got {type(release)}")

        # Verify ordering (should be descending by date)
        if len(releases) == 2:
            if releases[0].code == "R2" and releases[1].code == "R1":
                print("SUCCESS: Releases are ordered correctly (descending date).")
            else:
                print("FAILURE: Releases are NOT ordered correctly.")

    except Exception as e:
        print(f"Error fetching releases: {e}")


if __name__ == "__main__":
    verify_releases()
