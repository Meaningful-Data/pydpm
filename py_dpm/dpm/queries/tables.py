from typing import Optional
from sqlalchemy import distinct, or_, func
from py_dpm.dpm.models import (
    TableVersion,
    ViewDatapoints,
)
from py_dpm.dpm.queries.base import BaseQuery
from py_dpm.dpm.queries.filters import filter_by_release


class TableQuery:
    """
    Queries related to data structure references (Tables, Rows, Columns, Sheets).
    """

    @staticmethod
    def get_available_tables(session, release_id: Optional[int] = None) -> BaseQuery:
        """Get all available table codes."""
        q = session.query(distinct(TableVersion.code).label("code")).filter(
            TableVersion.code.isnot(None)
        )
        q = filter_by_release(
            q, release_id, TableVersion.startreleaseid, TableVersion.endreleaseid
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

        q = filter_by_release(q, release_id, subq.c.start_release, subq.c.end_release)
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

        q = filter_by_release(q, release_id, subq.c.start_release, subq.c.end_release)
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

        q = filter_by_release(q, release_id, subq.c.start_release, subq.c.end_release)
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

        q = filter_by_release(q, release_id, subq.c.start_release, subq.c.end_release)
        q = q.order_by(subq.c.sheet_code)

        return BaseQuery(session, q)

    @staticmethod
    def get_reference_statistics(
        session, release_id: Optional[int] = None
    ) -> BaseQuery:
        """Get row and column counts."""
        base_query = ViewDatapoints.create_view_query(session)
        subq = base_query.subquery()

        # Note: This returns a single row with 2 columns, not a list of items.
        # BaseQuery.to_dict should handle this as returning [{'row_count': X, 'column_count': Y}]

        # Base query for filtering context
        # We can't filter the aggregations directly inside the same query easily if we want to reuse the filter logic on the View
        # But here we are building a new query.

        # Let's apply filter to subquery alias context
        # Logic from original:
        # base = session.query(subq).filter(...)
        # row_count = base...scalar()

        # To return a BaseQuery that produces validity, we should construct a query that selects the counts.

        # Applying filter first
        filter_condition = []
        if release_id is not None:
            filter_condition.append(subq.c.start_release <= release_id)
            filter_condition.append(
                or_(subq.c.end_release.is_(None), subq.c.end_release > release_id)
            )

        # Construct main query with conditional aggregation or filtered subquery
        # Efficient way:
        q = session.query(
            func.count(distinct(subq.c.row_code)).label("row_count"),
            func.count(distinct(subq.c.column_code)).label("column_count"),
        )

        if filter_condition:
            q = q.filter(*filter_condition)

        # We add filter for not None codes too?
        # Original: base.filter(subq.c.row_code.isnot(None)) for row count
        # Combining them in one query is tricky if conditions differ.
        # Original did 2 separate queries.
        # "row_count = base.filter(subq.c.row_code.isnot(None))...scalar()"

        # If we want a unified query object, we can use CASE or just separate columns with filters if SQL supported it easily (FILTER clause in PG).
        # Since we use ORM for compat...

        # Let's replicate exact behavior using 2 scalar subqueries in 1 select if possible, or just return the query objects?
        # The user wants "Output as DF or Dict".

        # I will build a query that returns the single row of stats.

        # Using Filtered aggregations (standard SQL pattern) or just common filter.
        # In this dataset, row_code/col_code are columns in the view.

        from sqlalchemy import case

        q = session.query(
            func.count(
                distinct(
                    case((subq.c.row_code.isnot(None), subq.c.row_code), else_=None)
                )
            ).label("row_count"),
            func.count(
                distinct(
                    case(
                        (subq.c.column_code.isnot(None), subq.c.column_code), else_=None
                    )
                )
            ).label("column_count"),
        )

        q = filter_by_release(q, release_id, subq.c.start_release, subq.c.end_release)

        return BaseQuery(session, q)
