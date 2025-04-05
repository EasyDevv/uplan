# uplan/services/llm_service.py
"""Service for handling LLM interactions."""

import asyncio
from pathlib import Path
from typing import Callable, Optional

# Potential issue: uplan.process might depend on UI state or services. Need to check.
# Assuming get_all is self-contained or only depends on core services/config.
from uplan.process import get_all
from uplan.ui.state import (
    AppState,
)  # Dependency on UI state - acceptable for now, but could be refactored later
from uplan.services.stream_service import (
    StreamService,
)  # Import the refactored StreamService
from uplan.utils.logging import get_logger, trace  # Added logging
from uplan.utils.reactive import ReactiveStream  # Added import

logger = get_logger()  # Added logger instance


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
        logger.info("LLMService initialized.")  # Added log

    @trace  # Added trace
    async def _reset_state(self) -> None:
        """Reset processing state."""
        self.state.processing = False
        # Assuming stream_controller is part of AppState or accessible via StreamService
        if hasattr(self.state, "stream_controller") and self.state.stream_controller:
            self.state.stream_controller.reset()
        else:
            logger.warning("StreamController not found on state during reset.")

    @trace  # Added trace
    async def process_request(self) -> str:
        """Process the LLM request asynchronously based on AppState.

        Returns:
            The stream ID that can be used to subscribe to updates
        """
        self._request_id += 1
        stream_id = f"llm_stream_{self._request_id}"
        # logger.info(
        #     f"Processing LLM request, creating stream: {stream_id}",
        #     extra={"stream_id": stream_id, "request_id": self._request_id},
        # )
        stream = self.stream_service.create_stream(stream_id)

        # Define the handler within the scope where 'stream' is available
        async def stream_handler(text: str) -> None:
            # logger.debug(f"Pushing chunk to stream {stream_id}", extra={"stream_id": stream_id}) # Can be noisy
            await stream.push(text)

        # logger.debug(
        #     f"Creating asyncio task for LLM process for stream {stream_id}",
        #     extra={"stream_id": stream_id},
        # )
        self._current_task = asyncio.create_task(
            self._run_llm_process(
                stream, stream_handler, stream_id
            )  # Pass stream_id for logging
        )
        return stream_id

    @trace  # Added trace
    async def _run_llm_process(
        self,
        stream: ReactiveStream,
        stream_handler: Callable,
        stream_id: str,  # Added stream_id type hint and param
    ) -> None:
        """Run the LLM process and handle streaming updates.

        Args:
            stream: Reactive stream for updates
            stream_handler: Callback for handling streaming updates
            stream_id: The ID of the stream being processed (for logging)
        """
        # logger.info(
        #     f"Starting LLM process for stream {stream_id}",
        #     extra={"stream_id": stream_id},
        # )
        try:
            # Reset state specific to this run
            await self._reset_state()  # Reset state at the beginning of the run
            self.state.processing = True
            self.state.error_message = None
            logger.debug(
                f"State reset and processing set to True for stream {stream_id}",
                extra={"stream_id": stream_id},
            )

            # Ensure necessary state attributes are set before calling get_all
            if not all(
                [self.state.input_path, self.state.output_path, self.state.model]
            ):
                error_msg = f"Missing required state for LLM process on stream {stream_id}: input_path, output_path, or model."
                logger.error(
                    error_msg,
                    extra={"stream_id": stream_id, "state": self.state.to_dict()},
                )  # Log relevant state
                self.state.error_message = (
                    "Configuration error: Missing input/output path or model."
                )
                raise ValueError(error_msg)  # Raise to stop processing

            # Use stream_controller from state to run the task
            if (
                not hasattr(self.state, "stream_controller")
                or not self.state.stream_controller
            ):
                error_msg = (
                    f"StreamController not found in AppState for stream {stream_id}."
                )
                logger.error(error_msg, extra={"stream_id": stream_id})
                self.state.error_message = "Internal error: Stream controller missing."
                raise AttributeError(error_msg)

            # logger.debug(
            #     f"Calling get_all for stream {stream_id}",
            #     extra={
            #         "stream_id": stream_id,
            #         "input": self.state.input_path,
            #         "output": self.state.output_path,
            #         "model": self.state.model,
            #     },
            # )
            try:
                # Assuming get_all is an async function
                results = await self.state.stream_controller.run_cancellable(
                    get_all(
                        input_folder=Path(self.state.input_path),
                        output_folder=Path(self.state.output_path),
                        model=self.state.model,
                        retry=self.state.max_retries,  # Use state value
                        stream_handler=stream_handler,
                        stream_controller=self.state.stream_controller,
                    )
                )
                # Assuming get_all returns a tuple (plan_response, todo_response)
                plan_response, todo_response = (
                    results
                    if isinstance(results, tuple) and len(results) == 2
                    else ({}, {})
                )
                # logger.info(
                #     f"get_all completed for stream {stream_id}",
                #     extra={
                #         "stream_id": stream_id,
                #         "plan_status": plan_response.get("status"),
                #         "todo_status": todo_response.get("status"),
                #     },
                # )

            except asyncio.CancelledError:
                logger.warning(
                    f"LLM process cancelled for stream {stream_id}",
                    extra={"stream_id": stream_id},
                )
                self.state.error_message = "Request was cancelled"
                # No need to raise again, finally block will handle cleanup
                return  # Exit after cancellation
            except Exception as proc_err:
                logger.exception(
                    f"Error during get_all execution for stream {stream_id}: {proc_err}",
                    extra={"stream_id": stream_id},
                )
                self.state.error_message = f"Processing Error: {str(proc_err)}"
                # Raise to be caught by the outer try/except
                raise

            # --- Process results ---
            if plan_response.get("status") in ["exit", "error"]:
                error_msg = f"Failed to generate plan for stream {stream_id}. Status: {plan_response.get('status')}"
                logger.error(
                    error_msg, extra={"stream_id": stream_id, "response": plan_response}
                )
                self.state.error_message = "Failed to generate plan"
                # Decide if this is a critical failure or if todo can still proceed
                # For now, let's stop if plan fails critically
                return

            if todo_response.get("status") == "error":
                error_msg = f"Failed to generate todo for stream {stream_id}. Status: {todo_response.get('status')}"
                logger.error(
                    error_msg, extra={"stream_id": stream_id, "response": todo_response}
                )
                self.state.error_message = "Failed to generate todo"
                # Allow completion even if todo fails, plan might be useful
                # return # Uncomment if todo failure should stop everything

            # Update state with response data only if successful
            self.state.llm_response = {
                "plan": plan_response.get("data", {}),
                "todo": todo_response.get("data", {}),
            }
            logger.info(
                f"LLM response stored in state for stream {stream_id}",
                extra={"stream_id": stream_id},
            )

        except Exception as e:
            # Catch errors from state checks, stream_controller setup, or re-raised processing errors
            logger.exception(
                f"Unhandled error in LLM process for stream {stream_id}: {e}",
                extra={"stream_id": stream_id},
            )
            # Ensure error message is set if not already
            if not self.state.error_message:
                self.state.error_message = f"Unexpected Error: {str(e)}"
        finally:
            # logger.info(
            #     f"Finishing LLM process for stream {stream_id}. Resetting processing flag.",
            #     extra={"stream_id": stream_id},
            # )
            self.state.processing = False
            self._current_task = None
            # Ensure stream is completed regardless of success or failure
            if stream:
                stream.complete()
                logger.debug(
                    f"ReactiveStream completed for stream {stream_id}",
                    extra={"stream_id": stream_id},
                )

    # Add cancel method
    @trace  # Added trace
    async def cancel_current_request(self) -> None:
        """Cancels the currently running LLM process task."""
        if self._current_task and not self._current_task.done():
            # logger.info(
            #     f"Attempting to cancel current LLM task (ID: {self._current_task.get_name()})"
            # )
            self._current_task.cancel()
            try:
                # Wait briefly for cancellation to propagate
                await asyncio.wait_for(self._current_task, timeout=1.0)
            except asyncio.CancelledError:
                logger.info("LLM task successfully cancelled.")
            except asyncio.TimeoutError:
                logger.warning("LLM task did not cancel within timeout.")
            except Exception as e:
                # Catch potential errors if the task raised something other than CancelledError
                logger.error(
                    f"Error encountered while waiting for LLM task cancellation: {e}"
                )
            finally:
                # Ensure state is reset even if cancellation had issues
                await self._reset_state()
                self._current_task = None  # Clear the task reference
        else:
            logger.info("No active LLM task to cancel.")
            # Ensure processing flag is false if no task is active
            if self.state.processing:
                await self._reset_state()
