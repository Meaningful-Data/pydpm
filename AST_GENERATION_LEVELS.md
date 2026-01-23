# AST Generation Levels in pyDPM

This document explains the three levels of AST generation available in the `ASTGeneratorAPI`.

## Quick Comparison

| Feature | Level 1: Basic AST | Level 2: Complete AST | Level 3: Enriched AST |
|---------|-------------------|----------------------|----------------------|
| **Method** | `parse_expression()` | `generate_complete_ast()` | `generate_validations_script()` |
| **Database Required** | ❌ No | ✅ Yes | ✅ Yes |
| **Semantic Validation** | ❌ No | ✅ Yes | ✅ Yes |
| **Data Fields** | ❌ No | ✅ Yes (datapoint IDs, operand refs) | ✅ Yes |
| **Framework Structure** | ❌ No | ❌ No | ✅ Yes |
| **Engine Ready** | ❌ No | ❌ No | ✅ Yes |
| **Use Case** | Syntax validation, basic analysis | AST with metadata | Business rule engines |

## Level 1: Basic AST (`parse_expression`)

### What You Get
- ✅ Clean syntax tree structure
- ✅ Context information (if WITH clause present)
- ✅ Version compatibility normalization

### What You DON'T Get
- ❌ Datapoint IDs
- ❌ Operand references
- ❌ Framework structure

### Example Usage
```python
from py_dpm.api import ASTGeneratorAPI

generator = ASTGeneratorAPI()
result = generator.parse_expression("{tC_01.00, r0100, c0010}")

# Result structure:
{
    'success': True,
    'ast': {
        'class_name': 'VarID',
        'table': 'C_01.00',
        'rows': ['0100'],
        'cols': ['0010']
        # No 'data' field - that's in Level 2
    },
    'context': {...},
    'error': None,
    'metadata': {
        'has_context': True,
        'expression_type': 'VarID',
        'compatibility_mode': 'auto'
    }
}
```

### When to Use
- Syntax validation only
- Basic AST structure analysis
- No database available
- Quick parsing without metadata

---

## Level 2: Complete AST (`generate_complete_ast`)

### What You Get
- ✅ Everything from Level 1, PLUS:
- ✅ **Datapoint IDs** populated in `data` fields
- ✅ **Operand references** from database
- ✅ Full semantic validation results
- ✅ Format matching `json_scripts/*.json` examples

### What You DON'T Get
- ❌ Framework structure (operations, variables, tables, preconditions)
- ❌ Module metadata
- ❌ Engine-ready format

### Example Usage
```python
from py_dpm.api import ASTGeneratorAPI

generator = ASTGeneratorAPI(database_path="data.db")
result = generator.generate_complete_ast(
    "{tC_01.00, r0100, c0010}",
    release_id=123
)

# Result structure:
{
    'success': True,
    'ast': {
        'class_name': 'VarID',
        'table': 'C_01.00',
        'rows': ['0100'],
        'cols': ['0010'],
        'data': [  # ← NEW: Data fields populated!
            {
                'datapoint': 12345,  # ← Database ID
                'row': '0100',
                'column': '0010',
                'data_type': 'e'
            }
        ]
    },
    'context': {...},
    'error': None,
    'data_populated': True,  # ← Indicates data fields present
    'semantic_result': {...}  # ← Full semantic validation
}
```

### When to Use
- Need datapoint IDs and operand references
- AST analysis with complete metadata
- Matching the `json_scripts/*.json` format
- Semantic validation with database

---

## Level 3: Validations Script (`generate_validations_script`)

### What You Get
- ✅ Everything from Level 2, PLUS:
- ✅ **Framework structure** (operations, variables, tables, preconditions)
- ✅ **Module metadata** (version, release info, dates)
- ✅ **Dependency information**
- ✅ **Coordinates** (x/y/z) added to data entries
- ✅ **Engine-ready format** for business rule execution

