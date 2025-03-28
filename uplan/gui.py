"""Main GUI entry point for uplan.

Initializes the application with centralized state management.
"""

from nicegui import app, ui

from uplan.ui.layouts.main import create_main_layout
from uplan.ui.services.llm import LLMService
from uplan.ui.services.state_service import StateService
from uplan.ui.state import AppState
from uplan.utils.provider import setup_env


def init_app() -> None:
    """Initialize the NiceGUI application.

    Sets up the application state, services, and UI components.
    Implements centralized state management through StateService.
    """
    # Initialize environment
    setup_env()

    # Setup services with singleton state
    # Initialize services dictionary if it doesn't exist
    if not hasattr(app, "services"):
        app.services = {}

    # Create and register services
    state_service = StateService()  # This creates/gets AppState singleton
    llm_service = LLMService(state_service.state)
    app.services.update({"state": state_service, "llm": llm_service})

    # Create UI layout
    create_main_layout(state_service.state)


def main():
    """Main entry point for the GUI application."""
    init_app()
    ui.run(
        title="UPlan",
        favicon="✅",
        reload=True,
        show=False,
        dark=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
