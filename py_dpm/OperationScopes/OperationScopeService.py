import uuid
from datetime import datetime
from itertools import product

import numpy
import pandas as pd

from py_dpm.Exceptions import exceptions
from py_dpm.models import ModuleVersion, OperationScope, OperationScopeComposition
from py_dpm.Utils.tokens import VARIABLE_VID, WARNING_SEVERITY
from py_dpm.db_utils import get_session

FROM_REFERENCE_DATE = "FromReferenceDate"
TO_REFERENCE_DATE = "ToReferenceDate"
MODULE_VID = "ModuleVID"
TABLE_VID = "TableVID"


def _check_if_existing(composition_modules, existing_scopes):
    existing_scopes = existing_scopes[existing_scopes[MODULE_VID].isin(composition_modules)][MODULE_VID].tolist()
    if len(existing_scopes) and set(composition_modules) == set(existing_scopes):
        return True
    return False


class OperationScopeService:
    """
    Class to calculate OperationScope and OperationScopeComposition tables for an operation version
    """

    def __init__(self, operation_version_id, session=None):
        self.operation_version_id = operation_version_id
        self.session = session or get_session()
        self.module_vids = []
        self.current_date = datetime.today().date()

        self.operation_scopes = []

    def calculate_operation_scope(self, tables_vids: list, precondition_items: list, only_last_release=True):
        """
        Calculate OperationScope and OperationScopeComposition tables for an operation version, taking as input
        a list with the operation table version ids in order to calculate the module versions involved in the operation
        :param tables_vids: List with table version ids
        :param precondition_items: List with precondition codes
        :return two list with existing and new scopes
        """

        modules_info_dataframe = self.extract_module_info(
            tables_vids=tables_vids, precondition_items=precondition_items, only_last_release=only_last_release)  # We extract all the releases from the database
        if modules_info_dataframe is None:
            return [], []

        modules_vids = modules_info_dataframe[MODULE_VID].unique().tolist()
        if len(modules_info_dataframe) == 1:
            module_vid = modules_vids[0]
            from_date = modules_info_dataframe['FromReferenceDate'].values[0]
            operation_scope = self.create_operation_scope(from_date)
            self.create_operation_scope_composition(operation_scope=operation_scope, module_vid=module_vid)
        else:
            intra_modules = []
            cross_modules = {}
            unique_operands_number = len(tables_vids) + len(precondition_items)

            for module_vid, group_df in modules_info_dataframe.groupby(MODULE_VID):
                vids = group_df[VARIABLE_VID].unique().tolist()
                if len(vids) == unique_operands_number:
                    intra_modules.append(module_vid)
                else:
                    for table_vid in vids:
                        if table_vid not in cross_modules:
                            cross_modules[table_vid] = []
                        cross_modules[table_vid].append(module_vid)

            if len(intra_modules):
                self.process_repeated(intra_modules, modules_info_dataframe)

            if cross_modules:
                if set(cross_modules.keys())==set(tables_vids):
                    self.process_cross_module(cross_modules=cross_modules, modules_dataframe=modules_info_dataframe)
                else:
                    # add the missing table_vids to cross_modules
                    for table_vid in tables_vids:
                        if table_vid not in cross_modules:
                            cross_modules[table_vid] =  modules_info_dataframe[modules_info_dataframe[VARIABLE_VID]==table_vid][MODULE_VID].unique().tolist()
                    self.process_cross_module(cross_modules=cross_modules, modules_dataframe=modules_info_dataframe)

        return self.get_scopes_with_status()

    def extract_module_info(self, tables_vids, precondition_items, only_last_release=True):
        """
        Extracts modules information of tables version ids and preconditions from database and
        joins them in a single dataframe
        :param tables_vids: List with table version ids
        :param precondition_items: List with precondition codes
        :return two list with existing and new scopes
        """
        modules_info_lst = []
        modules_info_dataframe = None
        if len(tables_vids):
            tables_modules_info_dataframe = ModuleVersion.get_from_tables_vids(
                session=self.session, tables_vids=tables_vids, only_last_release=only_last_release)
            if tables_modules_info_dataframe.empty:
                missing_table_modules = tables_vids
            else:
                modules_tables = tables_modules_info_dataframe[TABLE_VID].tolist()
                missing_table_modules = set(tables_vids).difference(set(modules_tables))

            if len(missing_table_modules):
                raise exceptions.SemanticError("1-13", table_version_ids=missing_table_modules)

            tables_modules_info_dataframe.rename(columns={TABLE_VID: VARIABLE_VID}, inplace=True)
            modules_info_lst.append(tables_modules_info_dataframe)

        if len(precondition_items):
            preconditions_modules_info_dataframe = ModuleVersion.get_precondition_module_versions(session=self.session,
                                                                                                  precondition_items=precondition_items)

            if preconditions_modules_info_dataframe.empty:
                missing_precondition_modules = precondition_items
            else:
                modules_preconditions = preconditions_modules_info_dataframe['Code'].tolist()
                missing_precondition_modules = set(precondition_items).difference(set(modules_preconditions))

            if missing_precondition_modules:
                raise exceptions.SemanticError("1-14", precondition_items=missing_precondition_modules)

            preconditions_modules_info_dataframe.rename(columns={'VariableVID': VARIABLE_VID}, inplace=True)
            modules_info_lst.append(preconditions_modules_info_dataframe)

        if len(modules_info_lst):
            modules_info_dataframe = pd.concat(modules_info_lst)
        return modules_info_dataframe

    def process_repeated(self, modules_vids, modules_info):
        """
        Method to calculate OperationScope and OperationScopeComposition tables for repeated operations
        :param modules_vids: list with module version ids
        """
        for module_vid in modules_vids:
            from_date = modules_info[modules_info['ModuleVID'] == module_vid]['FromReferenceDate'].values[0]
            operation_scope = self.create_operation_scope(from_date)
            self.create_operation_scope_composition(operation_scope=operation_scope, module_vid=module_vid)

    def process_cross_module(self, cross_modules, modules_dataframe):
        """
        Method to calculate OperationScope and OperationScopeComposition tables for a cross module operation
        :param cross_modules: dictionary with table version ids as key and its module version ids as values
        :param modules_dataframe: dataframe with modules data
        """
        modules_dataframe[FROM_REFERENCE_DATE] = pd.to_datetime(modules_dataframe[FROM_REFERENCE_DATE])
        modules_dataframe[TO_REFERENCE_DATE] = pd.to_datetime(modules_dataframe[TO_REFERENCE_DATE])

        values = cross_modules.values()
        for combination in product(*values):
            combination_info = modules_dataframe[modules_dataframe[MODULE_VID].isin(combination)]
            from_dates = combination_info[FROM_REFERENCE_DATE].values
            to_dates = combination_info[TO_REFERENCE_DATE].values
            ref_from_date = from_dates.max()
            ref_to_date = to_dates.min()

            is_valid_combination = True
            for from_date, to_date in zip(from_dates, to_dates):
                if to_date < ref_from_date or ((not pd.isna(ref_to_date)) and from_date > ref_to_date):
                    is_valid_combination = False

            if is_valid_combination:
                from_submission_date = ref_from_date
            else:
                from_submission_date = None
            operation_scope = self.create_operation_scope(from_submission_date)
            combination = set(combination)
            for module in combination:
                self.create_operation_scope_composition(operation_scope=operation_scope, module_vid=module)

    def create_operation_scope(self, submission_date):
        """
        Method to populate OperationScope table
        """
        if not pd.isnull(submission_date):
            if isinstance(submission_date, numpy.datetime64):
                submission_date = str(submission_date).split('T')[0]
            if isinstance(submission_date, str):
                submission_date = datetime.strptime(submission_date, '%Y-%m-%d').date()
            elif isinstance(submission_date, datetime):
                submission_date = submission_date.date()
        else:
            submission_date = None
        operation_scope = OperationScope(
            OperationVID=self.operation_version_id,
            IsActive=True,
            Severity=WARNING_SEVERITY,
            FromSubmissionDate=submission_date,
            RowGUID=uuid.uuid4()
        )
        self.session.add(operation_scope)
        return operation_scope

    def create_operation_scope_composition(self, operation_scope, module_vid):
        """
        Method to populate OperationScopeComposition table
        :param operation_scope: Operation scope data
        :param module_vid: Module version id
        """
        operation_scope_composition = OperationScopeComposition(
            operation_scope=operation_scope,
            ModuleVID=module_vid,
            RowGUID=uuid.uuid4()
        )
        self.session.add(operation_scope_composition)

    def get_scopes_with_status(self):
        """
        Method that checks if operation scope exists in database and classifies it based on whether it exists or not
        :return two list with existing and new scopes
        """
        existing_scopes = []
        new_scopes = []
        operation_scopes = [o for o in self.session.new if isinstance(o, OperationScope)]
        database_scopes = OperationScopeComposition.get_from_operation_version_id(self.session,
                                                                                  self.operation_version_id)
        if database_scopes.empty:
            new_scopes = operation_scopes
        else:
            for scope in operation_scopes:
                composition_modules = [scope_comp.ModuleVID for scope_comp in scope.composition]
                result = database_scopes.groupby('OperationScopeID').filter(
                    lambda x: _check_if_existing(composition_modules, x))

                if not result.empty:
                    existing_scopes.append(scope)
                else:
                    # if the module is closed and the operation is new, we haven't to create a new scope wih the old module
                    # because we have the new module
                    existing_previous = False
                    for vid in composition_modules:
                        if id not in existing_scopes:
                            aux = ModuleVersion.get_module_version_by_vid(session=self.session, vid=vid)
                            if aux.empty:
                                continue
                            if aux['EndReleaseID'][0] is not None:
                                existing_previous = True
                                break

                    if not existing_previous:
                        new_scopes.append(scope)

        return existing_scopes, new_scopes
