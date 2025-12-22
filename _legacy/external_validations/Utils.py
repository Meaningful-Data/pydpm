import json
import warnings
from datetime import datetime
from http.client import BAD_REQUEST, INTERNAL_SERVER_ERROR
from pathlib import Path

import pandas as pd

from py_dpm.Exceptions.exceptions import ScriptingError, SemanticError
from py_dpm.models import OperationVersion, SubCategory, TableVersionCell, ViewReportTypeOperandReferenceInfo
from py_dpm.db_utils import get_session


def format_table_code(code: str):
    if not code or pd.isna(code):
        return None
    code = code.replace(' ', '_')
    return code

def assing_sign(formula):
    if "<" in formula:
        return "negative" # negative
    elif ">" in formula:
        return "positive" # positive
    else:
        return None


def read_external_sign_data(**kwargs):
    path = Path(__file__).parent / 'utils_report' / 'external_data'

    eba_rules = path / 'EBA_Validation_Rules_2022-12-12.xlsx'
    sht = '3.2(3.2.1, 3.2.2)'  # wb['v3.1(3.1.1)']  # the last one at 21/06/2022

    eba_df = pd.read_excel(eba_rules, sheet_name=sht)
    sign_validations = eba_df[eba_df['Type'] == 'Sign']
    sign_validations['Table Code'] = sign_validations['T1'].map(lambda x: x.replace(' ', '_'))#map(format_table_code)
    sign_validations["Sign"] = sign_validations["Formula"].map(assing_sign)
    sign_validations = sign_validations[["Table Code", "Sign", "ID"]]
    update_sign_db(sign_validations)
    return sign_validations


def update_sign_db(sign_validations):  # TODO: this does not work because DDL restrictions
    session = get_session()
    # sign_validations =  read_external_sign_data()
    neg_tables = sign_validations[sign_validations["Sign"]=='negative']["Table Code"].unique().tolist()
    pos_tables = sign_validations[sign_validations["Sign"]=='positive']["Table Code"].unique().tolist()
    all_neg_table_version_ids = TableVersionCell.get_sign_query(session=session, sign=neg_tables)
    all_pos_table_version_ids = TableVersionCell.get_sign_query(session=session, sign=pos_tables)
    for table_version in all_neg_table_version_ids:
        table_version.Sign = "negative"
        session.commit()
    for table_version in all_pos_table_version_ids:
        table_version.Sign = "positive"
        session.commit()

    # session.commit()
    session.close()

def _error_to_dict(error):
    if isinstance(error, SemanticError):
        status = BAD_REQUEST
        message_error = error.args[0]
        error_code = error.args[1]
    elif isinstance(error, SyntaxError):
        status = BAD_REQUEST
        message_error = error.args[0]
        error_code = "Syntax"
    elif isinstance(error, ScriptingError):
        status = BAD_REQUEST
        message_error = error.args[0]
        error_code = error.args[1]
    else:
        status = INTERNAL_SERVER_ERROR
        message_error = str(error)
        now = datetime.now()
        warnings.warn(f"[{now}] Unhandled exception:\n{error}", RuntimeWarning)
        error_code = "Other"

    return status, message_error, error_code


class ExternalData:

    def __init__(self):
        self.proposed_rules, self.rejected_rules = self.read_external_data()

    def read_external_data(self, **kwargs):
        path = Path(__file__).parent / 'utils_report' / 'external_data'

        proposed_rules_path = path / 'out_put_proposed_rules.xlsx'
        rejected_rules_path = path / 'RejectedRuleProposals.csv'
        proposed_rules = pd.read_excel(proposed_rules_path)
        rejected_rules = pd.read_csv(rejected_rules_path, encoding='latin-1')
        return proposed_rules, rejected_rules

    @staticmethod
    def get_expression_from_code(code: str):
        if not code or pd.isna(code):
            return None
        sql_session = get_session()
        expression = OperationVersion.get_operations_from_code(sql_session, code)
        expression = expression["Expression"].iloc[0]  # TODO check if there is more than one expression take the last one maybe
        sql_session.close()
        return expression

    @classmethod
    def create_report(cls, report_df:pd.DataFrame, info_dict:dict, path:Path, name_report:str):
        path_info = path / f"{name_report}_info.json"
        path_validations = path / f"{name_report}_validations.csv"
        report_df.to_csv(path_validations, index=False)
        with open(path_info, 'w') as f:
            f.write(json.dumps(info_dict))


