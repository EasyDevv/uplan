"""Core application class for UPlan.

Provides centralized initialization with GUI as primary and CLI as secondary mode.
"""

import os
from pathlib import Path
from typing import Any, Dict

from nicegui import app as nicegui_app, ui

from uplan.ui.layouts.main import create_main_layout

# Updated import paths for services
from uplan.services.llm_service import LLMService
from uplan.services.stream_service import StreamService

# StateService seems specific to UI state management, keep its location or refactor if needed.
# Assuming StateService remains UI-specific for now.
from uplan.ui.services.state_service import StateService  # Keep original path for now
from uplan.ui.services.stream_service import StreamService
from uplan.ui.state import AppState
from uplan.utils.provider import check_model_support, setup_env


class App:
    """Central application class with GUI as primary and CLI as secondary mode."""

    def __init__(self):
        """Initialize the UPlan application with GUI focus."""
        self.state = AppState.get_instance()
        self.services: Dict[str, Any] = {}
        # Setup environment first
        setup_env()

        # Initialize configuration (forms, models) before starting services or UI
        # GUI 환경에서는 기본값으로 초기화 (force=False, form_dir='dev')
        # TODO: GUI 설정에서 form_dir 등을 선택할 수 있도록 기능 추가 고려
        # try:
        #     initialize()  # 기본값 사용
        # except Exception as e:
        #     # 초기화 실패 시 로깅 또는 사용자 알림 처리 필요
        #     # 여기서는 간단히 에러를 출력합니다. 실제 애플리케이션에서는 더 견고한 처리가 필요합니다.
        #     print(f"[ERROR] Failed to initialize application: {e}")
        #     # 초기화 실패 시 GUI 실행을 중단할 수도 있습니다.
        #     # raise SystemExit("Initialization failed, cannot start GUI.") from e

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
            reload=os.getenv("DEV", "false").lower() == "true",
            show=options.get("show", False),
            dark=options.get("dark", True),
        )

    def run_cli(self) -> None:
        """Run the application in CLI mode (subsidiary mode)."""
        # Import the CLI entry point from the new location
        from uplan.cli.main import cli

        # Execute the click group
        cli()


# if __name__ in {"__main__", "__mp_main__"}:
#     # This block might be removed if direct execution of app.py is not intended.
#     # For now, let's assume it might be used for GUI testing/dev.
#     temp_app = create_app()
#     temp_app.run_gui()  # Default to GUI if run directly
