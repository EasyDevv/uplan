"""Options panel component for the right sidebar."""

import inspect
import json
import os  # Added for listing directories initially, will refine with pathlib
from pathlib import Path
from typing import List, Optional  # Added for type hinting

from nicegui import ui, app, events  # Added events

from uplan.config import INPUT_BASE_DIR, OUTPUT_BASE_DIR  # Import config constants
from uplan.ui.services.planner import PlannerService
from uplan.utils.logging import get_logger, trace
from uplan.ui.state import AppState

logger = get_logger()

# Load model data
MODEL_INFO_PATH = Path("input/model_info.json")
model_data = {}
if MODEL_INFO_PATH.exists():
    try:
        with open(MODEL_INFO_PATH, "r", encoding="utf-8") as f:
            model_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load or parse {MODEL_INFO_PATH}: {e}")
        model_data = {"ollama": ["gemma3:1b"]}  # Fallback
else:
    logger.warning(f"{MODEL_INFO_PATH} not found. Using default model list.")
    model_data = {"ollama": ["gemma3:1b"]}  # Default fallback

# Prepare initial provider and model lists
providers = sorted(list(model_data.keys()))
default_provider = (
    "ollama" if "ollama" in providers else (providers[0] if providers else None)
)
default_models = sorted(model_data.get(default_provider, []))
default_model = (
    "gemma3:1b"
    if "gemma3:1b" in default_models
    else (default_models[0] if default_models else None)
)

# Removed create_option_card as it's less flexible for mixed types like dropdowns


# Helper function to get category directories using config
def get_category_options(input_base_path: Path = INPUT_BASE_DIR) -> List[str]:
    """Gets a list of directory names from the configured input path."""
    base_path = input_base_path  # Use the Path object directly
    categories = []
    if base_path.is_dir():
        try:
            categories = sorted(
                [item.name for item in base_path.iterdir() if item.is_dir()]
            )
        except OSError as e:
            logger.error(f"Error reading directories from {base_path}: {e}")
    if not categories:
        logger.warning(
            f"No category directories found in {base_path}. Defaulting to ['dev']."
        )
        return ["dev"]  # Fallback if no dirs found or error
    return categories


