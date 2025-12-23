import warnings
import pandas as pd
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import Select


class BaseQuery:
    """
    Base wrapper for SQLAlchemy queries to provide unified output formatting.
    """

    def __init__(self, session: Session, query: Union[Query, Select]):
        self.session = session
        self._query = query

    def filter(self, *criteria):
        """Apply SQLAlchemy filters."""
        # Check if it's a legacy ORM Query or composite Select
        if hasattr(self._query, "filter"):
            self._query = self._query.filter(*criteria)
        else:
            # For 1.4/2.0 style select() objects, use where if filter not avail, but distinct() usually returns Select
            # SQLAlchemy Select objects usually have .where() or .filter() (which is an alias in 1.4+)
            self._query = self._query.filter(*criteria)
        return self

    def apply(self, func, *args, **kwargs):
        """
        Apply a function that modifies the query.
        The function must accept the BaseQuery (or its internal query) as first argument
        and return a modified query object.
        """
        # We pass the internal query to the function, and expect a query back
        # This allows filters to work on the raw SQLAlchemy object
        self._query = func(self._query, *args, **kwargs)
        return self

    @property
    def statement(self):
        """Return the underlying SQL statement."""
        if hasattr(self._query, "statement"):
            return self._query.statement
        return self._query

    def _compile_for_pandas(self):
        """Compile query for safe pandas execution."""
        stmt = self.statement
        # Compile with literal binds for pandas compatibility
        return str(
            stmt.compile(
                dialect=self.session.get_bind().dialect,
                compile_kwargs={"literal_binds": True},
            )
        )

    def to_df(self) -> pd.DataFrame:
        """Execute query and return as Pandas DataFrame."""
        sql = self._compile_for_pandas()

        # Suppress pandas/SQLAlchemy connection warnings
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=".*pandas only supports SQLAlchemy.*",
                category=UserWarning,
            )
            return pd.read_sql(sql, self.session.connection().connection)

    def to_dict(self) -> List[Dict[str, Any]]:
        """
        Execute query and return as list of dictionaries.

        Handles both ORM objects (using to_dict if available) and KeyedTuples.
        """
        # Execute the query
        if isinstance(self._query, Query):
            results = self._query.all()
        else:
            results = self.session.execute(self._query).all()

        if not results:
            return []

        # If results are ORM objects with to_dict method
        first = results[0]
        if hasattr(first, "to_dict"):
            return [r.to_dict() for r in results]

        # If results are SQLAlchemy Rows/KeyedTuples
        if hasattr(first, "_mapping"):
            return [dict(r._mapping) for r in results]

        # Fallback for older SQLAlchemy or simple tuples (try to map from query column descriptions if possible, but Row/KeyedTuple is standard)
        # In modern SA, .all() returns Rows which behave like tuples but have _mapping
        try:
            return [dict(row) for row in results]
        except (ValueError, TypeError):
            # Scalar results?
            return results
