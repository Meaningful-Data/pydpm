# pyDPM

A Python library for processing DPM (Data Point Model) expressions and working with regulatory reporting data.

## Overview

pyDPM provides two main areas of functionality:

- **DPM-XL Processing**: Parse, validate, and generate ASTs for DPM-XL expressions
- **DPM Utilities**: Work with DPM databases, explore data dictionaries, and manage operation scopes

## Installation

### Using Poetry (Recommended)

```bash
poetry install
```

### Using pip

```bash
pip install .
```

## Architecture

```
py_dpm/
├── api/              # Public APIs
│   ├── dpm_xl/      # DPM-XL expression APIs
│   └── dpm/         # General DPM APIs
├── dpm_xl/          # DPM-XL Processing Engine
│   ├── grammar/     # ANTLR grammar
│   ├── ast/         # AST generation
│   ├── operators/   # Expression operators
│   ├── types/       # Type system
│   ├── validation/  # Validation logic
│   └── utils/       # DPM-XL utilities
├── dpm/             # General DPM Core
│   ├── db/          # Database models & views
│   ├── scopes/      # Operation scopes
│   └── explorer/    # Data dictionary explorer
├── cli/             # Command-line interface
├── exceptions/      # Custom exceptions
└── utils/           # Shared utilities
```

## Database Configuration

pyDPM supports multiple database backends. It selects the connection method based on the following hierarchy of preference:

1.  **Explicit Argument**: Passing a connection URL or path directly in Python code overrides all configuration.
2.  **Unified RDBMS Configuration**: If `PYDPM_RDBMS` and the `PYDPM_DB_*` variables are set, it connects to the configured server database.
3.  **Legacy PostgreSQL**: If `USE_POSTGRES=true` in `.env`, it connects to the configured Postgres server.
4.  **SQLite**: If `USE_SQLITE=true` (default), it connects to a local SQLite file.
5.  **SQL Server**: Legacy fallback if no other option is selected.

### Environment Variables (.env)

Configure your database connection in the `.env` file:

```ini
# --- Option 1: SQLite (Default) ---
USE_SQLITE=true
SQLITE_DB_PATH=database.db

# --- Option 2: Unified server database (recommended) ---
# PYDPM_RDBMS=postgres        # or "sqlserver"
# PYDPM_DB_HOST=localhost
# PYDPM_DB_PORT=5432          # defaults: 5432 for postgres, 1433 for sqlserver
# PYDPM_DB_NAME=dpm_db
# PYDPM_DB_USER=myuser
# PYDPM_DB_PASSWORD=mypassword

# --- Option 3: Legacy PostgreSQL (backward compatible) ---
# USE_POSTGRES=true
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DB=dpm_db
# POSTGRES_USER=myuser
# POSTGRES_PASS=mypassword
```

## Usage

### Command Line Interface

#### Migrate Access Database
```bash
poetry run pydpm migrate-access ./path-to-release.accdb
```

#### Syntax Validation
```bash
poetry run pydpm syntax "{tT_01.00, r0010, c0010}"
```

#### Semantic Validation
```bash
poetry run pydpm semantic "{tT_01.00, r0010, c0010}"
```

### Python API

#### DPM-XL Expression Processing

```python
from py_dpm.api import SyntaxAPI, SemanticAPI, ASTGenerator

# Syntax validation
syntax_api = SyntaxAPI()
is_valid = syntax_api.is_valid_syntax("{tT_01.00, r0010, c0010}")
print(f"Valid syntax: {is_valid}")

# Get detailed syntax errors
errors = syntax_api.validate_syntax("invalid expression")
for error in errors:
    print(f"Line {error.line}, Col {error.column}: {error.message}")

# Generate AST
ast_gen = ASTGenerator()
ast = ast_gen.generate("{tT_01.00, r0010, c0010}")
print(f"AST: {ast}")

# Semantic validation (requires database)
semantic_api = SemanticAPI()
result = semantic_api.validate("{tT_01.00, r0010, c0010}", release_id=123)
if result.is_valid:
    print("Semantically valid!")
else:
    for error in result.errors:
        print(f"Error: {error.message}")
```

