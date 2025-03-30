"""CLI functionality for UPlan (subsidiary to GUI mode)."""

import click
from pathlib import Path
from rich import print

from uplan.app import create_app
from uplan.features.forms.initializer import initialize
from uplan.features.llm.processor import get_all, get_plan, get_todo

# Create app instance
app = create_app()


def common_options(f):
    """Common click options for all commands."""
    f = click.option(
        "--model",
        "-m",
        default="gpt-3.5-turbo",
        help="Model to use",
    )(f)
    f = click.option(
        "--category",
        "-c",
        default="dev",
        help="Form category",
    )(f)
    f = click.option(
        "--input",
        "-i",
        default="./input",
        help="Input folder",
    )(f)
    f = click.option(
        "--output",
        "-o",
        default="./output",
        help="Output folder",
    )(f)
    f = click.option(
        "--retry",
        "-r",
        default=3,
        help="Number of retries",
    )(f)
    return f


@click.group(invoke_without_command=True)
@common_options
@click.pass_context
def cli(ctx, **kwargs):
    """UPlan - Command Line Interface (subsidiary to GUI)"""
    if ctx.invoked_subcommand is None:
        # Validate model
        if not app.validate_model(kwargs["model"]):
            return

        # Setup folders
        input_folder, output_folder = app.setup_folders(
            kwargs["input"], kwargs["output"], kwargs["category"]
        )

        if not input_folder.exists():
            initialize(form_dir=kwargs["category"])

        # Run both plan and todo
        plan_response, todo_response = get_all(
            input_folder, output_folder, kwargs["model"], kwargs["retry"]
        )
        if plan_response.get("status") in ["exit", "error"]:
            return
        if todo_response.get("status") == "error":
            print("[red]Failed to complete the process[/red]")
            return


@cli.command()
@common_options
def plan(**kwargs):
    """Generate plan only"""
    if not app.validate_model(kwargs["model"]):
        return

    input_folder, output_folder = app.setup_folders(
        kwargs["input"], kwargs["output"], kwargs["category"]
    )

    if not input_folder.exists():
        initialize(form_dir=kwargs["category"])

    response = get_plan(input_folder, output_folder, kwargs["model"], kwargs["retry"])
    if response.get("status") in ["exit", "error"]:
        return


@cli.command()
@common_options
def todo(**kwargs):
    """Generate todo only"""
    if not app.validate_model(kwargs["model"]):
        return

    input_folder, output_folder = app.setup_folders(
        kwargs["input"], kwargs["output"], kwargs["category"]
    )

    if not input_folder.exists():
        initialize(form_dir=kwargs["category"])

    response = get_todo(input_folder, output_folder, kwargs["model"], kwargs["retry"])
    if response.get("status") == "error":
        print("[red]Failed to process todo[/red]")
        return


@cli.command()
@click.argument("form", default="dev")
@click.option("--force", is_flag=True, help="Force overwrite")
@common_options
def init(form, force, **kwargs):
    """Initialize form"""
    initialize(force=force, form_dir=form)


if __name__ == "__main__":
    cli()
