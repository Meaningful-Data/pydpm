from dataclasses import dataclass, asdict
from typing import Optional
from datetime import date


@dataclass
class APIModel:
    """Base class for API data models providing helper methods."""

    def to_dict(self):
        return asdict(self)


@dataclass
class ModuleVersionInfo(APIModel):
    """
    Module version information with metadata.
    """

    module_vid: int
    code: str
    name: str
    description: str
    version_number: str
    from_reference_date: Optional[date] = None
    to_reference_date: Optional[date] = None


@dataclass
class TableVersionInfo(APIModel):
    """
    Table version information with metadata.
    """

    table_vid: int
    code: str
    name: str
    description: str
    module_vid: Optional[int] = None
    module_code: Optional[str] = None
    module_name: Optional[str] = None
    module_version: Optional[str] = None


@dataclass
class HeaderVersionInfo(APIModel):
    """
    Header version information with metadata.
    """

    header_vid: int
    code: str
    label: str
    header_type: str
    table_vid: Optional[int] = None
    table_code: Optional[str] = None
    table_name: Optional[str] = None


@dataclass
class DatapointInfo(APIModel):
    """
    Metadata for a specific datapoint (cell).
    """

    cell_code: str
    table_code: str
    row_code: str
    column_code: str
    sheet_code: Optional[str]
    variable_id: Optional[int]
    data_type: Optional[str]
    table_vid: int
    property_id: Optional[int]
    start_release: int
    end_release: Optional[int]
    cell_id: int
    context_id: int
    variable_vid: int


@dataclass
class ItemCategoryInfo(APIModel):
    """
    Information about an item category (Code/Signature pair).
    """

    code: str
    signature: str


@dataclass
class ItemInfo(APIModel):
    """
    Information about an item.
    """

    code: str
    name: str
    description: str = ""
    is_active: bool = True


@dataclass
class DimensionInfo(APIModel):
    """
    Information about a dimension in a table.
    """

    code: str
    default_signature: Optional[str] = None


@dataclass
class OpenKeyInfo(APIModel):
    """
    Information about an open key (variable) in a table.
    """

    table_version_code: str
    property_code: str
    data_type_name: str


@dataclass
class ReleaseInfo(APIModel):
    """
    Information about a release version.
    """

    release_id: int
    code: str
    date: date
    description: str
    status: str
    is_current: bool
