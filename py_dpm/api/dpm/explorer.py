from typing import List, Optional, Dict, Any

from py_dpm.api.dpm.data_dictionary import DataDictionaryAPI
from py_dpm.dpm.queries.explorer_queries import ExplorerQuery


class ExplorerQueryAPI:
    """
    Explorer API for introspection and "inverse" queries of the DPM structure.
    Methods here answer "Where is X used?" or "What relates to Y?".

    This class composes DataDictionaryAPI for basic queries but adds higher-order logic.
    """

    def __init__(self, data_dict_api: Optional[DataDictionaryAPI] = None):
        self.api = data_dict_api or DataDictionaryAPI()

    def close(self):
        """
        Explicitly close the underlying DataDictionaryAPI (and its session).
        """
        if hasattr(self, "api") and hasattr(self.api, "close"):
            try:
                self.api.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== Existing Explorer Methods ====================

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

    # ==================== New Explorer Methods Backed by Query Layer ====================

    def get_variable_usage(
        self,
        variable_id: Optional[int] = None,
        variable_vid: Optional[int] = None,
        release_id: Optional[int] = None,
        date: Optional[str] = None,
        release_code: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Expose ExplorerQuery.get_variable_usage through the Explorer API.

        Exactly one of variable_id or variable_vid must be provided.
        Release arguments follow the same semantics as hierarchical queries:
        at most one of release_id, date or release_code may be specified.
        """
        return ExplorerQuery.get_variable_usage(
            self.api.session,
            variable_id=variable_id,
            variable_vid=variable_vid,
            release_id=release_id,
            date=date,
            release_code=release_code,
        )

    def get_module_url(
        self,
        module_code: str,
        date: Optional[str] = None,
        release_id: Optional[int] = None,
        release_code: Optional[str] = None,
    ) -> str:
        """
        Get the EBA taxonomy URL for a module.

        The URL has the form:
        http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/{framework_code}/{release_code}/mod/{module_code}.json

        Exactly one of date, release_id or release_code may be specified.
        If none are provided, the URL is built for the currently active
        module version.
        """
        return ExplorerQuery.get_module_url(
            self.api.session,
            module_code=module_code,
            date=date,
            release_id=release_id,
            release_code=release_code,
        )

    def get_variable_from_cell_address(
        self,
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
        Resolve variable information from a cell address (table/row/column/sheet).

        Row, column, sheet and module codes are optional and are only used when
        provided. Release parameters follow the standard semantics; if none
        are given, only active module versions are considered.
        """
        return ExplorerQuery.get_variable_from_cell_address(
            self.api.session,
            table_code=table_code,
            row_code=row_code,
            column_code=column_code,
            sheet_code=sheet_code,
            module_code=module_code,
            release_id=release_id,
            release_code=release_code,
            date=date,
        )

    def get_variable_by_code(
        self,
        variable_code: str,
        release_id: Optional[int] = None,
        release_code: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get variable_id and variable_vid for a given variable code.

        This is useful for resolving precondition variable references like {v_C_01.00}
        where the variable code corresponds to a table's filing indicator variable.

        Args:
            variable_code: The variable code to look up (e.g., "C_01.00")
            release_id: Optional release ID to filter by (mutually exclusive with release_code)
            release_code: Optional release code to filter by (mutually exclusive with release_id)

        Returns:
            Dict with variable_id, variable_vid, variable_code, variable_name if found,
            None otherwise.

        Example:
            >>> api = ExplorerQueryAPI()
            >>> result = api.get_variable_by_code("C_01.00", release_code="4.2")
            >>> print(result)
            {'variable_id': 2201, 'variable_vid': 2201, 'variable_code': 'C_01.00', 'variable_name': '...'}
        """
        return ExplorerQuery.get_variable_by_code(
            self.api.session,
            variable_code=variable_code,
            release_id=release_id,
            release_code=release_code,
        )

    def get_variables_by_codes(
        self,
        variable_codes: List[str],
        release_id: Optional[int] = None,
        release_code: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch lookup of variable_id and variable_vid for multiple variable codes.

        This is more efficient than calling get_variable_by_code multiple times
        when resolving multiple precondition variables, as it performs a single
        database query.

        Args:
            variable_codes: List of variable codes to look up
            release_id: Optional release ID to filter by (mutually exclusive with release_code)
            release_code: Optional release code to filter by (mutually exclusive with release_id)

        Returns:
            Dict mapping variable_code to {variable_id, variable_vid, variable_code, variable_name}.
            Only includes codes that were found in the database.

        Example:
            >>> api = ExplorerQueryAPI()
            >>> result = api.get_variables_by_codes(["C_01.00", "C_47.00"], release_code="4.2")
            >>> print(result)
            {
                'C_01.00': {'variable_id': 2201, 'variable_vid': 2201, ...},
                'C_47.00': {'variable_id': 1935, 'variable_vid': 1935, ...}
            }
        """
        return ExplorerQuery.get_variables_by_codes(
            self.api.session,
            variable_codes=variable_codes,
            release_id=release_id,
            release_code=release_code,
        )
