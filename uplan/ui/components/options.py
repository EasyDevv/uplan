"""Options panel component for the right sidebar."""

from pathlib import Path
from nicegui import ui

from uplan.utils.provider import check_model_support
from uplan.ui.services.llm import LLMService
from uplan.ui.services.planner import PlannerService
from uplan.ui.state import AppState


def create_option_card(title: str, value: str, placeholder: str) -> ui.input:
    """Create a card for a configuration option.

    Args:
        title: Title of the option
        value: Default value
        placeholder: Placeholder text

    Returns:
        The created input element
    """
    with ui.card().classes("w-full mb-4"):
        ui.label(title).classes("text-sm font-medium mb-1")
        input_element = ui.input(value=value, placeholder=placeholder).classes("w-full")
        return input_element


def create_options() -> None:
    """Create the options panel in the right sidebar."""
    # Initialize application state
    state = AppState()
    llm_service = LLMService(state)
    planner_service = PlannerService(state, llm_service)

    # Initialize storage if needed
    if not hasattr(ui.page, "_storage"):
        ui.page._storage = {}

    with ui.element("div").classes("min-w-[20%] max-w-xs bg-base-200 p-4"):
        ui.label("Options").classes("text-xl font-bold p-1")

        # Create a scrollable container for options
        with ui.element("div").classes("scroll-container"):
            with ui.element("div").classes("mb-20"):
                # Model selection
                model_input = create_option_card(
                    "Model", "ollama/gemma3:1b", "Enter model name"
                )

                # Category selection
                category_input = create_option_card("Category", "dev", "Enter category")

                # Input folder
                input_folder = create_option_card(
                    "Input Folder", "./input", "Enter input folder path"
                )

                # Output folder
                output_folder = create_option_card(
                    "Output Folder", "./output", "Enter output folder path"
                )

                # Retry count
                with ui.card().classes("w-full mb-4"):
                    ui.label("Max Retries").classes("text-sm font-medium mb-1")
                    retry_input = ui.number(value=5, min=1, max=10).classes("w-full")

                # Loading indicator
                loading_indicator = ui.spinner("dots").classes("hidden")

                async def on_plan_click() -> None:
                    """Handle plan button click."""
                    try:
                        loading_indicator.classes("visible")

                        # Get stream handler from content component with safe fallback
                        storage = getattr(ui.page, "_storage", {})
                        handle_stream_update = storage.get("handle_stream_update")
                        if not handle_stream_update:
                            ui.notify(
                                "Warning: Stream handler not initialized",
                                type="warning",
                            )

                        # Generate plan using planner service
                        success, message = await planner_service.generate_plan(
                            model=model_input.value,
                            category=category_input.value,
                            input_folder=input_folder.value,
                            output_folder=output_folder.value,
                            retry_count=retry_input.value,
                            stream_handler=handle_stream_update,
                        )

                        # Show appropriate notification
                        ui.notify(message, type="positive" if success else "negative")

                    except Exception as e:
                        ui.notify(f"Error: {str(e)}", type="negative")
                    finally:
                        loading_indicator.classes("hidden")

                ui.button("Plan", on_click=on_plan_click).classes("w-full")
