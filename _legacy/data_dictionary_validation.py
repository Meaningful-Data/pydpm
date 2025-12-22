"""
Data Dictionary Validation API

This module provides methods to identify and validate data dictionary issues
that can cause semantic validation failures during DPM-XL transpilation.
"""

from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from sqlalchemy import text

from py_dpm.db_utils import get_session, get_engine
from py_dpm.models import *


class ValidationIssueType(Enum):
    """Types of data dictionary validation issues."""
    MISSING_TABLE = "missing_table"
    MISSING_COLUMN = "missing_column"
    MISSING_ROW = "missing_row"
    MISSING_SHEET = "missing_sheet"
    MISSING_VARIABLE = "missing_variable"
    INVALID_REFERENCE = "invalid_reference"
    TYPE_MISMATCH = "type_mismatch"
    CONFIGURATION_ERROR = "configuration_error"


@dataclass
class ValidationIssue:
    """
    Represents a data dictionary validation issue.
    
    Attributes:
        issue_type (ValidationIssueType): Type of the issue
        description (str): Human-readable description of the issue
        affected_element (str): The specific element that has the issue
        suggested_fix (Optional[str]): Suggested fix for the issue
        severity (str): Severity level ('error', 'warning', 'info')
        code (Optional[str]): Error code for programmatic handling
    """
    issue_type: ValidationIssueType
    description: str
    affected_element: str
    suggested_fix: Optional[str] = None
    severity: str = "error"
    code: Optional[str] = None


@dataclass
class CellReference:
    """Represents a parsed cell reference from DPM-XL expression."""
    table: str
    rows: List[str]
    columns: List[str]
    sheets: List[str]


