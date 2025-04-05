"""CLI functionality for UPlan (subsidiary to GUI mode)."""

import click
from pathlib import Path
from rich import print

from uplan.app import UplanApp  # App 클래스를 직접 임포트
from uplan.init import initialize
from uplan.process import get_all, get_plan, get_todo

# App 인스턴스 생성 (CLI 모드에서 필요시 생성하도록 변경 가능)
# 여기서는 각 커맨드에서 필요시 App 인스턴스를 생성하거나
# 공유 인스턴스를 사용하는 방식으로 변경할 수 있습니다.
# 우선은 기존 구조를 유지하되, App 클래스를 직접 사용합니다.


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
    app = UplanApp()  # CLI 실행 시 App 인스턴스 생성
    if ctx.invoked_subcommand is None:
        # Validate model
        if not app.validate_model(kwargs["model"]):
            return

        # Setup folders
        input_folder, output_folder = app.setup_folders(
            kwargs["input"], kwargs["output"], kwargs["category"]
        )

        if not input_folder.exists():
            print(
                f"[yellow]Input folder '{input_folder}' not found. Initializing default form...[/yellow]"
            )
            initialize(form_dir=kwargs["category"])
            # 다시 폴더 존재 여부 확인 또는 에러 처리 필요

        # Run both plan and todo
        plan_response, todo_response = get_all(
            input_folder, output_folder, kwargs["model"], kwargs["retry"]
        )
        if plan_response.get("status") in ["exit", "error"]:
            print(
                f"[red]Plan generation failed or exited: {plan_response.get('message', '')}[/red]"
            )
            return
        if todo_response.get("status") == "error":
            print(
                f"[red]Todo generation failed: {todo_response.get('message', '')}[/red]"
            )
            return
        print("[green]Plan and Todo generation completed successfully.[/green]")


@cli.command()
@common_options
def plan(**kwargs):
    """Generate plan only"""
    app = UplanApp()
    if not app.validate_model(kwargs["model"]):
        return

    input_folder, output_folder = app.setup_folders(
        kwargs["input"], kwargs["output"], kwargs["category"]
    )

    if not input_folder.exists():
        print(
            f"[yellow]Input folder '{input_folder}' not found. Initializing default form...[/yellow]"
        )
        initialize(form_dir=kwargs["category"])

    response = get_plan(input_folder, output_folder, kwargs["model"], kwargs["retry"])
    if response.get("status") in ["exit", "error"]:
        print(
            f"[red]Plan generation failed or exited: {response.get('message', '')}[/red]"
        )
        return
    print("[green]Plan generation completed successfully.[/green]")


@cli.command()
@common_options
def todo(**kwargs):
    """Generate todo only"""
    app = UplanApp()
    if not app.validate_model(kwargs["model"]):
        return

    input_folder, output_folder = app.setup_folders(
        kwargs["input"], kwargs["output"], kwargs["category"]
    )

    if not input_folder.exists():
        print(
            f"[yellow]Input folder '{input_folder}' not found. Initializing default form...[/yellow]"
        )
        initialize(form_dir=kwargs["category"])

    response = get_todo(input_folder, output_folder, kwargs["model"], kwargs["retry"])
    if response.get("status") == "error":
        print(f"[red]Todo generation failed: {response.get('message', '')}[/red]")
        return
    print("[green]Todo generation completed successfully.[/green]")


@cli.command()
@click.argument("form", default="dev")
@click.option("--force", is_flag=True, help="Force overwrite")
def init(form, force):
    """Initialize form"""
    # common_options에서 input/output 폴더를 사용하지 않으므로 kwargs 제거
    initialize(force=force, form_dir=form)
    print(f"[green]Form '{form}' initialized successfully.[/green]")


# if __name__ == "__main__": 제거 -> uplan/__main__.py 에서 호출
