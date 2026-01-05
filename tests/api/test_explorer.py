import unittest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from py_dpm.api.dpm.explorer import ExplorerQueryAPI
from py_dpm.dpm.models import Base, Framework, Module, ModuleVersion, Release
from py_dpm.dpm.queries.explorer_queries import ExplorerQuery


# Mock models to avoid importing actual DB models which require DB connection


@dataclass
class MockProperty:
    code: str


class TestDPMExplorer(unittest.TestCase):
    def setUp(self):
        self.mock_api = MagicMock()
        self.mock_session = MagicMock()
        self.mock_api.session = self.mock_session
        self.explorer = ExplorerQueryAPI(data_dict_api=self.mock_api)

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

    @patch("py_dpm.dpm.queries.explorer_queries.ExplorerQuery.get_variable_usage")
    def test_get_variable_usage_delegates_to_query(self, mock_get_variable_usage):
        # Arrange
        expected_result = [
            {
                "cell_code": "A1",
                "cell_sign": "+",
                "table_code": "TBL_X",
                "table_name": "Table X",
                "module_code": "MOD_X",
                "module_name": "Module X",
            }
        ]
        mock_get_variable_usage.return_value = expected_result

        # Act
        result = self.explorer.get_variable_usage(
            variable_id=123, release_id=5, date=None, release_code=None
        )

        # Assert
        mock_get_variable_usage.assert_called_once_with(
            self.mock_api.session,
            variable_id=123,
            variable_vid=None,
            release_id=5,
            date=None,
            release_code=None,
        )
        self.assertEqual(result, expected_result)

    @patch("py_dpm.dpm.queries.explorer_queries.ExplorerQuery.get_module_url")
    def test_get_module_url_delegates_to_query(self, mock_get_module_url):
        # Arrange
        expected_url = (
            "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/FRM/1.0/mod/MOD_aaaX.json"
        )
        mock_get_module_url.return_value = expected_url

        # Act
        result = self.explorer.get_module_url(
            module_code="MOD_X", date=None, release_id=1, release_code=None
        )

        # Assert
        mock_get_module_url.assert_called_once_with(
            self.mock_api.session,
            module_code="MOD_X",
            date=None,
            release_id=1,
            release_code=None,
        )

        print(result)
        self.assertEqual(result, expected_url)

    @patch(
        "py_dpm.dpm.queries.explorer_queries.ExplorerQuery.get_variable_from_cell_address"
    )
    def test_get_variable_from_cell_address_delegates_to_query(
        self, mock_get_variable_from_cell_address
    ):
        # Arrange
        expected = [
            {
                "variable_id": 1,
                "variable_vid": 10,
                "table_code": "TBL_X",
                "cell_code": "A1",
                "row_code": "0010",
                "column_code": "0100",
                "sheet_code": "0001",
            }
        ]
        mock_get_variable_from_cell_address.return_value = expected

        # Act
        result = self.explorer.get_variable_from_cell_address(
            table_code="TBL_X",
            row_code="0010",
            column_code="0100",
            sheet_code="0001",
            release_id=1,
            release_code=None,
            date=None,
        )

        # Assert
        mock_get_variable_from_cell_address.assert_called_once_with(
            self.mock_api.session,
            table_code="TBL_X",
            row_code="0010",
            column_code="0100",
            sheet_code="0001",
            release_id=1,
            release_code=None,
            date=None,
        )
        self.assertEqual(result, expected)


class TestExplorerQueryModuleUrlIntegration(unittest.TestCase):
    def setUp(self):
        # Use an in-memory SQLite database for integration-style testing
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.session = SessionLocal()

        # Minimal data setup: one Release, Framework, Module, and ModuleVersion
        release = Release(releaseid=1, code="2.0")
        framework = Framework(frameworkid=10, code="FRM")
        module = Module(moduleid=100, frameworkid=framework.frameworkid)
        module_version = ModuleVersion(
            modulevid=1000,
            moduleid=module.moduleid,
            code="MOD_X",
            startreleaseid=release.releaseid,
            endreleaseid=None,
        )

        self.session.add_all([release, framework, module, module_version])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_get_module_url_uses_lowercase_codes(self):
        url = ExplorerQuery.get_module_url(
            self.session,
            module_code="MOD_X",
            date=None,
            release_id=None,
            release_code=None,
        )

        expected_url = (
            "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/frm/2.0/mod/mod_x.json"
        )
        self.assertEqual(url, expected_url)
