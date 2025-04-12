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
from pyhunt import trace

# Removed ContentManager class as its functionality is now handled
# by the simpler approach in options.py (one markdown element per stream).


# Removed handle_stream_update function as it relied on ContentManager
# and is no longer needed. Stream updates are handled directly by subscriptions
# set up in options.py.


# Removed stream_service argument as it's no longer directly used here.
# Services are typically accessed via app.services if needed globally,
# or passed during component creation/initialization.
@trace
def create_content() -> None:
    """Create the main content area container."""
    with ui.element("div").classes(
        "flex flex-1 bg-base-100 p-4 scroll-container overflow-y-auto"
    ) as main_container:
        content_container = ui.element("div").classes("w-full flex flex-col space-y-4")

        if not hasattr(app, "storage"):
            app.storage = {}

        storage_key = "stream_display_container"
        if not hasattr(app, "custom_storage"):
            app.custom_storage = {}
        if not hasattr(ui.page, "_storage"):
            ui.page._storage = {}
        ui.page._storage["stream_display"] = content_container
        app.custom_storage[storage_key] = content_container
