"""
Module for processing and generating development plans and to-do lists using LLMs.
"""

import json
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, Optional, Tuple, Awaitable

import litellm
from regex import E
import tomli_w
import tomllib
from rich import print

from uplan.models.todo import TodoModel
from uplan.question import collect_answers_cli, select_option
from uplan.utils.data import add_completed_status, toml_to_markdown
from uplan.utils.display import (
    display_json_panel,
    display_streaming,
    display_text_panel,
)
from uplan.utils.file import open_file
from uplan.utils.text import dict_to_xml, extract_code_block, optimize_for_prompt
import logging
import traceback
from uplan.ui.state import AppState


# 로그 설정
logging.basicConfig(
    filename="error.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


async def run(
    prompt_title: str,
    extracted_title: str,
    output_file: str,
    validate_model: object = None,
    max_retries: int = 5,
    prompt: dict = None,
    model: str = None,
    stream: bool = True,
    debug: bool = False,
    stream_handler: Optional[Callable[[str], Awaitable[Any]]] = None,
    **litellm_kwargs,
) -> dict:
    """Run LLM inference with streaming support."""
    display_json_panel(prompt, title=prompt_title, border_style="green")

    optimized_prompt = dict_to_xml(prompt)
    optimized_prompt = optimize_for_prompt(optimized_prompt)

    if debug:
        display_text_panel(optimized_prompt, title=prompt_title, border_style="green")

    async def process_stream(response: AsyncIterator[Any]) -> str:
        """Process streaming response and update UI."""
        full_text = ""
        state = AppState.get_instance()
        async for chunk in response:
            if state.stop_streaming:
                return full_text
            if chunk and chunk.choices and chunk.choices[0].delta.content:
                text_chunk = chunk.choices[0].delta.content
                full_text += text_chunk
                if stream_handler:
                    try:
                        await stream_handler(full_text)
                    except TypeError:
                        # Handle the case when stream_handler doesn't return an awaitable
                        pass
        return full_text

    for attempt in range(1, max_retries + 1):
        try:
            state = AppState.get_instance()
            if state.stop_streaming:
                return {"status": "stopped", "message": "Processing stopped by user"}
            response = await litellm.acompletion(
                model=model,
                messages=[{"content": optimized_prompt, "role": "user"}],
                stream=stream,
                **litellm_kwargs,
            )

            text = (
                await process_stream(response)
                if stream
                else response.choices[0].message.content
            )
            dict_block = extract_code_block(text)
            json_block = json.loads(dict_block)

            if validate_model:
                validate_model.model_validate(json_block)

            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "wb") as f:
                tomli_w.dump(json_block, f)

            return {"status": "success", "data": json_block, "output_file": output_file}

        except json.JSONDecodeError as je:
            display_text_panel(text=f"Invalid JSON format: {je}")
        except Exception as e:
            logging.error(f"Error processing response: {traceback.format_exc()}")
            raise traceback.format_exc()
            # display_text_panel(text=f"Error processing response: {e}")
        if state.stop_streaming:
            return {"status": "stopped", "message": "Processing stopped by user"}
        if attempt < max_retries:
            display_text_panel(text=f"Retrying ({attempt}/{max_retries})...")

    display_text_panel(text=f"Failed to process response after {max_retries} attempts.")
    raise Exception("Max retries exceeded")


async def get_plan(
    output_folder: Path,
    model: str,
    retry: int,
    answers_data: dict,
    stream_handler: Optional[Callable[[str], Awaitable[Any]]] = None,
    **litellm_kwargs,
) -> dict:
    """
    Execute plan generation process.

    Args:
        output_folder: Path where generated plan will be saved
        model: Name of the LLM model to use
        retry: Number of retry attempts
        answers_data: Pre-collected answers
        stream_handler: Optional callback for streaming updates
        **litellm_kwargs: Additional arguments for litellm

    Returns:
        dict: Response containing status and generated plan data
    """
    try:
        response = await run(
            prompt=answers_data,
            model=model,
            prompt_title="Plan Prompt",
            extracted_title="Extracted Plan Data",
            output_file=str(output_folder / "plan.toml"),
            max_retries=retry,
            stream_handler=stream_handler,
            **litellm_kwargs,
        )
        return response
    except Exception as e:
        print(f"[red]Error processing plan: {str(e)}[/red]")
        return {"status": "error", "message": str(e)}


async def get_todo(
    output_folder: Path,
    model: str,
    retry: int,
    todo: dict,
    stream_handler: Optional[Callable[[str], Awaitable[Any]]] = None,
    **litellm_kwargs,
) -> dict:
    """Execute todo generation process."""
    try:
        response = await run(
            prompt=todo,
            model=model,
            prompt_title="To-Do Prompt",
            extracted_title="Extracted To-Do Data",
            output_file=str(output_folder / "todo.toml"),
            max_retries=retry,
            validate_model=TodoModel,
            stream_handler=stream_handler,
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
        input_folder: Path to the input folder containing todo.toml
        output_folder: Path to the output folder containing plan.toml

    Returns:
        dict: Merged todo dictionary with plan data

    Raises:
        RuntimeError: If required TOML files are not found
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


def prepare_answers(input_folder: Path) -> dict:
    """
    Read and validate the plan form from input folder.

    Args:
        input_folder: Path to the input folder containing plan.toml

    Returns:
        dict: The answers data dictionary

    Raises:
        RuntimeError: If plan.toml is missing or form section is not found
    """
    try:
        with open(input_folder / "plan.toml", "rb") as f:
            answers_data = tomllib.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Failed to read plan.toml in {input_folder}")

    # form = answers_data.get("form")
    # if form is None:
    #     raise RuntimeError("No form found in plan.toml")

    return answers_data


async def get_all(
    input_folder: Path,
    output_folder: Path,
    model: str,
    retry: int,
    stream_handler: Optional[Callable[[str], Awaitable[Any]]] = None,
    **litellm_kwargs,
) -> Tuple[dict, dict]:
    """Generate both plan and todo documents in sequence with streaming support."""
    # Generate plan first
    answers_data = prepare_answers(input_folder)
    plan_response = await get_plan(
        output_folder=output_folder,
        model=model,
        retry=retry,
        answers_data=answers_data,
        stream_handler=stream_handler,
        **litellm_kwargs,
    )
    if plan_response.get("status") in ["exit", "error"]:
        return plan_response, {"status": "skipped"}

    # Generate todo using the created plan
    todo = prepare_todo(input_folder, output_folder)
    todo_response = await get_todo(
        output_folder=output_folder,
        model=model,
        retry=retry,
        todo=todo,
        stream_handler=stream_handler,
        **litellm_kwargs,
    )
    return plan_response, todo_response
