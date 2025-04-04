"""Service for handling interactions with the Language Model."""

from typing import Optional

from uplan.ui.state import AppState
from uplan.utils.logging import get_logger, trace

# Import StreamService for type hinting
from uplan.services.stream_service import StreamService
# Add necessary imports from uplan.process or other relevant modules later

logger = get_logger()


class LLMService:
    """Manages LLM requests and processing."""

    def __init__(self, state: AppState, stream_service: StreamService):
        """Initialize the LLMService.

        Args:
            state: The application state instance.
            stream_service: The stream service instance for potential interaction.
        """
        self.state = state
        self.stream_service = stream_service  # Store stream_service instance
        logger.info("LLMService initialized.")

    @trace
    async def process_request(self) -> Optional[str]:
        """Processes the LLM request based on the current application state.

        Handles model selection, prompt generation, API calls, and returns a stream ID.

        Returns:
            The stream ID if the request was successful, otherwise None.
        """
        logger.info(
            "Processing LLM request",
            extra={
                "provider": self.state.provider,
                "model": self.state.model,
                "category": self.state.category,
                "input_path": self.state.input_path,
                "output_path": self.state.output_path,
                "max_retries": self.state.max_retries,
                "operation_type": self.state.operation_type,
            },
        )

        # --- Placeholder for actual LLM interaction logic ---
        # This logic will be moved from options.py and potentially process.py
        # It should use self.state attributes (provider, model, etc.)
        # Example:
        # stream_id = await some_llm_api_call(
        #     provider=self.state.provider,
        #     model=self.state.model,
        #     input_data=..., # Prepare input based on state
        #     operation=self.state.operation_type,
        # )
        # For now, return a dummy value or None
        stream_id = (
            f"dummy_stream_{self.state.operation_type}"  # Replace with actual call
        )
        logger.info(f"LLM request processed, returning stream ID: {stream_id}")
        # -----------------------------------------------------

        return stream_id

    # Add stop_stream method if needed, potentially interacting with StreamService or state
    # async def stop_stream(self, stream_id: str): ...
