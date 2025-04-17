"""Header component of the application."""

from nicegui import ui


def create_header() -> None:
    """Create the application header with logo and navigation."""
    with ui.element("div").classes(
        "w-full max-h-[4%] bg-base-300 flex items-center justify-between p-4"
    ):
        ui.label("UPlan").classes("text-lg font-bold")
        ui.button(icon="home")
