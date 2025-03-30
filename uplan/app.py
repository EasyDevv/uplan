"""Core application class for UPlan.

Provides centralized initialization with GUI as primary and CLI as secondary mode.
"""

from pathlib import Path
from typing import Any, Dict

from nicegui import app as nicegui_app, ui

from uplan.ui.layouts.main import create_main_layout
from uplan.ui.services.llm import LLMService
from uplan.ui.services.state_service import StateService
from uplan.ui.services.stream_service import StreamService
from uplan.ui.state import AppState
from uplan.utils.provider import check_model_support, setup_env


class App:
    """Central application class with GUI as primary and CLI as secondary mode."""

    def __init__(self):
        """Initialize the UPlan application with GUI focus."""
        self.state = AppState.get_instance()
        self.services: Dict[str, Any] = {}
        self._initialize_services()

        # Setup environment by default
        setup_env()

    def _initialize_services(self) -> None:
        """Initialize and register core services."""
        # Setup base services
        state_service = StateService()
        stream_service = StreamService(self.state.stream_controller)
        llm_service = LLMService(self.state, stream_service)

        # Register services
        self.services.update(
            {"state": state_service, "stream": stream_service, "llm": llm_service}
        )

        # Register services with NiceGUI app
        if not hasattr(nicegui_app, "services"):
            nicegui_app.services = {}
        nicegui_app.services.update(self.services)

    def setup_folders(
        self, input_root: str, output_root: str, category: str
    ) -> tuple[Path, Path]:
        """Setup and validate input/output folders."""
        input_folder = Path(input_root) / category
        output_folder = Path(output_root) / category

        output_folder.mkdir(parents=True, exist_ok=True)
        return input_folder, output_folder

    def validate_model(self, model_name: str) -> bool:
        """Validate the specified LLM model."""
        success, _ = check_model_support(model_name)
        return success

    def run_gui(self, **options) -> None:
        """Run the application in GUI mode (primary mode)."""
        # Create UI layout
        create_main_layout(self.state)

        # Run NiceGUI app with sensible defaults
        ui.run(
            title=options.get("title", "UPlan"),
            favicon=options.get("favicon", "✅"),
            reload=options.get("reload", True),
            show=options.get("show", False),
            dark=options.get("dark", True),
        )

    def run_cli(self) -> None:
        """Run the application in CLI mode (subsidiary mode)."""
        from uplan.main import cli

        cli()


def init_gui() -> None:
    """Initialize the GUI interface.

    Sets up the UI components using centralized application instance.
    """
    # Create application instance
    app = App()

    # Run GUI with default configuration
    app.run_gui()


def main():
    """Main entry point for the GUI application."""
    init_gui()


if __name__ in {"__main__", "__mp_main__"}:
    main()