#### Working with DPM Database

```python
from py_dpm.api import DataDictionaryAPI, DPMExplorer

# Query data dictionary
dd_api = DataDictionaryAPI()

# Get all tables
tables = dd_api.get_all_tables(release_id=123)
for table in tables:
    print(f"Table: {table.code} - {table.name}")

# Get table details
table = dd_api.get_table_by_code("T_01.00", release_id=123)
print(f"Table headers: {len(table.headers)}")

# Explore database structure
explorer = DPMExplorer()
modules = explorer.get_modules(release_id=123)
for module in modules:
    print(f"Module: {module.code}")
```

#### Operation Scopes

```python
from py_dpm.api import OperationScopesAPI, calculate_scopes_from_expression

# Calculate scopes for an expression
scopes_api = OperationScopesAPI()
result = calculate_scopes_from_expression(
    expression="{tT_01.00, r0010, c0010}",
    release_id=123
)

if result.success:
    for scope in result.scopes:
        print(f"Table: {scope.table_code}")
        print(f"Headers: {[h.header_code for h in scope.headers]}")
else:
    print(f"Error: {result.error}")
```

#### Validations Script Generation

```python
from py_dpm.api import generate_validations_script

# Generate engine-ready validations script
result = generate_validations_script(
    "{tT_01.00, r0010, c0010}",
    database_path="data.db",
    release_code="4.2"
)
if result["success"]:
    print(f"Enriched AST: {result['enriched_ast']}")
else:
    print(f"Error: {result['error']}")
```

#### Migration

```python
from py_dpm.api import MigrationAPI

# Migrate Access database to SQLAlchemy
migration_api = MigrationAPI()
migration_api.migrate_from_access(
    access_db_path="./release.accdb",
    release_id=123
)
```

#### XBRL-CSV Instance Generation

```python
from py_dpm.api import InstanceAPI

api = InstanceAPI()

# Build package from dictionary
data = {
    "module_code": "F_01.01",
    "parameters": {"refPeriod": "2024-12-31"},
    "facts": [
        {"table_code": "t001", "row_code": "r010", "column_code": "c010", "value": 1000000}
    ]
}
output_path = api.build_package_from_dict(data, "/tmp/output")

# Build package from JSON file
output_path = api.build_package_from_json("instance_data.json", "/tmp/output")
```

#### DPM Explorer - Introspection Queries

```python
from py_dpm.api import ExplorerQueryAPI

with ExplorerQueryAPI() as api:
    # Find all properties using a specific item
    properties = api.get_properties_using_item("EUR")

    # Get module URL for documentation
    url = api.get_module_url(module_code="F_01.01")

    # Explore variable usage
    tables = api.get_tables_using_variable(variable_code="mi123")
```

#### Hierarchical Queries

```python
from py_dpm.api import HierarchicalQueryAPI

with HierarchicalQueryAPI() as api:
    # Get hierarchy for a domain
    hierarchy = api.get_hierarchy(domain_code="DOM_001")

    # Navigate parent-child relationships
    children = api.get_children(item_code="PARENT_001")

    # Get all ancestors
    ancestors = api.get_ancestors(item_code="LEAF_001")
```

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Structure

- See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed API reference
- See [REORGANIZATION_SUMMARY.md](REORGANIZATION_SUMMARY.md) for reorganization details

## Important Notes

### ANTLR Version
This project uses **ANTLR 4.9.2**. Always run Python scripts using Poetry to ensure the correct runtime version:

```bash
poetry run python your_script.py  # ✅ Correct
python your_script.py             # ❌ May use wrong ANTLR version
```

### Database Sessions
When using database APIs without explicit connection configuration, pyDPM uses global session management. For concurrent usage or testing, pass explicit database paths or connection URLs:

```python
api = DataDictionaryAPI(database_path="./test.db")
# or
api = DataDictionaryAPI(connection_url="postgresql://user:pass@localhost/db")
```

## License

[Add your license information here]
