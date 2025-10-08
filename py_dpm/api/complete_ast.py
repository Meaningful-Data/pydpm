#!/usr/bin/env python3
"""
Complete AST API - Generate ASTs exactly like the JSON examples

This API generates ASTs with complete data fields including datapoint IDs and operand references,
exactly matching the structure found in json_scripts/*.json files.
"""

from py_dpm.Utils.ast_serialization import ASTToJSONVisitor


def generate_complete_ast(expression: str, database_path: str = None):
    """
    Generate complete AST with all data fields, exactly like json_scripts examples.

    This function replicates the exact same process used to generate the reference
    JSON files in json_scripts/, ensuring complete data field population.

    Args:
        expression: DPM-XL expression string
        database_path: Path to SQLite database file (e.g., "./database.db")

    Returns:
        dict: {
            'success': bool,
            'ast': dict,        # Complete AST with data fields
            'context': dict,    # Context from WITH clause
            'error': str,       # Error if failed
            'data_populated': bool  # Whether data fields were populated
        }
    """
    try:
        # Import here to avoid circular imports
        from py_dpm.api import API
        from py_dpm.db_utils import get_engine

        # Initialize database connection if provided
        if database_path:
            try:
                engine = get_engine(database_path=database_path)
            except Exception as e:
                return {
                    'success': False,
                    'ast': None,
                    'context': None,
                    'error': f'Database connection failed: {e}',
                    'data_populated': False
                }

        # Use the legacy API which does complete semantic validation
        # This is the same API used to generate the original JSON files
        api = API()

        # Perform complete semantic validation with operand checking
        # This should populate all data fields on VarID nodes
        semantic_result = api.semantic_validation(expression)


        # Force data population if semantic validation completed successfully
        if hasattr(api, 'AST') and api.AST and semantic_result:
            try:
                from py_dpm.AST.check_operands import OperandsChecking
                from py_dpm.db_utils import get_session

                session = get_session()

                # Extract the expression AST
                def get_inner_ast(ast_obj):
                    if hasattr(ast_obj, 'children') and len(ast_obj.children) > 0:
                        child = ast_obj.children[0]
                        if hasattr(child, 'expression'):
                            return child.expression
                        else:
                            return child
                    return ast_obj

                inner_ast = get_inner_ast(api.AST)

                # Run operand checking to populate data fields
                oc = OperandsChecking(
                    session=session,
                    expression=expression,
                    ast=inner_ast,
                    release_id=None
                )

                # Apply the data from operand checker to VarID nodes
                if hasattr(oc, 'data') and oc.data is not None:

                    # Apply data to VarID nodes in the AST
                    def apply_data_to_varids(node):
                        if hasattr(node, '__class__') and node.__class__.__name__ == 'VarID':
                            table = getattr(node, 'table', None)
                            rows = getattr(node, 'rows', None)
                            cols = getattr(node, 'cols', None)

                            if table and table in oc.operands:
                                # Filter data for this specific VarID
                                # Start with table filter
                                filter_mask = (oc.data['table_code'] == table)

                                # Add row filter only if rows is not None and doesn't contain wildcards
                                # IMPORTANT: If rows contains '*', include all rows (don't filter)
                                if rows is not None and '*' not in rows:
                                    filter_mask = filter_mask & (oc.data['row_code'].isin(rows))

                                # Add column filter only if cols is not None and doesn't contain wildcards
                                # IMPORTANT: If cols contains '*', include all columns (don't filter)
                                if cols is not None and '*' not in cols:
                                    filter_mask = filter_mask & (oc.data['column_code'].isin(cols))

                                filtered_data = oc.data[filter_mask]

                                if not filtered_data.empty:
                                    # IMPORTANT: Remove wildcard entries (NULL column/row/sheet codes)
                                    # when specific entries exist for the same dimension
                                    # The database contains both wildcard entries (column_code=NULL for c*)
                                    # and specific entries (column_code='0010'). When we query with wildcards,
                                    # we want only the specific entries.

                                    # Remove rows where column_code is NULL if there are non-NULL column_code entries
                                    if filtered_data['column_code'].notna().any():
                                        filtered_data = filtered_data[filtered_data['column_code'].notna()]

                                    # Remove rows where row_code is NULL if there are non-NULL row_code entries
                                    if filtered_data['row_code'].notna().any():
                                        filtered_data = filtered_data[filtered_data['row_code'].notna()]

                                    # Remove rows where sheet_code is NULL if there are non-NULL sheet_code entries
                                    if filtered_data['sheet_code'].notna().any():
                                        filtered_data = filtered_data[filtered_data['sheet_code'].notna()]

                                    # IMPORTANT: After filtering, remove any remaining duplicates
                                    # based on (row_code, column_code, sheet_code) combination
                                    filtered_data = filtered_data.drop_duplicates(
                                        subset=['row_code', 'column_code', 'sheet_code'],
                                        keep='first'
                                    )

                                    # Set the data attribute on the VarID node
                                    if not filtered_data.empty:
                                        node.data = filtered_data

                        # Recursively apply to child nodes
                        for attr_name in ['children', 'left', 'right', 'operand', 'expression', 'condition', 'then_expr', 'else_expr']:
                            if hasattr(node, attr_name):
                                attr_value = getattr(node, attr_name)
                                if attr_value and hasattr(attr_value, '__class__'):
                                    apply_data_to_varids(attr_value)
                                elif isinstance(attr_value, list):
                                    for item in attr_value:
                                        if hasattr(item, '__class__'):
                                            apply_data_to_varids(item)

                    # Apply data to all VarID nodes in the AST
                    apply_data_to_varids(inner_ast)

            except Exception as e:
                # Silently continue if data population fails
                pass

        if hasattr(api, 'AST') and api.AST is not None:
            # Extract components exactly like batch_validator does
            def extract_components(ast_obj):
                if hasattr(ast_obj, 'children') and len(ast_obj.children) > 0:
                    child = ast_obj.children[0]
                    if hasattr(child, 'expression'):
                        return child.expression, child.partial_selection
                    else:
                        return child, None
                return ast_obj, None

            actual_ast, context = extract_components(api.AST)

            # Convert to JSON exactly like batch_validator does
            visitor = ASTToJSONVisitor(context)
            ast_dict = visitor.visit(actual_ast)

            # Check if data fields were populated
            data_populated = _check_data_fields_populated(ast_dict)

            # Serialize context
            context_dict = None
            if context:
                context_dict = {
                    'table': getattr(context, 'table', None),
                    'rows': getattr(context, 'rows', None),
                    'columns': getattr(context, 'cols', None),
                    'sheets': getattr(context, 'sheets', None),
                    'default': getattr(context, 'default', None),
                    'interval': getattr(context, 'interval', None)
                }

            return {
                'success': True,
                'ast': ast_dict,
                'context': context_dict,
                'error': None,
                'data_populated': data_populated,
                'semantic_result': semantic_result
            }

        else:
            return {
                'success': False,
                'ast': None,
                'context': None,
                'error': 'Semantic validation did not generate AST',
                'data_populated': False
            }

    except Exception as e:
        return {
            'success': False,
            'ast': None,
            'context': None,
            'error': f'API error: {str(e)}',
            'data_populated': False
        }


