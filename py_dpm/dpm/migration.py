import subprocess
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import sys
import tempfile
from .models import Base, ViewDatapoints

def extract_access_tables(access_file):
    """Extract tables from Access database using multiple methods"""
    
    # Method 1: Try mdbtools first
    try:
        # Get list of tables
        tables = subprocess.check_output(["mdb-tables", access_file]).decode().split()
        print("✓ Using mdb-tools for Access database extraction")
        return _extract_with_mdbtools(access_file, tables)
    except FileNotFoundError:
        print("⚠ mdb-tables command not found, trying alternative methods...", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"⚠ mdb-tools failed: {e}, trying alternative methods...", file=sys.stderr)
    
    # Method 2: Try pyodbc with different drivers
    try:
        print("Trying pyodbc with Access drivers...")
        return _extract_with_pyodbc(access_file)
    except Exception as e:
        print(f"⚠ pyodbc method failed: {e}", file=sys.stderr)
    
    # If all methods fail
    raise Exception(
        "Unable to extract Access database. Please install one of:\n"
        "  - mdb-tools: sudo apt-get install mdb-tools\n"
        "  - Microsoft Access ODBC Driver\n"
        "  - Or convert your .accdb file to SQLite manually"
    )

def _extract_with_mdbtools(access_file, tables):
    """Extract using mdb-tools (original method)"""
    data = {}
    for table in tables:
        # Export each table to CSV
        print(table)
        # Use platform-independent temporary file
        temp_dir = tempfile.gettempdir()
        csv_file = os.path.join(temp_dir, f"{table}.csv")
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
            if os.path.exists(csv_file):
                os.remove(csv_file)

    return data

def _extract_with_pyodbc(access_file):
    """Extract using pyodbc with different Access drivers"""
    try:
        import pyodbc
    except ImportError:
        raise Exception("pyodbc not available")

    import decimal

    # Try different Access drivers
    drivers_to_try = [
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};',
        r'DRIVER={Microsoft Access Driver (*.mdb)};',
        r'DRIVER={MDBTools};'
    ]

    conn = None
    for driver in drivers_to_try:
        try:
            conn_str = driver + f'DBQ={access_file};'
            conn = pyodbc.connect(conn_str)
            print(f"✓ Connected using: {driver}")
            break
        except pyodbc.Error:
            continue

    if not conn:
        raise Exception("No suitable ODBC driver found for Access database")

    try:
        # Get all table names
        cursor = conn.cursor()
        tables = []
        for table_info in cursor.tables(tableType='TABLE'):
            table_name = table_info.table_name
            if not table_name.startswith('MSys'):  # Skip system tables
                tables.append(table_name)

        data = {}

        # Extract each table
        for table_name in tables:
            print(table_name)
            try:
                cursor.execute(f"SELECT * FROM [{table_name}]")

                # Get column metadata from cursor.description
                # Each entry is: (name, type_code, display_size, internal_size, precision, scale, null_ok)
                # type_code is a Python type (str, int, float, decimal.Decimal, etc.)
                column_info = []
                for col_desc in cursor.description:
                    col_name = col_desc[0]
                    col_type = col_desc[1]  # Python type from ODBC metadata
                    column_info.append((col_name, col_type))

                columns = [info[0] for info in column_info]
                rows = cursor.fetchall()

                if rows:
                    # Convert to DataFrame
                    df = pd.DataFrame([list(row) for row in rows], columns=columns)

                    # Use the actual column types from Access schema metadata
                    # instead of inferring from data values (fixes Windows vs Linux inconsistency)
                    numeric_types = (int, float, decimal.Decimal)

                    for col_name, col_type in column_info:
                        if col_type in numeric_types:
                            # Column is defined as numeric in Access schema - convert to numeric
                            try:
                                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
                            except (ValueError, TypeError):
                                pass
                        else:
                            # Column is defined as text/other in Access schema - keep as string
                            df[col_name] = df[col_name].astype(object)
                            mask = df[col_name].notna()
                            df.loc[mask, col_name] = df.loc[mask, col_name].astype(str)

                    data[table_name] = df

            except Exception as e:
                print(f"Error processing table {table_name}: {e}", file=sys.stderr)
                continue

        return data

    finally:
        conn.close()