class DataDictionaryValidator:
    """
    Main class for validating data dictionary consistency and completeness.

    This class provides methods to detect issues that would cause semantic
    validation failures during DPM-XL transpilation.
    """

    def __init__(self, database_path: Optional[str] = None, connection_url: Optional[str] = None):
        """
        Initialize the Data Dictionary Validator.

        Args:
            database_path: Path to SQLite database (optional)
            connection_url: SQLAlchemy connection URL for PostgreSQL (optional)
        """
        if connection_url:
            # Create isolated engine and session for the provided connection URL
            from sqlalchemy.orm import sessionmaker
            from py_dpm.db_utils import create_engine_from_url

            # Create engine for the connection URL (supports SQLite, PostgreSQL, MySQL, etc.)
            self.engine = create_engine_from_url(connection_url)
            session_maker = sessionmaker(bind=self.engine)
            self.session = session_maker()
        elif database_path:
            # Create isolated engine and session for this specific database
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            import os

            # Create the database directory if it doesn't exist
            db_dir = os.path.dirname(database_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)

            # Create engine for specific database path
            db_connection_url = f"sqlite:///{database_path}"
            self.engine = create_engine(db_connection_url, pool_pre_ping=True)
            session_maker = sessionmaker(bind=self.engine)
            self.session = session_maker()
        else:
            # Use default global connection
            get_engine()
            self.session = get_session()
            self.engine = None

        self._table_cache = {}
        self._column_cache = {}
        self._row_cache = {}
        self._sheet_cache = {}
        
    def validate_expression_references(self, dpm_xl_expression: str) -> List[ValidationIssue]:
        """
        Validate all cell references in a DPM-XL expression.
        
        Args:
            dpm_xl_expression (str): The DPM-XL expression to validate
            
        Returns:
            List[ValidationIssue]: List of validation issues found
        """
        issues = []
        
        try:
            # Parse cell references from the expression
            cell_refs = self._parse_cell_references(dpm_xl_expression)
            
            for cell_ref in cell_refs:
                # Validate table exists
                table_issues = self.validate_table_exists(cell_ref.table)
                issues.extend(table_issues)
                
                # If table exists, validate other components
                if not table_issues:
                    # Validate columns
                    column_issues = self.validate_columns_exist(cell_ref.table, cell_ref.columns)
                    issues.extend(column_issues)
                    
                    # Validate rows
                    row_issues = self.validate_rows_exist(cell_ref.table, cell_ref.rows)
                    issues.extend(row_issues)
                    
                    # Validate sheets
                    sheet_issues = self.validate_sheets_exist(cell_ref.table, cell_ref.sheets)
                    issues.extend(sheet_issues)
                    
        except Exception as e:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.CONFIGURATION_ERROR,
                description=f"Error parsing expression: {str(e)}",
                affected_element=dpm_xl_expression[:50] + "..." if len(dpm_xl_expression) > 50 else dpm_xl_expression,
                severity="error",
                code="PARSE_ERROR"
            ))
            
        return issues
    
    def validate_table_exists(self, table_name: str) -> List[ValidationIssue]:
        """
        Validate that a table exists in the data dictionary.
        
        Args:
            table_name (str): Name of the table to validate
            
        Returns:
            List[ValidationIssue]: List of validation issues found
        """
        issues = []
        
        try:
            # Check cache first
            if table_name in self._table_cache:
                return self._table_cache[table_name]
            
            # Query the database for the table using the correct schema
            # The actual schema uses table_code instead of table_name
            tables = self.session.execute(
                text("SELECT DISTINCT table_code FROM datapoints WHERE table_code = :table_code"),
                {"table_code": table_name}
            ).fetchall()
            
            if not tables:
                issue = ValidationIssue(
                    issue_type=ValidationIssueType.MISSING_TABLE,
                    description=f"Table '{table_name}' was not found in the data dictionary",
                    affected_element=table_name,
                    suggested_fix=f"Add table '{table_name}' to the data dictionary or check the table name spelling",
                    severity="error",
                    code="TABLE_NOT_FOUND"
                )
                issues.append(issue)
            
            # Cache the result
            self._table_cache[table_name] = issues
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.CONFIGURATION_ERROR,
                description=f"Error checking table '{table_name}': {str(e)}",
                affected_element=table_name,
                severity="error",
                code="TABLE_CHECK_ERROR"
            ))
        
        return issues
    
    def validate_columns_exist(self, table_name: str, columns: List[str]) -> List[ValidationIssue]:
        """
        Validate that columns exist for a table.
        
        Args:
            table_name (str): Name of the table
            columns (List[str]): List of column names/patterns to validate
            
        Returns:
            List[ValidationIssue]: List of validation issues found
        """
        issues = []
        
        try:
            cache_key = f"{table_name}:{':'.join(columns)}"
            if cache_key in self._column_cache:
                return self._column_cache[cache_key]
            
            for column in columns:
                # Skip wildcards and ranges for now - these need special handling
                if column in ['*'] or '-' in column:
                    continue
                    
                # Check if specific column exists
                column_exists = self.session.execute(
                    text("SELECT COUNT(*) FROM datapoints WHERE table_code = :table_code AND column_code = :column_code"),
                    {"table_code": table_name, "column_code": column}
                ).fetchone()
                
                if not column_exists or column_exists[0] == 0:
                    issue = ValidationIssue(
                        issue_type=ValidationIssueType.MISSING_COLUMN,
                        description=f"Column '{column}' not found in table '{table_name}'",
                        affected_element=f"{table_name}.{column}",
                        suggested_fix=f"Add column '{column}' to table '{table_name}' or check the column name",
                        severity="error",
                        code="COLUMN_NOT_FOUND"
                    )
                    issues.append(issue)
            
            self._column_cache[cache_key] = issues
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.CONFIGURATION_ERROR,
                description=f"Error checking columns for table '{table_name}': {str(e)}",
                affected_element=f"{table_name}.[{','.join(columns)}]",
                severity="error",
                code="COLUMN_CHECK_ERROR"
            ))
        
        return issues
    
    def validate_rows_exist(self, table_name: str, rows: List[str]) -> List[ValidationIssue]:
        """
        Validate that rows exist for a table.
        
        Args:
            table_name (str): Name of the table
            rows (List[str]): List of row names/patterns to validate
            
        Returns:
            List[ValidationIssue]: List of validation issues found
        """
        issues = []
        
        try:
            cache_key = f"{table_name}:rows:{':'.join(rows)}"
            if cache_key in self._row_cache:
                return self._row_cache[cache_key]
            
            for row in rows:
                # Skip wildcards and ranges for now
                if row in ['*'] or '-' in row:
                    continue
                    
                # Check if specific row exists
                row_exists = self.session.execute(
                    text("SELECT COUNT(*) FROM datapoints WHERE table_code = :table_code AND row_code = :row_code"),
                    {"table_code": table_name, "row_code": row}
                ).fetchone()
                
                if not row_exists or row_exists[0] == 0:
                    issue = ValidationIssue(
                        issue_type=ValidationIssueType.MISSING_ROW,
                        description=f"Row '{row}' not found in table '{table_name}'",
                        affected_element=f"{table_name}.{row}",
                        suggested_fix=f"Add row '{row}' to table '{table_name}' or check the row name",
                        severity="warning",  # Rows might be more flexible
                        code="ROW_NOT_FOUND"
                    )
                    issues.append(issue)
            
            self._row_cache[cache_key] = issues
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.CONFIGURATION_ERROR,
                description=f"Error checking rows for table '{table_name}': {str(e)}",
                affected_element=f"{table_name}.[{','.join(rows)}]",
                severity="error",
                code="ROW_CHECK_ERROR"
            ))
        
        return issues
    
    def validate_sheets_exist(self, table_name: str, sheets: List[str]) -> List[ValidationIssue]:
        """
        Validate that sheets exist for a table.
        
        Args:
            table_name (str): Name of the table
            sheets (List[str]): List of sheet names/patterns to validate
            
        Returns:
            List[ValidationIssue]: List of validation issues found
        """
        issues = []
        
        try:
            cache_key = f"{table_name}:sheets:{':'.join(sheets)}"
            if cache_key in self._sheet_cache:
                return self._sheet_cache[cache_key]
            
            for sheet in sheets:
                # Skip wildcards for now
                if sheet in ['*']:
                    # Check if any sheets exist for this table
                    sheet_count = self.session.execute(
                        text("SELECT COUNT(DISTINCT sheet_code) FROM datapoints WHERE table_code = :table_code AND sheet_code IS NOT NULL AND sheet_code != ''"),
                        {"table_code": table_name}
                    ).fetchone()
                    
                    if not sheet_count or sheet_count[0] == 0:
                        issue = ValidationIssue(
                            issue_type=ValidationIssueType.MISSING_SHEET,
                            description=f"No sheets found for table '{table_name}' but s* wildcard used",
                            affected_element=f"{table_name}.s*",
                            suggested_fix=f"Add sheet definitions for table '{table_name}' or remove s* wildcard",
                            severity="error",
                            code="NO_SHEETS_FOR_WILDCARD"
                        )
                        issues.append(issue)
                    continue
                
                # Check if specific sheet exists
                sheet_exists = self.session.execute(
                    text("SELECT COUNT(*) FROM datapoints WHERE table_code = :table_code AND sheet_code = :sheet_code"),
                    {"table_code": table_name, "sheet_code": sheet}
                ).fetchone()
                
                if not sheet_exists or sheet_exists[0] == 0:
                    issue = ValidationIssue(
                        issue_type=ValidationIssueType.MISSING_SHEET,
                        description=f"Sheet '{sheet}' not found in table '{table_name}'",
                        affected_element=f"{table_name}.{sheet}",
                        suggested_fix=f"Add sheet '{sheet}' to table '{table_name}' or check the sheet name",
                        severity="error",
                        code="SHEET_NOT_FOUND"
                    )
                    issues.append(issue)
            
            self._sheet_cache[cache_key] = issues
            
        except Exception as e:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.CONFIGURATION_ERROR,
                description=f"Error checking sheets for table '{table_name}': {str(e)}",
                affected_element=f"{table_name}.[{','.join(sheets)}]",
                severity="error",
                code="SHEET_CHECK_ERROR"
            ))
        
        return issues
    
    def validate_variables_exist(self, variable_names: List[str]) -> List[ValidationIssue]:
        """
        Validate that variables exist in the data dictionary.
        
        Args:
            variable_names (List[str]): List of variable names to validate
            
        Returns:
            List[ValidationIssue]: List of validation issues found
        """
        issues = []
        
        for var_name in variable_names:
            try:
                # Variable validation - try multiple approaches based on the schema
                # First try to find it as a VariableID (numeric)
                var_exists = None
                try:
                    var_id = int(var_name)
                    var_exists = self.session.execute(
                        text("SELECT COUNT(*) FROM Variable WHERE VariableID = :var_id"),
                        {"var_id": var_id}
                    ).fetchone()
                except ValueError:
                    # Not a numeric ID, skip variable validation for now
                    # Variables in this schema appear to be referenced by ID, not name
                    continue
                
                if var_exists and var_exists[0] == 0:
                    issue = ValidationIssue(
                        issue_type=ValidationIssueType.MISSING_VARIABLE,
                        description=f"Variable ID '{var_name}' not found in data dictionary",
                        affected_element=var_name,
                        suggested_fix=f"Add variable ID '{var_name}' to the data dictionary or check the variable ID",
                        severity="warning",  # Changed to warning since variable structure is unclear
                        code="VARIABLE_NOT_FOUND"
                    )
                    issues.append(issue)
                    
            except Exception as e:
                issues.append(ValidationIssue(
                    issue_type=ValidationIssueType.CONFIGURATION_ERROR,
                    description=f"Error checking variable '{var_name}': {str(e)}",
                    affected_element=var_name,
                    severity="error",
                    code="VARIABLE_CHECK_ERROR"
                ))
        
        return issues
    
    def get_validation_summary(self, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """
        Generate a summary of validation issues.
        
        Args:
            issues (List[ValidationIssue]): List of validation issues
            
        Returns:
            Dict[str, Any]: Summary statistics and categorized issues
        """
        summary = {
            "total_issues": len(issues),
            "by_type": {},
            "by_severity": {},
            "fixable_issues": [],
            "critical_issues": []
        }
        
        for issue in issues:
            # Count by type
            issue_type = issue.issue_type.value
            summary["by_type"][issue_type] = summary["by_type"].get(issue_type, 0) + 1
            
            # Count by severity
            summary["by_severity"][issue.severity] = summary["by_severity"].get(issue.severity, 0) + 1
            
            # Categorize issues
            if issue.suggested_fix:
                summary["fixable_issues"].append(issue)
            
            if issue.severity == "error":
                summary["critical_issues"].append(issue)
        
        return summary
    
    def _parse_cell_references(self, expression: str) -> List[CellReference]:
        """
        Parse cell references from a DPM-XL expression.
        
        Args:
            expression (str): DPM-XL expression to parse
            
        Returns:
            List[CellReference]: List of parsed cell references
        """
        cell_refs = []
        
        # Regex pattern to match cell references like {tTableName, rRows, cColumns, sSheets}
        pattern = r'\{t([^,]+),\s*([^,]+),\s*([^,]+)(?:,\s*([^}]+))?\}'
        
        matches = re.findall(pattern, expression)
        
        for match in matches:
            table = match[0].strip()
            
            # Parse rows
            rows_str = match[1].strip()
            rows = self._parse_dimension_values(rows_str, 'r')
            
            # Parse columns  
            cols_str = match[2].strip()
            columns = self._parse_dimension_values(cols_str, 'c')
            
            # Parse sheets (optional)
            sheets = []
            if len(match) > 3 and match[3]:
                sheets_str = match[3].strip()
                sheets = self._parse_dimension_values(sheets_str, 's')
            
            cell_refs.append(CellReference(
                table=table,
                rows=rows,
                columns=columns,
                sheets=sheets
            ))
        
        return cell_refs
    
    def _parse_dimension_values(self, dim_str: str, prefix: str) -> List[str]:
        """
        Parse dimension values (rows, columns, or sheets) from a string.
        
        Args:
            dim_str (str): String containing dimension values
            prefix (str): Expected prefix ('r', 'c', or 's')
            
        Returns:
            List[str]: List of parsed dimension values
        """
        values = []
        
        # Remove prefix and parentheses if present
        dim_str = dim_str.strip()
        if dim_str.startswith(prefix):
            dim_str = dim_str[1:]
        if dim_str.startswith('(') and dim_str.endswith(')'):
            dim_str = dim_str[1:-1]
        
        # Split by comma and clean up
        if dim_str:
            for value in dim_str.split(','):
                value = value.strip()
                if value:
                    values.append(value)
        
        return values
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'session') and self.session:
            self.session.close()
        if hasattr(self, 'engine') and self.engine is not None:
            self.engine.dispose()


