import click
from rich.console import Console
from rich.table import Table
from rich.text import Text
import os
import sys
import pandas as pd

from py_dpm.api import API
from py_dpm.api.operation_scopes import OperationScopesAPI
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


@main.command()
@click.argument('expression', type=str, required=False)
@click.option('--operation-vid', type=int, help='Operation version ID to associate scopes with')
@click.option('--tables', type=str, help='Comma-separated table VIDs (for low-level mode)')
@click.option('--preconditions', type=str, help='Comma-separated precondition item codes')
@click.option('--release-id', type=int, help='Release ID to filter modules (defaults to last release)')
def calculate_scopes(expression, operation_vid, tables, preconditions, release_id):
    """
    Calculate operation scopes from a DPM-XL expression or table VIDs.

    EXPRESSION: DPM-XL expression to analyze (optional if --tables is provided)

    Examples:
        pydpm calculate-scopes "{tC_01.00, r0100, c0010}"
        pydpm calculate-scopes "{tC_01.00, r0100, c0010}" --release-id 42
        pydpm calculate-scopes --operation-vid 1 --tables 101,102 --release-id 42
    """
    api = OperationScopesAPI()

    try:
        # Determine mode: expression-based or table VID-based
        if expression:
            # Expression-based mode (recommended)
            # Always use read_only=True for CLI to prevent accidental database modifications
            result = api.calculate_scopes_from_expression(
                expression=expression,
                operation_version_id=operation_vid,
                release_id=release_id,
                read_only=True
            )
        elif tables:
            # Low-level mode with table VIDs
            table_vids = [int(t.strip()) for t in tables.split(',')]
            precondition_items = [p.strip() for p in preconditions.split(',')] if preconditions else []

            # Always use read_only=True for CLI to prevent accidental database modifications
            result = api.calculate_scopes(
                operation_version_id=operation_vid,
                tables_vids=table_vids,
                precondition_items=precondition_items,
                release_id=release_id,
                read_only=True
            )
        else:
            console.print("Error: Either EXPRESSION or --tables must be provided", style="bold red")
            sys.exit(1)

        # Check for errors
        if result.has_error:
            console.print(f"Error calculating scopes: {result.error_message}", style="bold red")
            sys.exit(1)

        # Display summary
        console.print("\n[bold cyan]Operation Scopes Calculation Results[/bold cyan]")
        console.print("=" * 60)

        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column("Label", style="bold")
        summary_table.add_column("Value")

        summary_table.add_row("Total Scopes:", str(result.total_scopes))
        summary_table.add_row("Existing Scopes:", str(len(result.existing_scopes)))
        summary_table.add_row("New Scopes:", str(len(result.new_scopes)))
        summary_table.add_row("Cross-Module:", "Yes" if result.is_cross_module else "No")
        summary_table.add_row("Module Versions:", ', '.join(map(str, result.module_versions)))
        summary_table.add_row("Release ID:", str(result.release_id) if result.release_id else "Default (Last)")

        if result.expression:
            summary_table.add_row("Expression:", result.expression)

        console.print(summary_table)

        # Display scope details
        if result.total_scopes > 0:
            console.print("\n[bold cyan]Scope Details[/bold cyan]")

            scopes_table = Table(show_header=True, header_style="bold magenta")
            scopes_table.add_column("Scope ID", justify="right")
            scopes_table.add_column("Status", justify="center")
            scopes_table.add_column("Module VIDs", justify="left")
            scopes_table.add_column("Type", justify="center")
            scopes_table.add_column("From Date", justify="center")

            for scope in result.existing_scopes:
                module_vids = [str(comp.modulevid) for comp in scope.operation_scope_compositions]
                scope_type = "Cross-Module" if len(module_vids) > 1 else "Intra-Module"
                from_date = str(scope.fromsubmissiondate) if scope.fromsubmissiondate else "N/A"

                scopes_table.add_row(
                    str(scope.operationscopeid),
                    "[yellow]Existing[/yellow]",
                    ", ".join(module_vids),
                    scope_type,
                    from_date
                )

            for scope in result.new_scopes:
                module_vids = [str(comp.modulevid) for comp in scope.operation_scope_compositions]
                scope_type = "Cross-Module" if len(module_vids) > 1 else "Intra-Module"
                from_date = str(scope.fromsubmissiondate) if scope.fromsubmissiondate else "N/A"

                scopes_table.add_row(
                    "[dim]New (not committed)[/dim]",
                    "[green]New[/green]",
                    ", ".join(module_vids),
                    scope_type,
                    from_date
                )

            console.print(scopes_table)

            # Display module version details if available
            if result.module_versions:
                console.print("\n[bold cyan]Module Versions Involved[/bold cyan]")

                modules_table = Table(show_header=True, header_style="bold magenta")
                modules_table.add_column("Module VID", justify="right")
                modules_table.add_column("Code", justify="left")
                modules_table.add_column("Name", justify="left")
                modules_table.add_column("From Date", justify="center")
                modules_table.add_column("To Date", justify="center")

                from py_dpm.models import ModuleVersion

                for module_vid in result.module_versions:
                    module_df = ModuleVersion.get_module_version_by_vid(api.session, module_vid)
                    if not module_df.empty:
                        module = module_df.iloc[0]
                        modules_table.add_row(
                            str(module['ModuleVID']),
                            str(module['Code']),
                            str(module['Name']),
                            str(module['FromReferenceDate']),
                            str(module['ToReferenceDate']) if module['ToReferenceDate'] is not pd.NaT else "Open"
                        )

                console.print(modules_table)

        console.print("\n[bold green]✓ Scope calculation completed successfully[/bold green]\n")

    except SemanticError as e:
        console.print(f"Semantic error: {str(e)}", style="bold red")
        sys.exit(1)
    except Exception as e:
        console.print(f"Unexpected error: {str(e)}", style="bold red")
        sys.exit(1)
    finally:
        api.session.close()


if __name__ == '__main__':
    main()