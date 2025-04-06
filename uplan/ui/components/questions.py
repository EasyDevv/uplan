"""Questions panel component for the left sidebar, dynamically loaded based on category."""

from pathlib import Path
from typing import Dict, Any, Optional, Callable  # Added Callable
from nicegui import ui, app  # Removed events

from uplan.config import INPUT_BASE_DIR  # Import config constant
from uplan.utils.data import load_toml_file
from uplan.utils.logging import trace


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
@trace
def build_questions_ui(category: Optional[str] = "dev") -> None:
    """Builds or rebuilds the questions UI based on the selected category."""
    global questions_container
    if questions_container is None:
        raise RuntimeError("Questions container is not initialized.")

    # Clear previous content explicitly
    questions_container.clear()

    with questions_container:
        if category is None:
            raise ValueError("No category provided, cannot load questions.")

        form_path = INPUT_BASE_DIR / category / "plan.toml"

        if not form_path.exists():
            raise FileNotFoundError(f"Questions file not found: {form_path}")

        form_data = load_toml_file(form_path)
        if form_data is None:
            raise ValueError(f"Failed to load or parse TOML data from {form_path}.")
        if "form" not in form_data:
            raise KeyError(
                f"Loaded data from {form_path}, but missing required 'form' key."
            )

        if not hasattr(ui.page, "_storage"):
            ui.page._storage = {}

        store = {"sections": {}, "form_data": {}}
        ui.page._storage[f"questions_store_{category}"] = store

        with ui.element("div").classes("vertical-scroll"):
            with ui.element("div").classes("mb-20 space-y-4"):
                form_sections = form_data.get("form", {})

                if not form_sections:
                    ui.label(
                        f"No question sections found under '[form]' in {form_path}."
                    ).classes("text-info")
                else:
                    for section_name, section_data in form_sections.items():
                        if isinstance(section_data, dict):
                            create_section(section_name, section_data, store)
                        else:
                            raise TypeError(
                                f"Invalid section data for '{section_name}' in {form_path}. Expected dict, got {type(section_data)}."
                            )


@trace
def create_questions() -> Callable:
    """Create the questions panel container and return its refresh method."""
    global questions_container
    with ui.element("div").classes(
        "w-[30%] max-w-xs bg-base-200 p-4 h-full flex flex-col"
    ):
        ui.label("Questions").classes("text-xl font-bold p-1 mb-2")

        questions_container = ui.element("div").classes("flex-1 overflow-auto")

        initial_category = "dev"
        build_questions_ui(initial_category)

        return build_questions_ui.refresh
