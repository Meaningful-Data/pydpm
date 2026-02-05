"""Tests for migration type inference from Access databases.

These tests verify that the pyodbc extraction method uses actual column type
metadata from the Access schema instead of inferring types from data values,
which fixes the Windows vs Linux inconsistency issue.
"""

import sys
import os
import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
import decimal

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from py_dpm.dpm.migration import _extract_with_pyodbc


class TestPyodbcTypeInference:
    """Tests for _extract_with_pyodbc type inference based on schema metadata."""

    @pytest.fixture
    def mock_pyodbc(self):
        """Create a mock pyodbc module."""
        mock_module = MagicMock()
        mock_module.Error = Exception
        return mock_module

    def test_text_column_with_numeric_values_stays_text(self, mock_pyodbc):
        """
        Text columns containing numeric-looking values should remain as text.
        This is the core bug fix - previously these would be converted to REAL/INTEGER.
        """
        # Mock cursor description: column 'product_code' is TEXT (str type) in Access
        # but contains values like '123', '456' that look numeric
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ('product_code', str, None, None, None, None, None),  # TEXT column
            ('quantity', int, None, None, None, None, None),       # INTEGER column
        ]
        mock_cursor.fetchall.return_value = [
            ('123', 10),
            ('456', 20),
            ('789', 30),
        ]
        mock_cursor.tables.return_value = [
            MagicMock(table_name='Products'),
        ]
        mock_cursor.execute = MagicMock()

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pyodbc.connect.return_value = mock_conn

        with patch.dict(sys.modules, {'pyodbc': mock_pyodbc}):
            result = _extract_with_pyodbc('/fake/path.accdb')

        assert 'Products' in result
        df = result['Products']

        # product_code should be TEXT (object dtype), not numeric
        assert df['product_code'].dtype == object
        assert df['product_code'].tolist() == ['123', '456', '789']

        # quantity should be numeric (it's defined as int in Access)
        assert pd.api.types.is_numeric_dtype(df['quantity'])

    def test_leading_zeros_preserved_for_text_columns(self, mock_pyodbc):
        """
        Text columns with leading zeros should preserve the leading zeros.
        """
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ('postal_code', str, None, None, None, None, None),  # TEXT column
        ]
        mock_cursor.fetchall.return_value = [
            ('01234',),
            ('00567',),
            ('09876',),
        ]
        mock_cursor.tables.return_value = [
            MagicMock(table_name='Addresses'),
        ]
        mock_cursor.execute = MagicMock()

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pyodbc.connect.return_value = mock_conn

        with patch.dict(sys.modules, {'pyodbc': mock_pyodbc}):
            result = _extract_with_pyodbc('/fake/path.accdb')

        df = result['Addresses']

        # Leading zeros must be preserved
        assert df['postal_code'].tolist() == ['01234', '00567', '09876']

    def test_numeric_columns_are_converted(self, mock_pyodbc):
        """
        Columns that are actually defined as numeric in Access should be converted.
        """
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ('id', int, None, None, None, None, None),
            ('price', float, None, None, None, None, None),
            ('amount', decimal.Decimal, None, None, None, None, None),
        ]
        mock_cursor.fetchall.return_value = [
            (1, 10.5, decimal.Decimal('100.00')),
            (2, 20.5, decimal.Decimal('200.00')),
        ]
        mock_cursor.tables.return_value = [
            MagicMock(table_name='Orders'),
        ]
        mock_cursor.execute = MagicMock()

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pyodbc.connect.return_value = mock_conn

        with patch.dict(sys.modules, {'pyodbc': mock_pyodbc}):
            result = _extract_with_pyodbc('/fake/path.accdb')

        df = result['Orders']

        # All numeric columns should be numeric types
        assert pd.api.types.is_numeric_dtype(df['id'])
        assert pd.api.types.is_numeric_dtype(df['price'])
        assert pd.api.types.is_numeric_dtype(df['amount'])

    def test_mixed_columns_respect_schema_types(self, mock_pyodbc):
        """
        Mixed table with both text and numeric columns should respect schema types.
        """
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ('account_number', str, None, None, None, None, None),  # TEXT - looks numeric
            ('balance', float, None, None, None, None, None),        # REAL - is numeric
            ('status_code', str, None, None, None, None, None),      # TEXT - looks numeric
            ('transaction_count', int, None, None, None, None, None), # INTEGER
        ]
        mock_cursor.fetchall.return_value = [
            ('1001234567', 1500.50, '200', 5),
            ('2009876543', 2500.75, '404', 10),
        ]
        mock_cursor.tables.return_value = [
            MagicMock(table_name='Accounts'),
        ]
        mock_cursor.execute = MagicMock()

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pyodbc.connect.return_value = mock_conn

        with patch.dict(sys.modules, {'pyodbc': mock_pyodbc}):
            result = _extract_with_pyodbc('/fake/path.accdb')

        df = result['Accounts']

        # Text columns stay as text
        assert df['account_number'].dtype == object
        assert df['status_code'].dtype == object

        # Numeric columns are converted
        assert pd.api.types.is_numeric_dtype(df['balance'])
        assert pd.api.types.is_numeric_dtype(df['transaction_count'])

    def test_null_values_handled_correctly(self, mock_pyodbc):
        """
        NULL values should be handled correctly for both text and numeric columns.
        """
        mock_cursor = MagicMock()
        mock_cursor.description = [
            ('name', str, None, None, None, None, None),
            ('value', float, None, None, None, None, None),
        ]
        mock_cursor.fetchall.return_value = [
            ('Alice', 100.0),
            (None, 200.0),
            ('Bob', None),
        ]
        mock_cursor.tables.return_value = [
            MagicMock(table_name='Data'),
        ]
        mock_cursor.execute = MagicMock()

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pyodbc.connect.return_value = mock_conn

        with patch.dict(sys.modules, {'pyodbc': mock_pyodbc}):
            result = _extract_with_pyodbc('/fake/path.accdb')

        df = result['Data']

        # Check that nulls are preserved correctly
        assert pd.isna(df.loc[1, 'name'])
        assert pd.isna(df.loc[2, 'value'])
        assert df.loc[0, 'name'] == 'Alice'
        assert df.loc[0, 'value'] == 100.0
