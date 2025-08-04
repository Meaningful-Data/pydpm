import click
from rich.console import Console
from rich.table import Table
from rich.text import Text
import os
import sys

from py_dpm.api import API
from py_dpm.migration import run_migration
from py_dpm.Utils.tokens import CODE, ERROR, ERROR_CODE, EXPRESSION, OP_VERSION_ID, STATUS, \
    STATUS_CORRECT, STATUS_UNKNOWN, VALIDATIONS, \
    VALIDATION_TYPE, \
    VARIABLES
from py_dpm.Exceptions.exceptions import SemanticError


console = Console()

@click.group()
@click.version_option()
def main():
    """pyDPM CLI - A command line interface for pyDPM"""
    pass

@main.command()
@click.argument('access_file', type=click.Path(exists=True))
def migrate_access(access_file: str):
    """
    Migrates data from an Access database to a SQLite database.

    ACCESS_FILE: Path to the Access database file (.mdb or .accdb).
    """

    sqlite_db = os.getenv("SQLITE_DB_PATH", "database.db")
    console.print(f"Starting migration from '{access_file}' to '{sqlite_db}'...")
    try:
        run_migration(access_file, sqlite_db)
        console.print("Migration completed successfully.", style="bold green")
    except Exception as e:
        console.print(f"An error occurred during migration: {e}", style="bold red")
        sys.exit(1)


@main.command()
@click.argument('expression', type=str)
def semantic(expression: str):
    """
    Semantically analyses the input expression by applying the syntax validation, the operands checking, the data type
    validation and the structure validation
    :param expression: Expression to be analysed
    :param release_id: ID of the release used. If None, gathers the live release
    Used only in DPM-ML generation
    :return if Return_data is False, any Symbol, else data extracted from DB based on operands cell references
    """

    error_code = ""
    validation_type = STATUS_UNKNOWN

    api = API()
    try:
        validation_type = "OTHER"
        api.semantic_validation(expression)
        status = 200
        message_error = ''
    except Exception as error:
        status = 500
        message_error = str(error)
        error_code = 1
    message_response = {
        ERROR: message_error,
        ERROR_CODE: error_code,
        VALIDATION_TYPE: validation_type,
    }
    api.session.close()
    if error_code and status == 500:
        console.print(f"Semantic validation failed for expression: {expression}.", style="bold red")
    else:
        console.log(f"Semantic validation completed for expression: {expression}.")
        console.print(f"Status: {status}", style="bold green")
    return status

@main.command()
@click.argument('expression', type=str)
def syntax(expression: str):
    """Perform syntactic analysis on a DPM expression."""

    status = 0
    api = API()
    try:
        api.syntax_validation(expression)
        message_formatted = Text("Syntax OK", style="bold green")
    except SyntaxError as e:
        message = str(e)
        message_formatted = Text(f"Syntax Error: {message}", style="bold red")
        status = 0
    except Exception as e:
        message = str(e)
        message_formatted = Text(f"Unexpected Error: {message}", style="bold red")
        status = 1

    console.print(message_formatted)

    return status

if __name__ == '__main__':
    main()