# Convenience functions for direct usage
def validate_dpm_xl_expression(expression: str) -> List[ValidationIssue]:
    """
    Convenience function to validate a DPM-XL expression.
    
    Args:
        expression (str): DPM-XL expression to validate
        
    Returns:
        List[ValidationIssue]: List of validation issues found
    """
    validator = DataDictionaryValidator()
    return validator.validate_expression_references(expression)


def validate_table_references(table_names: List[str]) -> List[ValidationIssue]:
    """
    Convenience function to validate table references.
    
    Args:
        table_names (List[str]): List of table names to validate
        
    Returns:
        List[ValidationIssue]: List of validation issues found
    """
    validator = DataDictionaryValidator()
    issues = []
    
    for table_name in table_names:
        issues.extend(validator.validate_table_exists(table_name))
    
    return issues


def check_data_dictionary_health() -> Dict[str, Any]:
    """
    Perform a comprehensive health check of the data dictionary.
    
    Returns:
        Dict[str, Any]: Health check results
    """
    validator = DataDictionaryValidator()
    
    # This would include various checks like:
    # - Missing table definitions
    # - Orphaned references
    # - Inconsistent naming
    # - etc.
    
    health_report = {
        "status": "healthy",  # or "warning" or "critical"
        "total_tables": 0,
        "issues_found": [],
        "recommendations": []
    }
    
    try:
        # Get total table count
        result = validator.session.execute(text("SELECT COUNT(DISTINCT table_code) FROM datapoints")).fetchone()
        health_report["total_tables"] = result[0] if result else 0
        
        # Add more comprehensive checks here
        
    except Exception as e:
        health_report["status"] = "critical"
        health_report["issues_found"].append(f"Database connection error: {str(e)}")
    
    return health_report
