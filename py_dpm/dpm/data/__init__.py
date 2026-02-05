"""Static data files for DPM module URL mappings."""

import csv
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string in DD-Mon-YY format to datetime."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d-%b-%y")
    except ValueError:
        return None


@lru_cache(maxsize=1)
def _load_module_schema_mapping() -> list[dict]:
    """Load the module schema mapping CSV file."""
    csv_path = Path(__file__).parent / "module_schema_mapping.csv"
    mappings = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mappings.append(
                {
                    "module_code": row["module_code"],
                    "xbrl_schema_ref": row["xbrl_schema_ref"],
                    "from_date": _parse_date(row["from_date"]),
                    "to_date": _parse_date(row["to_date"]),
                    "version": row["version"],
                }
            )
    return mappings


def get_module_schema_ref(
    module_code: str,
    date: Optional[str] = None,
) -> Optional[str]:
    """
    Look up the XBRL schema reference URL for a module.

    Args:
        module_code: The module code (e.g., "COREP_Con", "FINREP_Con_IFRS")
        date: Optional reference date in YYYY-MM-DD format

    Returns:
        The XbrlSchemaRef URL if found, None otherwise
    """
    mappings = _load_module_schema_mapping()

    # Filter by module code (case-insensitive)
    module_code_upper = module_code.upper()
    candidates = [
        m for m in mappings if m["module_code"].upper() == module_code_upper
    ]

    if not candidates:
        return None

    if date is None:
        # Return the latest entry (last one with no to_date, or the last entry)
        for candidate in reversed(candidates):
            if candidate["to_date"] is None:
                return candidate["xbrl_schema_ref"]
        return candidates[-1]["xbrl_schema_ref"]

    # Parse the input date
    try:
        ref_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return None

    # Find the matching entry based on date range
    for candidate in candidates:
        from_date = candidate["from_date"]
        to_date = candidate["to_date"]

        if from_date is None:
            continue

        # Check if ref_date falls within the range
        # from_date <= ref_date and (to_date is None or ref_date < to_date)
        if from_date <= ref_date:
            if to_date is None or ref_date < to_date:
                return candidate["xbrl_schema_ref"]

    return None
