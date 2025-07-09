import json
from itertools import groupby

import pandas as pd

from py_dpm.Utils.tokens import CELL_COMPONENTS, COLUMN, COLUMN_CODE, EXISTENCE_REPORT, \
    HIERARCHY_REPORT, ROW, ROW_CODE, SHEET, SHEET_CODE, \
    SIGN_REPORT
from py_dpm.ValidationsGeneration.Utils import ExternalDataExistence, ExternalDataHierarchies, \
    ExternalDataSign


def from_generate_to_response(validations):
    """
    """
    response_validations = {}
    for validation in validations:
        if validation['expression'] not in response_validations:
            response_validations[validation['expression']] = validation
        else:
            for op_code in validation['operation_code']:
                if op_code not in response_validations[validation['expression']]['operation_code']:
                    response_validations[validation['expression']]['operation_code'].append(op_code)
            if validation['subcategory_id'] not in response_validations[validation['expression']]['subcategory_id']:
                response_validations[validation['expression']]['subcategory_id'].append(validation['subcategory_id'][0])
                response_validations[validation['expression']]['subcategory_code'].append(validation['subcategory_code'][0])
    response_validations_list = list(response_validations.values())
    return response_validations_list

def generate_report_validation_view(validations, report_type):
    report_type_list = [HIERARCHY_REPORT, SIGN_REPORT, EXISTENCE_REPORT]
    if report_type not in report_type_list:
        raise ValueError(f"report_type must be one of {report_type_list}")
    #
    if report_type == HIERARCHY_REPORT:
        external_data = ExternalDataHierarchies()
        # TODO: Check this
        proposed = external_data.proposed_rules[external_data.proposed_rules['Type'] == 'Hierarchy']
        rejected = external_data.rejected_rules[external_data.proposed_rules['Type'] == 'Hierarchy']
    elif report_type == SIGN_REPORT:
        external_data = ExternalDataSign()
        proposed = external_data.proposed_rules
        rejected = external_data.rejected_rules
    else:
        external_data = ExternalDataExistence()
        proposed = external_data.proposed_rules
        rejected = external_data.rejected_rules
    #
    matched = {"number_validations": 0}
    unmatched = {"number_validations": 0}
    review = {"number_validations": 0}

    #
    for validation in validations:
        valdict = {
            "operation_code": validation['operation_code'],
            "expression": validation['expression'],
            # "parent_id": validation['parent_id'],
            "status": validation['status']
        }

        if valdict['status'] != 'Correct':
            if valdict['expression'] in review:
                # review[valdict['expression']]['subcategories'].append(validation['subcategory_id'])
                pass
            else:
                review[valdict['expression']] = valdict
                # review[valdict['expression']]['subcategories'] = [validation['subcategory_id']]

            review['number_validations'] += 1

        elif valdict['operation_code'] != []:
            if valdict['expression'] in matched:
                pass
                # matched[valdict['expression']]['subcategories'].append(validation['subcategory_id'])
            else:
                matched[valdict['expression']] = valdict
                # matched[valdict['expression']]['subcategories'] = [validation['subcategory_id']]

            matched['number_validations'] += 1
        else:
            if valdict['expression'] in unmatched:
                pass
                # unmatched[valdict['expression']]['subcategories'].append(validation['subcategory_id'])
            else:
                unmatched[valdict['expression']] = valdict
                # unmatched[valdict['expression']]['subcategories'] = [validation['subcategory_id']]
            unmatched['number_validations'] += 1


    matched_codes = []
    for val in matched:
        if val != 'number_validations':
            matched_codes += matched[val]['operation_code']

    # proposed = external_hierarchy_data.proposed_rules[external_hierarchy_data.proposed_rules['Type'] == 'Hierarchy']
    # rejected = external_hierarchy_data.rejected_rules[external_hierarchy_data.proposed_rules['Type'] == 'Hierarchy']

    proposed_not_generated = proposed[~proposed['ID'].isin(matched_codes)]
    rejected_not_generated = rejected[~rejected['ID'].isin(matched_codes)]

    with open('./development/data/' + report_type + '_matched.json', 'w') as fp:
        json.dump(matched, fp, indent=4)
    with open('./development/data/' + report_type + '_unmatched.json', 'w') as fp:
        json.dump(unmatched, fp, indent=4)
    with open('./development/data/' + report_type + '_review.json', 'w') as fp:
        json.dump(review, fp, indent=4)

    proposed_not_generated.to_csv('./development/data/' + report_type + '_proposed_not_generated.csv', index=False)
    rejected_not_generated.to_csv('./development/data/' + report_type + '_rejected_not_generated.csv', index=False)


