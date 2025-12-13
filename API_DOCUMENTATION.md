# pyDPM API Documentation

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
  - [MigrationAPI](#migrationapi)
  - [SyntaxAPI](#syntaxapi)
  - [SemanticAPI](#semanticapi)
  - [DataDictionaryValidator](#datadictionaryvalidator)
  - [Legacy API](#legacy-api)
- [CLI Reference](#cli-reference)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Overview

pyDPM is a comprehensive Python library for DPM-XL (Data Point Model eXtensible Language) data processing, migration, and analysis. It provides APIs for:

- **Database Migration**: Migrate data dictionary from MS Access databases to SQLite
- **Syntax Validation**: Validate DPM-XL expression syntax using ANTLR4 grammar
- **Semantic Analysis**: Perform comprehensive semantic validation of DPM-XL expressions
- **Data Dictionary Validation**: Validate data dictionary consistency and completeness

## Installation

```bash
# Install via Poetry (recommended)
poetry install

# Or using pip (if published to PyPI)
pip install pydpm
```

## Quick Start

```python
import pydpm
from pydpm.api import MigrationAPI, SyntaxAPI, SemanticAPI

# Database Migration
migration = MigrationAPI()
engine = migration.migrate_access_to_sqlite("data.mdb", "output.db")

# Syntax Validation
syntax = SyntaxAPI()
result = syntax.validate_expression("{tC_01.00, r0100, c0010}")
print(f"Valid syntax: {result.is_valid}")

# Semantic Analysis
semantic = SemanticAPI()
result = semantic.validate_expression("{tC_01.00, r0100, c0010} + {tC_01.00, r0200, c0010}")
print(f"Valid semantics: {result.is_valid}")
```

## API Reference

### MigrationAPI

The `MigrationAPI` class provides methods for database migration operations.

#### Class: `MigrationAPI`

```python
class MigrationAPI:
    def __init__(self)
    def migrate_access_to_sqlite(self, access_file_path: str, sqlite_db_path: Optional[str] = None) -> Engine
```

#### Methods

##### `migrate_access_to_sqlite(access_file_path, sqlite_db_path=None)`

Migrates data from an Access database to SQLite.

**Parameters:**
- `access_file_path` (str): Path to the Access database file (.mdb or .accdb)
- `sqlite_db_path` (Optional[str]): Path for the SQLite database. Defaults to "database.db" or `SQLITE_DB_PATH` environment variable

**Returns:**
- `Engine`: SQLAlchemy engine for the created SQLite database

**Raises:**
- `FileNotFoundError`: If the Access file doesn't exist
- `Exception`: If migration fails

**Example:**
```python
from pydpm.api import MigrationAPI

migration = MigrationAPI()
engine = migration.migrate_access_to_sqlite("data.mdb", "output.db")
print(f"Migration completed. Engine: {engine}")
```

#### Convenience Functions

```python
# Direct function usage
from pydpm.api.migration import migrate_access_to_sqlite
engine = migrate_access_to_sqlite("data.mdb", "output.db")
```

---

### SyntaxAPI

The `SyntaxAPI` class provides methods for DPM-XL syntax validation and parsing.

#### Class: `SyntaxAPI`

```python
class SyntaxAPI:
    def __init__(self)
    def validate_expression(self, expression: str) -> SyntaxValidationResult
    def parse_expression(self, expression: str) -> AST
    def is_valid_syntax(self, expression: str) -> bool
```

#### Data Classes

##### `SyntaxValidationResult`

```python
@dataclass
class SyntaxValidationResult:
    is_valid: bool                    # Whether the syntax is valid
    error_message: Optional[str]      # Error message if validation failed
    expression: str                   # The original expression that was validated
```

#### Methods

##### `validate_expression(expression)`

Validates the syntax of a DPM-XL expression.

**Parameters:**
- `expression` (str): The DPM-XL expression to validate

**Returns:**
- `SyntaxValidationResult`: Result containing validation status and details

**Example:**
```python
from pydpm.api import SyntaxAPI

syntax = SyntaxAPI()
result = syntax.validate_expression("{tC_01.00, r0100, c0010}")
print(f"Valid: {result.is_valid}")
if not result.is_valid:
    print(f"Error: {result.error_message}")
```

##### `parse_expression(expression)`

Parses a DPM-XL expression and returns the AST.

**Parameters:**
- `expression` (str): The DPM-XL expression to parse

**Returns:**
- `AST`: The Abstract Syntax Tree for the expression

**Raises:**
- `Exception`: If parsing fails

##### `is_valid_syntax(expression)`

Quick check if expression has valid syntax.

**Parameters:**
- `expression` (str): The DPM-XL expression to check

**Returns:**
- `bool`: True if syntax is valid, False otherwise

#### Convenience Functions

```python
from pydpm.api.syntax import validate_expression, is_valid_syntax

# Direct function usage
result = validate_expression("{tC_01.00, r0100, c0010}")
is_valid = is_valid_syntax("{tC_01.00, r0100, c0010}")
```

---

### SemanticAPI

The `SemanticAPI` class provides methods for DPM-XL semantic validation and analysis.

#### Class: `SemanticAPI`

```python
class SemanticAPI:
    def __init__(self)
    def validate_expression(self, expression: str) -> SemanticValidationResult
    def analyze_expression(self, expression: str) -> Dict[str, Any]
    def is_valid_semantics(self, expression: str) -> bool
```

#### Data Classes

##### `SemanticValidationResult`

```python
@dataclass
class SemanticValidationResult:
    is_valid: bool                    # Whether the semantic validation passed
    error_message: Optional[str]      # Error message if validation failed
    error_code: Optional[str]         # Error code if validation failed
    expression: str                   # The original expression that was validated
    validation_type: str              # Type of validation performed
    results: Optional[Any] = None     # Additional results from semantic analysis
```

#### Methods

##### `validate_expression(expression)`

Performs semantic validation on a DPM-XL expression.

This includes syntax validation, operands checking, data type validation, and structure validation.

**Parameters:**
- `expression` (str): The DPM-XL expression to validate

**Returns:**
- `SemanticValidationResult`: Result containing validation status and details

**Example:**
```python
from pydpm.api import SemanticAPI

semantic = SemanticAPI()
result = semantic.validate_expression("{tC_01.00, r0100, c0010} + {tC_01.00, r0200, c0010}")
print(f"Valid: {result.is_valid}")
if not result.is_valid:
    print(f"Error: {result.error_message} (Code: {result.error_code})")
```

##### `analyze_expression(expression)`

Performs detailed semantic analysis on a DPM-XL expression.

**Parameters:**
- `expression` (str): The DPM-XL expression to analyze

**Returns:**
- `Dict[str, Any]`: Detailed analysis results including data types and components

**Raises:**
- `Exception`: If analysis fails

##### `is_valid_semantics(expression)`

Quick check if expression has valid semantics.

**Parameters:**
- `expression` (str): The DPM-XL expression to check

**Returns:**
- `bool`: True if semantics are valid, False otherwise

#### Convenience Functions

```python
from pydpm.api.semantic import validate_expression, is_valid_semantics

# Direct function usage
result = validate_expression("{tC_01.00, r0100, c0010}")
is_valid = is_valid_semantics("{tC_01.00, r0100, c0010}")
```

---

### DataDictionaryValidator

The `DataDictionaryValidator` class provides methods for validating data dictionary consistency and completeness.

#### Class: `DataDictionaryValidator`

```python
class DataDictionaryValidator:
    def __init__(self)
    def validate_expression_references(self, dmp_xl_expression: str) -> List[ValidationIssue]
    def validate_table_exists(self, table_name: str) -> List[ValidationIssue]
    def validate_columns_exist(self, table_name: str, columns: List[str]) -> List[ValidationIssue]
    def validate_rows_exist(self, table_name: str, rows: List[str]) -> List[ValidationIssue]
    def validate_sheets_exist(self, table_name: str, sheets: List[str]) -> List[ValidationIssue]
    def validate_variables_exist(self, variable_names: List[str]) -> List[ValidationIssue]
    def get_validation_summary(self, issues: List[ValidationIssue]) -> Dict[str, Any]
```

#### Data Classes

##### `ValidationIssue`

```python
@dataclass
class ValidationIssue:
    issue_type: ValidationIssueType   # Type of the issue
    description: str                  # Human-readable description of the issue
    affected_element: str             # The specific element that has the issue
    suggested_fix: Optional[str]      # Suggested fix for the issue
    severity: str                     # Severity level ('error', 'warning', 'info')
    code: Optional[str]               # Error code for programmatic handling
```

##### `ValidationIssueType`

```python
class ValidationIssueType(Enum):
    MISSING_TABLE = "missing_table"
    MISSING_COLUMN = "missing_column"
    MISSING_ROW = "missing_row"
    MISSING_SHEET = "missing_sheet"
    MISSING_VARIABLE = "missing_variable"
    INVALID_REFERENCE = "invalid_reference"
    TYPE_MISMATCH = "type_mismatch"
    CONFIGURATION_ERROR = "configuration_error"
```

#### Methods

##### `validate_expression_references(dpm_xl_expression)`

Validates all cell references in a DPM-XL expression.

**Parameters:**
- `dpm_xl_expression` (str): The DPM-XL expression to validate

**Returns:**
- `List[ValidationIssue]`: List of validation issues found

**Example:**
```python
from pydpm.api.data_dictionary_validation import DataDictionaryValidator

validator = DataDictionaryValidator()
issues = validator.validate_expression_references("{tC_01.00, r0100, c0010}")
for issue in issues:
    print(f"{issue.severity.upper()}: {issue.description}")
```

##### `get_validation_summary(issues)`

Generates a summary of validation issues.

**Parameters:**
- `issues` (List[ValidationIssue]): List of validation issues

**Returns:**
- `Dict[str, Any]`: Summary statistics and categorized issues

#### Convenience Functions

```python
from pydpm.api.data_dictionary_validation import (
    validate_dpm_xl_expression,
    validate_table_references,
    check_data_dictionary_health
)

# Direct function usage
issues = validate_dpm_xl_expression("{tC_01.00, r0100, c0010}")
table_issues = validate_table_references(["C_01.00", "C_02.00"])
health_report = check_data_dictionary_health()
```

---

### Legacy API

The legacy `API` class combines all functionality for backward compatibility.

#### Class: `API`

```python
class API:
    def __init__(self)
    def syntax_validation(self, expression: str) -> None
    def create_ast(self, expression: str) -> None
    def semantic_validation(self, expression: str) -> Any
    def lexer(self, text: str) -> None
    def parser(self) -> bool
```

**Note:** The legacy API is maintained for backward compatibility. New projects should use the individual API classes (`MigrationAPI`, `SyntaxAPI`, `SemanticAPI`) instead.

---

## CLI Reference

### Commands

#### `pydpm migrate-access`

Migrates data from an Access database to SQLite.

```bash
poetry run pydpm migrate-access /path/to/database.accdb
```

**Arguments:**
- `ACCESS_FILE`: Path to the Access database file (.mdb or .accdb)

**Environment Variables:**
- `SQLITE_DB_PATH`: Path for the output SQLite database (default: "database.db")

#### `pydpm syntax`

Validates DPM-XL expression syntax.

```bash
poetry run pydpm syntax "{tC_01.00, r0100, c0010}"
```

**Arguments:**
- `EXPRESSION`: DPM-XL expression to validate

#### `pydpm semantic`

Performs semantic validation on DPM-XL expressions.

```bash
poetry run pydpm semantic "{tC_01.00, r0100, c0010} + {tC_01.00, r0200, c0010}" [OPTIONS]
```

**Arguments:**
- `EXPRESSION`: DPM-XL expression to analyze

**Options:**
- `--release-id INTEGER`: Release ID to use for validation
- `--dpm-version TEXT`: DPM Version (e.g. "4.2") to use for validation

---

## Data Models

### Core Data Types

The library uses several data types for representing DPM-XL concepts:

- **AST Nodes**: Abstract syntax tree representations of expressions
- **Cell References**: Structured references to table cells `{tTable, rRow, cColumn, sSheet}`
- **Operators**: Arithmetic, boolean, comparison, and aggregate operators
- **Data Types**: Scalar types, time classes, and type promotion rules

### Database Schema

The SQLite database schema includes tables for:
- `datapoints`: Main data storage
- `table_info`: Table metadata
- `Variable`: Variable definitions
- Various view definitions in `py_dpm/views/`

---

## Error Handling

### Exception Types

The library defines custom exceptions in `py_dpm.Exceptions`:

- `SemanticError`: Raised during semantic validation failures
- Custom error codes and messages for different validation scenarios

### Error Response Format

All validation results include structured error information:

```python
# Syntax validation
result = syntax.validate_expression("invalid expression")
if not result.is_valid:
    print(f"Error: {result.error_message}")

# Semantic validation  
result = semantic.validate_expression("invalid expression")
if not result.is_valid:
    print(f"Error: {result.error_message}")
    print(f"Code: {result.error_code}")

# Data dictionary validation
issues = validator.validate_expression_references("expression")
for issue in issues:
    print(f"{issue.severity}: {issue.description}")
    if issue.suggested_fix:
        print(f"  Fix: {issue.suggested_fix}")
```

---

## Examples

### Complete Migration and Validation Workflow

```python
from pydpm.api import MigrationAPI, SyntaxAPI, SemanticAPI
from pydpm.api.data_dictionary_validation import DataDictionaryValidator

# Step 1: Migrate database
print("Migrating database...")
migration = MigrationAPI()
engine = migration.migrate_access_to_sqlite("source.accdb", "target.db")
print("Migration completed.")

# Step 2: Validate expressions
expressions = [
    "{tC_01.00, r0100, c0010}",
    "{tC_01.00, r0100, c0010} + {tC_01.00, r0200, c0010}",
    "sum({tC_01.00, r*, c0010})"
]

syntax = SyntaxAPI()
semantic = SemanticAPI()
validator = DataDictionaryValidator()

for expr in expressions:
    print(f"\nValidating: {expr}")
    
    # Syntax check
    syntax_result = syntax.validate_expression(expr)
    print(f"  Syntax: {'✓' if syntax_result.is_valid else '✗'}")
    
    if syntax_result.is_valid:
        # Semantic check
        semantic_result = semantic.validate_expression(expr)
        print(f"  Semantics: {'✓' if semantic_result.is_valid else '✗'}")
        
        # Data dictionary check
        dd_issues = validator.validate_expression_references(expr)
        print(f"  Data Dictionary: {'✓' if not dd_issues else f'✗ ({len(dd_issues)} issues)'}")
        
        for issue in dd_issues:
            print(f"    - {issue.description}")
```

### Batch Processing

```python
from pydpm.api import SemanticAPI
import json

def process_expressions_batch(expressions):
    """Process multiple expressions and return results."""
    semantic = SemanticAPI()
    results = []
    
    for expr in expressions:
        try:
            result = semantic.validate_expression(expr)
            results.append({
                'expression': expr,
                'valid': result.is_valid,
                'error': result.error_message,
                'error_code': result.error_code
            })
        except Exception as e:
            results.append({
                'expression': expr,
                'valid': False,
                'error': str(e),
                'error_code': 'EXCEPTION'
            })
    
    return results

# Usage
expressions = [
    "{tC_01.00, r0100, c0010}",
    "{tC_01.00, r0200, c0010}",
    "invalid_expression"
]

results = process_expressions_batch(expressions)
print(json.dumps(results, indent=2))
```

### Custom Validation Pipeline

```python
from pydpm.api import SyntaxAPI, SemanticAPI
from pydpm.api.data_dictionary_validation import DataDictionaryValidator

class DPMValidationPipeline:
    def __init__(self):
        self.syntax = SyntaxAPI()
        self.semantic = SemanticAPI()
        self.dd_validator = DataDictionaryValidator()
    
    def validate_comprehensive(self, expression):
        """Perform comprehensive validation with detailed reporting."""
        report = {
            'expression': expression,
            'stages': {
                'syntax': {'passed': False, 'issues': []},
                'semantics': {'passed': False, 'issues': []},
                'data_dictionary': {'passed': False, 'issues': []}
            },
            'overall_result': False
        }
        
        # Stage 1: Syntax
        syntax_result = self.syntax.validate_expression(expression)
        report['stages']['syntax']['passed'] = syntax_result.is_valid
        if not syntax_result.is_valid:
            report['stages']['syntax']['issues'].append(syntax_result.error_message)
            return report  # Stop if syntax is invalid
        
        # Stage 2: Semantics
        semantic_result = self.semantic.validate_expression(expression)
        report['stages']['semantics']['passed'] = semantic_result.is_valid
        if not semantic_result.is_valid:
            report['stages']['semantics']['issues'].append(semantic_result.error_message)
        
        # Stage 3: Data Dictionary
        dd_issues = self.dd_validator.validate_expression_references(expression)
        report['stages']['data_dictionary']['passed'] = len(dd_issues) == 0
        for issue in dd_issues:
            report['stages']['data_dictionary']['issues'].append(issue.description)
        
        # Overall result
        report['overall_result'] = all(
            stage['passed'] for stage in report['stages'].values()
        )
        
        return report

# Usage
pipeline = DPMValidationPipeline()
result = pipeline.validate_comprehensive("{tC_01.00, r0100, c0010}")
print(f"Overall valid: {result['overall_result']}")
for stage_name, stage_data in result['stages'].items():
    print(f"{stage_name}: {'✓' if stage_data['passed'] else '✗'}")
    for issue in stage_data['issues']:
        print(f"  - {issue}")
```

---

## Version Information

- **Library Version**: 0.1.0
- **Python Requirements**: >=3.10
- **License**: GPL-3.0-or-later

For more information, visit the project repository or contact [info@meaningfuldata.eu](mailto:info@meaningfuldata.eu).