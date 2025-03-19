import asyncio
import tomllib
import tomli_w
from pathlib import Path
from typing import Any
from nicegui import ui

# Add centralized Tailwind components
ui.add_head_html("""
    <style type="text/tailwindcss">
        @layer components {
            .card-container {
                @apply w-full bg-gray-800 rounded-lg shadow-lg p-4;
            }
            .card-inner {
                @apply w-full bg-gray-700 p-4 rounded-lg mb-4;
            }
            .heading {
                @apply text-xl font-bold mb-4 text-blue-400;
            }
            .text-area {
                @apply w-full bg-gray-700 text-white rounded-md p-2 border border-gray-600 hover:border-blue-500 focus:border-blue-500 transition-colors;
            }
            .label-text {
                @apply text-lg font-semibold text-white mb-2;
            }
            .description-text {
                @apply text-sm text-gray-300 mb-2;
            }
            .field-label {
                @apply text-white w-24;
            }
            .field-input {
                @apply flex-grow bg-gray-700 text-white rounded-md;
            }
        }
    </style>
""")


def load_template() -> dict[str, Any]:
    """
    Loads template from TOML file

    Returns:
        dict[str, Any]: Template data structure

    Raises:
        FileNotFoundError: If template file doesn't exist
        tomllib.TOMLDecodeError: If TOML file is invalid
    """
    try:
        template_path = Path(__file__).parent / "templates" / "dev" / "plan.toml"
        with open(template_path, "rb") as f:
            data = tomllib.load(f)
        return data["template"]
    except FileNotFoundError:
        raise FileNotFoundError(f"Template file not found at {template_path}")
    except tomllib.TOMLDecodeError:
        raise ValueError(f"Invalid TOML format in {template_path}")


class TemplateInterface:
    """A GUI interface for managing templates and generating content using LLM."""

    def __init__(self):
        """Initialize the template interface with required components."""
        self.template = load_template()
        self.form_elements: dict[str, ui.textarea] = {}
        self.llm_stream: ui.textarea | None = None
        self.result_output: ui.code | None = None
        self.model: ui.select | None = None
        self.input_folder: ui.input | None = None
        self.output_folder: ui.input | None = None

    def create_question_template_area(self) -> None:
        """Creates the question template components using sections from template."""
        sections = [
            (section, section.replace("_", " ").title())
            for section in self.template.keys()
        ]

        with ui.column().classes("w-1/3 p-4 space-y-4 overflow-y-auto"):
            for section_key, section_title in sections:
                with ui.card().classes("card-container"):
                    ui.markdown(f"### {section_title}").classes("heading")

                    for field, details in self.template[section_key].items():
                        description = details.get("description", "")
                        key = f"{section_key}.{field}"

                        with ui.card().classes("card-inner"):
                            ui.label(details["ask"]).classes("label-text")
                            if description:
                                ui.label(description).classes("description-text")

                            text_area = ui.textarea(
                                placeholder="AI generates the content."
                            ).classes("text-area")
                            text_area.style("min-height: 4em; resize: vertical")
                            self.form_elements[key] = text_area

    def create_llm_stream_area(self) -> None:
        """Creates the LLM stream output components."""
        with ui.card().classes("card-container mb-4"):
            ui.markdown("### LLM Stream").classes("heading")
            self.llm_stream = ui.textarea(
                placeholder="LLM response will appear here..."
            ).classes("text-area")
            self.llm_stream.style("min-height: 20em; resize: vertical")
            self.llm_stream.disable()

    def create_editable_result_area(self) -> None:
        """Creates the editable result components."""
        with ui.card().classes("card-container mb-4"):
            ui.markdown("### Editable Result").classes("heading")
            self.result_output = ui.code("", language="python").classes("text-area")

    def create_options_area(self) -> None:
        """Creates the options components."""
        with ui.card().classes("card-container"):
            ui.markdown("### Options").classes("heading")

            with ui.column().classes("space-y-4 w-full"):
                with ui.row().classes("w-full items-center"):
                    ui.label("Model").classes("field-label")
                    self.model = ui.select(
                        options=["gpt-4", "gpt-3.5-turbo", "claude-3", "llama-3"],
                        value="gpt-3.5-turbo",
                    ).classes("field-input")

                with ui.row().classes("w-full items-center"):
                    ui.label("Input Path").classes("field-label")
                    self.input_folder = ui.input(value="./input").classes("field-input")

                with ui.row().classes("w-full items-center"):
                    ui.label("Output Path").classes("field-label")
                    self.output_folder = ui.input(value="./output").classes(
                        "field-input"
                    )

                ui.button("Generate", on_click=self.process_form).classes(
                    "w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition-colors"
                )

    async def process_form(self) -> None:
        """Process the form with all input elements and generate output."""
        try:
            # Get values from form elements
            inputs = {key: element.value for key, element in self.form_elements.items()}

            # Validate paths
            input_path = Path(self.input_folder.value)
            output_path = Path(self.output_folder.value)

            # Format template data
            template_data: dict[str, dict[str, Any]] = {}
            for key, value in inputs.items():
                if "." not in key:
                    continue
                section, field = key.split(".")
                if section not in template_data:
                    template_data[section] = {}
                template_data[section][field] = value

            # Save form data
            input_path.mkdir(parents=True, exist_ok=True)
            toml_path = input_path / "plan.toml"
            with open(toml_path, "wb") as f:
                tomli_w.dump({"template": template_data}, f)

            # Update stream with progress
            await self.stream_progress(
                f"Processing with {self.model.value}...\nSaved form data to {toml_path}"
            )

            # Simulate processing (replace with actual implementation)
            final_result = (
                f"Successfully processed form with {len(template_data)} sections.\n"
                f"Using model: {self.model.value}\n"
                f"Input path: {self.input_folder.value}\n"
                f"Output path: {self.output_folder.value}"
            )

            # Update result
            if self.result_output:
                self.result_output.set_content(final_result)

        except Exception as e:
            if self.llm_stream:
                self.llm_stream.value = f"Error: {str(e)}"

    async def stream_progress(self, text: str) -> None:
        """Stream text to the LLM stream area with a typing effect."""
        if not self.llm_stream:
            return

        self.llm_stream.value = ""
        for i in range(len(text)):
            self.llm_stream.value = text[: i + 1]
            await asyncio.sleep(0.01)

    def create_gui(self) -> None:
        """Creates the main interface layout."""
        with ui.element("div").classes("min-h-screen bg-gray-900 p-4"):
            with ui.row().classes("h-full gap-4"):
                # Left column - Questions
                self.create_question_template_area()

                # Right column - Stream, Result, Options
                with ui.column().classes("w-1/2 space-y-4"):
                    self.create_llm_stream_area()
                    self.create_editable_result_area()
                    self.create_options_area()


# Create and run the interface
template_interface = TemplateInterface()
template_interface.create_gui()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Template Interface", dark=True, reload=False)
