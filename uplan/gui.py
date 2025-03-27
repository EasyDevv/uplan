"""Main GUI entry point for uplan."""

from nicegui import app, ui

from uplan.ui.layouts.main import create_main_layout
from uplan.ui.services.llm import LLMService
from uplan.ui.state import AppState
from uplan.utils.provider import setup_env


def init_app() -> None:
    """Initialize the NiceGUI application.

    Sets up the application state, services, and UI components.
    """
    # Initialize environment
    setup_env()

    # Setup application state
    state = AppState()

    # Initialize services
    llm_service = LLMService(state)

    # Create UI layout
    create_main_layout(state)

    # Make services available to UI components
    app.services = {"llm": llm_service}


def main():
    """Main entry point for the GUI application."""
    init_app()
    ui.run(
        title="UPlan",
        host="127.0.0.1",
        port=8080,
        reload=True,
        show=False,
        dark=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
