from typing import Optional

from sqlalchemy import distinct
from py_dpm.dpm.models import (
    TableVersion,
    ViewDatapoints,
    ModuleVersion,
    ModuleVersionComposition,
)
from py_dpm.dpm.queries.base import BaseQuery
from py_dpm.dpm.queries.filters import filter_by_release, filter_by_date


class TableQuery:
    """
    Queries related to data structure references (Tables, Rows, Columns, Sheets).
    """

    @staticmethod
    def get_tables(
        session,
        release_id: Optional[int] = None,
        date: Optional[str] = None,
        release_code: Optional[str] = None,
    ) -> BaseQuery:
        """Get all available table codes."""

        if sum(bool(x) for x in [release_id, date, release_code]) > 1:
            raise ValueError(
                "Specify a maximum of one of release_id, release_code or date."
            )

        q = session.query(TableVersion)

        if date:
            q = q.join(
                ModuleVersionComposition,
                TableVersion.tablevid == ModuleVersionComposition.tablevid,
            ).join(
                ModuleVersion,
                ModuleVersionComposition.modulevid == ModuleVersion.modulevid,
            )
            q = filter_by_date(
                q, date, ModuleVersion.fromreferencedate, ModuleVersion.toreferencedate
            )
        elif release_id:
            q = filter_by_release(
                q,
                release_id=release_id,
                start_col=TableVersion.startreleaseid,
                end_col=TableVersion.endreleaseid,
            )
        elif release_code:
            q = filter_by_release(
                q,
                release_code=release_code,
                start_col=TableVersion.startreleaseid,
                end_col=TableVersion.endreleaseid,
            )

        q = q.order_by(TableVersion.code)

        return BaseQuery(session, q)

    @staticmethod
    def get_available_tables_from_datapoints(
        session, release_id: Optional[int] = None
    ) -> BaseQuery:
        """Get available table codes from datapoints view."""
        base_query = ViewDatapoints.create_view_query(session)
        subq = base_query.subquery()

        q = session.query(distinct(subq.c.table_code).label("table_code")).filter(
            subq.c.table_code.isnot(None)
        )

        q = filter_by_release(
            q,
            start_col=subq.c.start_release,
            end_col=subq.c.end_release,
            release_id=release_id,
        )
        q = q.order_by(subq.c.table_code)

        return BaseQuery(session, q)

    @staticmethod
    def get_available_rows(
        session, table_code: str, release_id: Optional[int] = None
    ) -> BaseQuery:
        """Get available row codes for a table."""
        base_query = ViewDatapoints.create_view_query(session)
        subq = base_query.subquery()

        q = session.query(distinct(subq.c.row_code).label("row_code")).filter(
            subq.c.table_code == table_code, subq.c.row_code.isnot(None)
        )

        q = filter_by_release(
            q,
            start_col=subq.c.start_release,
            end_col=subq.c.end_release,
            release_id=release_id,
        )
        q = q.order_by(subq.c.row_code)

        return BaseQuery(session, q)

    @staticmethod
    def get_available_columns(
        session, table_code: str, release_id: Optional[int] = None
    ) -> BaseQuery:
        """Get available column codes for a table."""
        base_query = ViewDatapoints.create_view_query(session)
        subq = base_query.subquery()

        q = session.query(distinct(subq.c.column_code).label("column_code")).filter(
            subq.c.table_code == table_code, subq.c.column_code.isnot(None)
        )

        q = filter_by_release(
            q,
            start_col=subq.c.start_release,
            end_col=subq.c.end_release,
            release_id=release_id,
        )
        q = q.order_by(subq.c.column_code)

        return BaseQuery(session, q)

    @staticmethod
    def get_available_sheets(
        session, table_code: str, release_id: Optional[int] = None
    ) -> BaseQuery:
        """Get available sheet codes."""
        base_query = ViewDatapoints.create_view_query(session)
        subq = base_query.subquery()

        q = session.query(distinct(subq.c.sheet_code).label("sheet_code")).filter(
            subq.c.table_code == table_code,
            subq.c.sheet_code.isnot(None),
            subq.c.sheet_code != "",
        )

        q = filter_by_release(
            q,
            start_col=subq.c.start_release,
            end_col=subq.c.end_release,
            release_id=release_id,
        )
        q = q.order_by(subq.c.sheet_code)

        return BaseQuery(session, q)