class ExternalDataHierarchies(ExternalData):

    def __init__(self):
        super().__init__()
        # self.proposed_rules = self.proposed_rules.rename(columns={'HierarchyCode':'Hierarchy Code'})
        self.proposed_rules = self.proposed_rules.dropna(subset=['Hierarchy Code']).reset_index(drop=True)
        self.rejected_rules = self.rejected_rules.dropna(subset=['HierarchyCode']).reset_index(drop=True)

    def get_hierarchy_subcategory(self, subcategory_code):
        proposed_rules, rejected_rules = self.proposed_rules, self.rejected_rules

        proposed_rules = proposed_rules[proposed_rules['Hierarchy Code'] == subcategory_code]
        rejected_rules = rejected_rules[rejected_rules['HierarchyCode'] == subcategory_code]

        return proposed_rules, rejected_rules

    def compare_all_hierarchies_report(self, validations: list):
        total_number_of_validations_created = 0
        total_number_of_validations_proposed = 0
        total_number_of_validations_rejected = 0
        total_matches_codes = 0
        total_duplicated_codes = 0
        total_codes_dont_match_with_proposed = 0
        total_missing_codes = 0
        total_expressions_dont_match_with_proposed = 0
        sql_session = get_session()
        subcategory_codes = SubCategory.get_codes(session=sql_session)
        sql_session.close()
        subcategory_codes = [subcategory_code[0] for subcategory_code in subcategory_codes]
        total_info = {}
        total_merged = pd.DataFrame()
        for subcategory_code in subcategory_codes:
            validations_subcategory = [elto for elto in validations if elto['subcategory_code'] == subcategory_code]
            merged, info = self.compare_hierarchies_report(validations_subcategory, subcategory_code)
            total_merged = pd.concat([total_merged, merged])
            for key, value in info.items():
                total_info[key] = value
                total_number_of_validations_created += value["number_of_validations_created"]
                total_number_of_validations_proposed += value["number_of_validations_proposed"]
                total_number_of_validations_rejected += value["number_of_validations_rejected"]
                total_matches_codes += len(value["matches_codes(generated_expressions)"])
                if "errors" in value.keys():
                    total_duplicated_codes += len(value["errors"]["duplicated_codes"])
                    total_codes_dont_match_with_proposed += len(value["errors"]["codes_dont_match_with_proposed"])
                    total_missing_codes += len(value["errors"]["missing_codes"])
                    total_expressions_dont_match_with_proposed += len(value["errors"]["expressions_dont_match_with_proposed"])

        # aditional actions on total info
        description = {}
        description["total_number_of_validations_created"] = total_number_of_validations_created
        description["total_number_of_validations_proposed"] = total_number_of_validations_proposed
        description["total_number_of_validations_rejected"] = total_number_of_validations_rejected
        description["total_matches_codes(generated_expressions)"] = total_matches_codes
        description["total_duplicated_codes"] = total_duplicated_codes
        description["total_codes_dont_match_with_proposed"] = total_codes_dont_match_with_proposed
        description["total_missing_codes"] = total_missing_codes
        description["total_expressions_dont_match_with_proposed"] = total_expressions_dont_match_with_proposed
        final_info = {}
        final_info["resume"] = description
        final_info["subcategories"] = total_info

        return total_merged, final_info

    def compare_hierarchies_report(self, validations: list, subcategory_code: str):
        proposed, rejected = self.get_hierarchy_subcategory(subcategory_code=subcategory_code)
        proposed_specific = pd.DataFrame(columns=['ID', 'Formula', 'ProposedAction', 'Review Action', 'Hierarchy Code']) if proposed.empty else proposed[['ID', 'Formula', 'ProposedAction', 'Review Action', 'Hierarchy Code']]
        rejected_specific = pd.DataFrame(columns=['ID', 'Formula', 'ProposedAction', 'Review Action', 'Hierarchy Code']) if rejected.empty else rejected[['ID', 'Formula', 'ProposedAction', 'ReviewAction', 'HierarchyCode']].rename(columns={'HierarchyCode':'Hierarchy Code', 'ReviewAction':'Review Action'})
        info = {}
        errors = {}
        errors[subcategory_code] = {}
        errors[subcategory_code]['duplicated_codes'] = []

        proposed_codes = proposed_specific[~proposed_specific['ID'].isna()]["ID"].unique().tolist()
        rejected_codes = rejected_specific['ID'].unique().tolist()
        total_external = pd.concat([proposed_specific, rejected_specific])
        total_external_codes = total_external['ID'].unique().tolist()
        # validations_codes
        validations_codes = []

        [validations_codes.extend(elto['operation_code']) for elto in validations]

        if len(validations_codes) != len(set(validations_codes)):
            errors[subcategory_code]['duplicated_codes'] = list(set([code for code in validations_codes if validations_codes.count(code) > 1]))
            validations_codes = list(set(validations_codes))

        errors[subcategory_code]['codes_dont_match_with_proposed'] = [code for code in validations_codes if code not in total_external_codes]  # TODO
        errors[subcategory_code]['missing_codes'] = [code for code in proposed_codes if code not in validations_codes]

        #create comparative report
        #first adapt validations
        validations_to_df = []
        errors[subcategory_code]['expressions_dont_match_with_proposed'] = []

        for elto in validations:
            is_duplicated = False
            if len(elto['operation_code']) == 0:
                if elto['expression'] not in errors[subcategory_code]['expressions_dont_match_with_proposed']:
                    errors[subcategory_code]['expressions_dont_match_with_proposed'].append(elto['expression'])
                validations_to_df.append(
                    {'code':None, 'expression':elto['expression'], 'status':elto['status'],
                    'subcategory_code':subcategory_code, 'is_duplicated':is_duplicated
                    }
                )
            if len(set(elto['operation_code'])) > 1:
                is_duplicated = True
                errors[subcategory_code]['duplicated_codes'].extend(elto['operation_code'])

            for op_code in elto['operation_code']:
                validations_to_df.append(
                    {'code':op_code, 'expression':elto['expression'], 'status':elto['status'],
                    'subcategory_code':subcategory_code, 'is_duplicated':is_duplicated
                    }
                )

        info[subcategory_code] = {'number_of_validations_created':len(validations)}
        info[subcategory_code]['number_of_validations_proposed'] = len(proposed_specific)
        info[subcategory_code]['number_of_validations_rejected'] = len(rejected_specific)
        comparative_report = pd.DataFrame(validations_to_df)
        if comparative_report.empty:
            comparative_report = pd.DataFrame(columns=['code', 'expression', 'status', 'subcategory_code', 'is_duplicated'])

        merged = comparative_report.merge(total_external, left_on='code', right_on='ID', how='outer', indicator=True)
        info[subcategory_code]['matches_codes(generated_expressions)'] = merged[~merged['code'].isna()]["code"].unique().tolist()
        # external_code, external_expression, proposed action, code, expression, ...

        # if not merged.empty:
        merged["expression_from_db"] = merged["code"].map(ExternalData.get_expression_from_code)
        del merged['_merge']
        errors[subcategory_code]['duplicated_codes'] = list(set(errors[subcategory_code]['duplicated_codes']))
        info[subcategory_code]["errors"] = errors[subcategory_code]  # TODO
        proposed_expressions_without_code = proposed_specific[proposed_specific['ID'].isna()]["Formula"].unique().tolist()
        if proposed_expressions_without_code:
            info[subcategory_code]['proposed_expressions_without_code'] = proposed_expressions_without_code
        info[subcategory_code]['aditional info']=[{elto["expression"]:elto["aproximated_operations"]} for elto in validations if not elto["operation_code"]]
        return merged, info

    # @staticmethod
    # def create_report(report_df:pd.DataFrame, info_dict:dict, subcategory_code:str=None):
    #     name_report = subcategory_code if subcategory_code else 'all_subcategories'
    #     path = Path(__file__).parent / 'utils_report' / 'hierarchies_report'
    #     path_errors = path / f"{name_report}_info.json"
    #     path_validations = path / f"{name_report}_validations.csv"
    #     report_df.to_csv(path_validations, index=False)
    #     with open(path_errors, 'w') as f:
    #         f.write(json.dumps(info_dict))

    @classmethod
    def create_report(cls, report_df:pd.DataFrame, info_dict:dict, subcategory_code:str=None):
        name_report = subcategory_code if subcategory_code else 'all_subcategories'
        path = Path(__file__).parent / 'utils_report' / 'hierarchies_report'
        super().create_report(report_df, info_dict, path, name_report)


