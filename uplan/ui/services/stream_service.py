"""Stream service for managing LLM streaming operations."""

from typing import Callable, Dict, Optional
from nicegui import ui

from uplan.utils.reactive import ReactiveStream
from uplan.utils.stream import StreamController


class StreamService:
    """Service for managing LLM streaming operations."""

    def __init__(self, stream_controller: StreamController):
        """Initialize the stream service.

        Args:
            stream_controller: The controller for managing stream tasks
        """
        self.stream_controller = stream_controller
        self.active_streams: Dict[str, ReactiveStream] = {}
        self._current_stream_id: Optional[str] = None

    def create_stream(self, stream_id: str) -> ReactiveStream:
        """Create a new named stream.

        Args:
            stream_id: Unique identifier for this stream

        Returns:
            A reactive stream instance
        """
        if stream_id in self.active_streams:
            self.active_streams[stream_id].complete()

        stream = ReactiveStream()
        self.active_streams[stream_id] = stream
        self._current_stream_id = stream_id
        return stream

    def get_stream(self, stream_id: str) -> Optional[ReactiveStream]:
        """Get an existing stream by ID."""
        return self.active_streams.get(stream_id)

    def get_current_stream(self) -> Optional[ReactiveStream]:
        """Get the most recently created stream."""
        if self._current_stream_id:
            return self.active_streams.get(self._current_stream_id)
        return None

    def stop_stream(self, stream_id: str) -> None:
        """Stop a specific stream."""
        if stream_id in self.active_streams:
            self.active_streams[stream_id].complete()

    def stop_all_streams(self) -> None:
        """Stop all active streams."""
        self.stream_controller.request_stop()
        for stream in self.active_streams.values():
            stream.complete()

    async def bind_to_ui_element(
        self,
        stream_id: str,
        element: ui.element,
        transform: Optional[Callable[[str], str]] = None,
    ) -> None:
        """Bind a stream to update a UI element.

        Args:
            stream_id: ID of the stream to bind
            element: UI element to update (must have a .value or .content attribute)
            transform: Optional function to transform stream values
        """
        stream = self.get_stream(stream_id)
        if not stream:
            stream = self.create_stream(stream_id)

        def update_element(value):
            display_value = transform(value) if transform else value

            if hasattr(element, "set_content"):
                element.set_content(display_value)
            elif hasattr(element, "content"):
                element.content = display_value
            elif hasattr(element, "value"):
                element.value = display_value

        stream.subscribe(update_element)
