"""Main content area component."""

from nicegui import ui


def create_content() -> None:
    """Create the main content area for displaying generated content."""
    with ui.element("div").classes("grow bg-base-100 p-4"):
        with ui.card().classes("w-full"):
            ui.label("Generated Content").classes("card-title")