class ExternalDataSign(ExternalData):

    def __init__(self):
        super().__init__()
        self.proposed_rules = self.proposed_rules[self.proposed_rules['Type']=="Sign"]
        self.rejected_rules = self.rejected_rules[self.rejected_rules['Type']=="Sign"]


    def match_code(self, validations: list, report_type: str):
        """
        """
        for elto in validations:
            total_cells_id = elto["cell_data"]
            sql_session = get_session()
            matched_codes = ViewReportTypeOperandReferenceInfo.get_cell_report_operations(sql_session, total_cells_id, report_type)
            elto["operation_code"] = matched_codes
            sql_session.close()
            # new version end

        return validations

    def compare_all_sign_report(self, validations: list):
        proposed, rejected = self.proposed_rules, self.rejected_rules
        proposed_specific = pd.DataFrame(columns=['ID', 'Formula', 'ProposedAction', 'Review Action', 'Framework']) if proposed.empty else proposed[['ID', 'Formula', 'ProposedAction', 'Review Action', 'Framework']]
        rejected_specific = pd.DataFrame(columns=['ID', 'Formula', 'ProposedAction', 'Review Action']) if rejected.empty else rejected[['ID', 'Formula', 'ProposedAction', 'ReviewAction']].rename(columns={'ReviewAction':'Review Action'})
        info = {}
        errors = {}

        proposed_codes = proposed_specific[~proposed_specific['ID'].isna()]["ID"].unique().tolist()
        rejected_codes = rejected_specific['ID'].unique().tolist()
        total_external = pd.concat([proposed_specific, rejected_specific])
        total_external_codes = total_external['ID'].unique().tolist()
        # validations_codes
        validations_codes = []

        [validations_codes.extend(elto['operation_code']) for elto in validations]

        if len(validations_codes) != len(set(validations_codes)):
            errors['duplicated_codes'] = list(set([code for code in validations_codes if validations_codes.count(code) > 1]))
            validations_codes = list(set(validations_codes))

        # no match expressions
        errors['expressions_dont_match_with_proposed'] = [elto['expression'] for elto in validations if len(elto['operation_code']) == 0]
        # missing codes
        errors['missing_codes'] = [code for code in total_external_codes if code not in validations_codes]
        # exceded codes
        errors['exceded_codes'] = [code for code in validations_codes if code not in total_external_codes]

        validations_to_df = []
        for elto in validations:
            if len(elto['operation_code']) == 0:
                validations_to_df.append(
                    {'code':None, 'expression':elto['expression'], 'status':elto['status'],
                    'table':None
                    }
                )
            elif len(elto['operation_code']) == 1:
                validations_to_df.append(
                    {'code':elto['operation_code'][0], 'expression':elto['expression'], 'status':elto['status'],
                    'table':None
                    }
                    )
            else:
                for code in elto['operation_code']:
                    validations_to_df.append(
                        {'code':code, 'expression':elto['expression'], 'status':elto['status'],
                        'table':None
                        }
                        )
        comparative_report = pd.DataFrame(validations_to_df)
        if comparative_report.empty:
            comparative_report = pd.DataFrame(columns=['code', 'expression', 'status', 'subcategory_code', 'is_duplicated'])

        merged = comparative_report.merge(total_external, left_on='code', right_on='ID', how='outer', indicator=True)
        merged["expression_from_db"] = merged["code"].map(ExternalData.get_expression_from_code)
        del merged['_merge']
        # total_merged, total_info = proposed_specific, rejected_specific

        return merged, errors

    @classmethod
    def create_report(cls, report_df:pd.DataFrame, info_dict:dict):
        name_report = 'signes'
        path = Path(__file__).parent / 'utils_report' / 'signes_report'
        super().create_report(report_df, info_dict, path, name_report)

class ExternalDataExistence(ExternalData):

    def __init__(self):
        super().__init__()
        self.proposed_rules = self.proposed_rules[self.proposed_rules['Type']=="Existence"]
        self.rejected_rules = self.rejected_rules[self.rejected_rules['Type']=="Existence"]

    def compare_all_existence_report(self, validations: list):
        pass