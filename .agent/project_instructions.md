# pyDPM Project Context & Instructions

Always run with poetry.


## Strategic Objective
**pyDPM** is designed to be a comprehensive, open-source **Data Point Model (DPM)** library. While its current implementation focuses heavily on **DPM-XL** (Data Point Model eXtensible Language), its strategic goal is to serve as a general-purpose toolkit for all DPM-related operations.

The library aims to facilitate not just the processing of DPM-XL expressions, but also the broader **exploration, querying, and understanding of DPM structures** (e.g., identifying which items belong to a specific property, analyzing hierarchies, and managing metadata).

## Core Capabilities & Vision

### 1. DPM-XL Processing (Current Core)
*   **Syntax & Semantics**: Robust parsing and semantic validation of DPM-XL expressions (e.g., `{tC_01.00, r0100, c0010}`).
*   **Validation Rules**: Enforcing data type correctness, operand validity, and structural integrity.
*   **AST Generation**: Generate abstract syntax trees from DPM-XL expressions with optional metadata enrichment.

### 2. DPM Querying & Exploration (Expanding Scope)
*   **Metadata Analysis**: Tools to query and understand the relationships within the DPM.
    *   *Example*: "What items are associated with Property X?"
    *   *Example*: "Retrieve the hierarchy of table Y."
*   **Structural Navigation**: Functions to traverse the complex web of Dimensions, Domains, and Members.
*   **Operation Scopes**: Calculate and retrieve operation scopes for expressions.

### 3. Data Management & Migration
*   **Database Migration**: Converting legacy DPM storage formats (MS Access) into modern, queryable schemas (SQLite/PostgreSQL).
*   **Data Dictionary Validation**: Ensuring the consistency of the underlying metadata (tables, rows, columns).

## Code Organization (Updated: December 2025)

The codebase has been reorganized to cleanly separate DPM-XL processing from general DPM utilities:

```
py_dpm/
├── api/                    # Public APIs (entry point for users)
│   ├── dpm_xl/            # DPM-XL specific APIs
│   │   ├── syntax.py      # SyntaxAPI
│   │   ├── semantic.py    # SemanticAPI
│   │   ├── ast_generator.py  # ASTGenerator
│   │   └── complete_ast.py   # Complete/Enriched AST functions
│   └── dpm/               # General DPM APIs
│       ├── migration.py   # MigrationAPI
│       ├── data_dictionary.py  # DataDictionaryAPI
│       ├── explorer.py    # DPMExplorer
│       └── operation_scopes.py  # OperationScopesAPI
│
├── dpm_xl/                # DPM-XL Processing Engine (internal)
│   ├── grammar/           # ANTLR grammar & generated code
│   ├── ast/               # AST generation & manipulation
│   ├── operators/         # Expression operators
│   ├── types/             # Type system & validation
│   ├── validation/        # Semantic validation logic
│   └── utils/             # DPM-XL specific utilities
│
├── dpm/                   # General DPM Core (internal)
│   ├── db/                # Database models, views, utilities
│   │   ├── models.py      # SQLAlchemy ORM models
│   │   ├── views/         # SQL views for complex queries
│   │   └── utils.py       # Session management
│   ├── scopes/            # Operation scope calculation
│   └── explorer/          # Data dictionary exploration
│
├── cli/                   # Command-line interface
│   └── main.py           # CLI entry point (pydpm command)
│
├── exceptions/            # Shared exception classes
│   ├── exceptions.py     # DrrException, SyntaxError, SemanticError
│   └── messages.py       # Centralized error messages
│
└── utils/                 # Shared utilities
```

### Key Architectural Principles

1. **Clear Separation**: DPM-XL processing (`dpm_xl/`) is completely separated from general DPM utilities (`dpm/`)
2. **API-First**: All user-facing functionality is exposed through clean APIs in `api/`
3. **Internal Isolation**: Users should import from `py_dpm.api`, not from internal modules
4. **Database Flexibility**: Supports SQLite, PostgreSQL, and other SQLAlchemy backends

### Public API Structure

```python
# Import DPM-XL APIs
from py_dpm.api import SyntaxAPI, SemanticAPI, ASTGenerator
from py_dpm.api import generate_complete_ast, generate_enriched_ast

# Import General DPM APIs
from py_dpm.api import MigrationAPI, DataDictionaryAPI, DPMExplorer, OperationScopesAPI

# Import convenience functions and types
from py_dpm.api import calculate_scopes_from_expression, get_existing_scopes
from py_dpm.api import ModuleVersionInfo, TableVersionInfo, HeaderVersionInfo
```

## Instructions for Future Development

When working on this codebase, always consider the **General DPM Context**:

### Architectural Guidelines
*   **Extensibility**: Design features that can apply to general DPM concepts, not just the specific implementation details of DPM-XL 1.0.
*   **Query-First**: Prioritize capabilities that help users ask questions about their data model (introspection).
*   **Independence**: While DPM-XL is a major use case, keep the core DPM data structures (Dimensions, Properties, Members) clean and potentially reusable for other DPM serialization formats if needed.
*   **API Consistency**: All new functionality should be exposed through appropriate API classes in `py_dpm/api/`
*   **Separation of Concerns**: Keep DPM-XL specific code in `dpm_xl/` and general DPM code in `dpm/`

### Important Technical Notes

1. **ANTLR Version**: This project uses ANTLR 4.9.2. Always run scripts with `poetry run python` to ensure correct runtime version.

2. **Import Paths**:
   - ✅ Users should import from: `from py_dpm.api import ...`
   - ❌ Users should NOT import from: `from py_dpm.dpm_xl.ast import ...`

3. **Database Sessions**:
   - Global session managed by `py_dpm.dpm.db.utils.get_session()`
   - APIs support explicit database paths or connection URLs for isolation

4. **Circular Dependencies**:
   - Use lazy imports within functions when needed
   - Avoid top-level imports that create circular dependencies

5. **Legacy Code**:
   - Legacy implementations in `_legacy/` directory
   - Do not delete - may be needed for reference
   - Old `API` class still exists for backward compatibility but is deprecated

### Development Workflow

1. **Making Changes**: Always use Poetry for dependency management and script execution
2. **Testing**: Run tests with `poetry run pytest`
3. **Adding APIs**: New public APIs should go in `py_dpm/api/` with appropriate submodule
4. **Documentation**: Update API_DOCUMENTATION.md when adding new public APIs
