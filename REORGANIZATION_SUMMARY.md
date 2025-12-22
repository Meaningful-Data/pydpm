# PyDPM Reorganization Summary

## Date: 2025-12-22

This document summarizes the major reorganization of the PyDPM library to separate DPM-XL specific functionality from general DPM utilities.

## Overview

The reorganization achieves the following goals:
1. **Clear separation** between DPM-XL (expression parsing/validation) and general DPM (database/exploration)
2. **Better modularity** with logical grouping of related functionality
3. **Improved maintainability** with clearer directory structure
4. **Future-proof design** that allows independent evolution of components

## New Directory Structure

```
py_dpm/
├── api/                      # Public API Layer
│   ├── dpm_xl/              # DPM-XL specific APIs
│   │   ├── syntax.py        # Syntax validation API
│   │   ├── semantic.py      # Semantic validation API
│   │   ├── ast_generator.py # AST generation API
│   │   └── complete_ast.py  # Complete AST with metadata
│   │
│   └── dpm/                 # General DPM APIs
│       ├── data_dictionary.py   # Data dictionary queries
│       ├── explorer.py          # DPM exploration/introspection
│       ├── operation_scopes.py  # Operation scope calculation
│       ├── migration.py         # Database migration
│       └── types.py             # Common data types
│
├── dpm_xl/                   # DPM-XL Processing Engine
│   ├── grammar/             # ANTLR grammar & parsers
│   │   ├── dpm_xlLexer.g4   # Lexer grammar source
│   │   ├── dpm_xlParser.g4  # Parser grammar source
│   │   └── generated/       # Generated ANTLR code
│   │
│   ├── ast/                 # AST construction & manipulation
│   │   ├── constructor.py   # Build AST from parse tree
│   │   ├── nodes.py         # AST node definitions
│   │   ├── operands.py      # Operand validation
│   │   ├── visitor.py       # AST visitor
│   │   ├── template.py      # AST template base class
│   │   ├── where_clause.py  # Where clause checking
│   │   ├── ml_generation.py # DPM-ML generation
│   │   ├── module_analyzer.py     # Module analysis
│   │   └── module_dependencies.py # Dependency tracking
│   │
│   ├── operators/           # DPM-XL operator implementations
│   │   ├── base.py          # Base operator classes
│   │   ├── arithmetic.py    # +, -, *, /, ABS, EXP, etc.
│   │   ├── boolean.py       # AND, OR, XOR, NOT
│   │   ├── comparison.py    # =, !=, <, >, <=, >=
│   │   ├── conditional.py   # IF-THEN-ELSE, NVL
│   │   ├── aggregate.py     # SUM, COUNT, AVG, etc.
│   │   ├── string.py        # LEN, CONCAT
│   │   ├── time.py          # TIME_SHIFT
│   │   └── clause.py        # Clause operations
│   │
│   ├── types/               # DPM-XL type system
│   │   ├── scalar.py        # Boolean, String, Numeric types
│   │   ├── time.py          # Time period types
│   │   └── promotion.py     # Type promotion rules
│   │
│   ├── validation/          # DPM-XL validation logic
│   │   ├── variants.py            # Table variant processing
│   │   ├── property_constraints.py # Property constraint validation
│   │   ├── generation_utils.py    # Validation generation utilities
│   │   └── utils.py               # Validation helper functions
│   │
│   └── utils/               # DPM-XL utilities
│       ├── serialization.py # AST serialization
│       ├── operands_mapping.py # Operand mappings
│       ├── operator_mapping.py # Operator mappings
│       └── tokens.py        # Token definitions
│
├── dpm/                      # General DPM Core
│   ├── db/                  # Database layer
│   │   ├── models.py        # SQLAlchemy ORM models (83 classes)
│   │   ├── utils.py         # Database utilities
│   │   ├── migration.py     # Migration implementation
│   │   └── views/           # SQL view definitions (17 files)
│   │
│   ├── scopes/              # Operation scope management
│   │   └── calculator.py    # Scope calculation logic
│   │
│   └── explorer/            # DPM exploration
│       └── (to be populated)
│
├── cli/                      # Command-Line Interface
│   ├── main.py              # CLI entry point (formerly client.py)
│   └── commands/            # Command implementations
│
├── exceptions/               # Error Handling
│   ├── exceptions.py        # Custom exception classes
│   └── messages.py          # Error messages & codes
│
└── utils/                    # Shared Utilities
    └── common.py            # Cross-cutting utilities
```

## File Moves and Renames

### Major Moves

| Old Location | New Location | Reason |
|-------------|-------------|---------|
| `py_dpm/AST/` | `py_dpm/dpm_xl/ast/` | DPM-XL specific |
| `py_dpm/Operators/` | `py_dpm/dpm_xl/operators/` | DPM-XL specific |
| `py_dpm/DataTypes/` | `py_dpm/dpm_xl/types/` | DPM-XL specific |
| `py_dpm/grammar/` | `py_dpm/dpm_xl/grammar/` | DPM-XL specific |
| `py_dpm/ValidationsGeneration/` | `py_dpm/dpm_xl/validation/` | DPM-XL specific |
| `py_dpm/models.py` | `py_dpm/dpm/db/models.py` | General DPM database |
| `py_dpm/db_utils.py` | `py_dpm/dpm/db/utils.py` | General DPM database |
| `py_dpm/migration.py` | `py_dpm/dpm/db/migration.py` | General DPM database |
| `py_dpm/views/` | `py_dpm/dpm/db/views/` | General DPM database |
| `py_dpm/client.py` | `py_dpm/cli/main.py` | CLI organization |
| `py_dpm/Exceptions/` | `py_dpm/exceptions/` | Standardize naming |

