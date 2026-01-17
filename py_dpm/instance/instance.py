from pathlib import Path
import tempfile
import zipfile
import json
from datetime import datetime

from py_dpm.api import ExplorerQueryAPI


class Fact:
    def __init__(
        self,
        table_code: str,
        column_code: str = None,
        row_code: str = None,
        sheet_code: str = None,
        open_values: dict = None,
        value: int = None,
        date: str = None,
    ):
        self.table_code = table_code
        self.column_code = column_code
        self.row_code = row_code
        self.sheet_code = sheet_code
        self.open_values = open_values
        self.value = value
        self.variable_id = None
        self._date = date

    def __str__(self):
        return f"Operand(table={self.table_code}, column={self.column_code}, row={self.row_code}, sheet={self.sheet_code}, open_values={self.open_values}, value={self.value})"

    def resolve_datapoint_id(self, date: str) -> str:
        variables = ExplorerQueryAPI().get_variable_from_cell_address(
            table_code=self.table_code,
            column_code=self.column_code,
            sheet_code=self.sheet_code,
            row_code=self.row_code,
            date=date,
        )

        if len(variables) == 0:
            raise ValueError(f"No mapping found for {self.operand_code}")
        if len(variables) > 1:
            raise ValueError(f"Multiple mappings found for {self.operand_code}")

        self.variable_id = variables[0]["variable_id"]

    @property
    def operand_code(self):
        code = f"{self.table_code}"

        if self.row_code:
            code += f", r{self.row_code}"
        if self.column_code:
            code += f", c{self.column_code}"
        if self.sheet_code:
            code += f", s{self.sheet_code}"

        return code

    @property
    def variable_csv_row(self):
        return f"dp{self.variable_id}"

    @classmethod
    def from_dict(cls, operand_data: dict):
        operand = cls(
            table_code=operand_data["table_code"],
            column_code=(
                operand_data["column_code"] if "column_code" in operand_data else None
            ),
            row_code=operand_data["row_code"] if "row_code" in operand_data else None,
            sheet_code=(
                operand_data["sheet_code"] if "sheet_code" in operand_data else None
            ),
            open_values=(
                operand_data["open_values"] if "open_values" in operand_data else None
            ),
            value=operand_data["value"] if "value" in operand_data else None,
            date=operand_data["date"] if "date" in operand_data else None,
        )

        return operand


