#!/usr/bin/env python3
"""
Complete AST API - Generate ASTs exactly like the JSON examples

This API generates ASTs with complete data fields including datapoint IDs and operand references,
exactly matching the structure found in json_scripts/*.json files.

Also provides enrichment functionality to create engine-ready ASTs with framework structure
(operations, variables, tables, preconditions sections) for business rule execution engines.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from py_dpm.Utils.ast_serialization import ASTToJSONVisitor


def generate_complete_ast(expression: str, database_path: str = None, connection_url: str = None):
    """
    Generate complete AST with all data fields, exactly like json_scripts examples.

    This function replicates the exact same process used to generate the reference
    JSON files in json_scripts/, ensuring complete data field population.

    Args:
        expression: DPM-XL expression string
        database_path: Path to SQLite database file (e.g., "./database.db")
        connection_url: SQLAlchemy connection URL for PostgreSQL (optional)

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
        if connection_url or database_path:
            try:
                engine = get_engine(database_path=database_path, connection_url=connection_url)
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
        api = API(database_path=database_path, connection_url=connection_url)

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
                        for attr_name in ['children', 'left', 'right', 'operand', 'operands', 'expression', 'condition', 'then_expr', 'else_expr']:
                            if hasattr(node, attr_name):
                                attr_value = getattr(node, attr_name)
                                if isinstance(attr_value, list):
                                    for item in attr_value:
                                        if hasattr(item, '__class__'):
                                            apply_data_to_varids(item)
                                elif attr_value and hasattr(attr_value, '__class__'):
                                    apply_data_to_varids(attr_value)

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


def generate_complete_batch(expressions: list, database_path: str = None, connection_url: str = None):
    """
    Generate complete ASTs for multiple expressions.

    Args:
        expressions: List of DPM-XL expression strings
        database_path: Path to SQLite database file
        connection_url: SQLAlchemy connection URL for PostgreSQL (optional)

    Returns:
        list: List of result dictionaries
    """
    results = []
    for i, expr in enumerate(expressions):
        result = generate_complete_ast(expr, database_path, connection_url)
        result['batch_index'] = i
        results.append(result)
    return results


# Convenience function with cleaner interface
def parse_with_data_fields(expression: str, database_path: str = None, connection_url: str = None):
    """
    Simple function to parse expression and get AST with data fields.

    Args:
        expression: DPM-XL expression string
        database_path: Path to SQLite database file
        connection_url: SQLAlchemy connection URL for PostgreSQL (optional)

    Returns:
        dict: AST dictionary with data fields, or None if failed
    """
    result = generate_complete_ast(expression, database_path, connection_url)
    return result['ast'] if result['success'] else None


# ============================================================================
# AST Enrichment Functions - Create engine-ready ASTs
# ============================================================================