### Example Usage
```python
from py_dpm.api import ASTGeneratorAPI

generator = ASTGeneratorAPI(database_path="data.db")
result = generator.generate_validations_script(
    expressions="{tC_01.00, r0100, c0010}",
    release_code="4.2"
)

# Result structure:
{
    'success': True,
    'enriched_ast': {
        'default_module': {  # ← Wrapped in module structure
            'module_code': 'default',
            'module_version': '1.0.0',
            'framework_code': 'default',
            'dpm_release': {
                'release': '4.2',
                'publication_date': '2021-01-01'
            },
            'dates': {'from': '2001-01-01', 'to': None},

            # Framework sections:
            'operations': {  # ← Operations section
                'my_validation': {
                    'version_id': 1234,
                    'code': 'my_validation',
                    'expression': '{tC_01.00, r0100, c0010}',
                    'root_operator_id': 24,
                    'ast': {...},  # Complete AST with coordinates
                    'from_submission_date': '2026-01-02',
                    'severity': 'Error'
                }
            },
            'variables': {  # ← Variables extracted from AST
                '12345': 'e'
            },
            'tables': {  # ← Tables grouped by table code
                'C_01.00': {
                    'variables': {'12345': 'e'},
                    'open_keys': {}
                }
            },
            'preconditions': {  # ← Preconditions section
                'p_5678': {
                    'ast': {...},
                    'affected_operations': ['my_validation'],
                    'version_id': 5678,
                    'code': 'p_5678'
                }
            },
            'precondition_variables': {
                '5678': 'b'
            },
            'dependency_information': {
                'intra_instance_validations': ['my_validation'],
                'cross_instance_dependencies': []
            },
            'dependency_modules': {}
        }
    },
    'error': None
}
```

### When to Use
- **Business rule execution engines**
- **Validation framework integration**
- **Production rule processing**
- Need complete framework structure for engine consumption

---

## Decision Tree: Which Level Should I Use?

```
Do you need to feed this to a business rule execution engine?
├─ YES → Use Level 3 (generate_validations_script)
└─ NO
   ├─ Do you need datapoint IDs and operand references?
   │  ├─ YES → Use Level 2 (generate_complete_ast)
   │  └─ NO
   │     ├─ Do you have a database available?
   │     │  ├─ YES → Use Level 2 (generate_complete_ast) for full validation
   │     │  └─ NO → Use Level 1 (parse_expression) for syntax only
   │     └─ Just validating syntax?
   │        └─ YES → Use Level 1 (parse_expression)
```

---

## Code Examples: Side-by-Side Comparison

### Same Expression, Three Levels

```python
from py_dpm.api import ASTGeneratorAPI

expression = "{tC_01.00, r0100, c0010}"

# Level 1: Basic AST (no database)
generator_basic = ASTGeneratorAPI()
basic = generator_basic.parse_expression(expression)
print(f"Level 1 - AST keys: {basic['ast'].keys()}")
# Output: dict_keys(['class_name', 'table', 'rows', 'cols', ...])
# No 'data' field

# Level 2: Complete AST (with database)
generator_complete = ASTGeneratorAPI(database_path="data.db")
complete = generator_complete.generate_complete_ast(expression)
print(f"Level 2 - AST keys: {complete['ast'].keys()}")
# Output: dict_keys(['class_name', 'table', 'rows', 'cols', 'data', ...])
# Has 'data' field with datapoint IDs!

# Level 3: Validations Script (with database + framework)
enriched = generator_complete.generate_validations_script(
    expression,
    release_code="4.2"
)
print(f"Level 3 - Top-level keys: {enriched['enriched_ast'].keys()}")
# Output: dict_keys(['default_module'])
print(f"Level 3 - Module sections: {enriched['enriched_ast']['default_module'].keys()}")
# Output: dict_keys(['module_code', 'operations', 'variables', 'tables', 'preconditions', ...])
# Full engine-ready structure!
```

---

## Summary

| **Level** | **Method** | **Best For** |
|-----------|-----------|-------------|
| 1 - Basic | `parse_expression()` | Syntax validation, quick parsing |
| 2 - Complete | `generate_complete_ast()` | AST analysis with metadata |
| 3 - Validations Script | `generate_validations_script()` | Business rule engines |

**Rule of thumb:** Start with the simplest level that meets your needs. Only use Level 3 if you're feeding the AST to an execution engine.
