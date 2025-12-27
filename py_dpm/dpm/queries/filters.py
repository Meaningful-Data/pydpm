from typing import Optional
from datetime import datetime
from sqlalchemy import or_, and_


def filter_by_date(query, date, start_col, end_col):
    """
    Filter a query by a date range.

    Args:
        query: SQLAlchemy Query object
        date: Date string (YYYY-MM-DD) or date object
        start_col: Column representing start date
        end_col: Column representing end date
    """
    if not date:
        return query

    if isinstance(date, str):
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        target_date = date

    from sqlalchemy import cast, Date

    # Check dialect to apply CAST only for Postgres where type mismatch occurs
    is_postgres = False
    if hasattr(query, "session") and query.session:
        bind = query.session.get_bind()
        if bind.dialect.name == "postgresql":
            is_postgres = True

    if is_postgres:
        start_expr = cast(start_col, Date)
        end_expr = cast(end_col, Date)
    else:
        start_expr = start_col
        end_expr = end_col

    return query.filter(
        and_(
            start_expr <= target_date,
            or_(end_col.is_(None), end_expr > target_date),
        )
    )


def filter_by_release(
    query,
    start_col,
    end_col,
    release_id: Optional[int] = None,
    release_code: Optional[str] = None,
):
    """
    Filter a query by DPM release versioning logic.

    Args:
        query: SQLAlchemy Query object
        release_id: The release ID to filter for. If None, no filtering is applied (or returns all? Usually active).
                    Wait, if release_id is None, usually implies 'latest' or 'active' or 'all'?
                    Looking at existing code:
                    If release_id IS None:
                        query.filter(or_(end_release.is_(None), end_release > release_id)) <-- This fails if release_id is None

                    Let's check `data_dictionary.helper`:
                    If `release_id` passed as None to `get_available_tables`:
                        It just executes `query.all()` without filtering (lines 93-100 only run `if release_id is not None`).

                    HOWEVER, in `ItemCategory` access:
                    `else: query.filter(ItemCategory.endreleaseid.is_(None))`

                    So there is inconsistency.
                    Reference: `data_dictionary.py` L93.

    Standard Logic adopted here:
    If release_id provided:
        start <= release_id AND (end is NULL OR end > release_id)
    If release_id IS None:
        Return query unmodified (fetch all history? or active? Caller decides by not calling this or passing optional arg)
    """
    if release_id is not None and release_code is not None:
        raise ValueError("Specify a maximum of one of release_id or release_code.")

    if release_id is None and release_code is None:
        return query
    elif release_id:
        return query.filter(
            and_(start_col <= release_id, or_(end_col.is_(None), end_col > release_id))
        )
    elif release_code:
        # Resolve release_code to release_id using the session from the query
        if hasattr(query, "session") and query.session:
            from py_dpm.dpm.queries.basic_objects import ReleaseQuery

            release_q = ReleaseQuery.get_release_by_code(query.session, release_code)
            results = release_q.to_dict()
            if results:
                release_id = results[0]["releaseid"]
            else:
                raise ValueError(f"Release code '{release_code}' not found.")
        else:
            raise ValueError("Query has no session, cannot resolve release_code.")
        print(release_id)

        return query.filter(
            and_(start_col <= release_id, or_(end_col.is_(None), end_col > release_id))
        )


def filter_active_only(query, end_col):
    """Filter for currently active records (end_release is None)."""
    return query.filter(end_col.is_(None))


def filter_item_version(ref_start_col, item_start_col, item_end_col):
    """
    Build a version-range condition for joining versioned items (such as
    ItemCategory) against a reference start-release column.

    The pattern is:
        ref_start_col >= item_start_col
        AND (item_end_col IS NULL OR ref_start_col < item_end_col)

    Args:
        ref_start_col: Column representing the reference start release
                       (e.g. TableVersion.startreleaseid).
        item_start_col: Item's start-release column
                        (e.g. ItemCategory.startreleaseid).
        item_end_col: Item's end-release column
                      (e.g. ItemCategory.endreleaseid).

    Returns:
        SQLAlchemy boolean expression combining the above conditions.
    """
    return and_(
        ref_start_col >= item_start_col,
        or_(ref_start_col < item_end_col, item_end_col.is_(None)),
    )