def generate_enriched_ast(
    expression: str,
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    dpm_version: Optional[str] = None,
    operation_code: Optional[str] = None,
    table_context: Optional[Dict[str, Any]] = None,
    precondition: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate enriched, engine-ready AST from DPM-XL expression.

    This extends generate_complete_ast() by adding framework structure
    (operations, variables, tables, preconditions) for execution engines.

    Args:
        expression: DPM-XL expression string
        database_path: Path to SQLite database (or None for PostgreSQL)
        connection_url: PostgreSQL connection URL (takes precedence over database_path)
        dpm_version: DPM version code (e.g., "4.0", "4.1", "4.2")
        operation_code: Optional operation code (defaults to "default_code")
        table_context: Optional table context dict with keys: 'table', 'columns', 'rows', 'sheets', 'default', 'interval'
        precondition: Optional precondition variable reference (e.g., {v_F_44_04})

    Returns:
        dict: {
            'success': bool,
            'enriched_ast': dict,  # Engine-ready AST with framework structure
            'error': str           # Error message if failed
        }
    """
    try:
        # Generate complete AST first
        complete_result = generate_complete_ast(expression, database_path, connection_url)

        if not complete_result['success']:
            return {
                'success': False,
                'enriched_ast': None,
                'error': f"Failed to generate complete AST: {complete_result['error']}"
            }

        complete_ast = complete_result['ast']
        context = complete_result.get('context') or table_context

        # Enrich with framework structure
        enriched_ast = enrich_ast_with_metadata(
            ast_dict=complete_ast,
            expression=expression,
            context=context,
            database_path=database_path,
            connection_url=connection_url,
            dpm_version=dpm_version,
            operation_code=operation_code,
            precondition=precondition
        )

        return {
            'success': True,
            'enriched_ast': enriched_ast,
            'error': None
        }

    except Exception as e:
        return {
            'success': False,
            'enriched_ast': None,
            'error': f'Enrichment error: {str(e)}'
        }


def enrich_ast_with_metadata(
    ast_dict: Dict[str, Any],
    expression: str,
    context: Optional[Dict[str, Any]],
    database_path: Optional[str] = None,
    connection_url: Optional[str] = None,
    dpm_version: Optional[str] = None,
    operation_code: Optional[str] = None,
    precondition: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Add framework structure (operations, variables, tables, preconditions) to complete AST.

    This creates the engine-ready format with all metadata sections.

    Args:
        ast_dict: Complete AST dictionary (from generate_complete_ast)
        expression: Original DPM-XL expression
        context: Context dict with table, rows, columns, sheets, default, interval
        database_path: Path to SQLite database
        connection_url: PostgreSQL connection URL (takes precedence)
        dpm_version: DPM version code (e.g., "4.2")
        operation_code: Operation code (defaults to "default_code")
        precondition: Precondition variable reference (e.g., {v_F_44_04})

    Returns:
        dict: Engine-ready AST with framework structure
    """
    from py_dpm.db_utils import get_engine, get_session
    from py_dpm.models import TableVersion, Release
    import copy

    # Initialize database connection
    engine = get_engine(database_path=database_path, connection_url=connection_url)

    # Generate operation code if not provided
    if not operation_code:
        operation_code = "default_code"

    # Get current date for framework structure
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Query database for release information using SQLAlchemy
    release_info = _get_release_info(dpm_version, engine)

    # Build module info
    module_info = {
        "module_code": "default",
        "module_version": "1.0.0",
        "framework_code": "default",
        "dpm_release": {
            "release": release_info['release'],
            "publication_date": release_info['publication_date']
        },
        "dates": {
            "from": "2001-01-01",
            "to": None
        }
    }

    # Add coordinates to AST data entries
    ast_with_coords = _add_coordinates_to_ast(ast_dict, context)

    # Build operations section
    operations = {
        operation_code: {
            "version_id": hash(expression) % 10000,
            "code": operation_code,
            "expression": expression,
            "root_operator_id": 24,  # Default for now
            "ast": ast_with_coords,
            "from_submission_date": current_date,
            "severity": "Error"
        }
    }

    # Build variables section by extracting from the complete AST
    all_variables, variables_by_table = _extract_variables_from_ast(ast_with_coords)

    variables = all_variables
    tables = {}

    # Build tables with their specific variables
    for table_code, table_variables in variables_by_table.items():
        tables[table_code] = {
            "variables": table_variables,
            "open_keys": {}
        }

    # Build preconditions
    preconditions = {}
    precondition_variables = {}

    if precondition or (context and 'table' in context):
        preconditions, precondition_variables = _build_preconditions(
            precondition=precondition,
            context=context,
            operation_code=operation_code,
            engine=engine
        )

    # Build dependency information
    dependency_info = {
        "intra_instance_validations": [operation_code],
        "cross_instance_dependencies": []
    }

    # Build dependency modules
    dependency_modules = {}

    # Build complete structure
    namespace = "default_module"

    return {
        namespace: {
            **module_info,
            "operations": operations,
            "variables": variables,
            "tables": tables,
            "preconditions": preconditions,
            "precondition_variables": precondition_variables,
            "dependency_information": dependency_info,
            "dependency_modules": dependency_modules
        }
    }


def _get_release_info(dpm_version: Optional[str], engine) -> Dict[str, Any]:
    """
    Get release information from database using SQLAlchemy.

    Args:
        dpm_version: DPM version code (e.g., "4.0", "4.1", "4.2")
        engine: SQLAlchemy engine

    Returns:
        dict: {'release': str, 'publication_date': str}
    """
    from py_dpm.models import Release
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        if dpm_version:
            # Query for specific version
            version_float = float(dpm_version)
            release = session.query(Release).filter(
                Release.code == str(version_float)
            ).first()

            if release:
                return {
                    'release': str(release.code) if release.code else dpm_version,
                    'publication_date': release.date.strftime("%Y-%m-%d") if release.date else "2001-01-01"
                }

        # Fallback: get latest released version
        release = session.query(Release).filter(
            Release.status == 'released'
        ).order_by(Release.code.desc()).first()

        if release:
            return {
                'release': str(release.code) if release.code else "4.1",
                'publication_date': release.date.strftime("%Y-%m-%d") if release.date else "2001-01-01"
            }

        # Final fallback
        return {
            'release': "4.1",
            'publication_date': "2001-01-01"
        }

    except Exception:
        # Fallback on any error
        return {
            'release': "4.1",
            'publication_date': "2001-01-01"
        }
    finally:
        session.close()


def _get_table_info(table_code: str, engine) -> Optional[Dict[str, Any]]:
    """
    Get table information from database using SQLAlchemy.

    Args:
        table_code: Table code like 'F_25_01' or 'F_25.01'
        engine: SQLAlchemy engine

    Returns:
        dict: {'table_vid': int, 'code': str} or None if not found
    """
    from py_dpm.models import TableVersion
    from sqlalchemy.orm import sessionmaker
    import re

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Try exact match first
        table = session.query(TableVersion).filter(
            TableVersion.code == table_code
        ).first()

        if table:
            return {
                'table_vid': table.tablevid,
                'code': table.code
            }

        # Handle precondition parser format: F_25_01 -> F_25.01
        if re.match(r'^[A-Z]_\d+_\d+', table_code):
            parts = table_code.split('_', 2)
            if len(parts) >= 3:
                table_code_with_dot = f"{parts[0]}_{parts[1]}.{parts[2]}"
                table = session.query(TableVersion).filter(
                    TableVersion.code == table_code_with_dot
                ).first()

                if table:
                    return {
                        'table_vid': table.tablevid,
                        'code': table.code
                    }

        # Try LIKE pattern as last resort (handles sub-tables like F_25.01.a)
        table = session.query(TableVersion).filter(
            TableVersion.code.like(f"{table_code}%")
        ).order_by(TableVersion.code).first()

        if table:
            return {
                'table_vid': table.tablevid,
                'code': table.code
            }

        return None

    except Exception:
        return None
    finally:
        session.close()


def _build_preconditions(
    precondition: Optional[str],
    context: Optional[Dict[str, Any]],
    operation_code: str,
    engine
) -> tuple:
    """
    Build preconditions and precondition_variables sections.

    Args:
        precondition: Precondition variable reference (e.g., {v_F_44_04})
        context: Context dict with 'table' key
        operation_code: Operation code
        engine: SQLAlchemy engine

    Returns:
        tuple: (preconditions_dict, precondition_variables_dict)
    """
    import re

    preconditions = {}
    precondition_variables = {}

    # Extract table code from precondition or context
    table_code = None

    if precondition:
        # Extract variable code from precondition reference like {v_F_44_04}
        match = re.match(r'\{v_([^}]+)\}', precondition)
        if match:
            table_code = match.group(1)
    elif context and 'table' in context:
        table_code = context['table']

    if table_code:
        # Query database for actual variable ID and version
        table_info = _get_table_info(table_code, engine)

        if table_info:
            precondition_var_id = table_info['table_vid']
            version_id = table_info['table_vid']
            precondition_code = f"p_{precondition_var_id}"

            preconditions[precondition_code] = {
                "ast": {
                    "class_name": "PreconditionItem",
                    "variable_id": precondition_var_id,
                    "variable_code": table_code
                },
                "affected_operations": [operation_code],
                "version_id": version_id,
                "code": precondition_code
            }

            precondition_variables[str(precondition_var_id)] = "b"

    return preconditions, precondition_variables


def _extract_variables_from_ast(ast_dict: Dict[str, Any]) -> tuple:
    """
    Extract variables from complete AST by table.

    Args:
        ast_dict: Complete AST dictionary

    Returns:
        tuple: (all_variables_dict, variables_by_table_dict)
    """
    variables_by_table = {}
    all_variables = {}

    def extract_from_node(node):
        if isinstance(node, dict):
            # Check if this is a VarID node with data
            if node.get('class_name') == 'VarID' and 'data' in node:
                table = node.get('table')
                if table:
                    if table not in variables_by_table:
                        variables_by_table[table] = {}

                    # Extract variable IDs and data types from AST data array
                    for data_item in node['data']:
                        if 'datapoint' in data_item:
                            var_id = str(data_item['datapoint'])
                            data_type = data_item.get('data_type', 'e')
                            variables_by_table[table][var_id] = data_type
                            all_variables[var_id] = data_type

            # Recursively process nested nodes
            for value in node.values():
                if isinstance(value, (dict, list)):
                    extract_from_node(value)
        elif isinstance(node, list):
            for item in node:
                extract_from_node(item)

    extract_from_node(ast_dict)
    return all_variables, variables_by_table


def _add_coordinates_to_ast(ast_dict: Dict[str, Any], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Add x/y/z coordinates to data entries in AST.

    Args:
        ast_dict: Complete AST dictionary
        context: Context dict with 'columns' key

    Returns:
        dict: AST with coordinates added to data entries
    """
    import copy

    def add_coords_to_node(node):
        if isinstance(node, dict):
            # Handle VarID nodes with data arrays
            if node.get('class_name') == 'VarID' and 'data' in node:
                # Get column information from context
                cols = []
                if context and 'columns' in context and context['columns']:
                    cols = context['columns']

                # Group data entries by row to assign coordinates correctly
                entries_by_row = {}
                for data_entry in node['data']:
                    row_code = data_entry.get('row', '')
                    if row_code not in entries_by_row:
                        entries_by_row[row_code] = []
                    entries_by_row[row_code].append(data_entry)

                # Assign coordinates based on column order and row grouping
                rows = list(entries_by_row.keys())
                for x_index, row_code in enumerate(rows, 1):
                    for data_entry in entries_by_row[row_code]:
                        column_code = data_entry.get('column', '')

                        # Find y coordinate based on column position in context
                        y_index = 1  # default
                        if cols and column_code in cols:
                            y_index = cols.index(column_code) + 1
                        elif cols:
                            # Fallback to order in data
                            row_columns = [entry.get('column', '') for entry in entries_by_row[row_code]]
                            if column_code in row_columns:
                                y_index = row_columns.index(column_code) + 1

                        # Always add y coordinate
                        data_entry['y'] = y_index

                        # Add x coordinate only if there are multiple rows
                        if len(rows) > 1:
                            data_entry['x'] = x_index

                        # TODO: Add z coordinate for sheets when needed

            # Recursively process child nodes
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    add_coords_to_node(value)
        elif isinstance(node, list):
            for item in node:
                add_coords_to_node(item)

    # Create a deep copy to avoid modifying the original
    result = copy.deepcopy(ast_dict)
    add_coords_to_node(result)
    return result