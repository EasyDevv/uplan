"""Options panel component for the right sidebar."""

import inspect
from pathlib import Path
from nicegui import ui, app

from uplan.utils.provider import check_model_support
from uplan.ui.services.llm import LLMService
from uplan.ui.services.planner import PlannerService
from uplan.utils.logging import get_logger, log_async_function, trace_function

logger = get_logger()
from uplan.ui.services.stream_service import StreamService
from uplan.ui.state import AppState


@trace_function
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


@trace_function
def create_options() -> None:
    """Create the options panel in the right sidebar."""
    # Initialize application state
    state = AppState()

    # Get the services from app.services
    llm_service = app.services.get("llm")
    stream_service = app.services.get("stream")

    # Create planner service if needed
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

                @log_async_function
                async def connect_to_stream(stream_id: str, operation_type: str):
                    """Connect to a stream by ID and display results.

                    Args:
                        stream_id: The ID of the stream to connect to
                        operation_type: The type of operation being performed
                    """
                    storage = getattr(ui.page, "_storage", {})
                    stream_display = storage.get("stream_display")

                    if not stream_display:
                        ui.notify("Stream display area not found", type="warning")
                        return

                    # Create new card and bind it to the stream
                    with stream_display:
                        with ui.card().classes("w-full mb-4 h-auto"):
                            ui.label(
                                f"Generated {operation_type} - Processing..."
                            ).classes("card-title")
                            content = ui.markdown("").classes(
                                "w-full whitespace-pre-wrap font-mono overflow-y-auto flex-grow"
                            )
                            # Log connection attempt to help with debugging
                            print(
                                f"Connecting to stream: {stream_id} for {operation_type}"
                            )
                            await stream_service.bind_to_ui_element(stream_id, content)

                @log_async_function
                async def process_operation(
                    operation_type: str, display_name: str
                ) -> None:
                    """Process an operation with the LLM.

                    Args:
                        operation_type: The type of operation to process ('plan', 'todo', or 'all')
                        display_name: The display name to show in the UI
                    """
                    func_name = inspect.currentframe().f_code.co_name
                    logger.info(
                        f"Processing operation",
                        extra={
                            "function": func_name,
                            "operation_type": operation_type,
                            "display_name": display_name,
                        },
                    )
                    try:
                        loading_indicator.classes("visible")
                        state.reset_processing()

                        # Update state with form values
                        state.model = model_input.value
                        state.category = category_input.value
                        state.input_path = input_folder.value
                        state.output_path = output_folder.value
                        state.max_retries = retry_input.value
                        state.operation_type = operation_type

                        # Log request details for debugging
                        print(
                            f"Processing {operation_type} request with model: {state.model}"
                        )

                        # Process request with streaming
                        # Pass the operation type through state instead of as a parameter
                        stream_id = await llm_service.process_request()

                        if stream_id:
                            print(f"Stream ID received: {stream_id}")
                            await connect_to_stream(stream_id, display_name)
                        else:
                            ui.notify(
                                "No stream ID returned from LLM service",
                                type="negative",
                            )

                    except Exception as e:
                        ui.notify(f"Error: {str(e)}", type="negative")
                        print(f"Error processing {operation_type}: {str(e)}")
                    finally:
                        loading_indicator.classes("hidden")

                @log_async_function
                async def on_plan_click() -> None:
                    """Handle plan button click."""
                    func_name = inspect.currentframe().f_code.co_name
                    logger.info(
                        f"Starting plan generation", extra={"function": func_name}
                    )
                    await process_operation("plan", "Plan")

                @log_async_function
                async def on_todo_click() -> None:
                    """Handle todo button click."""
                    func_name = inspect.currentframe().f_code.co_name
                    logger.info(
                        f"Starting todo generation", extra={"function": func_name}
                    )
                    await process_operation("todo", "Todo List")

                @log_async_function
                async def on_all_click() -> None:
                    """Handle all (plan + todo) button click."""
                    func_name = inspect.currentframe().f_code.co_name
                    logger.info(
                        f"Starting combined plan & todo generation",
                        extra={"function": func_name},
                    )
                    await process_operation("all", "Plan & Todo")

                @trace_function
                def on_stop_click() -> None:
                    """Handle stop button click."""
                    state = AppState.get_instance()
                    state.stream_controller.request_stop()
                    stream_service.stop_all_streams()
                    ui.notify("Stopping LLM processing...", type="info")

                with ui.row().classes("w-full gap-2"):
                    ui.button("Plan", on_click=on_plan_click).classes("flex-grow")
                    ui.button("Todo", on_click=on_todo_click).classes("flex-grow")
                with ui.row().classes("w-full gap-2 mt-2"):
                    ui.button("All", on_click=on_all_click).classes("flex-grow")
                    ui.button("Stop", on_click=on_stop_click).classes(
                        "flex-grow bg-negative"
                    )