# Correctly indented function definition follows
def create_options(questions_update_trigger: Optional[callable] = None) -> None:
    """Create the options panel in the right sidebar.

    Args:
        questions_update_trigger: Optional callable to trigger question updates.
    """
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
        ui.label("Options").classes("text-xl font-bold p-1 mb-2")  # Added margin

        # Create a scrollable container for options
        with ui.element("div").classes("scroll-container"):
            with ui.element("div").classes(
                "mb-20 space-y-4"
            ):  # Added spacing between cards
                # --- Provider Selection ---
                with ui.card().classes("w-full"):
                    ui.label("Provider").classes("text-sm font-medium mb-1")
                    provider_select = (
                        ui.select(
                            options=providers,
                            value=default_provider,
                            label="Select Provider",
                        )
                        .classes("w-full")
                        .props("dense options-dense")
                    )

                # --- Model Selection ---
                with ui.card().classes("w-full"):
                    ui.label("Model").classes("text-sm font-medium mb-1")
                    model_select = (
                        ui.select(
                            options=default_models,
                            value=default_model,
                            label="Select Model",
                        )
                        .classes("w-full")
                        .props("dense options-dense")
                    )

                def update_models():
                    """Update model dropdown options based on selected provider."""
                    selected_provider = provider_select.value
                    models = sorted(model_data.get(selected_provider, []))
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

                provider_select.on(
                    "update:model-value", update_models
                )  # Use 'update:model-value' for immediate reaction

                # --- Category Selection (Uses INPUT_BASE_DIR via get_category_options) ---
                category_options = get_category_options()  # Use config default path
                default_category = (
                    "dev"
                    if "dev" in category_options
                    else (category_options[0] if category_options else None)
                )

                with ui.card().classes("w-full"):
                    ui.label("Category").classes("text-sm font-medium mb-1")
                    category_select = (
                        ui.select(
                            options=category_options,
                            value=default_category,
                            label="Select Category",
                        )
                        .classes("w-full")
                        .props("dense options-dense")
                    )

                # --- Input Folder (Readonly based on Category) ---
                with ui.card().classes("w-full"):
                    ui.label("Input Folder").classes("text-sm font-medium mb-1")
                    # Display the input folder path, make it readonly as it's derived from category
                    # Display the input folder path using INPUT_BASE_DIR, make it readonly
                    input_folder_display = (
                        ui.input(
                            value=str(
                                INPUT_BASE_DIR / category_select.value
                            ),  # Use Path object and convert to string
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
                        value=str(OUTPUT_BASE_DIR),
                        placeholder="Enter output folder path",
                    ).classes("w-full")

                # --- Retry Count ---
                with ui.card().classes("w-full"):
                    ui.label("Max Retries").classes("text-sm font-medium mb-1")
                    retry_input = ui.number(value=5, min=1, max=10).classes("w-full")

                # Loading indicator
                loading_indicator = ui.spinner("dots").classes("hidden")

                # --- Event Handlers ---
                def update_input_folder_display():
                    """Update the readonly input folder display based on category using INPUT_BASE_DIR."""
                    # Construct path using INPUT_BASE_DIR and convert to string
                    new_path = str(INPUT_BASE_DIR / category_select.value)
                    input_folder_display.set_value(new_path)
                    logger.debug(f"Input folder display updated to: {new_path}")

                async def handle_category_change(event: events.GenericEventArguments):
                    """Handle category change event."""
                    new_category = event.args.get("category")
                    if new_category:
                        logger.info(f"Category changed to: {new_category}")
                        update_input_folder_display()
                        # Emit event for questions component
                        # Emit event via JavaScript CustomEvent
                        ui.run_javascript(
                            f"window.dispatchEvent(new CustomEvent('category_changed', {{detail: {{ value: '{new_category}' }} }}));"
                        )
                    else:
                        logger.warning(
                            "Category change event received without category value."
                        )

                # Register category change handler using ui.on for generic events
                # Note: We emit 'category_changed' below, this is where it would be caught if needed *within* this component
                # ui.on('category_changed', handle_category_change) # Example if needed here

                # Bind category select change to update input folder and emit event
                category_select.on(
                    "update:model-value",
                    lambda e: (
                        update_input_folder_display(),
                        # Emit event via JavaScript CustomEvent
                        ui.run_javascript(
                            f"window.dispatchEvent(new CustomEvent('category_changed', {{detail: {{ value: '{e.args}' }} }}));"
                        ),
                    ),
                )

                async def connect_to_stream(stream_id: str, operation_type: str):
                    """Connect to a stream by ID and display results."""
                    storage = getattr(ui.page, "_storage", {})
                    stream_display = storage.get("stream_display")
                    if not stream_display:
                        ui.notify("Stream display area not found", type="warning")
                        return
                    with stream_display:
                        with ui.card().classes("w-full mb-4 h-auto"):
                            ui.label(
                                f"Generated {operation_type} - Processing..."
                            ).classes("card-title")
                            content = ui.markdown("").classes(
                                "w-full whitespace-pre-wrap font-mono overflow-y-auto flex-grow"
                            )
                            await stream_service.bind_to_ui_element(stream_id, content)

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
                        "Processing operation",
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
                        state.provider = provider_select.value
                        state.model = model_select.value
                        state.category = (
                            category_select.value
                        )  # Use category_select value
                        state.input_path = (
                            input_folder_display.value
                        )  # Use display value
                        state.output_path = output_folder.value
                        state.max_retries = retry_input.value
                        state.operation_type = operation_type

                        # Process request with streaming
                        # Pass the operation type through state instead of as a parameter
                        stream_id = await llm_service.process_request()

                        if stream_id:
                            logger.info(
                                f"Stream ID received: {stream_id}",
                                extra={"function": func_name},
                            )
                            await connect_to_stream(stream_id, display_name)
                        else:
                            ui.notify(
                                "No stream ID returned from LLM service",
                                type="negative",
                            )

                    except Exception as e:
                        ui.notify(f"Error: {str(e)}", type="negative")
                    finally:
                        loading_indicator.classes("hidden")

                async def on_plan_click() -> None:
                    """Handle plan button click."""
                    func_name = inspect.currentframe().f_code.co_name
                    logger.info(
                        "Starting plan generation", extra={"function": func_name}
                    )
                    await process_operation("plan", "Plan")

                async def on_todo_click() -> None:
                    """Handle todo button click."""
                    func_name = inspect.currentframe().f_code.co_name
                    logger.info(
                        "Starting todo generation", extra={"function": func_name}
                    )
                    await process_operation("todo", "Todo List")

                async def on_all_click() -> None:
                    """Handle all (plan + todo) button click."""
                    func_name = inspect.currentframe().f_code.co_name
                    logger.info(
                        "Starting combined plan & todo generation",
                        extra={"function": func_name},
                    )
                    await process_operation("all", "Plan & Todo")

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