class ValidationsGenerationUtils:
    """
    Class with common methods used by the different generation processes of validations
    """

    @classmethod
    def get_components_to_group(cls, datapoints_variable: pd.DataFrame):
        """
        Gets cell components to group by
        :param datapoints_variable: dataframe with datapoints to group
        :return a list with cell components to group by
        """
        component_values = datapoints_variable[CELL_COMPONENTS]
        components_to_group = []
        components_to_check = []
        for cell_component in CELL_COMPONENTS:
            if not component_values[cell_component].isnull().all():
                components_to_check.append(cell_component)

        if len(components_to_check):

            if len(components_to_check) == 1:
                return []

            for cell_component in components_to_check:
                duplicated = component_values.duplicated(
                    subset=[comp for comp in components_to_check if comp != cell_component],
                    keep=False)
                if not duplicated.all():
                    components_to_group.append(cell_component)
        return components_to_group

    @classmethod
    def group_cells(cls, datapoints_variable: pd.DataFrame, datapoints_table: pd.DataFrame):
        """
        Get the cell groups from datapoints by grouping them when necessary
        :param datapoints_variable: datapoints of the variable
        :param datapoints_table: datapoints of the table associated which the table code of operand
        :return a list with rows, cols and sheets for each group
        """
        components_to_group = cls.get_components_to_group(datapoints_variable=datapoints_variable)
        result_lst = []
        if not len(components_to_group) or len(components_to_group) > 2:
            rows, cols, sheets = cls.group_cell_components(datapoints_variable=datapoints_variable,
                                                           datapoints_table=datapoints_table)
            result_lst.append((rows, cols, sheets))

        elif len(components_to_group) == 1:
            for key, group_df in datapoints_variable.groupby(components_to_group[0], dropna=False):
                rows, cols, sheets = cls.group_cell_components(datapoints_variable=group_df,
                                                               datapoints_table=datapoints_table)
                result_lst.append((rows, cols, sheets))
        else:
            ref_component = components_to_group[0]
            second_group_component = components_to_group[1]
            third_component = [component for component in CELL_COMPONENTS if component not in components_to_group][0]

            reference_prefix = ROW if ref_component == ROW_CODE else COLUMN if ref_component == COLUMN_CODE else SHEET
            second_component_prefix = ROW if second_group_component == ROW_CODE else COLUMN if second_group_component == COLUMN_CODE else SHEET
            third_component_prefix = ROW if third_component == ROW_CODE else COLUMN if third_component == COLUMN_CODE else SHEET

            datapoints_variable = datapoints_variable.sort_values([ref_component, second_group_component])

            components_dict = {}
            for value in datapoints_variable[ref_component].unique().tolist():
                components_dict[value] = datapoints_variable[datapoints_variable[ref_component] == value][
                    second_group_component].unique().tolist()

            # group reference component values by second group component values
            for keys_values, group_values in groupby(components_dict.items(), key=lambda x: sorted(x[1])):
                group_values = [v[0] for v in group_values]
                reference_component_grouping = cls.group_cell_component_elements(reference_prefix, group_values,
                                                                                 datapoints_table[ref_component])
                second_component_grouping = cls.group_cell_component_elements(second_component_prefix, keys_values,
                                                                              datapoints_table[second_group_component])
                third_component_grouping = None
                if not datapoints_variable[third_component].isnull().all():
                    third_values = datapoints_variable[
                        datapoints_variable[ref_component].isin(group_values) & datapoints_variable[
                            second_group_component].isin(keys_values)][third_component].unique().tolist()
                    third_component_grouping = cls.group_cell_component_elements(third_component_prefix, third_values,
                                                                                 datapoints_table[third_component])

                rows = reference_component_grouping if reference_prefix == ROW else second_component_grouping if second_component_prefix == ROW else third_component_grouping
                cols = reference_component_grouping if reference_prefix == COLUMN else second_component_grouping if second_component_prefix == COLUMN else third_component_grouping
                sheets = reference_component_grouping if reference_prefix == SHEET else second_component_grouping if second_component_prefix == SHEET else third_component_grouping
                result_lst.append((rows, cols, sheets))

        return result_lst

    @classmethod
    def group_cells_test(cls, datapoints_variable: pd.DataFrame, datapoints_table: pd.DataFrame):
        """
        Get the cell groups from datapoints by grouping them when necessary
        :param datapoints_variable: datapoints of the variable
        :param datapoints_table: datapoints of the table associated which the table code of operand
        :return a list with rows, cols and sheets for each group
        """
        components_to_group = cls.get_components_to_group(datapoints_variable=datapoints_variable)
        result_lst = []
        if not len(components_to_group) or len(components_to_group) > 2:
            is_several_vals, filtered_df=cls._several_validations_checker(datapoints_variable)
            if is_several_vals:
                for df in filtered_df:
                    rows, cols, sheets = cls.group_cell_components(datapoints_variable=df,
                                                        datapoints_table=datapoints_table)
                    result_lst.append((rows, cols, sheets, df['cell_id'].to_list()))
            else:
                rows, cols, sheets = cls.group_cell_components(datapoints_variable=datapoints_variable,
                                                            datapoints_table=datapoints_table)
                result_lst.append((rows, cols, sheets, datapoints_variable['cell_id'].to_list()))

        elif len(components_to_group) == 1:
            for key, group_df in datapoints_variable.groupby(components_to_group[0], dropna=False):
                rows, cols, sheets = cls.group_cell_components(datapoints_variable=group_df,
                                                               datapoints_table=datapoints_table)
                result_lst.append((rows, cols, sheets, group_df['cell_id'].to_list()))
        else:
            ref_component = components_to_group[0]
            second_group_component = components_to_group[1]
            third_component = [component for component in CELL_COMPONENTS if component not in components_to_group][0]

            reference_prefix = ROW if ref_component == ROW_CODE else COLUMN if ref_component == COLUMN_CODE else SHEET
            second_component_prefix = ROW if second_group_component == ROW_CODE else COLUMN if second_group_component == COLUMN_CODE else SHEET
            third_component_prefix = ROW if third_component == ROW_CODE else COLUMN if third_component == COLUMN_CODE else SHEET

            datapoints_variable = datapoints_variable.sort_values([ref_component, second_group_component])

            components_dict = {}
            for value in datapoints_variable[ref_component].unique().tolist():
                components_dict[value] = datapoints_variable[datapoints_variable[ref_component] == value][
                    second_group_component].unique().tolist()

            # group reference component values by second group component values
            for keys_values, group_values in groupby(components_dict.items(), key=lambda x: sorted(x[1])):
                group_values = [v[0] for v in group_values]
                reference_component_grouping = cls.group_cell_component_elements(reference_prefix, group_values,
                                                                                 datapoints_table[ref_component])
                second_component_grouping = cls.group_cell_component_elements(second_component_prefix, keys_values,
                                                                              datapoints_table[second_group_component])
                third_component_grouping = None
                if not datapoints_variable[third_component].isnull().all():
                    third_values = datapoints_variable[
                        datapoints_variable[ref_component].isin(group_values) & datapoints_variable[
                            second_group_component].isin(keys_values)][third_component].unique().tolist()
                    third_component_grouping = cls.group_cell_component_elements(third_component_prefix, third_values,
                                                                                 datapoints_table[third_component])

                rows = reference_component_grouping if reference_prefix == ROW else second_component_grouping if second_component_prefix == ROW else third_component_grouping
                cols = reference_component_grouping if reference_prefix == COLUMN else second_component_grouping if second_component_prefix == COLUMN else third_component_grouping
                sheets = reference_component_grouping if reference_prefix == SHEET else second_component_grouping if second_component_prefix == SHEET else third_component_grouping
                result_lst.append((rows, cols, sheets, datapoints_variable['cell_id'].to_list()))  #TODO: Check this

        return result_lst

    @classmethod
    def group_cell_components(cls, datapoints_variable, datapoints_table):
        """
        Extracts the cell components by grouping them when necessary
        :param datapoints_variable: datapoints of the variable
        :param datapoints_table: datapoints of the table associated which the table code of operand
        :return Rows, cols and sheets of operand
        """
        rows = cls.group_cell_component_elements(ROW, datapoints_variable[ROW_CODE].tolist(),
                                                 datapoints_table[ROW_CODE])
        cols = cls.group_cell_component_elements(COLUMN, datapoints_variable[COLUMN_CODE].tolist(),
                                                 datapoints_table[COLUMN_CODE])
        sheets = cls.group_cell_component_elements(SHEET, datapoints_variable[SHEET_CODE].tolist(),
                                                   datapoints_table[SHEET_CODE])
        return rows, cols, sheets

    @classmethod
    def group_cell_component_elements(cls, cell_component_prefix: str, cell_component_elements: list,
                                      datapoints: pd.Series):
        """
        Groups elements of a cell component
        :param cell_component_prefix: Cell component name to be operated on
        :param cell_component_elements: values of operand cell component associated with the cell_component_prefix
         argument
        :param datapoints: values of table cell component associated with the cell_component_prefix argument
        return the cell component by grouping it when necessary
        """
        unique_values = set(cell_component_elements)
        if len(unique_values) == 0:
            return None
        elif len(unique_values) == 1:
            if cell_component_elements[0]:
                return cell_component_prefix + str(cell_component_elements[0])
            return None

        cell_component_elements.sort()
        cell_component_all_unique_values = datapoints.drop_duplicates().tolist()
        datapoints_cell_component = datapoints[
            datapoints.between(cell_component_elements[0], cell_component_elements[-1])]

        if len(unique_values) == len(cell_component_all_unique_values):
            return f"{cell_component_prefix}*"

        if len(unique_values) == len(datapoints_cell_component.drop_duplicates()):
            return f"{cell_component_prefix}{cell_component_elements[0]}-{cell_component_elements[-1]}"

        return '(' + ', '.join([f"{cell_component_prefix}{component}" for component in sorted(unique_values)]) + ')'

    @classmethod
    def write_cell(cls, table_code, rows, cols, sheets):
        """
        Returns a string that represents a cell expression
        :param table_code: Table code
        :param rows: Expression rows
        :param cols: Expression cols
        :param sheets: Expression sheets
        """
        table_code = f"t{table_code}" if table_code else None
        cell_components = [components for components in (table_code, rows, cols, sheets) if components]
        if len(cell_components):
            cell_info = ', '.join(cell_components)
            return '{' + cell_info + '}'
        return ""

    @classmethod
    def write_cell_with_asterisk(cls, table_code, rows, cols, sheets, reference_data):
        """
        Returns a string that represents a cell expression
        :param table_code: Table code
        :param rows: Expression rows
        :param cols: Expression cols
        :param sheets: Expression sheets
        """
        cell_info = ""
        # check if * is needed
        if rows and "-" in rows:
            rows = replace_range_by_asterisk(rows, reference_data[ROW_CODE], ROW)
        if cols and "-" in cols:
            cols = replace_range_by_asterisk(cols, reference_data[COLUMN_CODE], COLUMN)
        if sheets and "-" in sheets:
            sheets = replace_range_by_asterisk(sheets, reference_data[SHEET_CODE], SHEET)

        table_code = f"t{table_code}" if table_code else None
        cell_components = [components for components in (table_code, rows, cols, sheets) if components]
        if len(cell_components):
            cell_info = ', '.join(cell_components)
            return '{' + cell_info + '}'
        return None

    @classmethod
    def _several_validations_checker(cls, df)->(bool,pd.DataFrame):
        """
        Checks if the dataframe has several validations
        :param df: dataframe with validations
        :return True if the dataframe has several validations, False otherwise
        """
        # TODO: Check this, example F_18.00.b sign validations
        checker = 0
        checker_component = []
        for c_component in CELL_COMPONENTS:
            if df[c_component].nunique() > 1:
                checker += 1
                checker_component.append(c_component)
        if checker == 2:
            results = _two_components_checker(df, checker_component)
            if results:
                return True, results
        if checker == 3:
            # TODO: To implement, not necessary for now because there are no sign validations (withoout components to group) with 3 components
            pass

        return False, None

