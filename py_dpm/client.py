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
from py_dpm.AST.SubaDpmXlTranspiler import SubaToDpmXlTranspiler, DpmXlToSubaTranspiler, TranspilerUtils


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
@click.argument('suba_expression', type=str)
@click.option('--no-optimize', is_flag=True, help='Disable WITH clause optimization')
@click.option('--analyze', is_flag=True, help='Show detailed expression analysis')
def transpile(suba_expression: str, no_optimize: bool, analyze: bool):
    """
    Transpile a SUBA expression to DPM-XL.
    
    SUBA_EXPRESSION: The SUBA expression to transpile.

    Examples:
    \b
    pydpm transpile "{T(C_17.01.a)R(0940)C(0010-0080)} = {T(C_17.01.a)R(0945)C(0010-0080)} + {T(C_17.01.a)R(0946)C(0010-0080)}"
    pydpm transpile "{T(C_01.00)R(0100)C(0010)} + {T(C_01.00)R(0200)C(0010)}" --analyze
    pydpm transpile "{T(C_01.00)R(0100)C(0010)} * 2" --no-optimize
    """
    
    optimize = not no_optimize
    
    console.print(f"[bold blue]SUBA to DPM-XL Transpiler[/bold blue]")
    console.print(f"Input SUBA: [cyan]{suba_expression}[/cyan]")
    console.print(f"Optimization: [green]{'Enabled' if optimize else 'Disabled'}[/green]")
    console.print()

    try:
        # Create transpiler
        transpiler = SubaToDpmXlTranspiler(optimize=optimize)
        
        # Validate SUBA expression
        if not transpiler.validate_suba(suba_expression):
            console.print("[bold red]❌ Error: Invalid SUBA syntax[/bold red]")
            return 1

        # Transpile
        dpm_xl_result = transpiler.transpile(suba_expression)
        console.print(f"Generated DPM-XL: [green]{dpm_xl_result}[/green]")

        # Analysis if requested
        if analyze:
            console.print()
            console.print("[bold]Expression Analysis:[/bold]")
            
            # Create analysis table
            table = Table(title="SUBA Expression Analysis")
            table.add_column("Metric", style="cyan", no_wrap=True)
            table.add_column("Value", style="magenta")
            
            analysis = TranspilerUtils.analyze_expression(suba_expression, is_suba=True)
            table.add_row("Valid", "✅ Yes" if analysis['valid'] else "❌ No")
            table.add_row("AST Type", analysis['ast_type'] or "N/A")
            table.add_row("Complexity", str(analysis['complexity']))
            table.add_row("Table References", ", ".join(analysis['table_references']) or "None")
            table.add_row("Operations", ", ".join(analysis['operations']) or "None")
            
            console.print(table)
        
        console.print()
        console.print("[bold green]✅ Transpilation successful![/bold green]")
        return 0
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {str(e)}[/bold red]")
        if analyze:
            console.print()
            console.print("[dim]Error details:[/dim]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1


@main.command()
@click.argument('suba_expression', type=str)
def validate_suba(suba_expression: str):
    """
    Validate SUBA expression syntax without transpiling.
    
    SUBA_EXPRESSION: The SUBA expression to validate.
    
    Examples:
    \b
    pydpm validate-suba "{T(C_01.00)R(0100)C(0010)} + {T(C_01.00)R(0200)C(0010)}"
    """

    console.print(f"[bold blue]SUBA Syntax Validator[/bold blue]")
    console.print(f"Validating: [cyan]{suba_expression}[/cyan]")
    console.print()

    try:
        transpiler = SubaToDpmXlTranspiler()
        
        if transpiler.validate_suba(suba_expression):
            console.print("[bold green]✅ SUBA syntax is valid[/bold green]")
            
            # Show basic analysis
            analysis = TranspilerUtils.analyze_expression(suba_expression, is_suba=True)
            console.print(f"Complexity: [yellow]{analysis['complexity']}[/yellow]")
            console.print(f"Table References: [blue]{', '.join(analysis['table_references']) or 'None'}[/blue]")
            console.print(f"Operations: [magenta]{', '.join(analysis['operations']) or 'None'}[/magenta]")

            return 0
        else:
            console.print("[bold red]❌ SUBA syntax is invalid[/bold red]")
            return 1

    except Exception as e:
        console.print(f"[bold red]❌ Validation error: {str(e)}[/bold red]")
        return 1


@main.command()
@click.argument('dpm_xl_expression', type=str)
@click.option('--analyze', is_flag=True, help='Show detailed expression analysis')
def reverse_transpile(dpm_xl_expression: str, analyze: bool):
    """
    Reverse transpile a DPM-XL expression to SUBA.
    
    DPM_XL_EXPRESSION: The DPM-XL expression to transpile.

    Examples:
    \b
    pydpm reverse-transpile "with {tC_17.01.a, c0010-0080}: {r0940} = {r0945} + {r0946}"
    pydpm reverse-transpile "{tC_01.00, r0100, c0010} + {tC_02.00, r0200, c0020}" --analyze
    """
    
    console.print(f"[bold blue]DPM-XL to SUBA Transpiler[/bold blue]")
    console.print(f"Input DPM-XL: [cyan]{dpm_xl_expression}[/cyan]")
    console.print()
    
    try:
        # Create reverse transpiler
        reverse_transpiler = DpmXlToSubaTranspiler()
        
        # Validate DPM-XL expression
        if not reverse_transpiler.validate_dpm_xl(dpm_xl_expression):
            console.print("[bold red]❌ Error: Invalid DPM-XL syntax[/bold red]")
            return 1

        # Transpile
        suba_result = reverse_transpiler.transpile(dpm_xl_expression)
        console.print(f"Generated SUBA: [green]{suba_result}[/green]")

        # Analysis if requested
        if analyze:
            console.print()
            console.print("[bold]Expression Analysis:[/bold]")
            
            # Create analysis table
            table = Table(title="DPM-XL Expression Analysis")
            table.add_column("Metric", style="cyan", no_wrap=True)
            table.add_column("Value", style="magenta")
            
            analysis = TranspilerUtils.analyze_expression(dpm_xl_expression, is_suba=False)
            table.add_row("Valid", "✅ Yes" if analysis['valid'] else "❌ No")
            table.add_row("AST Type", analysis['ast_type'] or "N/A")
            table.add_row("Complexity", str(analysis['complexity']))
            table.add_row("Table References", ", ".join(analysis['table_references']) or "None")
            table.add_row("Operations", ", ".join(analysis['operations']) or "None")
            
            console.print(table)
        
        console.print()
        console.print("[bold green]✅ Reverse transpilation successful![/bold green]")
        return 0
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {str(e)}[/bold red]")
        if analyze:
            console.print()
            console.print("[dim]Error details:[/dim]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1


@main.command()
@click.argument('dpm_xl_expression', type=str)
def validate_dpm_xl(dpm_xl_expression: str):
    """
    Validate DPM-XL expression syntax without transpiling.

    DPM_XL_EXPRESSION: The DPM-XL expression to validate.

    Examples:
    \b
    pydpm validate-dpm-xl "with {tC_01.00, c0010}: {r0100} + {r0200}"
    """
    
    console.print(f"[bold blue]DPM-XL Syntax Validator[/bold blue]")
    console.print(f"Validating: [cyan]{dpm_xl_expression}[/cyan]")
    console.print()

    try:
        reverse_transpiler = DpmXlToSubaTranspiler()
        
        if reverse_transpiler.validate_dpm_xl(dpm_xl_expression):
            console.print("[bold green]✅ DPM-XL syntax is valid[/bold green]")
            
            # Show basic analysis
            analysis = TranspilerUtils.analyze_expression(dpm_xl_expression, is_suba=False)
            console.print(f"Complexity: [yellow]{analysis['complexity']}[/yellow]")
            console.print(f"Table References: [blue]{', '.join(analysis['table_references']) or 'None'}[/blue]")
            console.print(f"Operations: [magenta]{', '.join(analysis['operations']) or 'None'}[/magenta]")
            
            return 0
        else:
            console.print("[bold red]❌ DPM-XL syntax is invalid[/bold red]")
            return 1
            
    except Exception as e:
        console.print(f"[bold red]❌ Validation error: {str(e)}[/bold red]")
        return 1


@main.command()
def transpiler_info():
    """Show information about the SUBA to DPM-XL transpiler."""
    
    console.print("[bold blue]SUBA to DPM-XL Transpiler Information[/bold blue]")
    console.print()
    
    # Create info table
    table = Table(title="Transpiler Features")
    table.add_column("Feature", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")
    table.add_column("Status", style="magenta", justify="center")
    
    table.add_row("SUBA Parsing", "Parse SUBA expressions using ANTLR4 grammar", "✅ Ready")
    table.add_row("AST Generation", "Convert to shared AST representation", "✅ Ready")
    table.add_row("DPM-XL Generation", "Generate DPM-XL code from AST", "✅ Ready")
    table.add_row("WITH Optimization", "Extract common table/column references", "✅ Ready")
    table.add_row("Expression Analysis", "Complexity and structure analysis", "✅ Ready")
    table.add_row("Syntax Validation", "Validate SUBA expressions", "✅ Ready")
    table.add_row("Error Handling", "Comprehensive error reporting", "✅ Ready")
    table.add_row("Reverse Transpilation", "DPM-XL to SUBA conversion", "✅ Ready")

    console.print(table)
    console.print()

    # Examples table
    examples_table = Table(title="Usage Examples")
    examples_table.add_column("Command", style="cyan")
    examples_table.add_column("Description", style="yellow")

    examples_table.add_row(
        'pydpm transpile "{T(C_01.00)R(0100)C(0010)} + {T(C_01.00)R(0200)C(0010)}"',
        "Basic transpilation with optimization"
    )
    examples_table.add_row(
        'pydpm transpile "expression" --analyze',
        "Transpile with detailed analysis"
    )
    examples_table.add_row(
        'pydpm transpile "expression" --no-optimize',
        "Transpile without WITH optimization"
    )
    examples_table.add_row(
        'pydpm validate-suba "expression"',
        "Validate SUBA syntax only"
    )
    examples_table.add_row(
        'pydpm reverse-transpile "dpm_xl_expression"',
        "Convert DPM-XL to SUBA"
    )
    examples_table.add_row(
        'pydpm validate-dpm-xl "dpm_xl_expression"',
        "Validate DPM-XL syntax only"
    )

    console.print(examples_table)
    console.print()

    # Test cases
    console.print("[bold]Test Cases:[/bold]")
    console.print("1. EGDQ_0507: Complex expression with optimization")
    console.print("   [dim]SUBA:[/dim] {T(C_17.01.a)R(0940)C(0010-0080)} = {T(C_17.01.a)R(0945)C(0010-0080)} + {T(C_17.01.a)R(0946)C(0010-0080)}")
    console.print("   [dim]DPM-XL:[/dim] with {tC_17.01.a, c0010-0080}: {r0940} = {r0945} + {r0946}")
    console.print()
    console.print("2. Simple arithmetic with shared table:")
    console.print("   [dim]SUBA:[/dim] {T(C_01.00)R(0100)C(0010)} + {T(C_01.00)R(0200)C(0010)}")
    console.print("   [dim]DPM-XL:[/dim] with {tC_01.00, c0010}: {r0100} + {r0200}")
    console.print()
    console.print("3. DATETIME function support:")
    console.print("   [dim]SUBA:[/dim] {T(C_14.00)R(*)C(0120)} > DATETIME('01-01-2019')")
    console.print("   [dim]DPM-XL:[/dim] {tC_14.00, r*, c0120} > #01-01-2019#")


if __name__ == '__main__':
    main()