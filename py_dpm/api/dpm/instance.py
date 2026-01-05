"""
Instance API

Public API for building XBRL-CSV report packages from instance data.
"""

from pathlib import Path
from typing import Union, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from py_dpm.instance.instance import Instance


class InstanceAPI:
    """
    API for working with Instance data and building XBRL-CSV report packages.

    This API provides methods to create instances from JSON files or dictionaries
    and build XBRL-CSV packages from them.
    """

    @staticmethod
    def build_package_from_dict(
        instance_data: Dict[str, Any],
        output_folder: Union[Path, str],
        file_prefix: str = None,
    ) -> Path:
        """
        Build an XBRL-CSV package from a dictionary containing instance data.

        Args:
            instance_data: Dictionary with the instance configuration.
                          Must contain: module_code, parameters (with refPeriod),
                          and facts (list of facts)
            output_folder: Directory where the output ZIP file will be created
            file_prefix: Optional prefix for the output filename

        Returns:
            Path to the created ZIP file

        Raises:
            ValueError: If required keys are missing or invalid
            TypeError: If data types are incorrect

        Example:
            >>> api = InstanceAPI()
            >>> data = {
            ...     "module_code": "F_01.01",
            ...     "parameters": {
            ...         "refPeriod": "2024-12-31"
            ...     },
            ...     "facts": [
            ...         {
            ...             "table_code": "t001",
            ...             "row_code": "r010",
            ...             "column_code": "c010",
            ...             "value": 1000000
            ...         }
            ...     ]
            ... }
            >>> output_path = api.build_package_from_dict(data, "/tmp/output")
        """
        # Import here to avoid circular import
        from py_dpm.instance.instance import Instance

        instance = Instance.from_dict(instance_data)
        return instance.build_package(output_folder=output_folder, file_prefix=file_prefix)

    @staticmethod
    def build_package_from_json(
        json_file: Union[Path, str],
        output_folder: Union[Path, str],
        file_prefix: str = None,
    ) -> Path:
        """
        Build an XBRL-CSV package from a JSON file containing instance data.

        Args:
            json_file: Path to JSON file with instance configuration.
                      Must contain: module_code, parameters (with refPeriod),
                      and facts (list of facts)
            output_folder: Directory where the output ZIP file will be created
            file_prefix: Optional prefix for the output filename

        Returns:
            Path to the created ZIP file

        Raises:
            FileNotFoundError: If the JSON file doesn't exist
            ValueError: If required keys are missing or invalid
            TypeError: If data types are incorrect
            json.JSONDecodeError: If the file contains invalid JSON

        Example:
            >>> api = InstanceAPI()
            >>> output_path = api.build_package_from_json(
            ...     "/path/to/instance.json",
            ...     "/tmp/output"
            ... )
        """
        # Import here to avoid circular import
        from py_dpm.instance.instance import Instance

        if isinstance(json_file, str):
            json_file = Path(json_file)

        if not json_file.exists():
            raise FileNotFoundError(f"JSON file not found: {json_file}")

        instance = Instance.from_json_file(json_file)
        return instance.build_package(output_folder=output_folder, file_prefix=file_prefix)
