import gradio as gr
import tomllib
from pathlib import Path
import tomli_w
from typing import Dict, Any
from gui_process import get_all
import os


# Load form Function
def load_form() -> Dict[str, Any]:
    """Loads form from TOML file"""
    form_path = Path(__file__).parent / "forms" / "dev" / "plan.toml"
    with open(form_path, "rb") as f:
        data = tomllib.load(f)
    return data["form"]


# Question form Area (Top Left)
def create_question_form_area(form: Dict[str, Any]):
    """Creates and returns the question form components using sections from form"""
    # Create the form elements dictionary but don't render them yet
    form_elements = {}

    # Define the sections from the form
    sections = [(section, section.replace("_", " ").title()) for section in form.keys()]

    # Container for all form elements
    with gr.Group() as question_area:
        for section_key, section_title in sections:
            gr.Markdown(f"### {section_title}")
            with gr.Group():
                # Create elements for this section
                for field, details in form[section_key].items():
                    description = details.get("description", "")
                    key = f"{section_key}.{field}"
                    form_elements[key] = gr.TextArea(
                        label=details["ask"],
                        info=description,
                        placeholder="AI generates the content.",
                        lines=1,
                    )

    return question_area, form_elements


# LLM Stream Area (Top Right)
def create_llm_stream_area():
    """Creates and returns the LLM stream output components"""
    llm_stream = gr.TextArea(
        label="LLM Stream",
        placeholder="LLM response will appear here...",
        lines=10,
        interactive=False,
    )
    return llm_stream


# Options Area (Bottom Left)
def create_options_area():
    """Creates and returns the options components"""
    with gr.Group() as options_group:
        gr.Markdown("### Options", container=True)
        model = gr.Dropdown(
            label="Model",
            choices=["gpt-4", "gpt-3.5-turbo", "claude-3", "llama-3"],
            value="gpt-3.5-turbo",
        )
        input_folder = gr.Text(label="Input Path", value="./input")
        output_folder = gr.Text(label="Output Path", value="./output")
        submit_btn = gr.Button("Generate", variant="primary")

    return options_group, model, input_folder, output_folder, submit_btn


# Editable Result Area (Bottom Right)
def create_editable_result_area():
    """Creates and returns the editable result components"""
    result_output = gr.TextArea(
        label="Editable Result",
        placeholder="Generated result will appear here...",
        lines=10,
        interactive=True,
    )
    return result_output


# Process Form Function
def process_form(input_folder: str, output_folder: str, model: str, **inputs):
    """Process the form with all input elements"""
    # Convert input paths to Path objects
    input_path = Path(input_folder)
    output_path = Path(output_folder)

    # Format form data from form inputs
    form_data = {}
    for key, value in inputs.items():
        if "." in key:  # Only process keys in the format "section.field"
            section, field = key.split(".")
            if section not in form_data:
                form_data[section] = {}
            form_data[section][field] = value

    # Save form data to plan.toml
    input_path.mkdir(parents=True, exist_ok=True)
    with open(input_path / "plan.toml", "wb") as f:
        tomli_w.dump({"form": form_data}, f)

    # Generate stream output for demonstration
    stream_output = (
        f"Processing with {model}...\nSaved form data to {input_folder}/plan.toml"
    )

    # In actual implementation, call get_all()
    # plan_response, todo_response = get_all(
    #     input_folder=input_path, output_folder=output_path, model=model, retry=3
    # )

    # For demonstration
    final_result = f"Successfully processed form with {len(form_data)} sections.\nUsing model: {model}\nInput path: {input_folder}\nOutput path: {output_folder}"

    return stream_output, final_result


# Main GUI Function
def create_gui():
    """Creates the main Gradio interface with all four areas"""
    form = load_form()

    with gr.Blocks(title="form Interface") as demo:
        with gr.Row():
            # Left column - Questions
            with gr.Column(scale=1):
                question_area, form_elements = create_question_form_area(form)

            # Right column - LLM Stream, Result, Options
            with gr.Column(scale=1):
                # LLM Stream area
                llm_stream = create_llm_stream_area()

                # Editable Result area
                result_output = create_editable_result_area()

                # Options area
                options_group, model, input_folder, output_folder, submit_btn = (
                    create_options_area()
                )

        # Set up the click event with all form elements
        input_components = [input_folder, output_folder, model]
        # input_components.extend(list(form_elements.values()))

        submit_btn.click(
            fn=process_form,
            inputs=input_components,
            outputs=[llm_stream, result_output],
        )

    return demo


if __name__ == "__main__":
    demo = create_gui()
    # Development mode configuration
    demo.launch()
