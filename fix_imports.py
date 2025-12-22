#!/usr/bin/env python3
"""
Script to fix all imports after reorganization.
"""

import os
import re
from pathlib import Path

# Define the mapping of old imports to new imports
IMPORT_MAPPINGS = {
    # Exceptions
    'from py_dpm.Exceptions.messages': 'from py_dpm.exceptions.messages',
    'from py_dpm.Exceptions.exceptions': 'from py_dpm.exceptions.exceptions',
    'from py_dpm.Exceptions import': 'from py_dpm.exceptions import',

    # Utils
    'from py_dpm.Utils.ast_serialization': 'from py_dpm.dpm_xl.utils.serialization',
    'from py_dpm.Utils.operands_mapping': 'from py_dpm.dpm_xl.utils.operands_mapping',
    'from py_dpm.Utils.operator_mapping': 'from py_dpm.dpm_xl.utils.operator_mapping',
    'from py_dpm.Utils.tokens': 'from py_dpm.dpm_xl.utils.tokens',
    'from py_dpm.Utils.utils': 'from py_dpm.utils.common',
    'from py_dpm.Utils.ValidationsGenerationUtils': 'from py_dpm.dpm_xl.validation.generation_utils',

    # Database
    'from py_dpm.models': 'from py_dpm.dpm.db.models',
    'from py_dpm.db_utils': 'from py_dpm.dpm.db.utils',
    'from py_dpm.migration import': 'from py_dpm.dpm.db.migration import',
    'import py_dpm.models': 'import py_dpm.dpm.db.models',
    'import py_dpm.db_utils': 'import py_dpm.dpm.db.utils',

    # Grammar
    'from py_dpm.grammar.dist.dpm_xlLexer': 'from py_dpm.dpm_xl.grammar.generated.dpm_xlLexer',
    'from py_dpm.grammar.dist.dpm_xlParser': 'from py_dpm.dpm_xl.grammar.generated.dpm_xlParser',
    'from py_dpm.grammar.dist.dpm_xlParserVisitor': 'from py_dpm.dpm_xl.grammar.generated.dpm_xlParserVisitor',
    'from py_dpm.grammar.dist.dpm_xlParserListener': 'from py_dpm.dpm_xl.grammar.generated.dpm_xlParserListener',
    'from py_dpm.grammar.dist.listeners': 'from py_dpm.dpm_xl.grammar.generated.listeners',
    'from py_dpm.grammar.dist import': 'from py_dpm.dpm_xl.grammar.generated import',

    # AST
    'from py_dpm.AST.ASTObjects': 'from py_dpm.dpm_xl.ast.nodes',
    'from py_dpm.AST.ASTConstructor': 'from py_dpm.dpm_xl.ast.constructor',
    'from py_dpm.AST.ASTVisitor': 'from py_dpm.dpm_xl.ast.visitor',
    'from py_dpm.AST.ASTTemplate': 'from py_dpm.dpm_xl.ast.template',
    'from py_dpm.AST.check_operands': 'from py_dpm.dpm_xl.ast.operands',
    'from py_dpm.AST.WhereClauseChecker': 'from py_dpm.dpm_xl.ast.where_clause',
    'from py_dpm.AST.MLGeneration': 'from py_dpm.dpm_xl.ast.ml_generation',
    'from py_dpm.AST.ModuleAnalyzer': 'from py_dpm.dpm_xl.ast.module_analyzer',
    'from py_dpm.AST.ModuleDependencies': 'from py_dpm.dpm_xl.ast.module_dependencies',
    'from py_dpm.AST import': 'from py_dpm.dpm_xl.ast import',
    'import py_dpm.AST': 'import py_dpm.dpm_xl.ast',

    # Types
    'from py_dpm.DataTypes.ScalarTypes': 'from py_dpm.dpm_xl.types.scalar',
    'from py_dpm.DataTypes.TimeClasses': 'from py_dpm.dpm_xl.types.time',
    'from py_dpm.DataTypes.TypePromotion': 'from py_dpm.dpm_xl.types.promotion',
    'from py_dpm.DataTypes import': 'from py_dpm.dpm_xl.types import',

    # Operators
    'from py_dpm.Operators.Operator': 'from py_dpm.dpm_xl.operators.base',
    'from py_dpm.Operators.NumericOperators': 'from py_dpm.dpm_xl.operators.arithmetic',
    'from py_dpm.Operators.BooleanOperators': 'from py_dpm.dpm_xl.operators.boolean',
    'from py_dpm.Operators.ComparisonOperators': 'from py_dpm.dpm_xl.operators.comparison',
    'from py_dpm.Operators.ConditionalOperators': 'from py_dpm.dpm_xl.operators.conditional',
    'from py_dpm.Operators.AggregateOperators': 'from py_dpm.dpm_xl.operators.aggregate',
    'from py_dpm.Operators.StringOperators': 'from py_dpm.dpm_xl.operators.string',
    'from py_dpm.Operators.TimeOperators': 'from py_dpm.dpm_xl.operators.time',
    'from py_dpm.Operators.ClauseOperators': 'from py_dpm.dpm_xl.operators.clause',
    'from py_dpm.Operators import': 'from py_dpm.dpm_xl.operators import',

    # Validation
    'from py_dpm.ValidationsGeneration.VariantsProcessor': 'from py_dpm.dpm_xl.validation.variants',
    'from py_dpm.ValidationsGeneration.PropertiesConstraintsProcessor': 'from py_dpm.dpm_xl.validation.property_constraints',
    'from py_dpm.ValidationsGeneration.auxiliary_functions': 'from py_dpm.dpm_xl.validation.utils',

    # Operation Scopes
    'from py_dpm.OperationScopes.OperationScopeService': 'from py_dpm.dpm.scopes.calculator',

    # API
    'from py_dpm.api.migration': 'from py_dpm.api.dpm.migration',
    'from py_dpm.api.syntax': 'from py_dpm.api.dpm_xl.syntax',
    'from py_dpm.api.semantic': 'from py_dpm.api.dpm_xl.semantic',
    'from py_dpm.api.data_dictionary': 'from py_dpm.api.dpm.data_dictionary',
    'from py_dpm.api.operation_scopes': 'from py_dpm.api.dpm.operation_scopes',
    'from py_dpm.api.ast_generator': 'from py_dpm.api.dpm_xl.ast_generator',
    'from py_dpm.api.complete_ast': 'from py_dpm.api.dpm_xl.complete_ast',
    'from py_dpm.api.common_types': 'from py_dpm.api.dpm.types',
    'from py_dpm.api.explorer': 'from py_dpm.api.dpm.explorer',

    # CLI
    'from py_dpm.client': 'from py_dpm.cli.main',
    'import py_dpm.client': 'import py_dpm.cli.main',
}

def fix_imports_in_file(filepath):
    """Fix imports in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Apply all import mappings
        for old_import, new_import in IMPORT_MAPPINGS.items():
            content = content.replace(old_import, new_import)

        # Only write if content changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Fix all imports in the py_dpm directory."""
    py_dpm_dir = Path(__file__).parent / 'py_dpm'

    files_changed = 0
    files_processed = 0

    # Process all Python files
    for py_file in py_dpm_dir.rglob('*.py'):
        # Skip __pycache__ and generated files
        if '__pycache__' in str(py_file) or '/generated/' in str(py_file):
            continue

        files_processed += 1
        if fix_imports_in_file(py_file):
            files_changed += 1
            print(f"Fixed: {py_file.relative_to(py_dpm_dir.parent)}")

    print(f"\nProcessed {files_processed} files, modified {files_changed} files.")

if __name__ == '__main__':
    main()
