from typing import Optional, Any
from sqlalchemy import or_, and_


def filter_by_release(query, release_id: Optional[int], start_col, end_col):
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
    if release_id is None:
        return query

    return query.filter(
        and_(start_col <= release_id, or_(end_col.is_(None), end_col > release_id))
    )


def filter_active_only(query, end_col):
    """Filter for currently active records (end_release is None)."""
    return query.filter(end_col.is_(None))
