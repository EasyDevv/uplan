"""Main content area component."""

import hashlib
import inspect
from datetime import datetime
from asyncio import Lock
from nicegui import ui
from typing_extensions import Any

from uplan.ui.state import AppState
from uplan.ui.services.stream_service import StreamService
from uplan.utils.logging import get_logger

# Initialize logger
logger = get_logger()


class ContentManager:
    """Manages content display and prevents duplicates."""

    def __init__(self):
        """Initialize the content manager."""
        self._lock = Lock()
        self._last_hash = None
        self._debounce_delay = 0.1  # seconds
        self._active_card = None
        self._active_content = None
        self._active_title = None
        self._is_streaming = False

    def _hash_content(self, text: str) -> str:
        """Create a hash of the content.

        Args:
            text: Text content to hash

        Returns:
            Hash string of the content
        """
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    async def _stop_streaming(self) -> None:
        """Handle cleanup and visual updates when streaming is stopped."""
        if self._active_title and self._active_card:
            current_title = self._active_title.text
            if not current_title.endswith("(Stopped)"):
                self._active_title.text = f"{current_title} (Stopped)"

        # Reset streaming state
        self._active_card = None
        self._active_content = None
        self._active_title = None
        self._is_streaming = False

    def _create_new_card(self, container: ui.element, text: str) -> None:
        """Create a new content card.

        Args:
            container: The container element to add the card to
            text: Text content to display
        """
        with container:
            with ui.card().classes("w-full mb-4 h-auto") as card:
                title = ui.label(
                    f"Generated Content - {datetime.now().strftime('%H:%M:%S')}"
                ).classes("card-title")
                content = ui.markdown(text).classes(
                    "w-full whitespace-pre-wrap font-mono overflow-y-auto flex-grow"
                )
                self._active_card = card
                self._active_content = content
                self._active_title = title

    async def update(
        self, container: ui.element, text: str, is_complete: bool = False
    ) -> None:
        """Update content with duplicate prevention.

        Args:
            container: The container element to add new cards to
            text: Text to append as a new card
            is_complete: Flag indicating if this is the final update in a stream
        """
        func_name = inspect.currentframe().f_code.co_name
        logger.debug(
            "Updating content",
            extra={"function": func_name, "is_complete": is_complete},
        )
        # Check if streaming has been stopped
        state = AppState.get_instance()
        if state.stop_streaming:
            await self._stop_streaming()
            return  # Don't create or update any cards if streaming is stopped

        content_hash = self._hash_content(text)

        async with self._lock:
            # If this is a new stream or a non-streaming update
            if content_hash != self._last_hash:
                self._last_hash = content_hash

                # If we have an active card, update it instead of creating a new one
                if self._active_card and not is_complete:
                    if self._active_content:
                        self._active_content.content = text
                else:
                    # Create a new card if there's no active one or the stream is complete
                    self._create_new_card(container, text)

            # Reset streaming state when complete
            if is_complete:
                self._active_card = None
                self._active_content = None


async def handle_stream_update(
    container: ui.element, text: str, is_complete: bool = False
) -> None:
    """Handle updates to the streaming display.

    Args:
        container: The container element to add new cards to
        text: Text to append as a new card
        is_complete: Flag indicating if this is the final update in a stream
    """
    func_name = inspect.currentframe().f_code.co_name
    logger.debug(
        "Handling stream update",
        extra={
            "function": func_name,
            "is_complete": is_complete,
            "container_exists": container is not None,
        },
    )
    # Check if streaming has been stopped before proceeding
    state = AppState.get_instance()
    if state.stop_streaming:
        if not hasattr(ui.page, "_content_manager"):
            return
        await ui.page._content_manager._stop_streaming()
        return  # Skip updates if streaming is stopped

    if container is not None:
        # Get or create content manager
        if not hasattr(ui.page, "_content_manager"):
            ui.page._content_manager = ContentManager()

        await ui.page._content_manager.update(container, text, is_complete)


def create_content(stream_service: StreamService) -> None:
    """Create the main content area for displaying generated content."""
    with ui.element("div").classes(
        "flex flex-1 bg-base-100 p-4 scroll-container overflow-y-auto"
    ):
        # Create container for cards
        content_container = ui.element("div").classes("w-full flex flex-col p-4")

        # Initialize storage if needed
        if not hasattr(ui.page, "_storage"):
            ui.page._storage = {}

        # Store references for other components
        ui.page._storage.update(
            {
                "stream_display": content_container,
                "handle_stream_update": lambda text,
                is_complete=False: handle_stream_update(
                    content_container, text, is_complete
                ),
            }
        )

        async def on_stream_created(stream_id: str) -> None:
            """Handle stream creation event."""
            func_name = inspect.currentframe().f_code.co_name
            logger.info(
                "Creating new stream",
                extra={"function": func_name, "stream_id": stream_id},
            )
            with content_container:
                card = ui.card().classes("w-full mb-4 h-auto")
                new_content = ui.markdown("").classes(
                    "w-full whitespace-pre-wrap font-mono overflow-y-auto flex-grow"
                )
                await stream_service.bind_to_ui_element(stream_id, new_content)