def _check_data_fields_populated(ast_dict):
    """Check if any VarID nodes have data fields populated"""
    if not isinstance(ast_dict, dict):
        return False

    if ast_dict.get('class_name') == 'VarID' and 'data' in ast_dict:
        return True

    # Recursively check nested structures
    for value in ast_dict.values():
        if isinstance(value, dict):
            if _check_data_fields_populated(value):
                return True
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and _check_data_fields_populated(item):
                    return True

    return False


def generate_complete_batch(expressions: list, database_path: str = None):
    """
    Generate complete ASTs for multiple expressions.

    Args:
        expressions: List of DPM-XL expression strings
        database_path: Path to SQLite database file

    Returns:
        list: List of result dictionaries
    """
    results = []
    for i, expr in enumerate(expressions):
        result = generate_complete_ast(expr, database_path)
        result['batch_index'] = i
        results.append(result)
    return results


# Convenience function with cleaner interface
def parse_with_data_fields(expression: str, database_path: str = None):
    """
    Simple function to parse expression and get AST with data fields.

    Args:
        expression: DPM-XL expression string
        database_path: Path to SQLite database file

    Returns:
        dict: AST dictionary with data fields, or None if failed
    """
    result = generate_complete_ast(expression, database_path)
    return result['ast'] if result['success'] else None