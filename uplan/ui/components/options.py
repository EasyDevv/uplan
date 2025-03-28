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
                        state.reset_processing()
                        storage = getattr(ui.page, "_storage", {})
                        handle_stream_update = storage.get("handle_stream_update")
                        success, message = await planner_service.generate_plan_only(
                            model=model_input.value,
                            category=category_input.value,
                            input_folder=input_folder.value,
                            output_folder=output_folder.value,
                            retry_count=retry_input.value,
                            stream_handler=handle_stream_update,
                        )
                        ui.notify(message, type="positive" if success else "negative")
                    except Exception as e:
                        ui.notify(f"Error: {str(e)}", type="negative")
                    finally:
                        loading_indicator.classes("hidden")

                async def on_todo_click() -> None:
                    """Handle todo button click."""
                    try:
                        loading_indicator.classes("visible")
                        state.reset_processing()
                        storage = getattr(ui.page, "_storage", {})
                        handle_stream_update = storage.get("handle_stream_update")
                        success, message = await planner_service.generate_todo_only(
                            model=model_input.value,
                            category=category_input.value,
                            input_folder=input_folder.value,
                            output_folder=output_folder.value,
                            retry_count=retry_input.value,
                            stream_handler=handle_stream_update,
                        )
                        ui.notify(message, type="positive" if success else "negative")
                    except Exception as e:
                        ui.notify(f"Error: {str(e)}", type="negative")
                    finally:
                        loading_indicator.classes("hidden")

                async def on_all_click() -> None:
                    """Handle all (plan + todo) button click."""
                    try:
                        loading_indicator.classes("visible")
                        state.reset_processing()
                        storage = getattr(ui.page, "_storage", {})
                        handle_stream_update = storage.get("handle_stream_update")
                        success, message = await planner_service.generate_plan_and_todo(
                            model=model_input.value,
                            category=category_input.value,
                            input_folder=input_folder.value,
                            output_folder=output_folder.value,
                            retry_count=retry_input.value,
                            stream_handler=handle_stream_update,
                        )
                        ui.notify(message, type="positive" if success else "negative")
                    except Exception as e:
                        ui.notify(f"Error: {str(e)}", type="negative")
                    finally:
                        loading_indicator.classes("hidden")

                def on_stop_click() -> None:
                    """Handle stop button click."""
                    state = AppState.get_instance()
                    state.stream_controller.request_stop()
                    ui.notify("Stopping LLM processing...", type="info")

                with ui.row().classes("w-full gap-2"):
                    ui.button("Plan", on_click=on_plan_click).classes("flex-grow")
                    ui.button("Todo", on_click=on_todo_click).classes("flex-grow")
                with ui.row().classes("w-full gap-2 mt-2"):
                    ui.button("All", on_click=on_all_click).classes("flex-grow")
                    ui.button("Stop", on_click=on_stop_click).classes(
                        "flex-grow bg-negative"
                    )
