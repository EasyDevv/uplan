import click
from pathlib import Path

from rich import print

from uplan.app import create_app
from uplan.init import initialize
from uplan.process import get_all, get_plan, get_todo


# Create app instance
app = create_app()


def common_options(f):
    """Common click options for all commands."""
    options = [
        click.option("--model", default="ollama/qwq", help="LLM model to use"),
        click.option(
            "--retry", default=5, type=int, help="Max retries for LLM requests"
        ),
        click.option("--category", default="dev", help="form category"),
        click.option("--input", default="./input", help="Input folder"),
        click.option("--output", default="./output", help="Output folder"),
    ]
    for option in reversed(options):
        f = option(f)
    return f


@click.group(invoke_without_command=True)
@common_options
@click.pass_context
def cli(ctx, **kwargs):
    """Plan and Todo Manager"""
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


def main():
    """Main entry point for the application."""
    app.run_cli()


if __name__ == "__main__":
    main()
