import subprocess
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import sys
from pathlib import Path
import re
from .models import Base, ViewDatapoints

def extract_access_tables(access_file):
    """Extract tables from Access database using mdbtools"""
    try:
        # Get list of tables
        tables = subprocess.check_output(["mdb-tables", access_file]).decode().split()
    except FileNotFoundError:
        print("Error: mdb-tables command not found. Please make sure mdbtools is installed.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error getting tables from {access_file}: {e}", file=sys.stderr)
        sys.exit(1)

    data = {}
    for table in tables:
        # Export each table to CSV
        print(table)
        csv_file = f"/tmp/{table}.csv"
        try:
            with open(csv_file, "w") as f:
                subprocess.run(["mdb-export", access_file, table], stdout=f, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error exporting table {table} to CSV: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"An unexpected error occurred during export of table {table}: {e}", file=sys.stderr)
            continue

        # Read CSV into pandas DataFrame with specific dtype settings
        STRING_COLUMNS = ["row", "column", "sheet"]

        try:
            df = pd.read_csv(csv_file, dtype=str)

            numeric_columns = []
            for column in df.columns:
                if column in STRING_COLUMNS:
                    continue
                # Check if the column contains only numeric values
                try:
                    # Convert to numeric and check if any values start with '0' (except '0' itself)
                    numeric_series = pd.to_numeric(df[column], errors='coerce')
                    has_leading_zeros = df[column].str.match(r'^0\d+').any()

                    if not has_leading_zeros and not numeric_series.isna().all():
                        numeric_columns.append(column)
                except Exception:
                    continue

            # Convert only the identified numeric columns
            for col in numeric_columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    # Keep as string if conversion fails
                    pass

            data[table] = df

        except Exception as e:
            print(f"Error processing table {table}: {str(e)}")
            continue
        finally:
            # Clean up
            os.remove(csv_file)

    return data

def migrate_to_sqlite(data, sqlite_db_path):
    """Migrate data to SQLite"""
    engine = create_engine(f"sqlite:///{sqlite_db_path}")

    # Create all tables defined in the models
    Base.metadata.create_all(engine)

    for table_name, df in data.items():
        df.to_sql(
            table_name.replace(" ", "_"), # Sanitize table names
            engine,
            if_exists="replace",
            index=False
        )
    return engine

def create_datapoints_view(engine):
    """Create the datapoints view in the database"""
    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get the view query
        view_query = ViewDatapoints.create_view_query(session)

        # Convert the SQLAlchemy query to SQL
        compiled_query = view_query.statement.compile(
            dialect=engine.dialect,
            compile_kwargs={"literal_binds": True}
        )

        # Create the view in the database
        create_view_sql = f"CREATE VIEW IF NOT EXISTS datapoints AS {compiled_query}"

        with engine.connect() as conn:
            conn.execute(text(create_view_sql))
            conn.commit()

        print("Datapoints view created successfully")

    except Exception as e:
        print(f"Error creating datapoints view: {e}")
        raise
    finally:
        session.close()

def run_migration(file_name, sqlite_db_path, export_csv=True, csv_path="datapoints.csv"):
    try:
        # Extract data from Access
        print("Extracting data from Access database...")
        data = extract_access_tables(file_name)

        # Migrate to SQLite
        print("Migrating data to SQLite...")
        engine = migrate_to_sqlite(data, sqlite_db_path)

        # Create the datapoints view
        print("Creating datapoints view...")
        create_datapoints_view(engine)

        print("Migration complete")
        return engine

    except Exception as e:
        print(f"An error occurred during migration: {e}")
        raise

# CLI functionality for standalone CSV export
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate Access database or dump datapoints view to CSV"
    )
    parser.add_argument(
        "database",
        help="Path to the SQLite database file (or Access file for migration)"
    )
    parser.add_argument(
        "-o", "--output",
        default="datapoints.csv",
        help="Output CSV file path (default: datapoints.csv)"
    )

    args = parser.parse_args()

    sqlite_path = args.database.replace('.mdb', '.db')
    run_migration(args.database, sqlite_path, export_csv=True, csv_path=args.output)
