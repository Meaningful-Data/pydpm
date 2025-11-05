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

    def calculate_operation_scope(self, tables_vids: list, precondition_items: list, release_id=None, table_codes: list = None):
        """
        Calculate OperationScope and OperationScopeComposition tables for an operation version, taking as input
        a list with the operation table version ids in order to calculate the module versions involved in the operation
        :param tables_vids: List with table version ids
        :param precondition_items: List with precondition codes
        :param release_id: Optional release ID to filter modules. If None, defaults to last release.
        :param table_codes: Optional list of table codes. If provided, finds ALL module versions with these table codes in the release.
        :return two list with existing and new scopes
        """
        # Get last release if not specified
        if release_id is None:
            release_id = ModuleVersion.get_last_release(self.session)

        modules_info_dataframe = self.extract_module_info(
            tables_vids=tables_vids, precondition_items=precondition_items, release_id=release_id, table_codes=table_codes)  # We extract all the releases from the database
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

            # When using table_codes, unique operands are based on table codes, not table VIDs
            if table_codes:
                unique_operands_number = len(table_codes) + len(precondition_items)

                # Categorize modules by lifecycle: starting vs ending in this release
                starting_modules = {}  # Modules that START in this release (replacements)
                ending_modules = {}    # Modules that END in this release (being replaced)

                for module_vid, group_df in modules_info_dataframe.groupby(MODULE_VID):
                    table_codes_in_module = group_df['TableCode'].unique().tolist() if 'TableCode' in group_df.columns else []

                    # Get module lifecycle info
                    start_release = group_df['StartReleaseID'].values[0] if 'StartReleaseID' in group_df.columns else None
                    end_release = group_df['EndReleaseID'].values[0]

                    # Determine if this is a "new" module starting in this release
                    # or an "old" module ending in this release
                    is_starting = (start_release == release_id)
                    is_ending = (end_release == release_id or end_release == float(release_id))

                    if len(table_codes_in_module) == unique_operands_number:
                        # Intra-module: include ALL modules active in the release
                        # (don't filter by lifecycle - that's only for cross-module)
                        intra_modules.append(module_vid)
                    else:
                        # For cross-module, group by table code AND lifecycle stage
                        target_dict = starting_modules if is_starting else ending_modules
                        for table_code in table_codes_in_module:
                            if table_code not in target_dict:
                                target_dict[table_code] = []
                            target_dict[table_code].append(module_vid)

                # Process cross-module scopes separately for each generation
                if starting_modules:
                    cross_modules['_starting'] = starting_modules
                if ending_modules:
                    cross_modules['_ending'] = ending_modules
            else:
                # Original logic for table VIDs
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
                # When using table_codes with lifecycle grouping
                if table_codes and ('_starting' in cross_modules or '_ending' in cross_modules):
                    # Process each generation separately
                    if '_starting' in cross_modules:
                        self.process_cross_module(cross_modules=cross_modules['_starting'], modules_dataframe=modules_info_dataframe)
                    if '_ending' in cross_modules:
                        self.process_cross_module(cross_modules=cross_modules['_ending'], modules_dataframe=modules_info_dataframe)
                # Legacy table_codes without lifecycle grouping
                elif table_codes:
                    self.process_cross_module(cross_modules=cross_modules, modules_dataframe=modules_info_dataframe)
                elif set(cross_modules.keys())==set(tables_vids):
                    self.process_cross_module(cross_modules=cross_modules, modules_dataframe=modules_info_dataframe)
                else:
                    # add the missing table_vids to cross_modules
                    for table_vid in tables_vids:
                        if table_vid not in cross_modules:
                            cross_modules[table_vid] =  modules_info_dataframe[modules_info_dataframe[VARIABLE_VID]==table_vid][MODULE_VID].unique().tolist()
                    self.process_cross_module(cross_modules=cross_modules, modules_dataframe=modules_info_dataframe)

        return self.get_scopes_with_status()

    def extract_module_info(self, tables_vids, precondition_items, release_id=None, table_codes=None):
        """
        Extracts modules information of tables version ids and preconditions from database and
        joins them in a single dataframe
        :param tables_vids: List with table version ids
        :param precondition_items: List with precondition codes
        :param release_id: Optional release ID to filter modules
        :param table_codes: Optional list of table codes. If provided, queries ALL module versions with these codes.
        :return two list with existing and new scopes
        """
        modules_info_lst = []
        modules_info_dataframe = None

        # If table_codes are provided, query by codes to get ALL versions
        if table_codes and len(table_codes):
            tables_modules_info_dataframe = ModuleVersion.get_from_table_codes(
                session=self.session, table_codes=table_codes, release_id=release_id)
            if tables_modules_info_dataframe.empty:
                raise exceptions.SemanticError("1-13", table_codes=table_codes)
            modules_info_lst.append(tables_modules_info_dataframe)
        # Otherwise use the traditional table VID approach
        elif len(tables_vids):
            tables_modules_info_dataframe = ModuleVersion.get_from_tables_vids(
                session=self.session, tables_vids=tables_vids, release_id=release_id)
            if tables_modules_info_dataframe.empty:
                missing_table_modules = tables_vids
            else:
                modules_tables = tables_modules_info_dataframe[VARIABLE_VID].tolist()
                missing_table_modules = set(tables_vids).difference(set(modules_tables))

            if len(missing_table_modules):
                raise exceptions.SemanticError("1-13", table_version_ids=missing_table_modules)

            modules_info_lst.append(tables_modules_info_dataframe)

        if len(precondition_items):
            preconditions_modules_info_dataframe = ModuleVersion.get_precondition_module_versions(session=self.session,
                                                                                                  precondition_items=precondition_items,
                                                                                                  release_id=release_id)

            if preconditions_modules_info_dataframe.empty:
                missing_precondition_modules = precondition_items
            else:
                modules_preconditions = preconditions_modules_info_dataframe['Code'].tolist()
                missing_precondition_modules = set(precondition_items).difference(set(modules_preconditions))

            if missing_precondition_modules:
                raise exceptions.SemanticError("1-14", precondition_items=missing_precondition_modules)

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
        modules_dataframe[FROM_REFERENCE_DATE] = pd.to_datetime(modules_dataframe[FROM_REFERENCE_DATE], format='mixed', dayfirst=True)
        modules_dataframe[TO_REFERENCE_DATE] = pd.to_datetime(modules_dataframe[TO_REFERENCE_DATE], format='mixed', dayfirst=True)

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
            operationvid=self.operation_version_id,
            isactive=1,  # Use 1 instead of True for PostgreSQL bigint compatibility
            severity=WARNING_SEVERITY,
            fromsubmissiondate=submission_date,
            rowguid=str(uuid.uuid4())
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
            modulevid=module_vid,
            rowguid=str(uuid.uuid4())
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
                composition_modules = [scope_comp.modulevid for scope_comp in scope.operation_scope_compositions]
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
