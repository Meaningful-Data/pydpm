from typing import Optional

from sqlalchemy import func, literal, and_, or_, join
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
    ItemCategory,
    ContextComposition,
    SubCategoryVersion,
    SubCategoryItem,
)
from py_dpm.dpm.queries.filters import (
    filter_by_release,
    filter_by_date,
    filter_active_only,
    filter_item_version,
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

        # If no table version matches the filters, the table does not exist
        # (for the requested context).
        if not table_version:
            raise ValueError(f"Table {table_code} was not found.")

        # If the underlying table is not abstract, return details for this
        # single table version as before.
        table_obj = table_version.table
        if not table_obj or not table_obj.isabstract:
            header_results, cell_results = HierarchicalQuery._fetch_header_and_cells(
                session, table_version.tablevid
            )
            if not header_results:
                return {}
            return HierarchicalQuery._transform_to_dpm_format(
                header_results, cell_results
            )

        # If the table is abstract, consolidate details for all table versions
        # that reference this table as their abstract table, applying the same
        # release/date filters.
        q_child = (
            session.query(TableVersion)
            .join(
                ModuleVersionComposition,
                ModuleVersionComposition.tablevid == TableVersion.tablevid,
            )
            .join(
                ModuleVersion,
                ModuleVersion.modulevid == ModuleVersionComposition.modulevid,
            )
            .filter(TableVersion.abstracttableid == table_obj.tableid)
        )

        if date:
            q_child = filter_by_date(
                q_child,
                date,
                ModuleVersion.fromreferencedate,
                ModuleVersion.toreferencedate,
            )
        elif release_id or release_code:
            q_child = filter_by_release(
                q_child,
                start_col=ModuleVersion.startreleaseid,
                end_col=ModuleVersion.endreleaseid,
                release_id=release_id,
                release_code=release_code,
            )
        else:
            q_child = filter_active_only(q_child, end_col=ModuleVersion.endreleaseid)

        child_versions = q_child.all()

        # If there are no child versions, fall back to the abstract table
        # version itself.
        if not child_versions:
            header_results, cell_results = HierarchicalQuery._fetch_header_and_cells(
                session, table_version.tablevid
            )
            if not header_results:
                return {}
            result = HierarchicalQuery._transform_to_dpm_format(
                header_results, cell_results
            )
            result["tableCode"] = table_version.code
            result["tableTitle"] = table_version.name
            result["tableVid"] = table_version.tablevid
            return result

        # Collect headers and cells from all matching child table versions.
        all_headers = []
        all_cells = []
        for child_tv in child_versions:
            child_headers, child_cells = HierarchicalQuery._fetch_header_and_cells(
                session, child_tv.tablevid
            )
            all_headers.extend(child_headers)
            all_cells.extend(child_cells)

        if not all_headers:
            return {}

        result = HierarchicalQuery._transform_to_dpm_format(all_headers, all_cells)

        # Represent the consolidated view as belonging to the originally
        # requested (abstract) table version.
        result["tableCode"] = table_version.code
        result["tableTitle"] = table_version.name
        result["tableVid"] = table_version.tablevid
        return result

    @staticmethod
    def get_table_modelling(
        session,
        table_code: str,
        release_id: Optional[int] = None,
        date: Optional[str] = None,
        release_code: Optional[str] = None,
    ) -> dict:
        """
        Return modelling metadata for a table, based on the context
        composition associated with each header.

        The selection logic for the relevant table version mirrors
        ``get_table_details``: table code plus optional release/date filters.
        """
        # Input Validation: Mutually exclusive release params
        if sum(bool(x) for x in [release_id, release_code, date]) > 1:
            raise ValueError(
                "Specify a maximum of one of release_id, release_code or date."
            )

        # Resolve the relevant table version using the same pattern as
        # get_table_details.
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

        if not table_version:
            raise ValueError(f"Table {table_code} was not found.")

        # Aliases for Item and ItemCategory used multiple times in the query
        iccp = aliased(ItemCategory)  # context property category
        icci = aliased(ItemCategory)  # context item category
        icmp = aliased(ItemCategory)  # main property category
        icp = aliased(Item)  # context property item
        ici = aliased(Item)  # context item
        mpi = aliased(Item)  # main property item

        # Pre-build joined table expressions so that the SQL more closely
        # matches:
        #   LEFT JOIN (ItemCategory_X JOIN Item_Y ON ...) ON ...
        context_property_join = join(iccp, icp, iccp.itemid == icp.itemid)
        context_item_join = join(icci, ici, icci.itemid == ici.itemid)
        main_property_join = join(icmp, mpi, icmp.itemid == mpi.itemid)

        # ORM translation of the desired SQL query with left joins so that
        # headers without a context (or without a main property) are still
        # returned.
        q = (
            session.query(
                HeaderVersion.headerid.label("header_id"),
                icmp.signature.label("main_property_code"),
                mpi.name.label("main_property_name"),
                iccp.signature.label("context_property_code"),
                icp.name.label("context_property_name"),
                icci.signature.label("context_item_code"),
                ici.name.label("context_item_name"),
            )
            .select_from(TableVersion)
            .join(
                TableVersionHeader,
                TableVersionHeader.tablevid == TableVersion.tablevid,
            )
            .join(
                HeaderVersion,
                TableVersionHeader.headervid == HeaderVersion.headervid,
            )
            # Context is optional, so use LEFT JOIN
            .outerjoin(
                ContextComposition,
                HeaderVersion.contextid == ContextComposition.contextid,
            )
            # Context property (optional, versioned)
            .outerjoin(
                context_property_join,
                and_(
                    ContextComposition.propertyid == iccp.itemid,
                    filter_item_version(
                        TableVersion.startreleaseid,
                        iccp.startreleaseid,
                        iccp.endreleaseid,
                    ),
                ),
            )
            # Context item (optional, versioned)
            .outerjoin(
                context_item_join,
                and_(
                    ContextComposition.itemid == icci.itemid,
                    filter_item_version(
                        TableVersion.startreleaseid,
                        icci.startreleaseid,
                        icci.endreleaseid,
                    ),
                ),
            )
            # Main property (optional, versioned)
            .outerjoin(
                main_property_join,
                and_(
                    HeaderVersion.propertyid == icmp.itemid,
                    filter_item_version(
                        TableVersion.startreleaseid,
                        icmp.startreleaseid,
                        icmp.endreleaseid,
                    ),
                ),
            )
            .filter(TableVersion.tablevid == table_version.tablevid)
        )

        modelling: dict[int, list[dict]] = {}
        for row in q.all():
            header_id = row.header_id
            if header_id not in modelling:
                modelling[header_id] = []

            # Main property pair (if present)
            if row.main_property_code is not None or row.main_property_name is not None:
                modelling[header_id].append(
                    {
                        "main_property_code": row.main_property_code,
                        "main_property_name": row.main_property_name,
                    }
                )

            # Context pair: property and item metadata in a single object
            if (
                row.context_property_code is not None
                or row.context_property_name is not None
                or row.context_item_code is not None
                or row.context_item_name is not None
            ):
                modelling[header_id].append(
                    {
                        "context_property_code": row.context_property_code,
                        "context_property_name": row.context_property_name,
                        "context_item_code": row.context_item_code,
                        "context_item_name": row.context_item_name,
                    }
                )

        return modelling

    @staticmethod
    def _fetch_header_and_cells(session, table_vid):
        # Get the table version and module version info for release filtering
        tv_info = (
            session.query(
                TableVersion.tablevid,
                TableVersion.startreleaseid,
                ModuleVersion.startreleaseid.label("mv_startreleaseid"),
            )
            .join(
                ModuleVersionComposition,
                ModuleVersionComposition.tablevid == TableVersion.tablevid,
            )
            .join(
                ModuleVersion,
                ModuleVersion.modulevid == ModuleVersionComposition.modulevid,
            )
            .filter(TableVersion.tablevid == table_vid)
            .first()
        )

        if not tv_info:
            return [], []

        release_id = tv_info.mv_startreleaseid

        # Aliases for the multiple ItemCategory and Item joins
        ic_prop = aliased(ItemCategory)  # For property code
        ic_enum = aliased(ItemCategory)  # For enumeration items
        item_prop = aliased(Item)  # For property name
        item_enum = aliased(Item)  # For enumeration item names

        # Headers query with property codes and enumeration items
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
                ic_prop.code.label("property_code"),
                item_prop.name.label("property_name"),
                DataType.name.label("data_type_name"),
                ic_enum.signature.label("item_signature"),
                item_enum.name.label("item_label"),
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
            .outerjoin(
                ic_prop,
                and_(
                    HeaderVersion.propertyid == ic_prop.itemid,
                    filter_item_version(
                        release_id,
                        ic_prop.startreleaseid,
                        ic_prop.endreleaseid,
                    ),
                ),
            )
            # Property and its Item (for name) do not require an ItemCategory row
            .outerjoin(Property, HeaderVersion.propertyid == Property.propertyid)
            .outerjoin(item_prop, Property.propertyid == item_prop.itemid)
            .outerjoin(DataType, Property.datatypeid == DataType.datatypeid)
            .outerjoin(
                SubCategoryVersion,
                HeaderVersion.subcategoryvid == SubCategoryVersion.subcategoryvid,
            )
            .outerjoin(
                SubCategoryItem,
                SubCategoryVersion.subcategoryvid
                == SubCategoryItem.subcategoryvid,
            )
            .outerjoin(
                ic_enum,
                and_(
                    SubCategoryItem.itemid == ic_enum.itemid,
                    filter_item_version(
                        release_id,
                        ic_enum.startreleaseid,
                        ic_enum.endreleaseid,
                    ),
                ),
            )
            .outerjoin(item_enum, ic_enum.itemid == item_enum.itemid)
            .filter(TableVersion.tablevid == table_vid)
            .order_by(TableVersionHeader.order)
        )

        header_results = header_query.all()

        if not header_results:
            return [], []

        # Cells query: ORM-based, returning cell-level metadata for the
        # selected table version.
        hv_col = aliased(HeaderVersion)
        hv_row = aliased(HeaderVersion)
        hv_sheet = aliased(HeaderVersion)

        # Aliases for ItemCategory and Property/DataType for each axis
        ic_col = aliased(ItemCategory)
        ic_row = aliased(ItemCategory)
        ic_sheet = aliased(ItemCategory)
        prop_col = aliased(Property)
        prop_row = aliased(Property)
        prop_sheet = aliased(Property)
        dt_col = aliased(DataType)
        dt_row = aliased(DataType)
        dt_sheet = aliased(DataType)

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
                func.coalesce(
                    ic_col.code, ic_row.code, ic_sheet.code
                ).label("property_code"),
                func.coalesce(
                    dt_col.name, dt_row.name, dt_sheet.name
                ).label("data_type_name"),
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
            # Column axis ItemCategory, Property, DataType
            .outerjoin(
                ic_col,
                and_(
                    hv_col.propertyid == ic_col.itemid,
                    filter_item_version(
                        release_id,
                        ic_col.startreleaseid,
                        ic_col.endreleaseid,
                    ),
                    ic_col.isdefaultitem != 0,
                ),
            )
            .outerjoin(prop_col, hv_col.propertyid == prop_col.propertyid)
            .outerjoin(dt_col, prop_col.datatypeid == dt_col.datatypeid)
            # Row axis ItemCategory, Property, DataType
            .outerjoin(
                ic_row,
                and_(
                    hv_row.propertyid == ic_row.itemid,
                    filter_item_version(
                        release_id,
                        ic_row.startreleaseid,
                        ic_row.endreleaseid,
                    ),
                    ic_row.isdefaultitem != 0,
                ),
            )
            .outerjoin(prop_row, hv_row.propertyid == prop_row.propertyid)
            .outerjoin(dt_row, prop_row.datatypeid == dt_row.datatypeid)
            # Sheet axis ItemCategory, Property, DataType
            .outerjoin(
                ic_sheet,
                and_(
                    hv_sheet.propertyid == ic_sheet.itemid,
                    filter_item_version(
                        release_id,
                        ic_sheet.startreleaseid,
                        ic_sheet.endreleaseid,
                    ),
                    ic_sheet.isdefaultitem != 0,
                ),
            )
            .outerjoin(prop_sheet, hv_sheet.propertyid == prop_sheet.propertyid)
            .outerjoin(dt_sheet, prop_sheet.datatypeid == dt_sheet.datatypeid)
            .filter(TableVersionCell.tablevid == table_vid)
            .distinct()
        )

        cell_results = cell_query.all()

        return header_results, cell_results

    @staticmethod
    def _transform_to_dpm_format(header_rows, cell_rows) -> dict:
        if not header_rows:
            return {}

        first_row = header_rows[0]

        # Group header rows by header_id and aggregate enumeration items
        headers_dict = {}
        for row in header_rows:
            header_id = row.header_id

            if header_id not in headers_dict:
                headers_dict[header_id] = {
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
                    "items": [],
                }

            # Aggregate enumeration items
            if (
                hasattr(row, "item_signature")
                and row.item_signature
                and hasattr(row, "item_label")
                and row.item_label
            ):
                item_str = f"{row.item_signature} - {row.item_label}"
                if item_str not in headers_dict[header_id]["items"]:
                    headers_dict[header_id]["items"].append(item_str)

        # Convert to list and sort by order
        headers = sorted(headers_dict.values(), key=lambda x: x["order"])

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
