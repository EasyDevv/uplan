"""Service for handling LLM interactions in the GUI."""

import asyncio
from pathlib import Path
from typing import Callable, Optional

from uplan.process import get_all
from uplan.ui.state import AppState


class LLMService:
    """Service for handling LLM interactions.

    Wraps the LLM processing functions in asynchronous methods
    suitable for use with NiceGUI.
    """

    def __init__(self, state: AppState):
        """Initialize the LLM service.

        Args:
            state: Application state instance
        """
        self.state = state
        self._current_task: Optional[asyncio.Task] = None

    async def _reset_state(self) -> None:
        """Reset processing state."""
        self.state.processing = False
        self.state.stream_controller.reset()

    async def process_request(
        self,
        stream_handler: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Process the LLM request asynchronously.

        Args:
            stream_handler: Optional callback for handling streaming updates
        """
        try:
            await self._reset_state()
            self.state.processing = True
            self.state.error_message = None

            # Use stream_controller to run the task
            try:
                (
                    plan_response,
                    todo_response,
                ) = await self.state.stream_controller.run_cancellable(
                    get_all(
                        input_folder=Path(self.state.input_path),
                        output_folder=Path(self.state.output_path),
                        model=self.state.model,
                        retry=5,
                        stream_handler=stream_handler,
                        stream_controller=self.state.stream_controller,
                    )
                )
            except asyncio.CancelledError:
                self.state.error_message = "Request was cancelled"
                return

            if plan_response.get("status") in ["exit", "error"]:
                self.state.error_message = "Failed to generate plan"
                return

            if todo_response.get("status") == "error":
                self.state.error_message = "Failed to generate todo"
                return

            # Update state with response data
            self.state.llm_response = {
                "plan": plan_response.get("data", {}),
                "todo": todo_response.get("data", {}),
            }

        except Exception as e:
            self.state.error_message = f"Error: {str(e)}"
        finally:
            self.state.processing = False
            self._current_task = None
