import gradio as gr
import tomllib
from pathlib import Path
import tomli_w

from typing import Dict, Any
from gui_process import get_all


def load_template() -> Dict[str, Any]:
    template_path = Path(__file__).parent / "templates" / "dev" / "plan.toml"
    with open(template_path, "rb") as f:
        data = tomllib.load(f)
    return data["template"]


def create_form_elements(template: Dict[str, Any]) -> Dict[str, Any]:
    form_elements = {}
    for section, questions in template.items():
        for field, details in questions.items():
            description = details.get("description", "")
            form_elements[f"{section}.{field}"] = gr.TextArea(
                label=details["ask"],
                info=description,
                lines=1,
            )
    return form_elements


def process_form(input_folder: Path, output_folder: Path, model: str, **inputs) -> str:
    template_data = {}
    for key, value in inputs.items():
        section, field = key.split(".")
        if section not in template_data:
            template_data[section] = {}
        template_data[section][field] = value

    # Save form data to plan.toml
    input_folder.mkdir(parents=True, exist_ok=True)
    with open(input_folder / "plan.toml", "wb") as f:
        tomli_w.dump({"template": template_data}, f)

    # Generate plan and todo
    plan_response, todo_response = get_all(
        input_folder=input_folder, output_folder=output_folder, model=model, retry=3
    )

    if plan_response["status"] == "success" and todo_response["status"] == "success":
        return "Successfully generated plan and todo documents!"
    else:
        return f"Error: Plan status: {plan_response['status']}, Todo status: {todo_response['status']}"


def create_gui():
    template = load_template()
    form_elements = create_form_elements(template)

    with gr.Blocks(title="UPlan Generator") as app:
        gr.Markdown("# UPlan - Development Plan Generator")

        with gr.Row():
            input_folder = gr.Text(label="Input Folder Path", value="./input")
            output_folder = gr.Text(label="Output Folder Path", value="./output")
            model = gr.Dropdown(
                label="LLM Model",
                choices=["gpt-4", "gpt-3.5-turbo"],
                value="gpt-3.5-turbo",
            )

        # Project Basics Section
        sections = [
            (section, section.replace("_", " ").title()) for section in template.keys()
        ]

        for section_key, section_title in sections:
            gr.Markdown(f"## {section_title}")
            with gr.Group():
                section_elements = {
                    k: v for k, v in form_elements.items() if k.startswith(section_key)
                }
                for element in section_elements.values():
                    element.render()

        with gr.Row():
            submit_btn = gr.Button("Generate Plan", variant="primary")
            output = gr.Text(label="Result")

        submit_btn.click(
            fn=process_form,
            inputs=[input_folder, output_folder, model, *form_elements.values()],
            outputs=output,
        )

    return app


if __name__ == "__main__":
    app = create_gui()
    app.launch()
