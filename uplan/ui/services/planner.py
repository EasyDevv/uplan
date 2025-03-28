"""Planning service for handling plan generation requests."""

from pathlib import Path
from nicegui import ui

from uplan.utils.provider import check_model_support
from uplan.ui.services.llm import LLMService
from uplan.ui.state import AppState


class PlannerService:
    """Service for handling plan generation."""

    def __init__(self, state: AppState, llm_service: LLMService):
        """Initialize the planner service.

        Args:
            state: Application state instance
            llm_service: LLM service instance
        """
        self.state = state
        self.llm_service = llm_service

    async def generate_plan(
        self,
        model: str,
        category: str,
        input_folder: str,
        output_folder: str,
        retry_count: int,
        stream_handler: callable | None = None,
    ) -> tuple[bool, str]:
        """Generate a plan using the provided parameters.

        Args:
            model: Model name to use
            category: Category for input/output paths
            input_folder: Base input folder path
            output_folder: Base output folder path
            retry_count: Maximum number of retries
            stream_handler: Optional callback for handling stream updates

        Returns:
            A tuple of (success, message)
        """
        try:
            # Validate model
            is_supported, message = check_model_support(model)
            if not is_supported:
                return False, message

            # Get questions store
            questions_store = getattr(ui.page, "_storage", {}).get("questions_store")
            if not questions_store:
                return False, "No questions data available"

            # Set state values
            self.state.input_path = str(Path(input_folder) / category)
            self.state.output_path = str(Path(output_folder) / category)
            self.state.model = model
            self.state.retry = retry_count

            # Process with LLM service
            await self.llm_service.process_request(stream_handler=stream_handler)

            if self.state.error_message:
                return False, self.state.error_message

            return True, "Plan and todo generated successfully"

        except Exception as e:
            return False, f"Error: {str(e)}"
