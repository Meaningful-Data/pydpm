"""
Data Dictionary API

This module provides ORM-based query methods for accessing the data dictionary.
All methods use SQLAlchemy ORM instead of raw SQL for PostgreSQL compatibility.
"""

from typing import List, Optional, Dict, Tuple, Any
from sqlalchemy import and_, or_, func, distinct, text
from sqlalchemy.orm import Session

from py_dpm.db_utils import get_session, get_engine
from py_dpm.models import (
    ViewDatapoints, TableVersion, ItemCategory, Cell, Property, DataType,
    KeyComposition, VariableVersion, Category, PropertyCategory,
    ModuleVersion, ModuleVersionComposition, Release, Header, HeaderVersion,
    TableVersionHeader
)


class DataDictionaryAPI:
    """
    Main API for querying the data dictionary using ORM.

    This class provides methods for:
    - Table/row/column reference lookups
    - Wildcard resolution
    - Item and sheet validation
    - Open key queries
    - Metadata retrieval

    All methods use SQLAlchemy ORM for database-agnostic queries.
    """

    def __init__(self, database_path: Optional[str] = None, connection_url: Optional[str] = None):
        """
        Initialize the Data Dictionary API.

        Args:
            database_path: Path to SQLite database (optional)
            connection_url: SQLAlchemy connection URL for PostgreSQL (optional)
        """
        engine = get_engine(database_path=database_path, connection_url=connection_url)
        self.session = get_session()

    # ==================== Reference Query Methods ====================

    def get_available_tables(self, release_id: Optional[int] = None) -> List[str]:
        """
        Get all available table codes from TableVersion.

        Args:
            release_id: Optional release ID to filter by

        Returns:
            List of table codes
        """
        query = self.session.query(distinct(TableVersion.code)).filter(
            TableVersion.code.isnot(None)
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    TableVersion.endreleaseid.is_(None),
                    TableVersion.endreleaseid > release_id
                ),
                TableVersion.startreleaseid <= release_id
            )

        results = query.order_by(TableVersion.code).all()
        return [r[0] for r in results]

    def get_available_tables_from_datapoints(self, release_id: Optional[int] = None) -> List[str]:
        """
        Get all available table codes from datapoints.
        Always uses ViewDatapoints class methods for database compatibility.

        Args:
            release_id: Optional release ID to filter by

        Returns:
            List of table codes
        """
        # Use ViewDatapoints class method (works for both SQLite and PostgreSQL)
        base_query = ViewDatapoints.create_view_query(self.session)
        subq = base_query.subquery()

        query = self.session.query(distinct(subq.c.table_code)).filter(
            subq.c.table_code.isnot(None)
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    subq.c.end_release.is_(None),
                    subq.c.end_release > release_id
                ),
                subq.c.start_release <= release_id
            )

        results = query.order_by(subq.c.table_code).all()
        return [r[0] for r in results]

    def get_available_rows(self, table_code: str, release_id: Optional[int] = None) -> List[str]:
        """
        Get all available row codes for a table.
        Always uses ViewDatapoints class methods for database compatibility.

        Args:
            table_code: Table code to query
            release_id: Optional release ID to filter by

        Returns:
            List of row codes
        """
        # Use ViewDatapoints class method (works for both SQLite and PostgreSQL)
        base_query = ViewDatapoints.create_view_query(self.session)
        subq = base_query.subquery()

        query = self.session.query(distinct(subq.c.row_code)).filter(
            subq.c.table_code == table_code,
            subq.c.row_code.isnot(None)
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    subq.c.end_release.is_(None),
                    subq.c.end_release > release_id
                ),
                subq.c.start_release <= release_id
            )

        results = query.order_by(subq.c.row_code).all()
        return [r[0] for r in results]

    def get_available_columns(self, table_code: str, release_id: Optional[int] = None) -> List[str]:
        """
        Get all available column codes for a table.
        Always uses ViewDatapoints class methods for database compatibility.

        Args:
            table_code: Table code to query
            release_id: Optional release ID to filter by

        Returns:
            List of column codes
        """
        # Use ViewDatapoints class method (works for both SQLite and PostgreSQL)
        base_query = ViewDatapoints.create_view_query(self.session)
        subq = base_query.subquery()

        query = self.session.query(distinct(subq.c.column_code)).filter(
            subq.c.table_code == table_code,
            subq.c.column_code.isnot(None)
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    subq.c.end_release.is_(None),
                    subq.c.end_release > release_id
                ),
                subq.c.start_release <= release_id
            )

        results = query.order_by(subq.c.column_code).all()
        return [r[0] for r in results]

    def get_reference_statistics(self, release_id: Optional[int] = None) -> Dict[str, int]:
        """
        Get statistics about rows and columns in the data dictionary.
        Always uses ViewDatapoints class methods for database compatibility.

        Args:
            release_id: Optional release ID to filter by

        Returns:
            Dictionary with row_count and column_count
        """
        # Use ViewDatapoints class method (works for both SQLite and PostgreSQL)
        base_query = ViewDatapoints.create_view_query(self.session)
        subq = base_query.subquery()

        # Base query for filtering
        base = self.session.query(subq)

        if release_id is not None:
            base = base.filter(
                or_(
                    subq.c.end_release.is_(None),
                    subq.c.end_release > release_id
                ),
                subq.c.start_release <= release_id
            )

        # Count distinct rows
        row_count = base.filter(subq.c.row_code.isnot(None)).with_entities(
            func.count(distinct(subq.c.row_code))
        ).scalar()

        # Count distinct columns
        column_count = base.filter(subq.c.column_code.isnot(None)).with_entities(
            func.count(distinct(subq.c.column_code))
        ).scalar()

        return {
            "row_count": row_count or 0,
            "column_count": column_count or 0
        }

    # ==================== Item Query Methods ====================

    def get_all_item_signatures(self, release_id: Optional[int] = None) -> List[str]:
        """
        Get all active item signatures from ItemCategory.

        Args:
            release_id: Optional release ID to filter by

        Returns:
            List of item signatures
        """
        query = self.session.query(distinct(ItemCategory.signature)).filter(
            ItemCategory.signature.isnot(None)
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    ItemCategory.endreleaseid.is_(None),
                    ItemCategory.endreleaseid > release_id
                )
            )
        else:
            # Default: only active items (no end release)
            query = query.filter(ItemCategory.endreleaseid.is_(None))

        results = query.order_by(ItemCategory.signature).all()
        return [r[0] for r in results]

    def get_item_categories(self, release_id: Optional[int] = None) -> List[Tuple[str, str]]:
        """
        Get all item categories with code and signature.

        Args:
            release_id: Optional release ID to filter by

        Returns:
            List of tuples (code, signature)
        """
        query = self.session.query(
            ItemCategory.code,
            ItemCategory.signature
        ).filter(
            ItemCategory.code.isnot(None),
            ItemCategory.signature.isnot(None)
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    ItemCategory.endreleaseid.is_(None),
                    ItemCategory.endreleaseid > release_id
                )
            )

        results = query.order_by(ItemCategory.code, ItemCategory.signature).all()
        return [(r[0], r[1]) for r in results]

    # ==================== Sheet Query Methods ====================

    def table_has_sheets(self, table_code: str, release_id: Optional[int] = None) -> bool:
        """
        Check if a table has any sheets defined.
        Always uses ViewDatapoints class methods for database compatibility.

        Args:
            table_code: Table code to check
            release_id: Optional release ID to filter by

        Returns:
            True if table has sheets, False otherwise
        """
        # Use ViewDatapoints class method (works for both SQLite and PostgreSQL)
        base_query = ViewDatapoints.create_view_query(self.session)
        subq = base_query.subquery()

        query = self.session.query(subq).filter(
            subq.c.table_code == table_code,
            subq.c.sheet_code.isnot(None),
            subq.c.sheet_code != ''
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    subq.c.end_release.is_(None),
                    subq.c.end_release > release_id
                ),
                subq.c.start_release <= release_id
            )

        count = query.with_entities(func.count()).scalar()
        return count > 0

    def get_available_sheets(self, table_code: str, release_id: Optional[int] = None) -> List[str]:
        """
        Get all available sheet codes for a table.
        Always uses ViewDatapoints class methods for database compatibility.

        Args:
            table_code: Table code to query
            release_id: Optional release ID to filter by

        Returns:
            List of sheet codes
        """
        # Use ViewDatapoints class method (works for both SQLite and PostgreSQL)
        base_query = ViewDatapoints.create_view_query(self.session)
        subq = base_query.subquery()

        query = self.session.query(distinct(subq.c.sheet_code)).filter(
            subq.c.table_code == table_code,
            subq.c.sheet_code.isnot(None),
            subq.c.sheet_code != ''
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    subq.c.end_release.is_(None),
                    subq.c.end_release > release_id
                ),
                subq.c.start_release <= release_id
            )

        results = query.order_by(subq.c.sheet_code).all()
        return [r[0] for r in results]

    def check_cell_exists(
        self,
        table_code: str,
        row_code: Optional[str] = None,
        column_code: Optional[str] = None,
        sheet_code: Optional[str] = None,
        release_id: Optional[int] = None
    ) -> bool:
        """
        Check if a cell reference exists in the datapoints.
        Always uses ViewDatapoints class methods for database compatibility.

        Args:
            table_code: Table code
            row_code: Optional row code
            column_code: Optional column code
            sheet_code: Optional sheet code
            release_id: Optional release ID to filter by

        Returns:
            True if cell exists, False otherwise
        """
        # Use ViewDatapoints class method (works for both SQLite and PostgreSQL)
        base_query = ViewDatapoints.create_view_query(self.session)
        subq = base_query.subquery()

        query = self.session.query(subq).filter(
            subq.c.table_code == table_code
        )

        if row_code:
            query = query.filter(subq.c.row_code == row_code)

        if column_code:
            query = query.filter(subq.c.column_code == column_code)

        if sheet_code:
            query = query.filter(subq.c.sheet_code == sheet_code)

        if release_id is not None:
            query = query.filter(
                or_(
                    subq.c.end_release.is_(None),
                    subq.c.end_release > release_id
                ),
                subq.c.start_release <= release_id
            )

        count = query.with_entities(func.count()).scalar()
        return count > 0

    def get_table_dimensions(self, table_code: str, release_id: Optional[int] = None) -> List[str]:
        """
        Get dimension codes for a table from KeyComposition.

        Args:
            table_code: Table code to query
            release_id: Optional release ID to filter by

        Returns:
            List of dimension codes
        """
        query = self.session.query(distinct(ItemCategory.code)).select_from(TableVersion).join(
            KeyComposition, TableVersion.keyid == KeyComposition.keyid
        ).join(
            VariableVersion, KeyComposition.variablevid == VariableVersion.variablevid
        ).join(
            ItemCategory, VariableVersion.propertyid == ItemCategory.itemid
        ).filter(
            TableVersion.code == table_code,
            ItemCategory.code.isnot(None)
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    TableVersion.endreleaseid.is_(None),
                    TableVersion.endreleaseid > release_id
                ),
                TableVersion.startreleaseid <= release_id
            )

        results = query.order_by(ItemCategory.code).all()
        return [r[0] for r in results]

    def get_default_dimension_signature(
        self,
        dimension_code: str,
        release_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Get the default signature for a dimension.

        Args:
            dimension_code: Dimension code to query
            release_id: Optional release ID to filter by

        Returns:
            Default signature or None
        """
        pattern1 = f"{dimension_code}:%"
        pattern2 = f"%:{dimension_code}"

        query = self.session.query(distinct(ItemCategory.signature)).filter(
            ItemCategory.code.isnot(None),
            ItemCategory.signature.isnot(None),
            or_(
                ItemCategory.signature.like(pattern1),
                ItemCategory.signature.like(pattern2)
            )
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    ItemCategory.endreleaseid.is_(None),
                    ItemCategory.endreleaseid > release_id
                )
            )

        result = query.order_by(ItemCategory.signature).first()
        return result[0] if result else None

    def get_valid_sheet_code_for_dimension(
        self,
        dimension_code: str,
        signature: Optional[str] = None,
        release_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Get a valid sheet code for a dimension and signature.

        Args:
            dimension_code: Dimension code to query
            signature: Optional signature to match
            release_id: Optional release ID to filter by

        Returns:
            Valid sheet code or None
        """
        if signature:
            pattern = f"{signature}%"
            query = self.session.query(ItemCategory.code).filter(
                ItemCategory.code.isnot(None),
                ItemCategory.signature.isnot(None),
                or_(
                    ItemCategory.signature.like(pattern),
                    ItemCategory.code == dimension_code
                )
            )
        else:
            query = self.session.query(ItemCategory.code).filter(
                ItemCategory.code == dimension_code
            )

        if release_id is not None:
            query = query.filter(
                or_(
                    ItemCategory.endreleaseid.is_(None),
                    ItemCategory.endreleaseid > release_id
                )
            )

        # Order by exact match first, then by code length and alphabetically
        # Note: SQLAlchemy's case expression for ordering
        from sqlalchemy import case, func as sa_func
        result = query.order_by(
            case((ItemCategory.code == dimension_code, 0), else_=1),
            sa_func.length(ItemCategory.code),
            ItemCategory.code
        ).first()

        return result[0] if result else None

    # ==================== Open Key Query Methods ====================

    def get_open_keys_for_table(
        self,
        table_code: str,
        release_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get open key information for a table.

        Args:
            table_code: Table code to query
            release_id: Optional release ID to filter by

        Returns:
            List of dictionaries with open key information
        """
        query = self.session.query(
            TableVersion.code.label('table_version_code'),
            ItemCategory.code.label('property_code'),
            DataType.name.label('data_type_name')
        ).select_from(DataType).join(
            Property, DataType.datatypeid == Property.datatypeid
        ).join(
            ItemCategory, Property.propertyid == ItemCategory.itemid
        ).join(
            VariableVersion, ItemCategory.itemid == VariableVersion.propertyid
        ).join(
            KeyComposition, VariableVersion.variablevid == KeyComposition.variablevid
        ).join(
            TableVersion, KeyComposition.keyid == TableVersion.keyid
        ).join(
            ModuleVersionComposition, TableVersion.tablevid == ModuleVersionComposition.tablevid
        ).join(
            ModuleVersion, ModuleVersionComposition.modulevid == ModuleVersion.modulevid
        ).filter(
            TableVersion.code == table_code
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    TableVersion.endreleaseid.is_(None),
                    TableVersion.endreleaseid > release_id
                ),
                TableVersion.startreleaseid <= release_id
            )

        results = query.distinct().order_by(
            TableVersion.code,
            ItemCategory.code
        ).all()

        return [
            {
                "table_version_code": r.table_version_code,
                "property_code": r.property_code,
                "data_type_name": r.data_type_name
            }
            for r in results
        ]

    def get_category_signature(
        self,
        property_code: str,
        category_code: str,
        release_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Get the signature for a category given a property code.

        Args:
            property_code: Property code
            category_code: Category code
            release_id: Optional release ID to filter by

        Returns:
            Category signature or None
        """
        ic_alias1 = ItemCategory
        ic_alias2 = ItemCategory.__table__.alias('ic2')

        query = self.session.query(ic_alias2.c.Signature).select_from(Property).join(
            ic_alias1, Property.propertyid == ic_alias1.itemid
        ).join(
            PropertyCategory, Property.propertyid == PropertyCategory.propertyid
        ).join(
            Category, PropertyCategory.categoryid == Category.categoryid
        ).join(
            ic_alias2, Category.categoryid == ic_alias2.c.CategoryID
        ).filter(
            ic_alias1.code == property_code,
            ic_alias2.c.Code == category_code
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    ic_alias1.endreleaseid.is_(None),
                    ic_alias1.endreleaseid > release_id
                ),
                or_(
                    ic_alias2.c.EndReleaseID.is_(None),
                    ic_alias2.c.EndReleaseID > release_id
                )
            )

        result = query.first()
        return result[0] if result else None

    def get_available_items_for_key(
        self,
        property_code: str,
        release_id: Optional[int] = None
    ) -> List[Tuple[str, str]]:
        """
        Get available items (code, signature) for an open key property.

        Args:
            property_code: Property code
            release_id: Optional release ID to filter by

        Returns:
            List of tuples (code, signature)
        """
        ic_alias1 = ItemCategory
        ic_alias2 = ItemCategory.__table__.alias('ic2')

        query = self.session.query(
            distinct(ic_alias2.c.Code),
            ic_alias2.c.Signature
        ).select_from(Property).join(
            ic_alias1, Property.propertyid == ic_alias1.itemid
        ).join(
            PropertyCategory, Property.propertyid == PropertyCategory.propertyid
        ).join(
            Category, PropertyCategory.categoryid == Category.categoryid
        ).join(
            ic_alias2, Category.categoryid == ic_alias2.c.CategoryID
        ).filter(
            ic_alias1.code == property_code
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    ic_alias1.endreleaseid.is_(None),
                    ic_alias1.endreleaseid > release_id
                ),
                or_(
                    ic_alias2.c.EndReleaseID.is_(None),
                    ic_alias2.c.EndReleaseID > release_id
                )
            )

        results = query.order_by(ic_alias2.c.Code).all()
        return [(r[0], r[1]) for r in results]

    # ==================== Metadata Query Methods ====================

    def get_datapoint_metadata(
        self,
        table_code: str,
        row_code: str,
        column_code: str,
        sheet_code: Optional[str] = None,
        release_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific datapoint.
        Always uses ViewDatapoints class methods for database compatibility.

        Args:
            table_code: Table code
            row_code: Row code
            column_code: Column code
            sheet_code: Optional sheet code
            release_id: Optional release ID to filter by

        Returns:
            Dictionary with datapoint metadata or None
        """
        # Use ViewDatapoints class method (works for both SQLite and PostgreSQL)
        base_query = ViewDatapoints.create_view_query(self.session)
        subq = base_query.subquery()

        query = self.session.query(subq).filter(
            subq.c.table_code == table_code,
            subq.c.row_code == row_code,
            subq.c.column_code == column_code
        )

        if sheet_code:
            query = query.filter(subq.c.sheet_code == sheet_code)

        if release_id is not None:
            query = query.filter(
                or_(
                    subq.c.end_release.is_(None),
                    subq.c.end_release > release_id
                ),
                subq.c.start_release <= release_id
            )

        result = query.first()

        if result:
            return {
                "cell_code": result.cell_code,
                "table_code": result.table_code,
                "row_code": result.row_code,
                "column_code": result.column_code,
                "sheet_code": result.sheet_code,
                "variable_id": result.variable_id,
                "data_type": result.data_type,
                "table_vid": result.table_vid,
                "property_id": result.property_id,
                "start_release": result.start_release,
                "end_release": result.end_release,
                "cell_id": result.cell_id,
                "context_id": result.context_id,
                "variable_vid": result.variable_vid
            }

        return None

    def get_table_version(self, table_code: str, release_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get table version information.

        Args:
            table_code: Table code
            release_id: Optional release ID to filter by

        Returns:
            Dictionary with table version info or None
        """
        query = self.session.query(
            TableVersion.tablevid,
            TableVersion.code
        ).filter(
            TableVersion.code == table_code
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    TableVersion.endreleaseid.is_(None),
                    TableVersion.endreleaseid > release_id
                ),
                TableVersion.startreleaseid <= release_id
            )

        result = query.first()

        if result:
            return {
                "table_vid": result.tablevid,
                "code": result.code
            }

        # Fallback with LIKE pattern
        pattern = f"{table_code}%"
        query = self.session.query(
            TableVersion.tablevid,
            TableVersion.code
        ).filter(
            TableVersion.code.like(pattern)
        )

        if release_id is not None:
            query = query.filter(
                or_(
                    TableVersion.endreleaseid.is_(None),
                    TableVersion.endreleaseid > release_id
                ),
                TableVersion.startreleaseid <= release_id
            )

        result = query.first()

        if result:
            return {
                "table_vid": result.tablevid,
                "code": result.code
            }

        return None

    def get_release_by_code(self, release_code: str) -> Optional[Dict[str, Any]]:
        """
        Get release information by code.

        Args:
            release_code: Release code

        Returns:
            Dictionary with release info or None
        """
        result = self.session.query(
            Release.releaseid,
            Release.code,
            Release.date
        ).filter(
            Release.code == release_code
        ).first()

        if result:
            return {
                "ReleaseID": result.releaseid,
                "code": result.code,
                "date": result.date
            }

        return None

    def get_latest_release(self) -> Optional[Dict[str, Any]]:
        """
        Get the latest released version.

        Returns:
            Dictionary with latest release info or None
        """
        result = self.session.query(
            Release.code,
            Release.date
        ).filter(
            Release.status == 'released'
        ).order_by(
            Release.date.desc()
        ).first()

        if result:
            return {
                "code": result.code,
                "date": result.date
            }

        return None

    def get_release_id_for_version(self, version_code: str) -> Optional[int]:
        """
        Get release ID for a version code.

        Args:
            version_code: Version code (e.g., "4.2")

        Returns:
            Release ID or None
        """
        result = self.session.query(Release.releaseid).filter(
            Release.code == version_code
        ).first()

        return result[0] if result else None

    def get_table_list(self, release_id: Optional[int] = None) -> List[str]:
        """
        Get list of all table names (used by database introspection).

        Args:
            release_id: Optional release ID to filter by

        Returns:
            List of table names
        """
        # For database introspection, we return distinct table codes from datapoints
        return self.get_available_tables_from_datapoints(release_id=release_id)

    def get_datapoints_count(self, release_id: Optional[int] = None) -> int:
        """
        Get count of datapoints.
        Always uses ViewDatapoints class methods for database compatibility.

        Args:
            release_id: Optional release ID to filter by

        Returns:
            Count of datapoints
        """
        # Use ViewDatapoints class method (works for both SQLite and PostgreSQL)
        base_query = ViewDatapoints.create_view_query(self.session)
        subq = base_query.subquery()

        query = self.session.query(func.count(subq.c.cell_code))

        if release_id is not None:
            query = query.select_from(subq).filter(
                or_(
                    subq.c.end_release.is_(None),
                    subq.c.end_release > release_id
                ),
                subq.c.start_release <= release_id
            )

        return query.scalar() or 0

    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session') and self.session:
            self.session.close()
