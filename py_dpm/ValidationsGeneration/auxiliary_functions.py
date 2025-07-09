import numpy as np
import pandas as pd

from py_dpm.Utils.ValidationsGenerationUtils import ValidationsGenerationUtils
from py_dpm.Utils.tokens import *


def generate_context_structure(lst: list, group_df: pd.DataFrame):
    """
    Method to generate the structure of the contexts of variables in order to generate the hierarchy validations
    :param lst: list to store the structure of contexts
    :param group_df: Dataframe with information about properties and items of variables
    """
    group_df.set_index(CONTEXT_PROPERTY, inplace=True)
    result = group_df.to_dict()[CONTEXT_ITEM]
    result[VARIABLE_VID] = group_df[VARIABLE_VID].tolist()[0]
    result[VARIABLE_PROPERTY_ID] = group_df[VARIABLE_PROPERTY_ID].tolist()[0]

    lst.append(result)


def generate_subexpression(common_values, data, table, operator:str=None):
    """
    Method to generate the subexpression of a hierarchy expression
    :param common_values: dictionary with information about the common components and their values
    :param data: variable datapoints
    :param table: table code
    """
    abs_value = True if operator and operator != '=' else False
    if ROW_CODE in common_values:
        rows = None
    else:
        rows = ROW + data[ROW_CODE].iloc[0] if data[ROW_CODE].iloc[0] else None

    if COLUMN_CODE in common_values:
        cols = None
    else:
        cols = COLUMN + data[COLUMN_CODE].iloc[0] if data[COLUMN_CODE].iloc[0] else None

    if SHEET_CODE in common_values:
        sheets = None
    else:
        sheets = SHEET + data[SHEET_CODE].iloc[0] if data[SHEET_CODE].iloc[0] else None
    
    if abs_value:
        expr = ValidationsGenerationUtils.write_cell(table, rows, cols, sheets)
        return 'abs(' + expr + ')'
    
    return ValidationsGenerationUtils.write_cell(table, rows, cols, sheets)


def get_common_components(left_data: pd.DataFrame, right_data: pd.DataFrame):
    """
    Method to get the common components of expression operands
    :param left_data: Dataframe corresponding to the data of the left operand
    :param right_data: Dataframe corresponding to the data of the right side operands
    """
    common_components = {}
    for component in CELL_COMPONENTS:
        left = left_data[component].dropna().tolist()
        right = right_data[component].isnull().values.any()
        if left and not right:
            intersection_component = np.intersect1d(left_data[component], right_data[component])
            if len(intersection_component):
                if all(right_data[component].isin(intersection_component)):
                    common_components[component] = intersection_component
    return common_components


def group_hierarchy_right_data(right_data: pd.DataFrame, left_table: str, common_components: list, comparisson_operator:str=None):
    """
    Method to group right side operands
    :param right_data: Dataframe with the datapoints of the right side of expression
    :param left_table: Table code of left operand
    :param common_components: List with the common components of right and left operands
    """
    right_table = right_data[TABLE_CODE].tolist()[0]
    is_table_unique = left_table == right_table
    right_operands_lst = []
    right_table_cell = right_table if not is_table_unique else None
    # Here we have to add the order of the items in the expression
    order_dict = {}
    for keys, group in right_data.groupby([ARITHMETIC_OPERATOR_SYMBOL, ITEM_ID]):
        operand = generate_subexpression(common_components, group, right_table_cell,comparisson_operator)
        operand = keys[0] + operand
        if ORDER in group:
            order_dict[group[ORDER].tolist()[0]] = operand
        else:
            order_dict[group[ORDER + '_x'].tolist()[0]] = operand

    right_operands_lst = [order_dict[order] for order in sorted(order_dict)]

    right_expression = ' '.join(right_operands_lst)
    if DUPLICATE_VARIABLES not in right_data:
        right_data[DUPLICATE_VARIABLES] = False
    duplicate_variables = right_data[DUPLICATE_VARIABLES].any()
    right_items = right_data[ITEM_ID].unique().tolist()
    return [right_expression, right_table, duplicate_variables,right_items]