def migrate_to_sqlite(data, sqlite_db_path):
    """Migrate data to SQLite"""
    engine = create_engine(f"sqlite:///{sqlite_db_path}")

    # Create all tables defined in the models, but exclude 'datapoints'
    # which should be created as a view, not a table
    tables_to_create = [table for table in Base.metadata.sorted_tables
                        if table.name != 'datapoints']
    Base.metadata.create_all(engine, tables=tables_to_create)

    # Use raw sqlite3 connection for pandas 2.2+ compatibility
    # (pandas 2.2+ requires cursor() method which SQLAlchemy connections don't have)
    with sqlite3.connect(sqlite_db_path) as raw_conn:
        for table_name, df in data.items():
            df.to_sql(
                table_name.replace(" ", "_"),  # Sanitize table names
                raw_conn,
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
        # Drop any existing table or view with this name first
        with engine.connect() as conn:
            try:
                conn.execute(text("DROP TABLE IF EXISTS datapoints"))
                conn.execute(text("DROP VIEW IF EXISTS datapoints"))
                conn.commit()
            except Exception:
                pass  # Ignore errors if they don't exist

        # Get the view query
        view_query = ViewDatapoints.create_view_query(session)

        # Convert the SQLAlchemy query to SQL
        compiled_query = view_query.statement.compile(
            dialect=engine.dialect,
            compile_kwargs={"literal_binds": True}
        )

        # Create the view in the database
        create_view_sql = f"CREATE VIEW datapoints AS {compiled_query}"

        with engine.connect() as conn:
            conn.execute(text(create_view_sql))
            conn.commit()

        print("Datapoints view created successfully")

    except Exception as e:
        print(f"Error creating datapoints view: {e}")
        raise
    finally:
        session.close()


def create_key_components_view(engine):
    """Create the key_components view for SQLite database"""
    from sqlalchemy.orm import sessionmaker

    session_maker = sessionmaker(bind=engine)
    session = session_maker()

    try:
        # Drop existing view/table if it exists
        try:
            session.execute(text("DROP TABLE IF EXISTS key_components"))
            session.execute(text("DROP VIEW IF EXISTS key_components"))
            session.commit()
        except Exception:
            pass  # Ignore errors if view/table doesn't exist

        # Create the key_components view with SQLite-compatible syntax
        key_components_query = """
        CREATE VIEW key_components AS
        SELECT tv.Code AS table_code,
               ic.Code AS property_code,
               dt.Code AS data_type,
               tv.TableVID AS table_version_id,
               ic.StartReleaseID AS start_release_ic,
               ic.EndReleaseID AS end_release_ic,
               mv.StartReleaseID AS start_release_mv,
               mv.EndReleaseID AS end_release_mv
        FROM TableVersion tv
        INNER JOIN KeyComposition kc ON tv.KeyID = kc.KeyID
        INNER JOIN VariableVersion vv ON vv.VariableVID = kc.VariableVID
        INNER JOIN Item i ON vv.PropertyID = i.ItemID
        INNER JOIN ItemCategory ic ON ic.ItemID = i.ItemID
        INNER JOIN Property p ON vv.PropertyID = p.PropertyID
        LEFT JOIN DataType dt ON p.DataTypeID = dt.DataTypeID
        INNER JOIN ModuleVersionComposition mvc ON tv.TableVID = mvc.TableVID
        INNER JOIN ModuleVersion mv ON mvc.ModuleVID = mv.ModuleVID
        """

        session.execute(text(key_components_query))
        session.commit()

        print("Key components view created successfully")

    except Exception as e:
        print(f"Error creating key_components view: {e}")
        raise
    finally:
        session.close()


def create_open_keys_view(engine):
    """Create the open_keys view for SQLite database"""
    from sqlalchemy.orm import sessionmaker

    session_maker = sessionmaker(bind=engine)
    session = session_maker()

    try:
        # Drop existing view/table if it exists
        try:
            session.execute(text("DROP TABLE IF EXISTS open_keys"))
            session.execute(text("DROP VIEW IF EXISTS open_keys"))
            session.commit()
        except Exception:
            pass  # Ignore errors if view/table doesn't exist

        # Create the open_keys view with SQLite-compatible syntax
        # This view provides information about open keys (dimensions) used in WHERE clauses
        open_keys_query = """
        CREATE VIEW open_keys AS
        SELECT ic.Code AS property_code,
               dt.Code AS data_type,
               ic.StartReleaseID AS start_release,
               ic.EndReleaseID AS end_release
        FROM KeyComposition kc
        INNER JOIN VariableVersion vv ON vv.VariableVID = kc.VariableVID
        INNER JOIN Item i ON vv.PropertyID = i.ItemID
        INNER JOIN ItemCategory ic ON ic.ItemID = i.ItemID
        INNER JOIN Property p ON vv.PropertyID = p.PropertyID
        LEFT JOIN DataType dt ON p.DataTypeID = dt.DataTypeID
        """

        session.execute(text(open_keys_query))
        session.commit()

        print("Open keys view created successfully")

    except Exception as e:
        print(f"Error creating open_keys view: {e}")
        raise
    finally:
        session.close()


def run_migration(file_name, sqlite_db_path):
    try:
        # Extract data from Access
        print("Extracting data from Access database...")
        data = extract_access_tables(file_name)

        # Migrate to SQLite
        print("Migrating data to SQLite...")
        engine = migrate_to_sqlite(data, sqlite_db_path)

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
    run_migration(args.database, sqlite_path)
