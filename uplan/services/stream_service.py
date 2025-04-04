"""Service for managing LLM streams and updating UI elements."""

from typing import Dict

from nicegui import ui

from uplan.ui.state import AppState
from uplan.utils.logging import get_logger, trace
# Add imports for StreamController or related stream handling logic if needed

logger = get_logger()


class StreamService:
    """Manages LLM stream connections and UI updates."""

    def __init__(self, state: AppState):
        """Initialize the StreamService.

        Args:
            state: The application state instance containing the StreamController.
        """
        self.state = state
        # Store active stream bindings if needed (e.g., stream_id -> ui_element)
        self.active_streams: Dict[str, ui.markdown] = {}
        logger.info("StreamService initialized.")

    @trace
    async def bind_to_ui_element(self, stream_id: str, element: ui.markdown) -> None:
        """Binds a stream ID to a NiceGUI UI element for displaying content.

        Args:
            stream_id: The unique identifier for the LLM stream.
            element: The NiceGUI ui.markdown element to update with stream content.
        """
        logger.info(f"Binding stream {stream_id} to UI element {element.id}")
        self.active_streams[stream_id] = element

        # --- Placeholder for actual stream handling logic ---
        # This logic will likely involve interacting with self.state.stream_controller
        # or a similar mechanism to receive data for stream_id and update element.
        # Example:
        # async for chunk in self.state.stream_controller.get_stream(stream_id):
        #     element.content += chunk # Or use element.set_content for full updates
        #     await element.update() # Ensure UI updates
        #
        # # Clean up after stream ends
        # del self.active_streams[stream_id]
        # logger.info(f"Stream {stream_id} finished and unbound.")

        # Simulate stream content for now
        import asyncio

        for i in range(5):
            await asyncio.sleep(0.5)
            element.content += f"Chunk {i + 1} for stream {stream_id}... "
            element.update()
        element.content += f"\nStream {stream_id} finished."
        element.update()
        if stream_id in self.active_streams:  # Check if not stopped
            del self.active_streams[stream_id]
        logger.info(f"Simulated stream {stream_id} finished and unbound.")
        # -----------------------------------------------------

    @trace
    def stop_all_streams(self) -> None:
        """Requests stopping all active LLM streams."""
        logger.info("Requesting to stop all active streams.")
        # Interact with the StreamController in the state
        if hasattr(self.state, "stream_controller") and self.state.stream_controller:
            self.state.stream_controller.request_stop()
            # Optionally, add logic here to immediately clear UI elements or show a message
            for element in self.active_streams.values():
                element.content += "\n\n**Stopping stream...**"
                element.update()
            self.active_streams.clear()  # Clear active streams as they are being stopped
            logger.info("Stop request sent to StreamController.")
        else:
            logger.warning("StreamController not found in state. Cannot stop streams.")

    # Add other stream management methods if needed (e.g., stop_specific_stream)
