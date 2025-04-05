"""Main content area component."""

import hashlib
import inspect
from datetime import datetime
from asyncio import Lock
from nicegui import ui, app  # Import app to potentially access services if needed

# Removed AppState import as it's not directly used after removing ContentManager
# from uplan.ui.state import AppState
# Import the refactored StreamService
from uplan.services.stream_service import StreamService
from uplan.utils.logging import get_logger  # Removed trace as it's not used

# Initialize logger
logger = get_logger()

# Removed ContentManager class as its functionality is now handled
# by the simpler approach in options.py (one markdown element per stream).


# Removed handle_stream_update function as it relied on ContentManager
# and is no longer needed. Stream updates are handled directly by subscriptions
# set up in options.py.


# Removed stream_service argument as it's no longer directly used here.
# Services are typically accessed via app.services if needed globally,
# or passed during component creation/initialization.
def create_content() -> None:
    """Create the main content area container."""
    logger.info("Creating main content area.")
    with (
        ui.element("div").classes(
            "flex flex-1 bg-base-100 p-4 scroll-container overflow-y-auto"  # Added overflow-y-auto
        ) as main_container
    ):
        # Create container where stream outputs will be dynamically added by options.py
        content_container = ui.element("div").classes(
            "w-full flex flex-col space-y-4"
        )  # Added spacing

        # Initialize page storage if needed (good practice)
        if not hasattr(app, "storage"):  # Check app storage, more common pattern
            logger.warning(
                "Initializing app.storage - this might indicate it wasn't set up earlier."
            )
            app.storage = {}  # Consider using app.storage.user or app.storage.general

        # Store only the container reference needed by options.py
        # Use a more specific key if possible
        storage_key = "stream_display_container"
        if not hasattr(app, "custom_storage"):
            app.custom_storage = {}
        # Also store in ui.page._storage for options.py compatibility
        if not hasattr(ui.page, "_storage"):
            ui.page._storage = {}
        ui.page._storage["stream_display"] = content_container
        app.custom_storage[storage_key] = content_container

        logger.debug(
            f"Stored content container reference in app.storage with key: {storage_key}"
        )

        # Removed handle_stream_update registration from storage

        # Removed on_stream_created function.
        # UI element creation and binding are now handled in options.py's connect_to_stream
        # when a stream_id is available after llm_service.process_request.
