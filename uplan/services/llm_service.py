"""Service for handling LLM interactions."""

import asyncio
from pathlib import Path
from typing import Callable, Optional

from uplan.process import get_all
from uplan.ui.state import AppState
from uplan.services.stream_service import StreamService
from uplan.utils.logging import get_logger, trace
from uplan.utils.reactive import ReactiveStream

logger = get_logger()


class LLMService:
    """Service for handling LLM interactions.

    Wraps the LLM processing functions in asynchronous methods.
    """

    def __init__(self, state: AppState, stream_service: StreamService):
        """Initialize the LLM service.

        Args:
            state: Application state instance
            stream_service: Service for managing streams
        """
        self.state = state
        self.stream_service = stream_service
        self._current_task: Optional[asyncio.Task] = None
        self._request_id = 0

    @trace
    async def _reset_state(self) -> None:
        """Reset processing state."""
        self.state.processing = False
        if hasattr(self.state, "stream_controller") and self.state.stream_controller:
            self.state.stream_controller.reset()
        else:
            raise AttributeError("StreamController not found on state during reset.")

    @trace
    async def process_request(self) -> str:
        """Process the LLM request asynchronously based on AppState.

        Returns:
            The stream ID that can be used to subscribe to updates
        """
        self._request_id += 1
        stream_id = f"llm_stream_{self._request_id}"
        stream = self.stream_service.create_stream(stream_id)

        async def stream_handler(text: str) -> None:
            await stream.push(text)

        self._current_task = asyncio.create_task(
            self._run_llm_process(stream, stream_handler, stream_id)
        )
        return stream_id

    @trace
    async def _run_llm_process(
        self,
        stream: ReactiveStream,
        stream_handler: Callable,
        stream_id: str,
    ) -> None:
        """Run the LLM process and handle streaming updates.

        Args:
            stream: Reactive stream for updates
            stream_handler: Callback for handling streaming updates
            stream_id: The ID of the stream being processed (for logging)
        """
        try:
            await self._reset_state()
            self.state.processing = True
            self.state.error_message = None

            if not all(
                [self.state.input_path, self.state.output_path, self.state.model]
            ):
                error_msg = (
                    f"Missing required state for LLM process on stream {stream_id}: "
                    "input_path, output_path, or model."
                )
                self.state.error_message = (
                    "Configuration error: Missing input/output path or model."
                )
                raise ValueError(error_msg)

            if (
                not hasattr(self.state, "stream_controller")
                or not self.state.stream_controller
            ):
                error_msg = (
                    f"StreamController not found in AppState for stream {stream_id}."
                )
                self.state.error_message = "Internal error: Stream controller missing."
                raise AttributeError(error_msg)

            try:
                results = await self.state.stream_controller.run_cancellable(
                    get_all(
                        input_folder=Path(self.state.input_path),
                        output_folder=Path(self.state.output_path),
                        model=self.state.model,
                        retry=self.state.max_retries,
                        stream_handler=stream_handler,
                        stream_controller=self.state.stream_controller,
                    )
                )
                plan_response, todo_response = (
                    results
                    if isinstance(results, tuple) and len(results) == 2
                    else ({}, {})
                )

            except asyncio.CancelledError:
                self.state.error_message = "Request was cancelled"
                return
            except Exception as proc_err:
                self.state.error_message = f"Processing Error: {str(proc_err)}"
                raise

            if plan_response.get("status") in ["exit", "error"]:
                error_msg = (
                    f"Failed to generate plan for stream {stream_id}. "
                    f"Status: {plan_response.get('status')}"
                )
                raise RuntimeError(error_msg)

            if todo_response.get("status") == "error":
                error_msg = (
                    f"Failed to generate todo for stream {stream_id}. "
                    f"Status: {todo_response.get('status')}"
                )
                raise RuntimeError(error_msg)

            self.state.llm_response = {
                "plan": plan_response.get("data", {}),
                "todo": todo_response.get("data", {}),
            }

        except Exception as e:
            raise RuntimeError(
                f"Unhandled error in LLM process for stream {stream_id}: {e}"
            )
        finally:
            self.state.processing = False
            self._current_task = None
            if stream:
                stream.complete()

    @trace
    async def cancel_current_request(self) -> None:
        """Cancels the currently running LLM process task."""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            try:
                await asyncio.wait_for(self._current_task, timeout=1.0)
            except asyncio.CancelledError:
                raise asyncio.CancelledError("LLM task successfully cancelled.")
            except asyncio.TimeoutError:
                raise asyncio.TimeoutError("LLM task did not cancel within timeout.")
            except Exception as e:
                raise RuntimeError(
                    f"Error encountered while waiting for LLM task cancellation: {e}"
                )
            finally:
                await self._reset_state()
                self._current_task = None
        else:
            if self.state.processing:
                await self._reset_state()
