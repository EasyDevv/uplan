"""Main GUI entry point for uplan.

Provides the GUI interface through NiceGUI framework.
"""

from nicegui import ui

from uplan.app import create_app


# Create application instance
app = create_app()


def init_gui() -> None:
    """Initialize the GUI interface.

    Sets up the UI components using centralized application instance.
    """
    # Run GUI with default configuration
    app.run_gui()


def main():
    """Main entry point for the GUI application."""
    init_gui()


if __name__ in {"__main__", "__mp_main__"}:
    main()
