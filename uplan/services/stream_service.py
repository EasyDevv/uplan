# uplan/services/stream_service.py
"""Stream service for managing LLM streaming operations and controllers."""

from typing import Dict, Optional
from contextlib import suppress  # For cleaner task cancellation handling

from uplan.utils.reactive import ReactiveStream
from uplan.utils.stream import StreamController
from pyhunt import trace


class StreamService:
    """Service for managing LLM streaming operations via ReactiveStreams and StreamController.

    This service acts as a central point for creating, retrieving, and managing
    data streams associated with LLM operations. It interacts with the
    StreamController to handle the underlying asynchronous tasks and cancellation.
    UI components should subscribe to the ReactiveStreams provided by this service
    to display updates.
    """

    def __init__(self, stream_controller: StreamController):
        """Initialize the stream service.

        Args:
            stream_controller: The controller for managing stream tasks.

        Raises:
            TypeError: If stream_controller is not an instance of StreamController.
        """
        if not isinstance(stream_controller, StreamController):
            raise TypeError("stream_controller must be an instance of StreamController")

        self.stream_controller = stream_controller
        self.active_streams: Dict[str, ReactiveStream] = {}
        self._current_stream_id: Optional[str] = None

    @trace
    def create_stream(self, stream_id: str) -> ReactiveStream:
        """Create a new named reactive stream or retrieve an existing one.

        If a stream with the same ID already exists, it completes the old one
        before creating a new one. This ensures only one active stream per ID.

        Args:
            stream_id: Unique identifier for this stream.

        Returns:
            A reactive stream instance.
        """
        if stream_id in self.active_streams:
            # Complete the existing stream cleanly
            self.stop_stream(stream_id)  # stop_stream handles removal from dict

        # logger.info(
        #     f"Creating new reactive stream with ID: {stream_id}",
        #     extra={"stream_id": stream_id},
        # )
        stream = ReactiveStream()
        self.active_streams[stream_id] = stream
        self._current_stream_id = stream_id  # Track the latest created stream
        return stream

    @trace
    def get_stream(self, stream_id: str) -> Optional[ReactiveStream]:
        """Get an existing reactive stream by ID.

        Args:
            stream_id: The ID of the stream to retrieve.

        Returns:
            The ReactiveStream instance if found, otherwise None.
        """
        stream = self.active_streams.get(stream_id)
        if not stream:
            pass
        return stream

    @trace
    def get_current_stream(self) -> Optional[ReactiveStream]:
        """Get the most recently created reactive stream.

        Returns:
            The most recent ReactiveStream instance, or None if no streams have been created.
        """
        if self._current_stream_id:
            return self.get_stream(self._current_stream_id)
        return None

    @trace
    def stop_stream(self, stream_id: str) -> None:
        """Stop and remove a specific reactive stream.

        Completes the stream, allowing subscribers to perform cleanup,
        and removes it from the active streams dictionary.

        Args:
            stream_id: The ID of the stream to stop.
        """
        if stream_id in self.active_streams:
            stream = self.active_streams.pop(stream_id)  # Remove from dict first
            stream.complete()  # Signal completion to subscribers
            if self._current_stream_id == stream_id:
                self._current_stream_id = None  # Clear current if it was stopped
        else:
            pass

    @trace
    def stop_all_streams(self) -> None:
        """Stop all active reactive streams and request cancellation via StreamController.

        This method signals the StreamController to cancel underlying tasks
        and completes all managed ReactiveStreams.
        """
        # logger.info("Requesting stop for all active streams via StreamController.")
        # Request cancellation of underlying tasks first
        self.stream_controller.request_stop()

        # Then complete all reactive streams
        # Iterate over keys to avoid issues with modifying dict during iteration
        stream_ids = list(self.active_streams.keys())
        for stream_id in stream_ids:
            self.stop_stream(stream_id)  # Use stop_stream for consistent cleanup

        self._current_stream_id = None  # Reset current stream ID

    # Note: Removed bind_to_ui_element method. UI binding is now the responsibility
    # of the UI components themselves, which will get the stream using get_stream()
    # and subscribe to it.
