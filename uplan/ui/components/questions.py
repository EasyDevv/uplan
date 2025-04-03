"""Questions panel component for the left sidebar, dynamically loaded based on category."""

from pathlib import Path
from typing import Dict, Any, Optional, Callable  # Added Callable
from nicegui import ui, app  # Removed events

from uplan.config import INPUT_BASE_DIR  # Import config constant
from uplan.utils.data import load_toml_file
from uplan.utils.logging import get_logger, trace  # Added logger

logger = get_logger()  # Initialize logger


def create_question_card(field_name: str, field_data: dict, store: dict) -> None:
    """Create a card for a single question.

    Args:
        field_name: Name of the form field
        field_data: Field configuration data
        store: Dictionary to store input values
    """
    with ui.card().classes("w-full"):
        ui.label(field_data.get("ask", "")).classes("text-sm font-medium mb-1")

        if field_data.get("description"):
            desc = field_data.get("description", "")
            ui.label(desc).classes("text-x mb-4 text-gray-300 hover:text-clip").tooltip(
                desc
            )

        input_element = ui.input(placeholder="<select>").classes("w-full")

        if field_data.get("required", False):
            ui.label("Recommended input").classes("text-xs mt-2 text-warning")

        # Update store when input changes
        def on_input_change(e):
            # Use '<select>' as default value if input is empty
            value = e.value if e.value else "<select>"
            store["values"][field_name] = value
            store["form_data"] = {
                "form": {
                    section: {k: {"value": v} for k, v in values.items()}
                    for section, values in store["sections"].items()
                }
            }

        input_element.on("change", on_input_change)
        # Initialize with '<select>' as default value
        store["values"][field_name] = "<select>"


def create_section(section_name: str, section_data: dict, store: dict) -> None:
    """Create an expansion panel for a form section.56^

    Args:
        section_name: Name of the section
        section_data: Section configuration data
        store: Dictionary to store input values
    """
    with ui.expansion(f"{section_name.replace('_', ' ').title()}", value=True).classes(
        "w-full"
    ):
        store["sections"][section_name] = {}
        for field_name, field_data in section_data.items():
            create_question_card(
                field_name,
                field_data,
                {
                    "values": store["sections"][section_name],
                    "sections": store["sections"],
                    "form_data": store["form_data"],
                },
            )


# Define a container for the questions that can be refreshed
questions_container = None


@ui.refreshable
def build_questions_ui(category: Optional[str] = "dev") -> None:
    """Builds or rebuilds the questions UI based on the selected category."""
    global questions_container
    if questions_container is None:
        logger.error("Questions container is not initialized.")
        return

    # Clear previous content explicitly
    questions_container.clear()

    with questions_container:  # Rebuild content within the container
        # Load form structure from TOML based on category
        if category is None:
            logger.warning("No category provided, cannot load questions.")
            ui.label("Please select a category first.").classes("text-warning")
            return

        # Construct path using INPUT_BASE_DIR config constant
        form_path = INPUT_BASE_DIR / category / "plan.toml"
        logger.info(f"Attempting to load questions from: {form_path}")

        if not form_path.exists():
            logger.error(f"Questions file not found: {form_path}")
            ui.label(
                f"Error: Questions file not found for category '{category}'."
            ).classes("text-negative")
            ui.label(f"Expected path: {form_path}").classes("text-xs text-gray-500")
            return

        form_data = load_toml_file(form_path)
        if form_data is None:
            # load_toml_file likely logged specifics, this log indicates the consequence.
            logger.error(
                f"Failed to load or parse TOML data from {form_path}. Check preceding logs for details."
            )
            ui.label(f"Error loading questions file for '{category}'.").classes(
                "text-negative"
            )
            ui.label(f"Path: {form_path}").classes("text-xs text-gray-500")
            return
        elif "form" not in form_data:
            logger.error(
                f"Loaded data from {form_path}, but missing required 'form' key."
            )
            ui.label(
                f"Error: Invalid structure in questions file for '{category}'."
            ).classes("text-negative")
            ui.label(f"File: {form_path}").classes("text-xs text-gray-500")
            return

        # Initialize storage if needed (might be redundant if already done elsewhere)
        if not hasattr(ui.page, "_storage"):
            ui.page._storage = {}

        # Initialize store for form data for this category
        # Ensure store is reset or managed correctly when category changes
        store = {"sections": {}, "form_data": {}}
        # Store under a category-specific key or reset it
        ui.page._storage[f"questions_store_{category}"] = (
            store  # Example: category-specific store
        )
        # Or potentially reset a general store: ui.page._storage["questions_store"] = store

        # Create a scrollable container for the form
        with ui.element("div").classes("vertical-scroll"):
            with ui.element("div").classes("mb-20 space-y-4"):
                # Iterate over the sections found under the 'form' key
                form_sections = form_data.get("form", {})  # Use 'form' key

                if not form_sections:
                    ui.label(
                        f"No question sections found under '[form]' in {form_path}."  # Updated message
                    ).classes("text-info")
                else:
                    # Create expansion panels for each section from the form data
                    for (
                        section_name,
                        section_data,
                    ) in form_sections.items():  # Use form_sections
                        # Ensure section_data is a dictionary before proceeding
                        if isinstance(section_data, dict):
                            create_section(section_name, section_data, store)
                        else:
                            logger.warning(
                                f"Skipping invalid section data for '{section_name}' in {form_path}. Expected a dictionary, got {type(section_data)}."
                            )


@trace
def create_questions() -> Callable:
    """Create the questions panel container and return its refresh method."""
    global questions_container
    with ui.element("div").classes(
        "w-[30%] max-w-xs bg-base-200 p-4 h-full flex flex-col"
    ):  # Ensure height and flex
        ui.label("Questions").classes("text-xl font-bold p-1 mb-2")

        # Create the container where questions will be dynamically rendered
        # Use flex-grow to make it fill available space and overflow-auto for scrolling
        questions_container = ui.element("div").classes("flex-1 overflow-auto")

        # Initial build with default category (e.g., 'dev')
        # Consider getting the initial category from options.py default if possible
        initial_category = "dev"  # Hardcoded for now, could be improved
        build_questions_ui(initial_category)

        # Return the refresh method so it can be called externally
        return build_questions_ui.refresh
