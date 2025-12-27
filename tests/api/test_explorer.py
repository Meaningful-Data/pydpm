import unittest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from py_dpm.api.explorer import DPMExplorer


# Mock models to avoid importing actual DB models which require DB connection


@dataclass
class MockProperty:
    code: str


class TestDPMExplorer(unittest.TestCase):
    def setUp(self):
        self.mock_api = MagicMock()
        self.mock_session = MagicMock()
        self.mock_api.session = self.mock_session
        self.explorer = DPMExplorer(data_dict_api=self.mock_api)

    @patch("sqlalchemy.or_")
    @patch("py_dpm.dpm.models.TableVersion")
    def test_search_table(self, mock_table_version, mock_or):
        # Setup mock return values

        # Setup column mocks to behave like SQLAlchemy columns for comparison
        mock_col = MagicMock()
        mock_col.__gt__.return_value = MagicMock()
        mock_col.__le__.return_value = MagicMock()
        mock_col.is_.return_value = MagicMock()
        mock_col.like.return_value = MagicMock()

        mock_table_version.endreleaseid = mock_col
        mock_table_version.startreleaseid = mock_col
        mock_table_version.code = mock_col
        mock_table_version.name = mock_col

        # When or_ is called, return a mock expression
        mock_or.return_value = MagicMock()

        # Mock the query result items
        # We need the items returned by the query to have attributes matching what search_table expects
        row_mock = MagicMock()
        row_mock.tablevid = 1
        row_mock.code = "TABLE_A"
        row_mock.name = "Table A"
        row_mock.description = "Desc"

        # Mock the session.query chain
        mock_query = self.mock_session.query.return_value
        mock_query.filter.return_value.all.return_value = [row_mock]

        # With release_id filter
        mock_query.filter.return_value.filter.return_value.all.return_value = [row_mock]

        # Test search
        results = self.explorer.search_table("TABLE", release_id=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], dict)
        self.assertEqual(results[0]["code"], "TABLE_A")

    @patch("sqlalchemy.orm.aliased")
    @patch("py_dpm.dpm.models.Category")
    @patch("py_dpm.dpm.models.PropertyCategory")
    @patch("py_dpm.dpm.models.ItemCategory")
    def test_get_properties_using_item(self, mock_ic, mock_pc, mock_cat, mock_aliased):
        # Setup mock return values
        mock_result = MagicMock()
        mock_result.code = "PROP_CODE"

        # Setup aliased return values
        mock_aliased_ic = MagicMock()
        mock_aliased.return_value = mock_aliased_ic

        # Mock the session.query chain
        # The chain is: query(ic_parent.code).select_from().join().join().join().filter().distinct().all()
        mock_query = self.mock_session.query.return_value
        (
            mock_query.select_from.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value
        ) = [mock_result]

        results = self.explorer.get_properties_using_item("ITEM_CODE")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "PROP_CODE")

    def test_audit_table(self):
        # Setup mock values for dependent API calls
        mock_table_info = {
            "table_vid": 1,
            "code": "TABLE_X",
            "name": "Table X",
            "description": "Desc",
        }
        self.mock_api.get_table_version.return_value = mock_table_info

        mock_open_keys = [
            {
                "table_version_code": "TABLE_X",
                "property_code": "P1",
                "data_type_name": "String",
            }
        ]
        self.mock_api.get_open_keys_for_table.return_value = mock_open_keys

        # Test audit
        audit = self.explorer.audit_table("TABLE_X", release_id=1)

        self.assertEqual(audit["info"], mock_table_info)
        self.assertEqual(audit["open_keys"], mock_open_keys)
        self.assertEqual(audit["open_keys_count"], 1)

    def test_audit_table_not_found(self):
        self.mock_api.get_table_version.return_value = None

        audit = self.explorer.audit_table("NON_EXISTENT")
        self.assertIn("error", audit)
