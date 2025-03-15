"""
Module for processing and generating development plans and to-do lists using LLMs.
"""

import json
from pathlib import Path
from typing import Any, Dict, Tuple

import litellm
import tomli_w
import tomllib
from rich import print

from uplan.models.todo import TodoModel
from uplan.question import collect_answers, select_option
from uplan.utils.data import add_completed_status, toml_to_markdown
from uplan.utils.display import (
    display_json_panel,
    display_streaming,
    display_text_panel,
)
from uplan.utils.file import open_file
from uplan.utils.text import dict_to_xml, extract_code_block


def run(
    prompt_title: str,
    extracted_title: str,
    output_file: str,
    validate_model: object = None,
    max_retries: int = 5,
    prompt: Dict = None,
    model: str = None,
    stream: bool = True,
    debug: bool = False,
    **litellm_kwargs,
) -> dict:
    display_json_panel(prompt, title=prompt_title, border_style="green")

    optimized_prompt = dict_to_xml(prompt)

    if debug:
        display_text_panel(optimized_prompt, title=prompt_title, border_style="green")

    for attempt in range(1, max_retries + 1):
        try:
            response = litellm.completion(
                model=model,
                messages=[{"content": optimized_prompt, "role": "user"}],
                stream=stream,
                **litellm_kwargs,
            )

            text = display_streaming(response)
            dict_block = extract_code_block(text)
            json_block = json.loads(dict_block)

            if validate_model:
                validate_model.model_validate(json_block)

            # display_json_panel(json_block, title=extracted_title, border_style="green")

            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "wb") as f:
                tomli_w.dump(json_block, f)

            open_file(output_file)

            answer = select_option(
                text="Please review the generated document [dim]\n- Complete: Enter or Y \n- Regenerate: R \n- Exit: X[dim]",
                choices=["y", "r", "x"],
            )

            if answer.lower() == "r":
                display_text_panel(text="Regenerating document. Retrying...")
                continue
            elif answer.lower() == "x":
                display_text_panel(text="Exiting process.")

                return {"status": "exit", "data": None, "output_file": output_file}

            return {"status": "success", "data": json_block, "output_file": output_file}
        except json.JSONDecodeError as je:
            display_text_panel(text=f"Invalid JSON format: {je}")
        except Exception as e:
            display_text_panel(text=f"Error processing response: {e}")
        if attempt < max_retries:
            display_text_panel(text=f"Retrying ({attempt}/{max_retries})...")

    display_text_panel(text=f"Failed to process response after {max_retries} attempts.")
    raise Exception("Max retries exceeded")


def get_plan(
    input_folder: Path,
    output_folder: Path,
    model: str,
    retry: int,
    **litellm_kwargs: Any,
) -> Dict:
    """Execute plan generation process."""
    try:
        with open(input_folder / "plan.toml", "rb") as f:
            questions = tomllib.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Failed to read plan.toml in {input_folder}")

    template = questions.get("template")
    if template is None:
        raise RuntimeError("No template found in plan.toml")

    template, only_answers = collect_answers(template)
    questions.update({"user_input": only_answers, "template": template})

    try:
        response = run(
            prompt=questions,
            model=model,
            prompt_title="Plan Prompt",
            extracted_title="Extracted Plan Data",
            output_file=str(output_folder / "plan.toml"),
            max_retries=retry,
            **litellm_kwargs,
        )
        return response
    except Exception as e:
        print(f"[red]Error processing plan: {str(e)}[/red]")
        return {"status": "error", "message": str(e)}


def get_todo(
    input_folder: Path,
    output_folder: Path,
    model: str,
    retry: int,
    **litellm_kwargs: Any,
) -> Dict:
    """Execute todo generation process."""
    try:
        with open(input_folder / "todo.toml", "rb") as f:
            todo = tomllib.load(f)
        with open(output_folder / "plan.toml", "rb") as f:
            plan = tomllib.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Failed to read required TOML files in {input_folder}")

    todo.update({"plan": plan})

    try:
        response = run(
            prompt=todo,
            model=model,
            prompt_title="To-Do Prompt",
            extracted_title="Extracted To-Do Data",
            output_file=str(output_folder / "todo.toml"),
            max_retries=retry,
            validate_model=TodoModel,
            **litellm_kwargs,
        )

        json_block = response.get("data")

        markdown = toml_to_markdown(json_block)
        with open(output_folder / "todo.md", "w", encoding="utf-8") as f:
            f.write(markdown)

        json_dict = add_completed_status(json_block)
        with open(output_folder / "todo.json", "w", encoding="utf-8") as f:
            json.dump(json_dict, f, indent=2)
        return response
    except Exception as e:
        print(f"[red]Error processing todo: {str(e)}[/red]")
        return {"status": "error", "message": str(e)}


def get_all(
    input_folder: Path,
    output_folder: Path,
    model: str,
    retry: int,
    **litellm_kwargs: Any,
) -> Tuple[Dict, Dict]:
    """Generate both plan and todo documents in sequence."""
    # Generate plan first
    plan_response = get_plan(
        input_folder, output_folder, model, retry, **litellm_kwargs
    )
    if plan_response.get("status") in ["exit", "error"]:
        return plan_response, {"status": "skipped"}

    # Generate todo using the created plan
    todo_response = get_todo(
        input_folder, output_folder, model, retry, **litellm_kwargs
    )
    return plan_response, todo_response
