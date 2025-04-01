"""Questions panel component for the left sidebar."""

from pathlib import Path
from nicegui import ui

from uplan.utils.data import load_toml_file


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
    """Create an expansion panel for a form section.

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


def create_questions() -> None:
    """Create the questions panel in the left sidebar."""
    with ui.element("div").classes("w-[30%] max-w-xs bg-base-200 p-4"):
        ui.label("Questions").classes("text-xl font-bold p-1")

        # Load form structure from TOML
        form_data = load_toml_file(Path("uplan/forms/dev/plan.toml"))

        # Initialize storage if needed
        if not hasattr(ui.page, "_storage"):
            ui.page._storage = {}

        # Initialize store for form data
        store = {"sections": {}, "form_data": {}}
        ui.page._storage["questions_store"] = store

        # Create a scrollable container for the form
        with ui.element("div").classes("vertical-scroll"):
            with ui.element("div").classes("mb-20"):
                # Organize questions by section
                sections = {}
                for key, value in form_data.get("form", {}).items():
                    section_name = key
                    if isinstance(value, dict):
                        sections[section_name] = value

                # Create expansion panels for each section
                for section_name, section_data in sections.items():
                    create_section(section_name, section_data, store)
