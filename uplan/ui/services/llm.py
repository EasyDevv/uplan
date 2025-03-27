"""Service for handling LLM interactions in the GUI."""

import asyncio
from pathlib import Path

from uplan.process import get_all
from uplan.ui.state import AppState


class LLMService:
    """Service for handling LLM interactions.

    Wraps the synchronous LLM processing functions in asynchronous methods
    suitable for use with NiceGUI.
    """

    def __init__(self, state: AppState):
        """Initialize the LLM service.

        Args:
            state: Application state instance
        """
        self.state = state

    async def process_request(self) -> None:
        """Process the LLM request asynchronously."""
        try:
            self.state.processing = True
            self.state.error_message = None

            # Run the synchronous process in a thread pool
            plan_response, todo_response = await asyncio.to_thread(
                get_all,
                Path("./input"),
                self.state.output_path,
                self.state.model,
                5,  # Default retry count
            )

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