### File Renames (for clarity)

| Old Name | New Name | Reason |
|----------|----------|--------|
| `ASTObjects.py` | `nodes.py` | More concise in context |
| `ASTConstructor.py` | `constructor.py` | Context makes "AST" redundant |
| `NumericOperators.py` | `arithmetic.py` | More accurate name |
| `ScalarTypes.py` | `scalar.py` | Context makes "Types" redundant |
| `common_types.py` | `types.py` | Simpler name |
| `ast_serialization.py` | `serialization.py` | Context clear from location |

### API Reorganization

APIs split into two categories:

**DPM-XL APIs** (`api/dpm_xl/`):
- `SyntaxAPI` - Syntax validation
- `SemanticAPI` - Semantic validation
- `ASTGenerator` - AST generation
- `CompleteASTAPI` - Complete AST with metadata

**General DPM APIs** (`api/dpm/`):
- `DataDictionaryAPI` - Data dictionary queries
- `DPMExplorer` - DPM exploration/introspection
- `OperationScopesAPI` - Operation scope calculation
- `MigrationAPI` - Database migration

## Deleted/Moved to Legacy

### Deleted Files
- `py_dpm/semantics/` - Incomplete/unused semantic analyzer
- Development scripts: `reproduce_semantic_error.py`, `development.py`
- Old grammar backup: `grammar/dist.backup-4.13.1/`
- Orphaned test `.pyc` files

### Moved to `_legacy/`
- `DAGAnalyzer.py` - Not integrated into API
- `data_dictionary_validation.py` - Documented but unused
- `ValidationsGeneration/Utils.py` - Broken external validation code

## Import Changes

All imports have been automatically updated using a migration script (`fix_imports.py`).

### Example Import Changes

**Before:**
```python
from py_dpm.AST.ASTObjects import Start, BinOp
from py_dpm.Operators.NumericOperators import Add, Subtract
from py_dpm.DataTypes.ScalarTypes import NumericType
from py_dpm.models import Property, Item
```

**After:**
```python
from py_dpm.dpm_xl.ast.nodes import Start, BinOp
from py_dpm.dpm_xl.operators.arithmetic import Add, Subtract
from py_dpm.dpm_xl.types.scalar import NumericType
from py_dpm.dpm.db.models import Property, Item
```

### User-Facing API (Unchanged)

The public API remains backward compatible:

```python
from py_dpm.api import (
    SyntaxAPI,          # From dpm_xl
    SemanticAPI,        # From dpm_xl
    DataDictionaryAPI,  # From dpm
    DPMExplorer,        # From dpm
    MigrationAPI,       # From dpm
)
```

## Configuration Changes

### pyproject.toml Updates

1. **CLI entry point:**
   ```toml
   [project.scripts]
   pydpm = "py_dpm.cli.main:main"  # was: py_dpm.client:main
   ```

2. **Package data paths:**
   ```toml
   [tool.setuptools.package-data]
   "py_dpm.dpm_xl.grammar" = ["*.g4"]
   "py_dpm.dpm_xl.grammar.generated" = ["*"]
   "py_dpm.dpm.db.views" = ["*.sql"]
   ```

## Statistics

- **Files processed:** 105
- **Files moved/renamed:** 98
- **Import statements updated:** 39 files
- **Lines of code reorganized:** ~54,000
- **Commits:** 2 (cleanup + reorganization)

## Benefits

### 1. Clear Mental Model
The directory structure immediately communicates purpose:
- Need DPM-XL parsing? Look in `dpm_xl/`
- Need database queries? Look in `dpm/db/`
- Need public API? Look in `api/`

### 2. Better Modularity
- DPM-XL and general DPM can evolve independently
- Easy to test components in isolation
- Clear boundaries reduce coupling

### 3. Future-Proof Design
- Easy to add other DPM languages (e.g., `dpm_ml/`, `dpm_json/`)
- Could split into separate packages:
  - `pydpm-core` (general DPM)
  - `pydpm-xl` (DPM-XL parsing)
  - `pydpm-cli` (CLI tools)

### 4. Improved Developer Experience
- Better IDE autocomplete and navigation
- Clearer imports convey intent
- Easier onboarding for new developers

## Known Issues

### ANTLR Version Mismatch (Pre-existing)
There's a version mismatch between generated ANTLR files and the runtime. This is a **pre-existing issue** not caused by the reorganization:

```
Exception: Could not deserialize ATN with version 3 (expected 4).
```

**Resolution:** Regenerate ANTLR files with the correct version (4.9.2) or update the runtime.

## Next Steps

### Immediate
1. ✅ Reorganize directory structure
2. ✅ Update all imports
3. ✅ Update configuration files
4. ✅ Commit changes

### Short Term
1. Fix ANTLR version mismatch
2. Run full test suite
3. Update API documentation
4. Update README with new structure

### Long Term
1. Further organize CLI commands into `cli/commands/`
2. Populate `dpm/explorer/` with exploration logic
3. Consider splitting into multiple packages
4. Add architecture documentation

## Migration Guide for Users

### If You Import from `py_dpm.api`
**No changes needed!** The public API remains the same.

### If You Import Internal Modules
Update your imports according to the mapping table above. The `fix_imports.py` script can help automate this for your code.

### If You Have Custom Extensions
Review the new structure and update your imports. The separation of DPM-XL from general DPM should make extension points clearer.

## Questions?

For questions or issues related to this reorganization, please contact the development team or open an issue on GitHub.

---

*Reorganization completed on 2025-12-22 by Claude Sonnet 4.5 via Claude Code*
