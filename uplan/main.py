import argparse
from pathlib import Path

from rich import print

from uplan.init import initialize
from uplan.process import get_all, get_plan, get_todo
from uplan.utils.provider import check_model_support, setup_env


def setup_folders(
    input_root: str, output_root: str, category: str
) -> tuple[Path, Path]:
    """Setup and validate input/output folders."""
    input_folder = Path(input_root) / category
    output_folder = Path(output_root) / category

    if not input_folder.exists():
        initialize(template_dir=category)

    output_folder.mkdir(parents=True, exist_ok=True)
    return input_folder, output_folder


def setup_base_parser() -> argparse.ArgumentParser:
    """Create base parser with common arguments."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--model", type=str, default="ollama/qwq", help="LLM model to use"
    )
    parser.add_argument(
        "--retry", type=int, default=5, help="Max retries for LLM requests"
    )
    parser.add_argument("--category", type=str, default="dev", help="Template category")
    parser.add_argument("--input", type=str, default="./input", help="Input folder")
    parser.add_argument("--output", type=str, default="./output", help="Output folder")
    return parser


def main():
    base_parser = setup_base_parser()
    parser = argparse.ArgumentParser(
        description="Plan and Todo Manager", parents=[base_parser]
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Initialize subparsers with parent arguments
    subparsers.add_parser(
        "plan",
        help="Generate plan only",
        parents=[base_parser],
    )
    subparsers.add_parser(
        "todo",
        help="Generate todo only",
        parents=[base_parser],
    )
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize template",
        parents=[base_parser],
    )
    init_parser.add_argument("template", nargs="?", default="dev", help="Template name")
    init_parser.add_argument("--force", action="store_true", help="Force overwrite")

    args = parser.parse_args()

    if args.command == "init":
        initialize(force=args.force, template_dir=args.template)
        return

    # Setup environment and validate model
    success, message = check_model_support(args.model)
    print(message)
    if not success:
        return

    setup_env()

    # Setup folders
    input_folder, output_folder = setup_folders(args.input, args.output, args.category)

    # Execute commands based on arguments
    if args.command == "plan":
        response = get_plan(input_folder, output_folder, args.model, args.retry)
        if response.get("status") in ["exit", "error"]:
            return
    elif args.command == "todo":
        response = get_todo(input_folder, output_folder, args.model, args.retry)
        if response.get("status") == "error":
            print("[red]Failed to process todo[/red]")
            return
    else:
        # Default behavior: run both
        plan_response, todo_response = get_all(
            input_folder, output_folder, args.model, args.retry
        )
        if plan_response.get("status") in ["exit", "error"]:
            return
        if todo_response.get("status") == "error":
            print("[red]Failed to complete the process[/red]")
            return


if __name__ == "__main__":
    main()
