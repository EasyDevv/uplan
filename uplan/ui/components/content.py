"""Main content area component."""

from nicegui import ui
from fastapi.responses import StreamingResponse


async def handle_stream_update(stream_display: ui.markdown, text: str) -> None:
    """Handle updates to the streaming display.

    Args:
        stream_display: The markdown element to update
        text: Text to append to the display
    """
    await stream_display.set_content(text)


def create_content() -> None:
    """Create the main content area for displaying generated content."""
    with ui.element("div").classes("grow bg-base-100 p-4"):
        with ui.card().classes("w-full"):
            ui.label("Generated Content").classes("card-title")

            # Create stream display
            stream_display = ui.markdown().classes(
                "w-full whitespace-pre-wrap font-mono"
            )

            # Initialize storage if needed
            if not hasattr(ui.page, "_storage"):
                ui.page._storage = {}

            # Store references for other components
            ui.page._storage.update(
                {
                    "stream_display": stream_display,
                    "handle_stream_update": lambda text: handle_stream_update(
                        stream_display, text
                    ),
                }
            )
