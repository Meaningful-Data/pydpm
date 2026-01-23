# pyDPM API Documentation

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
  - [DPM-XL APIs](#dpm-xl-apis)
    - [SyntaxAPI](#syntaxapi)
    - [SemanticAPI](#semanticapi)
    - [ASTGenerator](#astgenerator)
    - [Complete AST Functions](#complete-ast-functions)
  - [General DPM APIs](#general-dpm-apis)
    - [MigrationAPI](#migrationapi)
    - [DataDictionaryAPI](#datadictionaryapi)
    - [DPMExplorer](#dpmexplorer)
    - [OperationScopesAPI](#operationscopesapi)
- [CLI Reference](#cli-reference)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Overview

pyDPM is a comprehensive Python library for DPM (Data Point Model) processing, with specialized support for DPM-XL (Data Point Model eXtensible Language). The library is organized into two main areas:

- **DPM-XL Processing** (`py_dpm.api.dpm_xl`): Expression parsing, syntax validation, semantic analysis, and AST generation
- **General DPM Utilities** (`py_dpm.api.dpm`): Database operations, data dictionary queries, DPM exploration, and migration

### Key Features

- **Database Migration**: Migrate data dictionaries from MS Access to SQLite/PostgreSQL
- **Syntax Validation**: Validate DPM-XL expression syntax using ANTLR4 grammar
- **Semantic Analysis**: Comprehensive semantic validation with type checking
- **AST Generation**: Build and analyze Abstract Syntax Trees
- **Data Dictionary Queries**: ORM-based queries for tables, columns, items, and properties
- **DPM Exploration**: Introspection and "inverse" queries on DPM structure
- **Operation Scopes**: Calculate module scopes from expressions

## Installation

```bash
# Using Poetry (recommended)
poetry install

# Or using pip (when published)
pip install pydpm-xl
```

## Architecture

The library follows a clear architectural separation:

```
py_dpm/
├── api/                    # Public API Layer
│   ├── dpm_xl/            # DPM-XL specific APIs
│   │   ├── syntax.py      # Syntax validation
│   │   ├── semantic.py    # Semantic validation
│   │   ├── ast_generator.py  # AST generation
│   │   └── complete_ast.py   # Complete AST with metadata
│   └── dpm/               # General DPM APIs
│       ├── migration.py   # Database migration
│       ├── data_dictionary.py  # Data dictionary queries
│       ├── explorer.py    # DPM exploration
│       └── operation_scopes.py # Scope calculation
├── dpm_xl/                # DPM-XL Processing Engine
│   ├── grammar/           # ANTLR grammar & parsers
│   ├── ast/              # AST construction & manipulation
│   ├── operators/        # Operator implementations
│   ├── types/           # Type system
│   └── validation/      # Validation logic
└── dpm/                  # General DPM Core
    ├── db/              # Database layer (models, utils, migration)
    ├── scopes/          # Operation scope management
    └── explorer/        # DPM introspection
```

## Quick Start

### Basic Usage

```python
from py_dpm.api import (
    SyntaxAPI,          # DPM-XL syntax validation
    SemanticAPI,        # DPM-XL semantic validation
    DataDictionaryAPI,  # Data dictionary queries
    DPMExplorer,        # DPM exploration
    MigrationAPI,       # Database migration
)

# Syntax Validation
syntax_api = SyntaxAPI()
is_valid = syntax_api.is_valid_syntax("{tC_01.00, r0100, c0010}")
print(f"Valid syntax: {is_valid}")  # True

# Semantic Analysis
semantic_api = SemanticAPI(database_path="data.db")
result = semantic_api.validate_expression(
    "{tC_01.00, r0100, c0010} + {tC_01.00, r0200, c0010}"
)
print(f"Valid semantics: {result.is_valid}")

# Data Dictionary Query
dd_api = DataDictionaryAPI(database_path="data.db")
properties = dd_api.get_all_properties()
print(f"Found {len(properties)} properties")

# Database Migration
migration_api = MigrationAPI()
engine = migration_api.migrate_access_to_sqlite("data.mdb", "output.db")
```

### Using Poetry Environment

```bash
# Always use poetry run for correct dependencies
poetry run python your_script.py

# Or activate the virtual environment
poetry shell
python your_script.py
```

## API Reference

## DPM-XL APIs

APIs for DPM-XL expression processing, located in `py_dpm.api.dpm_xl`.

### SyntaxAPI

Validates DPM-XL expression syntax using ANTLR4 grammar.

#### Class: `SyntaxAPI`

```python
from py_dpm.api.dpm_xl import SyntaxAPI

class SyntaxAPI:
    def __init__(self)
    def is_valid_syntax(self, expression: str) -> bool
    def validate_expression(self, expression: str) -> bool
    def parse_expression(self, expression: str)
```

#### Methods

##### `is_valid_syntax(expression)`

Validates the syntax of a DPM-XL expression.

**Parameters:**
- `expression` (str): The DPM-XL expression to validate

**Returns:**
- `bool`: True if syntax is valid, False otherwise

**Example:**
```python
from py_dpm.api import SyntaxAPI

api = SyntaxAPI()

# Valid expression
is_valid = api.is_valid_syntax("{tC_01.00, r0100, c0010}")
print(is_valid)  # True

# Invalid expression
is_valid = api.is_valid_syntax("{invalid syntax")
print(is_valid)  # False
```

##### `validate_expression(expression)`

Alias for `is_valid_syntax()`.

##### `parse_expression(expression)`

Parses an expression and returns the parse tree.

**Parameters:**
- `expression` (str): The DPM-XL expression to parse

**Returns:**
- Parse tree object

---

### SemanticAPI

Performs comprehensive semantic validation of DPM-XL expressions.

#### Class: `SemanticAPI`

```python
from py_dpm.api.dpm_xl import SemanticAPI

class SemanticAPI:
    def __init__(self, database_path: Optional[str] = None,
                 connection_url: Optional[str] = None)
    def validate_expression(self, expression: str,
                          release_id: Optional[int] = None) -> SemanticValidationResult
    def validate_batch(self, expressions: List[str],
                      release_id: Optional[int] = None) -> List[SemanticValidationResult]
```

#### Methods

##### `__init__(database_path=None, connection_url=None)`

Initialize the Semantic API with database connection.

**Parameters:**
- `database_path` (Optional[str]): Path to SQLite database
- `connection_url` (Optional[str]): SQLAlchemy connection URL (PostgreSQL, MySQL, etc.)

**Example:**
```python
# SQLite
api = SemanticAPI(database_path="data.db")

# PostgreSQL
api = SemanticAPI(connection_url="postgresql://user:pass@localhost/dbname")

# Use environment variables
# - PYDPM_RDBMS / PYDPM_DB_* for server databases (recommended)
# - or SQLITE_DB_PATH for SQLite (default)
api = SemanticAPI()
```

##### `validate_expression(expression, release_id=None)`

Validates the semantics of a DPM-XL expression.

**Parameters:**
- `expression` (str): The DPM-XL expression to validate
- `release_id` (Optional[int]): DPM release ID for validation context

**Returns:**
- `SemanticValidationResult`: Object with validation results

**Example:**
```python
from py_dpm.api import SemanticAPI

api = SemanticAPI(database_path="data.db")

result = api.validate_expression("{tC_01.00, r0100, c0010} + {tC_01.00, r0200, c0010}")

if result.is_valid:
    print("✓ Expression is semantically valid")
    print(f"Result type: {result.result_type}")
else:
    print("✗ Validation failed")
    for error in result.errors:
        print(f"  - {error}")
```

##### `validate_batch(expressions, release_id=None)`

Validates multiple expressions in batch.

**Parameters:**
- `expressions` (List[str]): List of expressions to validate
- `release_id` (Optional[int]): DPM release ID

**Returns:**
- `List[SemanticValidationResult]`: List of validation results

---

### ASTGenerator

Generates Abstract Syntax Trees from DPM-XL expressions.

#### Class: `ASTGenerator`

```python
from py_dpm.api.dpm_xl import ASTGenerator

class ASTGenerator:
    def __init__(self)
    def generate_ast(self, expression: str) -> dict
    def generate_batch(self, expressions: List[str]) -> List[dict]
```

#### Methods

##### `generate_ast(expression)`

Generates an AST from a DPM-XL expression.

**Parameters:**
- `expression` (str): The DPM-XL expression

**Returns:**
- `dict`: AST representation as dictionary

**Example:**
```python
from py_dpm.api import ASTGenerator

generator = ASTGenerator()
ast = generator.generate_ast("{tC_01.00, r0100, c0010} + 5")

print(ast)
# {
#   'type': 'BinOp',
#   'operator': '+',
#   'left': {'type': 'CellRef', ...},
#   'right': {'type': 'Constant', 'value': 5}
# }
```

---

### Validations Script Function

Generate engine-ready validations scripts with framework structure.

#### Function

```python
from py_dpm.api.dpm_xl import generate_validations_script
```

##### `generate_validations_script(expressions, database_path=None, connection_url=None, release_code=None, ...)`

Generates an engine-ready validations script with AST and framework structure.

**Parameters:**
- `expressions`: Single expression string or list of (expression, operation_code, precondition) tuples
- `database_path` (Optional[str]): Path to SQLite database
- `connection_url` (Optional[str]): PostgreSQL connection URL
- `release_code` (Optional[str]): DPM release code (e.g., "4.2")
- `module_code` (Optional[str]): Module code (e.g., "FINREP9")

**Returns:**
- `dict`: `{'success': bool, 'enriched_ast': dict, 'error': str}`

**Example:**
```python
from py_dpm.api.dpm_xl import generate_validations_script

result = generate_validations_script(
    "{tC_01.00, r0100, c0010}",
    database_path="data.db",
    release_code="4.2"
)

if result["success"]:
    print(result["enriched_ast"])
```

---

## General DPM APIs

APIs for general DPM operations, located in `py_dpm.api.dpm`.

### MigrationAPI

Migrates data dictionaries from MS Access to SQLite/PostgreSQL.

#### Class: `MigrationAPI`

```python
from py_dpm.api.dpm import MigrationAPI

class MigrationAPI:
    def __init__(self)
    def migrate_access_to_sqlite(self, access_file_path: str,
                                 sqlite_db_path: Optional[str] = None) -> Engine
```

#### Methods

##### `migrate_access_to_sqlite(access_file_path, sqlite_db_path=None)`

Migrates an Access database to SQLite.

**Parameters:**
- `access_file_path` (str): Path to Access .mdb or .accdb file
- `sqlite_db_path` (Optional[str]): Output SQLite path (default: "database.db")

**Returns:**
- `Engine`: SQLAlchemy engine for the SQLite database

**Example:**
```python
from py_dpm.api import MigrationAPI

api = MigrationAPI()
engine = api.migrate_access_to_sqlite("data.mdb", "output.db")
print(f"✓ Migration complete: {engine}")
```

---

### DataDictionaryAPI

Query and validate data dictionary elements.

#### Class: `DataDictionaryAPI`

```python
from py_dpm.api.dpm import DataDictionaryAPI

class DataDictionaryAPI:
    def __init__(self, database_path: Optional[str] = None,
                 connection_url: Optional[str] = None)

    # Query methods
    def get_all_properties(self) -> List[Property]
    def get_property_by_code(self, code: str) -> Optional[Property]
    def get_all_items(self) -> List[Item]
    def get_item_by_code(self, code: str) -> Optional[Item]
    def get_tables_by_module(self, module_code: str) -> List[TableVersion]
    # ... many more methods
```

#### Key Methods

##### `get_all_properties()`

Retrieves all properties from the data dictionary.

**Returns:**
- `List[Property]`: List of Property objects

**Example:**
```python
from py_dpm.api import DataDictionaryAPI

api = DataDictionaryAPI(database_path="data.db")
properties = api.get_all_properties()

for prop in properties:
    print(f"{prop.code}: {prop.name}")
```

##### `get_property_by_code(code)`

Gets a specific property by its code.

**Parameters:**
- `code` (str): Property code

**Returns:**
- `Optional[Property]`: Property object or None

##### `get_tables_by_module(module_code)`

Gets all tables in a module.

**Parameters:**
- `module_code` (str): Module code

**Returns:**
- `List[TableVersion]`: List of table versions

---

### DPMExplorer

Explore and introspect DPM structure with "inverse" queries.

#### Class: `DPMExplorer`

```python
from py_dpm.api.dpm import DPMExplorer

class DPMExplorer:
    def __init__(self, database_path: Optional[str] = None,
                 connection_url: Optional[str] = None)

    def get_properties_using_item(self, item_code: str) -> List[PropertyInfo]
    def get_tables_containing_property(self, property_code: str) -> List[TableInfo]
    def explore_hierarchy(self, starting_point: str) -> dict
```

#### Methods

##### `get_properties_using_item(item_code)`

Finds all properties that use a specific item.

**Parameters:**
- `item_code` (str): Item code to search for

**Returns:**
- `List[PropertyInfo]`: Properties using this item

**Example:**
```python
from py_dpm.api import DPMExplorer

explorer = DPMExplorer(database_path="data.db")
properties = explorer.get_properties_using_item("i001")

for prop in properties:
    print(f"Property {prop.code} uses item i001")
```

---

### OperationScopesAPI

Calculate operation scopes and module dependencies.

#### Class: `OperationScopesAPI`

```python
from py_dpm.api.dpm import OperationScopesAPI

class OperationScopesAPI:
    def __init__(self, database_path: Optional[str] = None,
                 connection_url: Optional[str] = None)

    def calculate_scopes(self, expression: str) -> OperationScopeResult
    def get_scopes_metadata(self, scope_ids: List[int]) -> List[OperationScopeDetailedInfo]
```

#### Methods

##### `calculate_scopes(expression)`

Calculates operation scopes from an expression.

**Parameters:**
- `expression` (str): DPM-XL expression

**Returns:**
- `OperationScopeResult`: Calculated scopes

**Example:**
```python
from py_dpm.api import OperationScopesAPI

api = OperationScopesAPI(database_path="data.db")
result = api.calculate_scopes("{tC_01.00, r0100, c0010}")

print(f"Module versions involved: {result.module_versions}")
```

---

## CLI Reference

PyDPM provides a command-line interface for common operations.

### Installation

The CLI is installed automatically with the package:

```bash
poetry install
```

### Commands

#### `pydpm migrate-access`

Migrate an Access database to SQLite.

```bash
pydpm migrate-access <access_file> [--output <sqlite_file>]
```

**Options:**
- `access_file`: Path to .mdb or .accdb file
- `--output`: Output SQLite file path (default: database.db)

**Example:**
```bash
pydpm migrate-access data.mdb --output output.db
```

#### `pydpm syntax`

Validate DPM-XL expression syntax.

```bash
pydpm syntax "<expression>"
```

**Example:**
```bash
pydpm syntax "{tC_01.00, r0100, c0010} + 5"
```

#### `pydpm semantic`

Validate DPM-XL expression semantics.

```bash
pydpm semantic "<expression>" [--release-id <id>] [--dpm-version <version>]
```

**Options:**
- `--release-id`: DPM release ID
- `--dpm-version`: DPM version string

**Example:**
```bash
pydpm semantic "{tC_01.00, r0100, c0010}" --release-id 5
```

#### `pydpm calculate-scopes`

Calculate operation scopes from expression.

```bash
pydpm calculate-scopes "<expression>"
```

---

## Data Models

### ModuleVersion

The `ModuleVersion` model represents a version of a module in the DPM data dictionary.

#### Class Methods

##### `ModuleVersion.get_from_release_id(session, release_id, module_id=None, module_code=None)`

Get the module version applicable to a given release for a specific module.

**Parameters:**
- `session`: SQLAlchemy session
- `release_id` (int): The release ID to filter for
- `module_id` (Optional[int]): Module ID to filter by (mutually exclusive with `module_code`)
- `module_code` (Optional[str]): Module code to filter by (mutually exclusive with `module_id`)

**Returns:**
- `ModuleVersion`: The applicable module version instance, or `None` if not found

**Raises:**
- `ValueError`: If neither `module_id` nor `module_code` is provided, or if both are provided

**Special Behavior:**
If the resulting module version has `fromreferencedate == toreferencedate`, the method returns the previous module version for the same module instead. This handles cases where a module version has an empty date range and the previous version should be used.

This serves to manage those dummy modules versions for which the FromReferenceDate = ToReferenceDate, which in practice do not exist.

**Example:**
```python
from py_dpm.dpm.models import ModuleVersion
from sqlalchemy.orm import Session

# Get module version by module_code
module_version = ModuleVersion.get_from_release_id(
    session,
    release_id=4,
    module_code="FINREP9"
)

if module_version:
    print(f"Module: {module_version.code}")
    print(f"Start Release: {module_version.start_release.releaseid}")
    print(f"From Date: {module_version.fromreferencedate}")
    print(f"To Date: {module_version.toreferencedate}")

# Get module version by module_id
module_version = ModuleVersion.get_from_release_id(
    session,
    release_id=4,
    module_id=123
)
```

---

### Common Data Types

Located in `py_dpm.api.dpm.types`:

```python
from py_dpm.api.dpm.types import (
    ModuleVersionInfo,
    TableVersionInfo,
    HeaderVersionInfo,
)
```

#### `ModuleVersionInfo`

```python
@dataclass
class ModuleVersionInfo:
    module_code: str
    module_name: str
    version_code: str
    version_id: int
```

#### `TableVersionInfo`

```python
@dataclass
class TableVersionInfo:
    table_code: str
    table_name: str
    version_code: str
    module_code: str
```

---

## Error Handling

### Exception Types

Located in `py_dpm.exceptions`:

```python
from py_dpm.exceptions import (
    DrrException,      # Base exception
    SyntaxError,       # Syntax validation errors
    SemanticError,     # Semantic validation errors
    DataTypeError,     # Type-related errors
    ScriptingError,    # Scripting errors
)
```

### Example Error Handling

```python
from py_dpm.api import SemanticAPI
from py_dpm.exceptions import SemanticError

api = SemanticAPI(database_path="data.db")

try:
    result = api.validate_expression("{invalid}")
except SemanticError as e:
    print(f"Semantic error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Examples

### Complete Validation Workflow

```python
from py_dpm.api import SyntaxAPI, SemanticAPI

expression = "{tC_01.00, r0100, c0010} + {tC_01.00, r0200, c0010}"

# Step 1: Syntax validation
syntax_api = SyntaxAPI()
if not syntax_api.is_valid_syntax(expression):
    print("✗ Invalid syntax")
    exit(1)

print("✓ Syntax valid")

# Step 2: Semantic validation
semantic_api = SemanticAPI(database_path="data.db")
result = semantic_api.validate_expression(expression)

if result.is_valid:
    print("✓ Semantics valid")
    print(f"Result type: {result.result_type}")
else:
    print("✗ Semantic errors:")
    for error in result.errors:
        print(f"  - {error}")
```

### Database Query Example

```python
from py_dpm.api import DataDictionaryAPI

api = DataDictionaryAPI(database_path="data.db")

# Get all properties
properties = api.get_all_properties()
print(f"Total properties: {len(properties)}")

# Get specific property
prop = api.get_property_by_code("p001")
if prop:
    print(f"Property: {prop.name}")

    # Get items used by this property
    items = api.get_items_by_property(prop.code)
    print(f"Uses {len(items)} items")
```

### DPM Exploration Example

```python
from py_dpm.api import DPMExplorer

explorer = DPMExplorer(database_path="data.db")

# Find which properties use a specific item
properties = explorer.get_properties_using_item("i001")
print(f"Item i001 is used in {len(properties)} properties:")
for prop in properties:
    print(f"  - {prop.code}: {prop.name}")

# Find tables containing a property
tables = explorer.get_tables_containing_property("p001")
print(f"\nProperty p001 appears in {len(tables)} tables:")
for table in tables:
    print(f"  - {table.code}: {table.name}")
```

---

## Best Practices

### 1. Use Poetry Environment

Always use Poetry to ensure correct dependency versions:

```bash
poetry run python your_script.py
```

### 2. Database Connection

Prefer connection URLs for flexibility:

```python
# Good - supports multiple databases
api = SemanticAPI(connection_url="postgresql://localhost/dpm")

# Also good - simple SQLite
api = SemanticAPI(database_path="data.db")
```

### 3. Error Handling

Always handle exceptions appropriately:

```python
from py_dpm.exceptions import SemanticError

try:
    result = api.validate_expression(expr)
except SemanticError as e:
    logger.error(f"Validation failed: {e}")
    # Handle gracefully
```

### 4. Batch Operations

Use batch methods for multiple validations:

```python
# Efficient
results = semantic_api.validate_batch(expressions)

# Less efficient
results = [semantic_api.validate_expression(e) for e in expressions]
```

---

## Version Information

- **Library Version:** 0.2.4
- **Python Requirements:** >=3.10
- **ANTLR Version:** 4.9.2
- **SQLAlchemy Version:** 1.4.50

---

## Support and Contributing

For issues, questions, or contributions, please visit:
- GitHub: https://github.com/Meaningful-Data/pydpm

---

*Last Updated: 2025-12-22*
*After major reorganization separating DPM-XL from general DPM functionality*
