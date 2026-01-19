import click
from rich.console import Console
from rich.table import Table
from rich.text import Text
import os
import sys
import pandas as pd

from py_dpm.api import SemanticAPI, SyntaxAPI
from py_dpm.api.dpm_xl.semantic import SemanticValidationResult
from py_dpm.api.dpm_xl.operation_scopes import OperationScopesAPI
from py_dpm.dpm.migration import run_migration
from py_dpm.dpm_xl.utils.tokens import (
    CODE,
    ERROR,
    ERROR_CODE,
    EXPRESSION,
    OP_VERSION_ID,
    STATUS,
    STATUS_CORRECT,
    STATUS_UNKNOWN,
    VALIDATIONS,
    VALIDATION_TYPE,
    VARIABLES,
)
from py_dpm.exceptions.exceptions import SemanticError


console = Console()


@click.group()
@click.version_option()
def main():
    """pyDPM CLI - A command line interface for pyDPM"""
    pass


@main.command()
@click.argument("access_file", type=click.Path(exists=True))
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
@click.argument("expression", type=str)
@click.option(
    "--release-id", type=int, help="Release ID to use for validation", default=None
)
@click.option(
    "--release-code",
    type=str,
    help="Release code (e.g. 4.2) to use for validation",
    default=None,
)
def semantic(expression: str, release_id: int, release_code: str):
    """
    Semantically analyses the input expression by applying the syntax validation, the operands checking, the data type
    validation and the structure validation
    :param expression: Expression to be analysed
    :param release_id: ID of the release used. If None, gathers the live release
    :param release_code: Version code of the release used.
    Used only in DPM-ML generation
    :return if Return_data is False, any Symbol, else data extracted from DB based on operands cell references
    """

    if release_id is not None and release_code is not None:
        raise click.UsageError("Cannot provide both --release-id and --release-code")

    error_code = ""
    validation_type = STATUS_UNKNOWN

    semantic_api = SemanticAPI()

    if release_code:
        from py_dpm.dpm.models import Release

        release_id = (
            semantic_api.session.query(Release.releaseid)
            .filter(Release.code == release_code)
            .scalar()
        )
        if release_id is None:
            console.print(
                f"Error: Release code '{release_code}' not found.", style="bold red"
            )
            sys.exit(1)

    try:
        validation_type = "OTHER"
        # Validate using the semantic API with release_id support
        result: SemanticValidationResult = semantic_api.validate_expression(
            expression, release_id=release_id
        )

        if result.is_valid:
            status = 200
            message_error = ""
        else:
            status = 500
            message_error = result.error_message
            error_code = result.error_code or 1

    except Exception as error:
        status = 500
        message_error = str(error)
        error_code = 1

    # Clean up resources
    # semantic_api destructor handles this, but we can be explicit if needed

    message_response = {
        ERROR: message_error,
        ERROR_CODE: error_code,
        VALIDATION_TYPE: validation_type,
    }

    if error_code and status == 500:
        console.print(
            f"Semantic validation failed for expression: {expression}.",
            style="bold red",
        )
        if message_error:
            console.print(f"Error: {message_error}", style="red")
    else:
        console.log(f"Semantic validation completed for expression: {expression}.")
        console.print(f"Status: {status}", style="bold green")
    return status


