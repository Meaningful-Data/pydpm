from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from py_dpm.dpm.models import (
    VariableVersion,
    TableVersionCell,
    TableVersion,
    ModuleVersionComposition,
    ModuleVersion,
)
from py_dpm.dpm.queries.filters import (
    filter_by_release,
    filter_by_date,
    filter_active_only,
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