def _two_components_checker(df, checker_component)->list:
    """
    Checks if the dataframe has several validations
    :param df: dataframe with validations
    :return True if the dataframe has several validations, False otherwise
    """
    results = []
    for i in enumerate(checker_component):
        component_group = checker_component[i[0]-1]
        other_component = checker_component[i[0]]
        # component_group_values = df[component_group].unique().tolist()
        group_df = df.groupby(component_group)
        dict_related = {}
        dict_values = {}
        for a, b in group_df:
            dict_values[a] = b[other_component].unique().tolist()

        for k, v in dict_values.items():
            dict_related[k] = []
            for i, j in dict_values.items():
                if k != i:
                    if set(v) == set(j):
                        dict_related[k].append(i)
        components_grouped_list = [(k, *v) for k, v in dict_related.items()]
        components_grouped_sorted = [sorted(x) for x in components_grouped_list]
        components_grouped_sorted = [tuple(x) for x in components_grouped_sorted]
        components_set = set(components_grouped_sorted)

        if len(components_set) > 1:
            for elto in components_set:
                results.append(df[df[component_group].isin(elto)])

    return results

def replace_range_by_asterisk(expression, df_component, component_prefix):
    """
    Replaces range by asterisk
    :param expression: expression to be replaced
    :return expression with asterisk
    """
    sorted_list = sorted(df_component.drop_duplicates().to_list())
    # sorted_list = sorted(list(set(df_component.to_list())))
    first_element_expression = expression.split("-")[0][1:]
    last_element_expression = expression.split("-")[1]
    if len(sorted_list) > 1 and first_element_expression == sorted_list[0] \
            and last_element_expression == sorted_list[-1]:
        return component_prefix + "*"

    return expression
