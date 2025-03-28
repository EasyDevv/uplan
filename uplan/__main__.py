"""Main entry point for the uplan package."""

import sys

from uplan.app import create_app


def main():
    """Main entry point for the application - defaults to GUI mode."""
    app = create_app()

    # Check if CLI mode is specifically requested via command line args
    if len(sys.argv) > 1 and sys.argv[1] in ["plan", "todo", "init"]:
        app.run_cli()
    else:
        # Default to GUI mode
        app.run_gui()


if __name__ == "__main__":
    main()
