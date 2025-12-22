# pyDPM

## Installation

`poetry install`

## Database Configuration

pyDPM supports multiple database backends. It selects the connection method based on the following hierarchy of preference:

1.  **Explicit Argument**: Passing a connection URL or path directly in Python code overrides all configuration.
2.  **PostgreSQL**: If `USE_POSTGRES=true` in `.env`, it connects to the configured Postgres server.
3.  **SQLite**: If `USE_SQLITE=true` (default), it connects to a local SQLite file.
4.  **SQL Server**: Legacy fallback if no other option is selected.

### Environment Variables (.env)

Configure your database connection in the `.env` file:

```ini
# --- Option 1: SQLite (Default) ---
USE_SQLITE=true
SQLITE_DB_PATH=database.db

# --- Option 2: PostgreSQL ---
# USE_POSTGRES=true
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DB=dpm_db
# POSTGRES_USER=myuser
# POSTGRES_PASS=mypassword
```

## Usage

### Load DB

`poetry run pydpm migrate-access ./path-to-release.accdb`

### Syntax validation

`poetry run pydpm syntax "expression"`

### Semantic validation

`poetry run pydpm semantic "expression"`

