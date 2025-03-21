"""
Module for processing and generating development plans and to-do lists using LLMs.
"""

import json
from pathlib import Path

import litellm
import tomli_w
import tomllib
from rich import print

from uplan.models.todo import TodoModel
from uplan.question import collect_answers_cli, select_option
from uplan.utils.data import add_completed_status, toml_to_markdown
from uplan.utils.file import open_file
from uplan.utils.text import dict_to_xml, extract_code_block, optimize_for_prompt


def run(
    prompt_title: str,
    extracted_title: str,
    output_file: str,
    validate_model: object = None,
    max_retries: int = 5,
    prompt: dict = None,
    model: str = None,
    stream: bool = True,
    debug: bool = False,
    stream_handler=None,
    **litellm_kwargs,
) -> dict:
    """
    Execute LLM completion with streaming support.

    Args:
        prompt_title: Title of the prompt
        extracted_title: Title for extracted data
        output_file: Path to save generated content
        validate_model: Optional Pydantic model for validation
        max_retries: Maximum number of retry attempts
        prompt: Prompt dictionary
        model: LLM model name
        stream: Whether to stream responses
        debug: Enable debug logging
        stream_handler: Optional callback for handling streamed chunks
        **litellm_kwargs: Additional arguments for litellm
    """
    optimized_prompt = dict_to_xml(prompt)
    optimized_prompt = optimize_for_prompt(optimized_prompt)

    for attempt in range(1, max_retries + 1):
        try:
            response = litellm.completion(
                model=model,
                messages=[{"content": optimized_prompt, "role": "user"}],
                stream=stream,
                **litellm_kwargs,
            )

            if stream and stream_handler:
                # For streaming, delegate to handler and return early
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        stream_handler(chunk.choices[0].delta.content)
                return {"status": "success", "data": None}

            # For non-streaming, accumulate full response
            full_response = ""
            if stream:
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
            else:
                full_response = response.choices[0].message.content

            dict_block = extract_code_block(full_response)
            json_block = json.loads(dict_block)

            if validate_model:
                validate_model.model_validate(json_block)

            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "wb") as f:
                tomli_w.dump(json_block, f)

            # Only open file and prompt for review in non-streaming mode
            if not stream:
                open_file(output_file)
                answer = select_option(
                    text="Please review the generated document [dim]\n- Complete: Enter or Y \n- Regenerate: R \n- Exit: X[dim]",
                    choices=["y", "r", "x"],
                )

            return {
                "status": "success",
                "data": json_block if not stream else None,
                "output_file": output_file,
            }
        except Exception as e:
            print(e)

    raise Exception("Max retries exceeded")


def get_plan(
    output_folder: Path,
    model: str,
    retry: int,
    answers_data: dict,
    **litellm_kwargs,
) -> dict:
    """
    Execute plan generation process.

    Args:
        output_folder: Path where generated plan will be saved
        model: Name of the LLM model to use
        retry: Number of retry attempts
        answers: Pre-collected answers (for non-CLI usage)
        **litellm_kwargs: Additional arguments for litellm

    Returns:
        dict: Response containing status and generated plan data
    """

    try:
        response = run(
            prompt=answers_data,
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
    output_folder: Path,
    model: str,
    retry: int,
    todo: dict,
    **litellm_kwargs,
) -> dict:
    """Execute todo generation process."""

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
            json.dump(json_dict, f, indent=2, ensure_ascii=False)
        return response
    except Exception as e:
        print(f"[red]Error processing todo: {str(e)}[/red]")
        return {"status": "error", "message": str(e)}


def prepare_todo(input_folder: Path, output_folder: Path) -> dict:
    """
    Read and merge todo and plan TOML files.

    Args:
        input_folder: Path to the input folder containing todo.toml.
        output_folder: Path to the output folder containing plan.toml.

    Returns:
        dict: Merged todo dictionary with plan data.

    Raises:
        RuntimeError: If required TOML files are not found.
    """
    try:
        with open(input_folder / "todo.toml", "rb") as f:
            todo = tomllib.load(f)
        with open(output_folder / "plan.toml", "rb") as f:
            plan = tomllib.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Failed to read required TOML files in {input_folder}")

    todo.update({"plan": plan})
    return todo


def prepare_answers_cli(input_folder: Path) -> tuple[dict, dict]:
    """
    Read and validate the plan form from input folder.
    Args:
        input_folder: Path to the input folder containing plan.toml
    Returns:
        tuple[dict, dict]: Tuple containing (questions, form)
            where questions is the full questions dict and form is the form section
    Raises:
        RuntimeError: If plan.toml is missing or form section is not found
    """
    try:
        with open(input_folder / "plan.toml", "rb") as f:
            answers_data = tomllib.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Failed to read plan.toml in {input_folder}")

    form = answers_data.get("form")
    if form is None:
        raise RuntimeError("No form found in plan.toml")

    form, only_answers = collect_answers_cli(form)

    answers_data.update({"user_input": only_answers, "form": form})

    return answers_data


def get_all(
    input_folder: Path,
    output_folder: Path,
    model: str,
    retry: int,
    **litellm_kwargs,
) -> tuple[dict, dict]:
    """Generate both plan and todo documents in sequence."""
    # Generate plan first
    answers_data = prepare_answers_cli(input_folder)
    plan_response = get_plan(
        input_folder, output_folder, model, retry, answers_data, **litellm_kwargs
    )
    if plan_response.get("status") in ["exit", "error"]:
        return plan_response, {"status": "skipped"}

    # Generate todo using the created plan
    todo = prepare_todo(input_folder, output_folder)
    todo_response = get_todo(
        input_folder, output_folder, model, retry, todo, **litellm_kwargs
    )
    return plan_response, todo_response
