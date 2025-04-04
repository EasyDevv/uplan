"""Options panel component for the right sidebar."""

from pathlib import Path
from typing import Optional, Callable  # Removed List, added imports for services

from nicegui import ui, app

from uplan.config import INPUT_BASE_DIR, OUTPUT_BASE_DIR
from uplan.utils.logging import get_logger, trace
from uplan.ui.state import AppState

# Import services
from uplan.services.llm_service import LLMService
from uplan.services.stream_service import StreamService
from uplan.services.option_service import OptionService


logger = get_logger()
# Service instances will be created/retrieved here


def create_options(
    questions_update_trigger: Optional[Callable] = None,
) -> None:  # Changed callable to Callable
    """Create the options panel in the right sidebar.

    Args:
        questions_update_trigger: Optional callable to trigger question updates.
    """
    # Initialize services and state
    state = AppState()  # Keep state for now, services might need it
    option_service = OptionService()  # Instantiate OptionService directly
    # Retrieve LLM and Stream services (assuming they are registered in app startup)
    # If not registered, they might need to be instantiated here, potentially passing state
    llm_service: LLMService = app.services.get("llm")
    stream_service: StreamService = app.services.get("stream")

    if not llm_service or not stream_service:
        logger.error(
            "LLMService or StreamService not found in app.services. UI might not function correctly."
        )
        # Optionally, raise an error or display a notification
        # For now, we'll proceed, but operations requiring these services will fail.
        # llm_service = LLMService(state) # Fallback instantiation if needed
        # stream_service = StreamService(state) # Fallback instantiation if needed

    # Initialize storage if needed
    if not hasattr(ui.page, "_storage"):
        ui.page._storage = {}

    with ui.element("div").classes("min-w-[20%] max-w-xs bg-base-200 p-4"):
        ui.label("Options").classes("text-xl font-bold p-1 mb-2")  # Added margin

        # Create a scrollable container for options
        with ui.element("div").classes("scroll-container"):
            with ui.element("div").classes(
                "mb-20 space-y-4"
            ):  # Added spacing between cards
                # --- Define update_models callback first ---
                def update_models() -> None:
                    """Update model dropdown options based on selected provider using OptionService."""
                    selected_provider = provider_select.value
                    models = option_service.get_models_for_provider(
                        selected_provider
                    )  # Use service
                    model_select.options = models
                    # Try to keep the current model if it exists for the new provider, else select the first one
                    current_model_value = model_select.value
                    if current_model_value not in models:
                        new_value = models[0] if models else None
                        # Check if the value actually needs changing before setting it
                        if model_select.value != new_value:
                            model_select.set_value(new_value)
                        else:
                            # If value is the same but options changed, force UI update
                            model_select.update()

                    else:
                        # If the value is valid, ensure the UI reflects the potentially updated options list
                        model_select.update()
                    logger.debug(
                        f"Provider changed to {selected_provider}. Models updated: {models}. Selected: {model_select.value}"
                    )

                # --- Provider Selection ---
                providers = option_service.get_providers()
                default_provider, default_models_list = (
                    option_service.get_default_provider_and_models()
                )
                with ui.card().classes("w-full"):
                    ui.label("Provider").classes("text-sm font-medium mb-1")
                    provider_select = (
                        ui.select(
                            options=providers,
                            value=default_provider,  # Use value from option_service
                        )
                        .classes("w-full")
                        .props("dense options-dense")
                        .on(
                            "update:model-value", update_models
                        )  # Correctly chained .on()
                    )

                # --- Model Selection ---
                default_model = option_service.get_default_model(default_models_list)
                with ui.card().classes("w-full"):
                    ui.label("Model").classes("text-sm font-medium mb-1")
                    model_select = (
                        ui.select(
                            options=default_models_list,  # Use value from option_service
                            value=default_model,  # Use value from option_service
                        )
                        .classes("w-full")
                        .props("dense options-dense")
                    )

                # update_models function definition moved above provider_select
                # Removed duplicated/incorrect .on() call here
            # --- Category Selection ---
            category_options = option_service.get_category_options()  # Use service
            default_category = option_service.get_default_category(
                category_options
            )  # Use service

            with ui.card().classes("w-full"):
                ui.label("Category").classes("text-sm font-medium mb-1")

                # Define the callback function first
                def handle_category_change(e):
                    """Handles category selection change via on_change.

                    Updates the input folder display and triggers the questions UI refresh.

                    Args:
                        e: The event object containing the new value.
                    """
                    new_category = e.value
                    update_input_folder_display(new_category)  # Pass category directly

                    # Trigger the questions UI update if the callback is provided
                    if questions_update_trigger:
                        logger.debug(
                            f"Category changed to {new_category}, triggering questions update."
                        )
                        questions_update_trigger(new_category)  # Pass the new category

                category_select = (
                    ui.select(
                        options=category_options,
                        value=default_category,
                        label="Select Category",
                        on_change=handle_category_change,  # Use on_change here
                    )
                    .classes("w-full")
                    .props("dense options-dense")
                )

            # --- Input Folder (Readonly based on Category) ---
            with ui.card().classes("w-full"):
                ui.label("Input Folder").classes("text-sm font-medium mb-1")
                # Display the input folder path using INPUT_BASE_DIR, make it readonly
                input_folder_display = (
                    ui.input(
                        value=option_service.get_input_path_for_category(
                            category_select.value
                        ),  # Use service
                        placeholder="Input folder path",
                    )
                    .classes("w-full")
                    .props("readonly")
                )

            # --- Output Folder ---
            with ui.card().classes("w-full"):
                ui.label("Output Folder").classes("text-sm font-medium mb-1")
                # Use OUTPUT_BASE_DIR for default value, convert to string
                output_folder = ui.input(
                    value=option_service.get_default_output_path(
                        OUTPUT_BASE_DIR
                    ),  # Use service
                    placeholder="Enter output folder path",
                ).classes("w-full")

            # --- Retry Count ---
            with ui.card().classes("w-full"):
                ui.label("Max Retries").classes("text-sm font-medium mb-1")
                retry_input = ui.number(value=5, min=1, max=10).classes("w-full")

            # Loading indicator
            loading_indicator = ui.spinner("dots").classes("hidden")

            # --- Event Handlers (will be updated to use services) ---
            def update_input_folder_display(category: str):
                """Update the readonly input folder display based on category using OptionService."""
                new_path = option_service.get_input_path_for_category(
                    category
                )  # Use service
                input_folder_display.set_value(new_path)
                logger.debug(f"Input folder display updated to: {new_path}")

            # Removed unused handle_category_change function as we now use a direct callback

            # The on_change handler is now directly attached to the ui.select definition above.
            # The category_selected function and the .on() binding below are no longer needed.

            # connect_to_stream and process_operation logic moved to services
            # Re-define helpers to use services

            async def connect_to_stream(stream_id: str, operation_type: str):
                """Connect to a stream by ID and delegate UI creation/binding to StreamService."""
                storage = getattr(ui.page, "_storage", {})
                stream_display_container = storage.get(
                    "stream_display"
                )  # Get the container

                if not stream_display_container:
                    logger.error("Stream display container not found in page storage.")
                    ui.notify("Stream display area not found", type="warning")
                    return
                if not stream_service:
                    logger.error("StreamService not available.")
                    ui.notify("Streaming service is unavailable.", type="negative")
                    return

                # Delegate UI creation and binding to the StreamService
                # Assumes StreamService has a method like create_and_bind_stream_ui
                try:
                    await stream_service.create_and_bind_stream_ui(
                        stream_id=stream_id,
                        operation_type=operation_type,
                        container=stream_display_container,
                    )
                except Exception as e:
                    logger.error(
                        f"Error calling stream_service.create_and_bind_stream_ui: {e}",
                        exc_info=True,
                    )
                    ui.notify(
                        f"Failed to display stream output for {operation_type}.",
                        type="negative",
                    )

            async def process_operation(operation_type: str, display_name: str) -> None:
                """Process an operation using LLMService and StreamService.

                Args:
                    operation_type: The type of operation ('plan', 'todo', 'all').
                    display_name: The display name for the UI.
                """
                if not llm_service or not stream_service:
                    logger.error("LLM or Stream service not available for processing.")
                    ui.notify("Required services are unavailable.", type="negative")
                    return

                logger.info(
                    "Processing operation",
                    extra={
                        "operation_type": operation_type,
                        "display_name": display_name,
                    },
                )
                try:
                    loading_indicator.classes(remove="hidden")  # Show spinner

                    state.reset_processing()  # Reset any previous state flags

                    # Update state with current form values BEFORE calling service
                    state.provider = provider_select.value
                    state.model = model_select.value
                    state.category = category_select.value
                    state.input_path = input_folder_display.value  # Get current value
                    state.output_path = output_folder.value
                    state.max_retries = retry_input.value
                    state.operation_type = operation_type  # Set the specific operation

                    # Call LLMService to process the request (which uses the state)
                    stream_id = await llm_service.process_request()

                    if stream_id:
                        logger.info(f"Stream ID received: {stream_id}")
                        # Connect the stream to the UI
                        await connect_to_stream(stream_id, display_name)
                    else:
                        logger.error("No stream ID returned from LLM service.")
                        ui.notify(
                            "Failed to initiate processing stream.", type="negative"
                        )

                except Exception as e:
                    logger.error(
                        f"Error during '{display_name}' operation: {e}", exc_info=True
                    )
                    ui.notify(
                        f"Error processing {display_name}: {str(e)}", type="negative"
                    )
                finally:
                    loading_indicator.classes(add="hidden")  # Hide spinner

            @trace
            async def on_plan_click() -> None:
                await process_operation("plan", "Plan")

            @trace
            async def on_todo_click() -> None:
                await process_operation("todo", "Todo List")

            @trace
            async def on_all_click() -> None:
                await process_operation("all", "Plan & Todo")

            def on_stop_click() -> None:
                """Handle stop button click using StreamService."""
                if not stream_service:
                    logger.error("StreamService not available to stop streams.")
                    ui.notify("Streaming service is unavailable.", type="negative")
                    return

                logger.info("Stop button clicked.")
                # No need to get state instance here, service handles it
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

                # Removed duplicated code block from here to end of file
