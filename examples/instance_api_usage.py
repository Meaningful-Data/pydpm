"""
Example usage of the InstanceAPI to build XBRL-CSV packages.

This script demonstrates how to use the InstanceAPI to create
XBRL-CSV report packages from either dictionaries or JSON files.
"""

from pathlib import Path
from py_dpm.api import InstanceAPI


def example_from_dict():
    """Example: Build a package from a dictionary."""
    api = InstanceAPI()

    # Define instance data as a dictionary
    instance_data = {
        "module_code": "COREP_OF",
        "parameters": {
            "refPeriod": "2024-12-31"
        },
        "operands": [
            {
                "table_code": "C_14.01",
                "column_code": "0330",
                "sheet_code": "0020",
                "value": 1000,
                "open_values": {
                    "SIC": "AAAA"
                }
            },
            {
                "table_code": "C_14.00",
                "column_code": "0110",
                "value": "eba_RS:x2",
                "open_values": {
                    "SIC": "AAAA"
                }
            },
            {
                "table_code": "C_14.00",
                "column_code": "0252",
                "value": 100,
                "open_values": {
                    "SIC": "AAAA"
                }
            }
        ]
    }

    # Build the package
    output_folder = Path("./output")
    output_folder.mkdir(exist_ok=True)

    result = api.build_package_from_dict(
        instance_data=instance_data,
        output_folder=output_folder,
        file_prefix="my_report"
    )

    print(f"Package created at: {result}")
    return result


def example_from_json():
    """Example: Build a package from a JSON file."""
    api = InstanceAPI()

    # Path to the JSON file
    json_file = Path("./examples/instance_example.json")

    # Build the package
    output_folder = Path("./output")
    output_folder.mkdir(exist_ok=True)

    result = api.build_package_from_json(
        json_file=json_file,
        output_folder=output_folder,
        file_prefix="my_report"
    )

    print(f"Package created at: {result}")
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("Example 1: Build package from dictionary")
    print("=" * 60)
    example_from_dict()

    print("\n" + "=" * 60)
    print("Example 2: Build package from JSON file")
    print("=" * 60)
    example_from_json()
