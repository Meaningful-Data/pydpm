from typing import List, Optional, Dict, Any
from py_dpm.api.dpm.data_dictionary import DataDictionaryAPI


class DPMExplorer:
    """
    Explorer API for introspection and "inverse" queries of the DPM structure.
    Methods here answer "Where is X used?" or "What relates to Y?".

    This class composes DataDictionaryAPI for basic queries but adds higher-order logic.
    """

    def __init__(self, data_dict_api: Optional[DataDictionaryAPI] = None):
        self.api = data_dict_api or DataDictionaryAPI()

    def get_properties_using_item(
        self, item_code: str, release_id: Optional[int] = None
    ) -> List[str]:
        """
        Find all property codes that use the given item code as a valid value.
        (Inverse of getting valid items for a property).

        Args:
            item_code: The item code to search for (e.g. 'EUR')
            release_id: Optional release ID

        Returns:
            List of property codes (e.g. ['sCRNCY', 'sTRNS_CRNCY'])
        """
        from py_dpm.dpm.models import ItemCategory, PropertyCategory, Category
        from sqlalchemy.orm import aliased

        session = self.api.session

        # Aliases for clarity
        ic_child = aliased(ItemCategory, name="ic_child")  # The item (value)
        ic_parent = aliased(ItemCategory, name="ic_parent")  # The property

        query = (
            session.query(ic_parent.code)
            .select_from(ic_child)
            .join(Category, ic_child.categoryid == Category.categoryid)
            .join(PropertyCategory, Category.categoryid == PropertyCategory.categoryid)
            .join(ic_parent, PropertyCategory.propertyid == ic_parent.itemid)
            .filter(ic_child.code == item_code)
            .distinct()
        )

        if release_id is not None:
            query = query.filter(
                (ic_child.endreleaseid.is_(None))
                | (ic_child.endreleaseid > release_id),
                ic_child.startreleaseid <= release_id,
                (ic_parent.endreleaseid.is_(None))
                | (ic_parent.endreleaseid > release_id),
                ic_parent.startreleaseid <= release_id,
            )

        results = query.all()
        return [r.code for r in results]

    def search_table(
        self, query: str, release_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for tables by code or name substring.

        Args:
            query: Substring to search for
            release_id: Optional release ID

        Returns:
            List of matching dictionaries with table info
        """
        from py_dpm.dpm.models import TableVersion
        from sqlalchemy import or_

        session = self.api.session
        search_pattern = f"%{query}%"

        db_query = session.query(
            TableVersion.tablevid,
            TableVersion.code,
            TableVersion.name,
            TableVersion.description,
        ).filter(
            or_(
                TableVersion.code.like(search_pattern),
                TableVersion.name.like(search_pattern),
            )
        )

        if release_id is not None:
            db_query = db_query.filter(
                or_(
                    TableVersion.endreleaseid.is_(None),
                    TableVersion.endreleaseid > release_id,
                ),
                TableVersion.startreleaseid <= release_id,
            )

        results = db_query.all()
        return [
            {
                "table_vid": r.tablevid,
                "code": r.code,
                "name": r.name,
                "description": r.description,
            }
            for r in results
        ]

    def audit_table(self, table_code: str, release_id: Optional[int] = None) -> dict:
        """
        Provide a comprehensive audit of a table structure: dimensions, open keys, and basic stats.

        Args:
            table_code: Table code
            release_id: Optional release ID

        Returns:
            Dict summarizing table metadata
        """
        table_info = self.api.get_table_version(table_code, release_id)
        if not table_info:
            return {"error": f"Table {table_code} not found"}

        open_keys = self.api.get_open_keys_for_table(table_code, release_id)

        # Dimensions (Header Rows/Cols) could be fetched if we had a method.
        # For now we return what we can easily aggregate.

        return {
            "info": table_info,
            "open_keys": open_keys,
            "open_keys_count": len(open_keys),
        }
