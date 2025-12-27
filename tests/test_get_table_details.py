import pytest
from py_dpm.api.dpm.data_dictionary import DataDictionaryAPI
import inspect

from py_dpm.dpm.models import (
    Base,
    Header,
    HeaderVersion,
    Table,
    TableVersion,
    TableVersionHeader,
    ModuleVersionComposition,
    ModuleVersion,
    Module,
    Framework,
    Property,
    DataType,
    Item,
    Cell,
    TableVersionCell,
    VariableVersion,
    Release,
)
from py_dpm.dpm.queries.hierarchical_queries import HierarchicalQuery


@pytest.fixture
def session():
    db_url = "sqlite:///:memory:"
    api = DataDictionaryAPI(connection_url=db_url)
    Base.metadata.create_all(api.session.bind)
    yield api.session
    api.session.close()


def test_get_table_details_structure(session):
    # Setup Data
    fw = Framework(frameworkid=1, code="FW1")
    mod = Module(moduleid=1, frameworkid=1)
    mv = ModuleVersion(modulevid=10, moduleid=1, startreleaseid=1)

    t = Table(tableid=100)
    tv = TableVersion(tablevid=1000, tableid=100, code="T1", name="Table 1")

    # Header Chain
    h = Header(headerid=1, direction="X", iskey=True)
    hv = HeaderVersion(
        headervid=10, headerid=1, code="H1", label="Header 1", propertyid=1
    )
    tvh = TableVersionHeader(
        tablevid=1000, headervid=10, headerid=1, order=1, isabstract=False
    )

    mvc = ModuleVersionComposition(modulevid=10, tablevid=1000, tableid=100)

    # Property / DataType
    dt = DataType(datatypeid=1, name="String")
    prop_item = Item(itemid=1, name="Prop1")
    prop = Property(propertyid=1, datatypeid=1)  # Name comes from Item

    # Cell Data
    vv = VariableVersion(variablevid=500, variableid=50, code="V1")
    cell = Cell(
        cellid=900,
        tableid=100,
        columnid=1,  # matches header above
        rowid=None,
        sheetid=None,
    )
    tvc = TableVersionCell(
        tablevid=1000,
        cellid=900,
        variablevid=500,
        isnullable=True,
        isvoid=False,
        isexcluded=False,
    )

    session.add_all(
        [fw, mod, mv, t, tv, h, hv, dt, prop, prop_item, tvh, mvc, vv, cell, tvc]
    )
    session.commit()

    # Call Method
    result = HierarchicalQuery.get_table_details(session, table_code="T1")

    # Verify Structure
    assert result["tableCode"] == "T1"
    assert result["tableTitle"] == "Table 1"
    assert result["tableVid"] == 1000

    # Verify Headers
    assert len(result["headers"]) == 1
    header = result["headers"][0]
    assert header["code"] == "H1"
    assert header["label"] == "Header 1"
    assert header["dataTypeName"] == "String"
    assert header["propertyName"] == "Prop1"
    assert header["direction"] == "X"

    # Verify Cells
    assert len(result["cells"]) == 1
    cell_res = result["cells"][0]
    assert cell_res["column_code"] == "H1"
    assert cell_res["variable_vid"] == 500
    assert cell_res["data_type_name"] == "String"  # via property


def test_get_table_details_filtering(session):
    # Setup multiple versions
    t = Table(tableid=1)
    # V1 in Release 1
    tv1 = TableVersion(
        tablevid=101,
        tableid=1,
        code="T_MULTI",
        name="Table V1",
        startreleaseid=1,
        endreleaseid=2,
    )
    # V2 in Release 2
    tv2 = TableVersion(
        tablevid=102,
        tableid=1,
        code="T_MULTI",
        name="Table V2",
        startreleaseid=2,
        endreleaseid=None,
    )

    mv1 = ModuleVersion(modulevid=11, moduleid=1, startreleaseid=1, endreleaseid=2)
    mv2 = ModuleVersion(modulevid=12, moduleid=1, startreleaseid=2, endreleaseid=None)

    mvc1 = ModuleVersionComposition(modulevid=11, tablevid=101, tableid=1)
    mvc2 = ModuleVersionComposition(modulevid=12, tablevid=102, tableid=1)

    # Headers logic needs to be present for the query to return anything at all
    h = Header(headerid=99)
    hv = HeaderVersion(headervid=999, headerid=99)
    # Link header to both TV
    tvh1 = TableVersionHeader(tablevid=101, headervid=999, headerid=99)
    tvh2 = TableVersionHeader(tablevid=102, headervid=999, headerid=99)

    session.add_all([t, tv1, tv2, mv1, mv2, mvc1, mvc2, h, hv, tvh1, tvh2])
    session.commit()

    # Filter for Release 1
    res1 = HierarchicalQuery.get_table_details(session, "T_MULTI", release_id=1)
    assert res1["tableVid"] == 101  # TV1
    assert res1["tableTitle"] == "Table V1"

    # Filter for Release 2
    res2 = HierarchicalQuery.get_table_details(session, "T_MULTI", release_id=2)
    assert res2["tableVid"] == 102  # TV2
    assert res2["tableTitle"] == "Table V2"


def test_get_table_details_filtering_release_code(session):
    # Setup releases
    r1 = Release(releaseid=1, code="R1")
    r2 = Release(releaseid=2, code="R2")

    t = Table(tableid=10)
    # V1 in Release 1
    tv1 = TableVersion(
        tablevid=201,
        tableid=10,
        code="T_MULTI_RC",
        name="Table RC V1",
        startreleaseid=1,
        endreleaseid=2,
    )
    # V2 in Release 2
    tv2 = TableVersion(
        tablevid=202,
        tableid=10,
        code="T_MULTI_RC",
        name="Table RC V2",
        startreleaseid=2,
        endreleaseid=None,
    )

    mv1 = ModuleVersion(modulevid=21, moduleid=2, startreleaseid=1, endreleaseid=2)
    mv2 = ModuleVersion(modulevid=22, moduleid=2, startreleaseid=2, endreleaseid=None)

    mvc1 = ModuleVersionComposition(modulevid=21, tablevid=201, tableid=10)
    mvc2 = ModuleVersionComposition(modulevid=22, tablevid=202, tableid=10)

    # Minimal header linkage so the query returns something
    h = Header(headerid=199)
    hv = HeaderVersion(headervid=1999, headerid=199)
    tvh1 = TableVersionHeader(tablevid=201, headervid=1999, headerid=199)
    tvh2 = TableVersionHeader(tablevid=202, headervid=1999, headerid=199)

    session.add_all(
        [r1, r2, t, tv1, tv2, mv1, mv2, mvc1, mvc2, h, hv, tvh1, tvh2]
    )
    session.commit()

    # Filter using release_code, which should resolve via ReleaseQuery
    res = HierarchicalQuery.get_table_details(
        session, "T_MULTI_RC", release_code="R2"
    )
    assert res["tableVid"] == 202  # TV2
    assert res["tableTitle"] == "Table RC V2"


def test_get_table_details_implementation_avoids_func_null_and_text():
    # Regression test: ensure we don't reintroduce func.null() or raw SQL text()
    from py_dpm.dpm.queries import hierarchical_queries

    source = inspect.getsource(
        hierarchical_queries.HierarchicalQuery.get_table_details
    )
    assert "func.null" not in source
    assert "text(" not in source
