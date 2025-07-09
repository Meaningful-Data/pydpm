import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from py_dpm.api import API

console = Console()

@click.group()
@click.version_option()
def main():
    """pyDPM CLI - A command line interface for pyDPM"""
    pass

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