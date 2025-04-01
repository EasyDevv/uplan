"""Main entry point for the uplan package."""

import sys

# Import the factory function to create the App instance
from uplan.app import App


def main():
    """Main entry point for the application.

    Determines whether to run in GUI or CLI mode based on command-line arguments.
    - No arguments: Runs GUI mode.
    - Any arguments: Runs CLI mode (delegating argument parsing to click).
    """
    app = App()

    # Check the number of command-line arguments
    if len(sys.argv) == 1:
        # No arguments provided, default to GUI mode
        print("Starting UPlan in GUI mode...")
        app.run_gui()
    else:
        # Arguments provided, run in CLI mode
        # The uplan.cli.main module (invoked via app.run_cli) will handle
        # argument parsing using click.
        print("Starting UPlan in CLI mode...")
        app.run_cli()


if __name__ in {"__main__", "__mp_main__"}:
    main()
