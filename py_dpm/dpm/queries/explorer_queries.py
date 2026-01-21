from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session, aliased

from py_dpm.dpm.models import (
    VariableVersion,
    TableVersionCell,
    TableVersion,
    ModuleVersionComposition,
    ModuleVersion,
    Module,
    Framework,
    Release,
    Cell,
    HeaderVersion,
)
from py_dpm.dpm.queries.filters import (
    filter_by_release,
    filter_by_date,
    filter_active_only,
    filter_item_version,
)


class ExplorerQuery:
    """
    Queries used by the Explorer API for inverse lookups, such as
    "where is this variable used?".
    """

    @staticmethod
    def get_variable_usage(
        session: Session,
        variable_id: Optional[int] = None,
        variable_vid: Optional[int] = None,
        release_id: Optional[int] = None,
        date: Optional[str] = None,
        release_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return all table cells and module versions in which a given variable
        (by id or vid) is used.

        Args:
            session: SQLAlchemy session
            variable_id: VariableID to filter on (mutually exclusive with variable_vid)
            variable_vid: VariableVID to filter on (mutually exclusive with variable_id)
            release_id: Optional release id, mutually exclusive with date/release_code
            date: Optional reference date (YYYY-MM-DD), mutually exclusive with release args
            release_code: Optional release code, mutually exclusive with release_id/date

        Returns:
            List of dictionaries with cell and module/table metadata.
        """

        # Exactly one of variable_id / variable_vid must be provided
        if (variable_id is None) == (variable_vid is None):
            raise ValueError(
                "Specify exactly one of variable_id or variable_vid."
            )

        # Release/date arguments follow the same rules as hierarchical queries
        if sum(bool(x) for x in [release_id, date, release_code]) > 1:
            raise ValueError(
                "Specify a maximum of one of release_id, release_code or date."
            )

        # Build SQLAlchemy ORM query mirroring:
        # FROM VariableVersion vv
        #   JOIN TableVersionCell tvc ON tvc.VariableVID = vv.VariableVID
        #   JOIN TableVersion tv ON tv.TableVID = tvc.TableVID
        #   JOIN ModuleVersionComposition mvc ON mvc.TableVID = tv.TableVID
        #   JOIN ModuleVersion mv ON mv.ModuleVID = mvc.ModuleVID
        q = (
            session.query(
                TableVersionCell.cellcode.label("cell_code"),
                TableVersionCell.sign.label("cell_sign"),
                TableVersion.code.label("table_code"),
                TableVersion.name.label("table_name"),
                ModuleVersion.code.label("module_code"),
                ModuleVersion.name.label("module_name"),
                ModuleVersion.versionnumber.label("module_version_number"),
                ModuleVersion.startreleaseid.label("module_startreleaseid"),
                ModuleVersion.endreleaseid.label("module_endreleaseid"),
                ModuleVersion.fromreferencedate.label("module_fromreferencedate"),
                ModuleVersion.toreferencedate.label("module_toreferencedate"),
            )
            .select_from(VariableVersion)
            .join(
                TableVersionCell,
                TableVersionCell.variablevid == VariableVersion.variablevid,
            )
            .join(TableVersion, TableVersion.tablevid == TableVersionCell.tablevid)
            .join(
                ModuleVersionComposition,
                ModuleVersionComposition.tablevid == TableVersion.tablevid,
            )
            .join(
                ModuleVersion,
                ModuleVersion.modulevid == ModuleVersionComposition.modulevid,
            )
        )

        # Filter by the chosen variable identifier
        if variable_vid is not None:
            q = q.filter(VariableVersion.variablevid == variable_vid)
        else:
            q = q.filter(VariableVersion.variableid == variable_id)

        # Apply release/date filtering on ModuleVersion.
        # If no release arguments are provided, return all results without
        # restricting to "active only".
        if date:
            q = filter_by_date(
                q,
                date,
                ModuleVersion.fromreferencedate,
                ModuleVersion.toreferencedate,
            )
        elif release_id or release_code:
            q = filter_by_release(
                q,
                start_col=ModuleVersion.startreleaseid,
                end_col=ModuleVersion.endreleaseid,
                release_id=release_id,
                release_code=release_code,
            )

        results = q.all()
        return [dict(row._mapping) for row in results]

    @staticmethod
    def get_module_url(
        session: Session,
        module_code: str,
        date: Optional[str] = None,
        release_id: Optional[int] = None,
        release_code: Optional[str] = None,
    ) -> str:
        """
        Resolve the EBA taxonomy URL for a given module code.

        The URL format is:
            http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/{framework_code}/{release_code}/mod/{module_code}.json

        Exactly one of date, release_id or release_code may be provided.
        If none are provided, the currently active module version is used
        (based on ModuleVersion.endreleaseid being NULL).
        """

        if sum(bool(x) for x in [release_id, date, release_code]) > 1:
            raise ValueError(
                "Specify a maximum of one of release_id, release_code or date."
            )

        # Base query to resolve framework and module version metadata
        q = (
            session.query(
                Framework.code.label("framework_code"),
                ModuleVersion.code.label("module_code"),
                ModuleVersion.startreleaseid.label("module_startreleaseid"),
                ModuleVersion.endreleaseid.label("module_endreleaseid"),
                ModuleVersion.fromreferencedate.label("module_fromreferencedate"),
                ModuleVersion.toreferencedate.label("module_toreferencedate"),
            )
            .select_from(ModuleVersion)
            .join(Module, ModuleVersion.moduleid == Module.moduleid)
            .join(Framework, Module.frameworkid == Framework.frameworkid)
            .filter(ModuleVersion.code == module_code)
        )

        # Apply release/date filtering mirroring HierarchicalQuery.get_module_version
        if date:
            q = filter_by_date(
                q,
                date,
                ModuleVersion.fromreferencedate,
                ModuleVersion.toreferencedate,
            )
        elif release_id or release_code:
            q = filter_by_release(
                q,
                start_col=ModuleVersion.startreleaseid,
                end_col=ModuleVersion.endreleaseid,
                release_id=release_id,
                release_code=release_code,
            )
        else:
            # Default to currently active module versions
            q = filter_active_only(q, end_col=ModuleVersion.endreleaseid)

        rows = q.all()

        if len(rows) != 1:
            raise ValueError(
                f"Should return 1 record, but returned {len(rows)}"
            )

        row = rows[0]
        framework_code = row.framework_code
        resolved_module_code = row.module_code

        # Determine which release_code to embed in the URL
        if release_code is not None:
            effective_release_code = release_code
        elif release_id is not None:
            release_row = (
                session.query(Release.code)
                .filter(Release.releaseid == release_id)
                .first()
            )
            if not release_row:
                raise ValueError(f"Release with id {release_id} was not found.")
            effective_release_code = release_row.code
        else:
            # For date-based or default queries, use the module version's
            # starting release to derive the release code.
            start_release_id = row.module_startreleaseid
            release_row = (
                session.query(Release.code)
                .filter(Release.releaseid == start_release_id)
                .first()
            )
            if not release_row:
                raise ValueError(
                    f"Release with id {start_release_id} was not found."
                )
            effective_release_code = release_row.code

        return (
            "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/"
            f"{framework_code.lower()}/{effective_release_code}/mod/{resolved_module_code.lower()}.json"
        )

    @staticmethod
    def get_variable_from_cell_address(
        session: Session,
        table_code: str,
        row_code: Optional[str] = None,
        column_code: Optional[str] = None,
        sheet_code: Optional[str] = None,
        module_code: Optional[str] = None,
        release_id: Optional[int] = None,
        release_code: Optional[str] = None,
        date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Resolve variables from a cell address (table / row / column / sheet).

        The query mirrors the provided SQL, but uses SQLAlchemy ORM and the
        standard release/date filtering helpers. Row, column and sheet codes
        are optional and are only applied when not None.
        """

        if sum(bool(x) for x in [release_id, release_code, date]) > 1:
            raise ValueError(
                "Specify a maximum of one of release_id, release_code or date."
            )

        # Base query: link variables to cells and table versions
        q = (
            session.query(
                VariableVersion.variableid.label("variable_id"),
                VariableVersion.variablevid.label("variable_vid")
            )
            .select_from(VariableVersion)
            .join(
                TableVersionCell,
                TableVersionCell.variablevid == VariableVersion.variablevid,
            )
            .join(TableVersion, TableVersion.tablevid == TableVersionCell.tablevid)
            .join(Cell, Cell.cellid == TableVersionCell.cellid)
            .join(
                ModuleVersionComposition,
                ModuleVersionComposition.tablevid == TableVersion.tablevid,
            )
            .join(
                ModuleVersion,
                ModuleVersion.modulevid == ModuleVersionComposition.modulevid,
            )
        )

        # Aliases for the three header axes
        hv_row = aliased(HeaderVersion, name="hv_row")
        hv_col = aliased(HeaderVersion, name="hv_col")
        hv_sheet = aliased(HeaderVersion, name="hv_sheet")

        q = q.add_columns(
            hv_row.code.label("row_code"),
            hv_col.code.label("column_code"),
            hv_sheet.code.label("sheet_code"),
        )

        q = q.outerjoin(
            hv_row,
            (Cell.rowid == hv_row.headerid)
            & filter_item_version(
                TableVersion.startreleaseid,
                hv_row.startreleaseid,
                hv_row.endreleaseid,
            ),
        ).outerjoin(
            hv_col,
            (Cell.columnid == hv_col.headerid)
            & filter_item_version(
                TableVersion.startreleaseid,
                hv_col.startreleaseid,
                hv_col.endreleaseid,
            ),
        ).outerjoin(
            hv_sheet,
            (Cell.sheetid == hv_sheet.headerid)
            & filter_item_version(
                TableVersion.startreleaseid,
                hv_sheet.startreleaseid,
                hv_sheet.endreleaseid,
            ),
        )

        # Mandatory table filter
        q = q.filter(TableVersion.code == table_code)

        # Optional axis filters
        if row_code is not None:
            q = q.filter(hv_row.code == row_code)
        if column_code is not None:
            q = q.filter(hv_col.code == column_code)
        if sheet_code is not None:
            q = q.filter(hv_sheet.code == sheet_code)
        if module_code is not None:
            q = q.filter(ModuleVersion.code == module_code)

        # Apply standard release/date filtering on ModuleVersion.
        # For this method, if no release argument is provided, we default
        # to filtering active-only module versions.
        if date:
            q = filter_by_date(
                q,
                date,
                ModuleVersion.fromreferencedate,
                ModuleVersion.toreferencedate,
            )
        elif release_id or release_code:
            q = filter_by_release(
                q,
                start_col=ModuleVersion.startreleaseid,
                end_col=ModuleVersion.endreleaseid,
                release_id=release_id,
                release_code=release_code,
            )
        else:
            q = filter_active_only(q, end_col=ModuleVersion.endreleaseid)

        results = q.all()
        return [dict(row._mapping) for row in results]

    @staticmethod
    def get_variable_by_code(
        session: Session,
        variable_code: str,
        release_id: Optional[int] = None,
        release_code: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get variable_id and variable_vid for a given variable code.

        This is useful for resolving precondition variable references like {v_C_01.00}
        where the variable code is the table code (e.g., "C_01.00").

        Args:
            session: SQLAlchemy session
            variable_code: The variable code to look up (e.g., "C_01.00")
            release_id: Optional release ID to filter by
            release_code: Optional release code to filter by

        Returns:
            Dict with variable_id and variable_vid if found, None otherwise.
            If multiple versions exist, returns the one matching the release filter
            or the latest active version if no filter is provided.
        """
        if release_id is not None and release_code is not None:
            raise ValueError(
                "Specify a maximum of one of release_id or release_code."
            )

        q = (
            session.query(
                VariableVersion.variableid.label("variable_id"),
                VariableVersion.variablevid.label("variable_vid"),
                VariableVersion.code.label("variable_code"),
                VariableVersion.name.label("variable_name"),
            )
            .select_from(VariableVersion)
            .filter(VariableVersion.code == variable_code)
        )

        # Apply release filtering
        if release_id or release_code:
            q = filter_by_release(
                q,
                start_col=VariableVersion.startreleaseid,
                end_col=VariableVersion.endreleaseid,
                release_id=release_id,
                release_code=release_code,
            )
        else:
            # Default to active-only (endreleaseid is NULL)
            q = filter_active_only(q, end_col=VariableVersion.endreleaseid)

        result = q.first()
        if result:
            return dict(result._mapping)
        return None

    @staticmethod
    def get_variables_by_codes(
        session: Session,
        variable_codes: List[str],
        release_id: Optional[int] = None,
        release_code: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch lookup of variable_id and variable_vid for multiple variable codes.

        This is more efficient than calling get_variable_by_code multiple times
        when resolving multiple precondition variables.

        Args:
            session: SQLAlchemy session
            variable_codes: List of variable codes to look up
            release_id: Optional release ID to filter by
            release_code: Optional release code to filter by

        Returns:
            Dict mapping variable_code to {variable_id, variable_vid, ...}
            Only includes codes that were found in the database.
        """
        if release_id is not None and release_code is not None:
            raise ValueError(
                "Specify a maximum of one of release_id or release_code."
            )

        if not variable_codes:
            return {}

        q = (
            session.query(
                VariableVersion.variableid.label("variable_id"),
                VariableVersion.variablevid.label("variable_vid"),
                VariableVersion.code.label("variable_code"),
                VariableVersion.name.label("variable_name"),
            )
            .select_from(VariableVersion)
            .filter(VariableVersion.code.in_(variable_codes))
        )

        # Apply release filtering
        if release_id or release_code:
            q = filter_by_release(
                q,
                start_col=VariableVersion.startreleaseid,
                end_col=VariableVersion.endreleaseid,
                release_id=release_id,
                release_code=release_code,
            )
        else:
            # Default to active-only (endreleaseid is NULL)
            q = filter_active_only(q, end_col=VariableVersion.endreleaseid)

        results = q.all()
        return {row.variable_code: dict(row._mapping) for row in results}
