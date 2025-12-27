from typing import Optional

from sqlalchemy import func, literal
from sqlalchemy.orm import aliased

from py_dpm.dpm.models import (
    Framework,
    Module,
    ModuleVersionComposition,
    Table,
    ModuleVersion,
    TableVersion,
    Header,
    HeaderVersion,
    TableVersionHeader,
    Cell,
    TableVersionCell,
    VariableVersion,
    Property,
    DataType,
    Item,
)
from py_dpm.dpm.queries.filters import (
    filter_by_release,
    filter_by_date,
    filter_active_only,
)


class HierarchicalQuery:
    """
    Queries that return hierarchical dictionaries for collections
    and similar objects
    """

    @staticmethod
    def get_module_version(
        session,
        module_code: str,
        release_id: Optional[int] = None,
        date: Optional[str] = None,
        release_code: Optional[str] = None,
    ) -> dict:

        if sum(bool(x) for x in [release_id, date, release_code]) > 1:
            raise ValueError(
                "Specify a maximum of one of release_id, release_code or date."
            )

        q = session.query(ModuleVersion).filter(ModuleVersion.code == module_code)

        if date:
            q = filter_by_date(
                q,
                date,
                ModuleVersion.fromreferencedate,
                ModuleVersion.toreferencedate,
            )
        elif release_id:
            q = filter_by_release(
                q,
                start_col=ModuleVersion.startreleaseid,
                end_col=ModuleVersion.endreleaseid,
                release_id=release_id,
            )
        elif release_code:
            q = filter_by_release(
                q,
                start_col=ModuleVersion.startreleaseid,
                end_col=ModuleVersion.endreleaseid,
                release_code=release_code,
            )
        else:
            q = filter_active_only(q, end_col=ModuleVersion.endreleaseid)

        query_result = q.all()

        if len(query_result) != 1:
            raise ValueError(
                f"Should return 1 record, but returned {len(query_result)}"
            )
        result = query_result[0].to_dict()

        table_versions = query_result[0].table_versions
        result["table_versions"] = [tv.to_dict() for tv in table_versions]

        return result

    @staticmethod
    def get_all_frameworks(
        session,
        release_id: Optional[int] = None,
        date: Optional[str] = None,
        release_code: Optional[str] = None,
    ) -> list[dict]:

        if sum(bool(x) for x in [release_id, date, release_code]) > 1:
            raise ValueError(
                "Specify a maximum of one of release_id, release_code or date."
            )

        q = (
            session.query(
                # Framework
                Framework.frameworkid,
                Framework.code.label("framework_code"),
                Framework.name.label("framework_name"),
                Framework.description.label("framework_description"),
                # ModuleVersion
                ModuleVersion.modulevid,
                ModuleVersion.moduleid,
                ModuleVersion.startreleaseid.label("module_version_startreleaseid"),
                ModuleVersion.endreleaseid.label("module_version_endreleaseid"),
                ModuleVersion.code.label("module_version_code"),
                ModuleVersion.name.label("module_version_name"),
                ModuleVersion.description.label("module_version_description"),
                ModuleVersion.versionnumber,
                ModuleVersion.fromreferencedate,
                ModuleVersion.toreferencedate,
                # TableVersion
                TableVersion.tablevid,
                TableVersion.code.label("table_version_code"),
                TableVersion.name.label("table_version_name"),
                TableVersion.description.label("table_version_description"),
                TableVersion.tableid.label("table_version_tableid"),
                TableVersion.abstracttableid,
                TableVersion.startreleaseid.label("table_version_startreleaseid"),
                TableVersion.endreleaseid.label("table_version_endreleaseid"),
                # Table
                Table.tableid.label("table_tableid"),
                Table.isabstract,
                Table.hasopencolumns,
                Table.hasopenrows,
                Table.hasopensheets,
                Table.isnormalised,
                Table.isflat,
            )
            .join(Module, Framework.modules)
            .join(ModuleVersion, Module.module_versions)
            .join(
                ModuleVersionComposition,
                ModuleVersion.module_version_compositions,
            )
            .join(TableVersion, ModuleVersionComposition.table_version)
            .join(Table, TableVersion.table)
        )

        if date:
            q = filter_by_date(
                q,
                date,
                ModuleVersion.fromreferencedate,
                ModuleVersion.toreferencedate,
            )
        elif release_id:
            q = filter_by_release(
                q,
                start_col=ModuleVersion.startreleaseid,
                end_col=ModuleVersion.endreleaseid,
                release_id=release_id,
            )
        elif release_code:
            q = filter_by_release(
                q,
                start_col=ModuleVersion.startreleaseid,
                end_col=ModuleVersion.endreleaseid,
                release_code=release_code,
            )
        else:
            q = filter_active_only(q, end_col=ModuleVersion.endreleaseid)

        # Execute query and return list of dictionaries
        query_result = [dict(row._mapping) for row in q.all()]

        frameworks = {}

        for row in query_result:
            fw_id = row["frameworkid"]
            if fw_id not in frameworks:
                frameworks[fw_id] = {
                    "frameworkid": row["frameworkid"],
                    "code": row["framework_code"],
                    "name": row["framework_name"],
                    "description": row["framework_description"],
                    "module_versions": {},
                }

            fw = frameworks[fw_id]

            mod_vid = row["modulevid"]
            if mod_vid not in fw["module_versions"]:
                fw["module_versions"][mod_vid] = {
                    "modulevid": row["modulevid"],
                    "moduleid": row["moduleid"],
                    "startreleaseid": row["module_version_startreleaseid"],
                    "endreleaseid": row["module_version_endreleaseid"],
                    "code": row["module_version_code"],
                    "name": row["module_version_name"],
                    "description": row["module_version_description"],
                    "versionnumber": row["versionnumber"],
                    "fromreferencedate": row["fromreferencedate"],
                    "toreferencedate": row["toreferencedate"],
                    "table_versions": [],
                }

            mod = fw["module_versions"][mod_vid]

            # Flatten TableVersion and Table info
            table_ver = {
                "tablevid": row["tablevid"],
                "code": row["table_version_code"],
                "name": row["table_version_name"],
                "description": row["table_version_description"],
                "tableid": row["table_version_tableid"],
                "abstracttableid": row["abstracttableid"],
                "startreleaseid": row["table_version_startreleaseid"],
                "endreleaseid": row["table_version_endreleaseid"],
                "isabstract": row["isabstract"],
                "hasopencolumns": row["hasopencolumns"],
                "hasopenrows": row["hasopenrows"],
                "hasopensheets": row["hasopensheets"],
                "isnormalised": row["isnormalised"],
                "isflat": row["isflat"],
            }
            mod["table_versions"].append(table_ver)

        # Convert dicts back to lists
        final_result = []
        for fw in frameworks.values():
            fw["module_versions"] = list(fw["module_versions"].values())
            final_result.append(fw)

        return final_result

    @staticmethod
    def get_table_details(
        session,
        table_code: str,
        release_id: Optional[int] = None,
        date: Optional[str] = None,
        release_code: Optional[str] = None,
    ) -> dict:
        # Input Validation: Mutually exclusive release params
        if sum(bool(x) for x in [release_id, release_code, date]) > 1:
            raise ValueError(
                "Specify a maximum of one of release_id, release_code or date."
            )

        # Determine the relevant table version using the same filter helpers
        # as other hierarchical queries.
        q_tv = (
            session.query(TableVersion)
            .join(
                ModuleVersionComposition,
                ModuleVersionComposition.tablevid == TableVersion.tablevid,
            )
            .join(
                ModuleVersion,
                ModuleVersion.modulevid == ModuleVersionComposition.modulevid,
            )
            .filter(TableVersion.code == table_code)
        )

        if date:
            q_tv = filter_by_date(
                q_tv,
                date,
                ModuleVersion.fromreferencedate,
                ModuleVersion.toreferencedate,
            )
        elif release_id or release_code:
            q_tv = filter_by_release(
                q_tv,
                start_col=ModuleVersion.startreleaseid,
                end_col=ModuleVersion.endreleaseid,
                release_id=release_id,
                release_code=release_code,
            )
        else:
            q_tv = filter_active_only(q_tv, end_col=ModuleVersion.endreleaseid)

        table_version = q_tv.order_by(
            ModuleVersion.startreleaseid.desc()
        ).first()

        # If no table version matches the filters, return an empty structure.
        if not table_version:
            return {}

        table_vid = table_version.tablevid

        # Headers query: ORM-based, returning one row per header with
        # associated property and datatype information.
        header_query = (
            session.query(
                TableVersion.tablevid.label("table_vid"),
                TableVersion.code.label("table_code"),
                TableVersion.name.label("table_name"),
                TableVersionHeader.headerid.label("header_id"),
                TableVersionHeader.parentheaderid.label("parent_header_id"),
                TableVersionHeader.parentfirst.label("parent_first"),
                TableVersionHeader.order.label("order"),
                TableVersionHeader.isabstract.label("is_abstract"),
                HeaderVersion.code.label("header_code"),
                HeaderVersion.label.label("label"),
                Header.direction.label("direction"),
                Header.iskey.label("is_key"),
                literal(None).label("property_code"),
                Item.name.label("property_name"),
                DataType.name.label("data_type_name"),
                literal(None).label("items"),
            )
            .join(
                TableVersionHeader,
                TableVersionHeader.tablevid == TableVersion.tablevid,
            )
            .join(
                HeaderVersion,
                TableVersionHeader.headervid == HeaderVersion.headervid,
            )
            .join(Header, HeaderVersion.headerid == Header.headerid)
            .outerjoin(Property, HeaderVersion.propertyid == Property.propertyid)
            .outerjoin(Item, Property.propertyid == Item.itemid)
            .outerjoin(DataType, Property.datatypeid == DataType.datatypeid)
            .filter(TableVersion.tablevid == table_vid)
            .order_by(TableVersionHeader.order)
        )

        header_results = header_query.all()

        if not header_results:
            return {}

        # Cells query: ORM-based, returning cell-level metadata for the
        # selected table version.
        hv_col = aliased(HeaderVersion)
        hv_row = aliased(HeaderVersion)
        hv_sheet = aliased(HeaderVersion)

        cell_query = (
            session.query(
                hv_col.code.label("column_code"),
                hv_row.code.label("row_code"),
                hv_sheet.code.label("sheet_code"),
                VariableVersion.variableid.label("variable_id"),
                VariableVersion.variablevid.label("variable_vid"),
                TableVersionCell.isnullable.label("cell_is_nullable"),
                TableVersionCell.isexcluded.label("cell_is_excluded"),
                TableVersionCell.isvoid.label("cell_is_void"),
                TableVersionCell.sign.label("cell_sign"),
                literal(None).label("property_code"),
                DataType.name.label("data_type_name"),
            )
            .select_from(TableVersionCell)
            .join(
                TableVersion,
                TableVersion.tablevid == TableVersionCell.tablevid,
            )
            .join(Cell, TableVersionCell.cellid == Cell.cellid)
            .outerjoin(hv_col, Cell.columnid == hv_col.headerid)
            .outerjoin(hv_row, Cell.rowid == hv_row.headerid)
            .outerjoin(hv_sheet, Cell.sheetid == hv_sheet.headerid)
            .join(
                VariableVersion,
                VariableVersion.variablevid == TableVersionCell.variablevid,
            )
            .outerjoin(Property, hv_col.propertyid == Property.propertyid)
            .outerjoin(DataType, Property.datatypeid == DataType.datatypeid)
            .filter(TableVersionCell.tablevid == table_vid)
            .distinct()
        )

        cell_results = cell_query.all()

        # Transform to the expected DPM JSON-like format.
        return HierarchicalQuery._transform_to_dpm_format(
            header_results, cell_results
        )

    @staticmethod
    def _transform_to_dpm_format(header_rows, cell_rows) -> dict:
        if not header_rows:
            return {}

        first_row = header_rows[0]

        headers = []
        for row in header_rows:
            items_list = []
            if getattr(row, "items", None):
                items_list = row.items.split("\n")

            headers.append(
                {
                    "id": row.header_id,
                    "parentId": row.parent_header_id,
                    "code": row.header_code,
                    "label": row.label,
                    "direction": row.direction,
                    "order": row.order,
                    "isAbstract": row.is_abstract,
                    "isKey": row.is_key,
                    "propertyCode": getattr(row, "property_code", None),
                    "propertyName": row.property_name,
                    "dataTypeName": row.data_type_name,
                    "items": items_list,
                }
            )

        cells = []
        for row in cell_rows:
            cells.append(
                {
                    "column_code": row.column_code,
                    "row_code": row.row_code,
                    "sheet_code": row.sheet_code,
                    "variable_id": row.variable_id,
                    "variable_vid": row.variable_vid,
                    "cell_is_nullable": row.cell_is_nullable,
                    "cell_is_excluded": row.cell_is_excluded,
                    "cell_is_void": row.cell_is_void,
                    "cell_sign": row.cell_sign,
                    "property_code": getattr(row, "property_code", None),
                    "data_type_name": row.data_type_name,
                }
            )

        return {
            "tableCode": first_row.table_code,
            "tableTitle": first_row.table_name,  # Assuming Name -> Title mapping
            "tableVid": first_row.table_vid,
            "headers": headers,
            "data": {},
            "metadata": {
                "version": "1.0",
                "source": "database",
                "recordCount": len(headers),
            },
            "cells": cells,
        }