class Instance:
    PARAMETERS_DEFAULT = {
        "entityID": "rs:DUMMYLEI123456789012.CON",
        "baseCurrency": "iso4217:EUR",
        "decimalsInteger": 0,
        "decimalsMonetary": 2,
        "decimalsPercentage": 8,
        "decimalsDecimal": 2,
    }

    META_JSON = {
        "documentInfo": {
            "documentType": "http://xbrl.org/PWD/2020-12-09/report-package"
        }
    }

    REPORTS_JSON = {
        "documentInfo": {
            "documentType": "https://xbrl.org/CR/2021-02-03/xbrl-csv",
            "extends": [],
        }
    }

    def __init__(self, module_url: str, operands: dict[Fact], parameters: dict = None):

        self.module_url = module_url
        self.operands = operands
        self.parameters = parameters

    @staticmethod
    def _validate_dict_structure(instance_json: dict):
        required_keys = {"module_code", "parameters", "facts"}
        if required_keys != set(instance_json.keys()):
            missing = required_keys - set(instance_json.keys())
            raise ValueError(f"Missing required keys: {missing}")

        if not isinstance(instance_json["module_code"], str):
            raise TypeError("module_code must be a string")

        if not isinstance(instance_json["parameters"], dict):
            raise TypeError("parameters must be a dictionary")

        if "refPeriod" not in instance_json["parameters"]:
            raise ValueError("parameters must contain 'refPeriod'")

        if not isinstance(instance_json["facts"], list):
            raise TypeError("facts must be a list")

    @classmethod
    def from_json_file(cls, json_file: Path):
        with open(json_file, "r") as f:
            json_data = json.load(f)
        instance = cls.from_dict(json_data)
        return instance

    @classmethod
    def from_dict(cls, instance_json: dict):
        cls._validate_dict_structure(instance_json)

        parameters = cls.PARAMETERS_DEFAULT.copy()
        parameters.update(instance_json["parameters"])

        ref_period = parameters["refPeriod"]

        with ExplorerQueryAPI() as explorer:
            url = explorer.get_module_url(
                module_code=instance_json["module_code"],
                date=ref_period,
            )

            # Build Fact objects grouped by table without triggering DB lookups
            operands = {}
            for fact_data in instance_json["facts"]:
                fact = Fact.from_dict(fact_data)
                if fact.table_code not in operands:
                    operands[fact.table_code] = []
                operands[fact.table_code].append(fact)

            # Resolve datapoint IDs in batches per table
            for table_code, facts in operands.items():
                variables = explorer.get_variable_from_cell_address(
                    table_code=table_code,
                    row_code=None,
                    column_code=None,
                    sheet_code=None,
                    module_code=instance_json["module_code"],
                    date=ref_period,
                )

                # Build mapping from (row, column, sheet) -> list of variable rows
                variable_map = {}
                for var in variables:
                    key = (
                        var.get("row_code"),
                        var.get("column_code"),
                        var.get("sheet_code"),
                    )
                    variable_map.setdefault(key, []).append(var)

                # Assign variable_id to each fact, preserving previous error semantics
                for fact in facts:
                    key = (fact.row_code, fact.column_code, fact.sheet_code)
                    candidates = variable_map.get(key, [])

                    if len(candidates) == 0:
                        raise ValueError(f"No mapping found for {fact.operand_code}")
                    if len(candidates) > 1:
                        raise ValueError(
                            f"Multiple mappings found for {fact.operand_code}"
                        )

                    fact.variable_id = candidates[0]["variable_id"]

        instance = cls(
            module_url=url,
            operands=operands,
            parameters=parameters,
        )

        return instance

    @property
    def folder_name(self):
        module_code = self.module_url.split("/")[-1].split(".")[0]
        entity_id = self.parameters["entityID"].split(":")[1]
        ref_period = self.parameters["refPeriod"]
        return f"{entity_id}_{ref_period}_{module_code}"

    def build_package(self, output_folder: Path | str, file_prefix: str = None):
        """Build the XBRL‑CSV package and write to *output_zip*."""

        if isinstance(output_folder, str):
            output_folder = Path(output_folder)

        with tempfile.TemporaryDirectory() as tmpdir:
            if file_prefix:
                file_name_root = f"{file_prefix}_{self.folder_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            else:
                file_name_root = (
                    f"{self.folder_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                )

            tmp = Path(tmpdir)
            root = tmp / file_name_root
            root.mkdir()

            # META‑INF/reportPackage.json
            meta_dir = root / "META-INF"
            meta_dir.mkdir(parents=True, exist_ok=True)
            (meta_dir / "reportPackage.json").write_text(
                json.dumps(self.META_JSON, indent=2)
            )

            # reports/
            reports_dir = root / "reports"
            reports_dir.mkdir()

            # parameters.csv
            param_lines = ["name,value"] + [
                f"{k},{v}" for k, v in self.parameters.items()
            ]
            (reports_dir / "parameters.csv").write_text("\n".join(param_lines))

            # FilingIndicators.csv
            filing_indicators_lines = ["templateID,reported"]
            seen_templates = set()
            for table in self.operands.keys():
                normalized_table = table
                if "." in normalized_table:
                    parts = normalized_table.split(".")
                    normalized_table = parts[0] + "." + parts[1]
                if normalized_table not in seen_templates:
                    seen_templates.add(normalized_table)
                    filing_indicators_lines.append(f"{normalized_table},true")

            (reports_dir / "FilingIndicators.csv").write_text(
                "\n".join(filing_indicators_lines)
            )

            # report.json
            reports_json_dict = self.REPORTS_JSON
            reports_json_dict["documentInfo"]["extends"] = [self.module_url]
            (reports_dir / "report.json").write_text(
                json.dumps(reports_json_dict, indent=2)
            )

            # tables.csv
            for table, operands in self.operands.items():
                header = ["datapoint", "factValue"]
                first_operand = operands[0]
                if first_operand.open_values:
                    for key_dimension in first_operand.open_values.keys():
                        header.append(key_dimension)
                header = ",".join(header)
                lines = [header]
                for operand in operands:
                    line = [operand.variable_csv_row, str(operand.value)]
                    if operand.open_values:
                        for key_dimension in operand.open_values.keys():
                            line.append(str(operand.open_values[key_dimension]))
                    line = ",".join(line)
                    lines.append(line)
                (reports_dir / f"{table}.csv").write_text("\n".join(lines))

            # Zip everything

            with zipfile.ZipFile(
                output_folder / (file_name_root + ".zip"),
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as zf:
                for file_path in tmp.rglob("*"):
                    zf.write(file_path, file_path.relative_to(tmp))

            output_path = output_folder / (file_name_root + ".zip")

            print(f"Instance package written to: {output_path}")

            return output_path