@main.command()
@click.argument("expression", type=str)
def syntax(expression: str):
    """Perform syntactic analysis on a DPM expression."""

    status = 0
    api = SyntaxAPI()
    try:
        result = api.validate_expression(expression)
        if not result.is_valid:
            raise SyntaxError(result.error_message or "Syntax errors detected")
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
@click.argument("expression", type=str, required=False)
@click.option(
    "--operation-vid", type=int, help="Operation version ID to associate scopes with"
)
@click.option(
    "--tables", type=str, help="Comma-separated table VIDs (for low-level mode)"
)
@click.option(
    "--preconditions", type=str, help="Comma-separated precondition item codes"
)
@click.option(
    "--release-id",
    type=int,
    help="Release ID to filter modules (defaults to last release)",
)
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
                read_only=True,
            )
        elif tables:
            # Low-level mode with table VIDs
            table_vids = [int(t.strip()) for t in tables.split(",")]
            precondition_items = (
                [p.strip() for p in preconditions.split(",")] if preconditions else []
            )

            # Always use read_only=True for CLI to prevent accidental database modifications
            result = api.calculate_scopes(
                operation_version_id=operation_vid,
                tables_vids=table_vids,
                precondition_items=precondition_items,
                release_id=release_id,
                read_only=True,
            )
        else:
            console.print(
                "Error: Either EXPRESSION or --tables must be provided",
                style="bold red",
            )
            sys.exit(1)

        # Check for errors
        if result.has_error:
            console.print(
                f"Error calculating scopes: {result.error_message}", style="bold red"
            )
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
        summary_table.add_row(
            "Cross-Module:", "Yes" if result.is_cross_module else "No"
        )
        summary_table.add_row(
            "Module Versions:", ", ".join(map(str, result.module_versions))
        )
        summary_table.add_row(
            "Release ID:",
            str(result.release_id) if result.release_id else "Default (Last)",
        )

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
                module_vids = [
                    str(comp.modulevid) for comp in scope.operation_scope_compositions
                ]
                scope_type = "Cross-Module" if len(module_vids) > 1 else "Intra-Module"
                from_date = (
                    str(scope.fromsubmissiondate) if scope.fromsubmissiondate else "N/A"
                )

                scopes_table.add_row(
                    str(scope.operationscopeid),
                    "[yellow]Existing[/yellow]",
                    ", ".join(module_vids),
                    scope_type,
                    from_date,
                )

            for scope in result.new_scopes:
                module_vids = [
                    str(comp.modulevid) for comp in scope.operation_scope_compositions
                ]
                scope_type = "Cross-Module" if len(module_vids) > 1 else "Intra-Module"
                from_date = (
                    str(scope.fromsubmissiondate) if scope.fromsubmissiondate else "N/A"
                )

                scopes_table.add_row(
                    "[dim]New (not committed)[/dim]",
                    "[green]New[/green]",
                    ", ".join(module_vids),
                    scope_type,
                    from_date,
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

                from py_dpm.dpm.models import ModuleVersion

                for module_vid in result.module_versions:
                    module_df = ModuleVersion.get_module_version_by_vid(
                        api.session, module_vid
                    )
                    if not module_df.empty:
                        module = module_df.iloc[0]
                        modules_table.add_row(
                            str(module["ModuleVID"]),
                            str(module["Code"]),
                            str(module["Name"]),
                            str(module["FromReferenceDate"]),
                            (
                                str(module["ToReferenceDate"])
                                if module["ToReferenceDate"] is not pd.NaT
                                else "Open"
                            ),
                        )

                console.print(modules_table)

        console.print(
            "\n[bold green]✓ Scope calculation completed successfully[/bold green]\n"
        )

    except SemanticError as e:
        console.print(f"Semantic error: {str(e)}", style="bold red")
        sys.exit(1)
    except Exception as e:
        console.print(f"Unexpected error: {str(e)}", style="bold red")
        sys.exit(1)
    finally:
        api.session.close()


@main.command()
@click.argument("expression", type=str, required=False)
@click.option("--operation-vid", type=int, help="Operation version ID")
@click.option(
    "--release-id",
    type=int,
    help="Release ID to filter modules (defaults to last release)",
)
def get_scopes_metadata(expression, operation_vid, release_id):
    """
    Get operation scopes with detailed module metadata.

    EXPRESSION: DPM-XL expression to analyze (optional if --operation-vid is provided)

    Examples:
        pydpm get-scopes-metadata --operation-vid 1
        pydpm get-scopes-metadata "{tC_01.00, r0100, c0010}"
        pydpm get-scopes-metadata "{tC_01.00, r0100, c0010}" --release-id 42
    """
    api = OperationScopesAPI()

    try:
        # Determine mode: expression-based or operation-vid-based
        if expression:
            scopes = api.get_scopes_with_metadata_from_expression(
                expression=expression, release_id=release_id
            )
            mode = "expression"
        elif operation_vid:
            scopes = api.get_scopes_with_metadata(operation_version_id=operation_vid)
            mode = "operation_vid"
        else:
            console.print(
                "Error: Either EXPRESSION or --operation-vid must be provided",
                style="bold red",
            )
            sys.exit(1)

        # Display results
        if not scopes:
            console.print("\n[yellow]No scopes found[/yellow]\n")
            return

        console.print(
            f"\n[bold cyan]Operation Scopes with Metadata[/bold cyan] (Total: {len(scopes)})"
        )
        console.print("=" * 80)

        for idx, scope in enumerate(scopes, 1):
            console.print(f"\n[bold]Scope #{idx}[/bold]")

            # Scope details
            details_table = Table(show_header=False, box=None, padding=(0, 2))
            details_table.add_column("Label", style="bold")
            details_table.add_column("Value")

            details_table.add_row("Scope ID:", str(scope.operation_scope_id))
            details_table.add_row("Operation VID:", str(scope.operation_vid))
            details_table.add_row("Active:", "Yes" if scope.is_active else "No")
            details_table.add_row("Severity:", scope.severity)
            if scope.from_submission_date:
                details_table.add_row("From Date:", str(scope.from_submission_date))

            console.print(details_table)

            # Module versions
            if scope.module_versions:
                console.print(
                    f"\n  [bold]Modules ({len(scope.module_versions)}):[/bold]"
                )

                modules_table = Table(show_header=True, header_style="bold magenta")
                modules_table.add_column("Module VID", justify="right")
                modules_table.add_column("Code", justify="left")
                modules_table.add_column("Name", justify="left")
                modules_table.add_column("Version", justify="center")
                modules_table.add_column("From Date", justify="center")
                modules_table.add_column("To Date", justify="center")

                for module in scope.module_versions:
                    modules_table.add_row(
                        str(module.module_vid),
                        module.code,
                        (
                            module.name[:40] + "..."
                            if len(module.name) > 40
                            else module.name
                        ),
                        module.version_number,
                        (
                            str(module.from_reference_date)
                            if module.from_reference_date
                            else "N/A"
                        ),
                        (
                            str(module.to_reference_date)
                            if module.to_reference_date
                            else "Open"
                        ),
                    )

                console.print(modules_table)

        console.print(
            "\n[bold green]✓ Scopes metadata retrieved successfully[/bold green]\n"
        )

    except Exception as e:
        console.print(f"Error: {str(e)}", style="bold red")
        sys.exit(1)
    finally:
        api.session.close()


@main.command()
@click.argument("expression", type=str, required=False)
@click.option("--operation-vid", type=int, help="Operation version ID")
@click.option(
    "--release-id",
    type=int,
    help="Release ID to filter modules (defaults to last release)",
)
def get_tables_metadata(expression, operation_vid, release_id):
    """
    Get tables from operation scopes with metadata.

    EXPRESSION: DPM-XL expression to analyze (optional if --operation-vid is provided)

    Examples:
        pydpm get-tables-metadata --operation-vid 1
        pydpm get-tables-metadata "{tC_01.00, r0100, c0010}"
        pydpm get-tables-metadata "{tC_01.00, r0100, c0010}" --release-id 42
    """
    api = OperationScopesAPI()

    try:
        # Determine mode: expression-based or operation-vid-based
        if expression:
            tables = api.get_tables_with_metadata_from_expression(
                expression=expression, release_id=release_id
            )
        elif operation_vid:
            tables = api.get_tables_with_metadata(operation_version_id=operation_vid)
        else:
            console.print(
                "Error: Either EXPRESSION or --operation-vid must be provided",
                style="bold red",
            )
            sys.exit(1)

        # Display results
        if not tables:
            console.print("\n[yellow]No tables found[/yellow]\n")
            return

        console.print(
            f"\n[bold cyan]Tables with Metadata[/bold cyan] (Total: {len(tables)})"
        )
        console.print("=" * 80)

        tables_table = Table(show_header=True, header_style="bold magenta")
        tables_table.add_column("Table VID", justify="right", style="cyan")
        tables_table.add_column("Code", justify="left", style="green")
        tables_table.add_column("Name", justify="left")
        tables_table.add_column("Description", justify="left")

        for table in tables:
            # Truncate long descriptions
            description = (
                table.description[:60] + "..."
                if len(table.description) > 60
                else table.description
            )

            tables_table.add_row(
                str(table.table_vid),
                table.code,
                table.name[:40] + "..." if len(table.name) > 40 else table.name,
                description,
            )

        console.print(tables_table)
        console.print(
            "\n[bold green]✓ Tables metadata retrieved successfully[/bold green]\n"
        )

    except Exception as e:
        console.print(f"Error: {str(e)}", style="bold red")
        sys.exit(1)
    finally:
        api.session.close()


@main.command()
@click.argument("expression", type=str, required=False)
@click.option("--operation-vid", type=int, help="Operation version ID")
@click.option("--table-vid", type=int, help="Filter by specific table VID")
@click.option(
    "--release-id",
    type=int,
    help="Release ID to filter modules (defaults to last release)",
)
def get_headers_metadata(expression, operation_vid, table_vid, release_id):
    """
    Get headers from operation scopes with metadata.

    EXPRESSION: DPM-XL expression to analyze (optional if --operation-vid is provided)

    Examples:
        pydpm get-headers-metadata --operation-vid 1
        pydpm get-headers-metadata --operation-vid 1 --table-vid 101
        pydpm get-headers-metadata "{tC_01.00, r0100, c0010}"
        pydpm get-headers-metadata "{tC_01.00, r0100, c0010}" --table-vid 101
    """
    api = OperationScopesAPI()

    try:
        # Determine mode: expression-based or operation-vid-based
        if expression:
            headers = api.get_headers_with_metadata_from_expression(
                expression=expression, table_vid=table_vid, release_id=release_id
            )
        elif operation_vid:
            headers = api.get_headers_with_metadata(
                operation_version_id=operation_vid, table_vid=table_vid
            )
        else:
            console.print(
                "Error: Either EXPRESSION or --operation-vid must be provided",
                style="bold red",
            )
            sys.exit(1)

        # Display results
        if not headers:
            console.print("\n[yellow]No headers found[/yellow]\n")
            return

        console.print(
            f"\n[bold cyan]Headers with Metadata[/bold cyan] (Total: {len(headers)})"
        )
        if table_vid:
            console.print(f"[dim]Filtered by Table VID: {table_vid}[/dim]")
        console.print("=" * 80)

        headers_table = Table(show_header=True, header_style="bold magenta")
        headers_table.add_column("Header VID", justify="right", style="cyan")
        headers_table.add_column("Table VID", justify="right", style="yellow")
        headers_table.add_column("Code", justify="left", style="green")
        headers_table.add_column("Label", justify="left")
        headers_table.add_column("Type", justify="center")

        for header in headers:
            headers_table.add_row(
                str(header.header_vid),
                str(header.table_vid) if header.table_vid else "N/A",
                header.code,
                header.label[:50] + "..." if len(header.label) > 50 else header.label,
                header.header_type,
            )

        console.print(headers_table)
        console.print(
            "\n[bold green]✓ Headers metadata retrieved successfully[/bold green]\n"
        )

    except Exception as e:
        console.print(f"Error: {str(e)}", style="bold red")
        sys.exit(1)
    finally:
        api.session.close()


if __name__ == "__main__":
    main()
