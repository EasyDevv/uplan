"""Options panel component for the right sidebar."""

from nicegui import ui


def create_option_card(title: str, value: str, placeholder: str) -> None:
    """Create a card for a configuration option.

    Args:
        title: Title of the option
        value: Default value
        placeholder: Placeholder text
    """
    with ui.card().classes("w-full mb-4"):
        ui.label(title).classes("text-sm font-medium mb-1")
        ui.input(value=value, placeholder=placeholder).classes("w-full")


def create_options() -> None:
    """Create the options panel in the right sidebar."""
    with ui.element("div").classes("w-[25%] max-w-xs bg-base-200 p-4"):
        ui.label("Options").classes("text-xl font-bold p-1")

        # Create a scrollable container for options
        with ui.element("div").classes("scroll-container"):
            with ui.element("div").classes("mb-20"):
                # Model selection
                create_option_card("Model", "ollama/qwq", "Enter model name")

                # Category selection
                create_option_card("Category", "dev", "Enter category")

                # Input folder
                create_option_card("Input Folder", "./input", "Enter input folder path")

                # Output folder
                create_option_card(
                    "Output Folder", "./output", "Enter output folder path"
                )

                # Retry count
                with ui.card().classes("w-full mb-4"):
                    ui.label("Max Retries").classes("text-sm font-medium mb-1")
                    ui.number(value=5, min=1, max=10).classes("w-full")
