"""Core application class for UPlan.

Provides centralized initialization and service management for both CLI and GUI modes.
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


class UPlanApp:
    """Central application class managing both CLI and GUI modes."""

    def __init__(self):
        """Initialize the UPlan application."""
        self.state = AppState.get_instance()
        self.services: Dict[str, Any] = {}
        self._initialize_services()

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

        # Register services with NiceGUI app for GUI mode
        if not hasattr(nicegui_app, "services"):
            nicegui_app.services = {}
        nicegui_app.services.update(self.services)

    def setup_folders(
        self, input_root: str, output_root: str, category: str
    ) -> tuple[Path, Path]:
        """Setup and validate input/output folders.

        Args:
            input_root: Root directory for input files
            output_root: Root directory for output files
            category: Form category name

        Returns:
            Tuple of (input_folder, output_folder) Paths
        """
        input_folder = Path(input_root) / category
        output_folder = Path(output_root) / category

        output_folder.mkdir(parents=True, exist_ok=True)
        return input_folder, output_folder

    def validate_model(self, model_name: str) -> bool:
        """Validate the specified LLM model.

        Args:
            model_name: Name of the model to validate

        Returns:
            True if model is valid, False otherwise
        """
        success, message = check_model_support(model_name)
        return success

    def run_cli(self, **options) -> None:
        """Run the application in CLI mode.

        Args:
            **options: CLI options including model, retry count, etc.
        """
        from uplan.main import cli

        cli.main(standalone_mode=False, **options)

    def run_gui(self, **options) -> None:
        """Run the application in GUI mode.

        Args:
            **options: GUI options including title, theme, etc.
        """
        # Setup environment
        setup_env()

        # Create UI layout
        create_main_layout(self.state)

        # Run NiceGUI app
        ui.run(
            title=options.get("title", "UPlan"),
            favicon=options.get("favicon", "✅"),
            reload=options.get("reload", True),
            show=options.get("show", False),
            dark=options.get("dark", True),
        )


def create_app() -> UPlanApp:
    """Create and configure the UPlan application.

    Returns:
        Configured UPlanApp instance
    """
    return UPlanApp()
