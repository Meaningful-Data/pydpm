from typing import Optional, List
from sqlalchemy import distinct, or_
from py_dpm.dpm.models import ItemCategory
from py_dpm.dpm.queries.base import BaseQuery
from py_dpm.dpm.queries.filters import filter_by_release, filter_active_only


class ItemQuery:
    """
    Queries related to Items and Categories.
    """

    @staticmethod
    def get_all_item_signatures(session, release_id: Optional[int] = None) -> BaseQuery:
        """Get all item signatures."""
        q = session.query(distinct(ItemCategory.signature).label("signature")).filter(
            ItemCategory.signature.isnot(None)
        )

        if release_id is not None:
            q = filter_by_release(
                q, release_id, ItemCategory.startreleaseid, ItemCategory.endreleaseid
            )
        else:
            q = filter_active_only(q, ItemCategory.endreleaseid)

        q = q.order_by(ItemCategory.signature)
        return BaseQuery(session, q)

    @staticmethod
    def get_item_categories(session, release_id: Optional[int] = None) -> BaseQuery:
        """Get item categories (code, signature)."""
        q = session.query(ItemCategory.code, ItemCategory.signature).filter(
            ItemCategory.code.isnot(None), ItemCategory.signature.isnot(None)
        )

        if release_id is not None:
            q = filter_by_release(
                q, release_id, ItemCategory.startreleaseid, ItemCategory.endreleaseid
            )
        else:
            pass

        q = q.order_by(ItemCategory.code, ItemCategory.signature)
        return BaseQuery(session, q)
