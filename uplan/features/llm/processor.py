"""
Module for processing and generating development plans and to-do lists using LLMs.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Optional, Tuple

import litellm
import tomli_w
import tomllib

from uplan.shared.models.todo import TodoModel
from uplan.shared.components.state import AppState
from uplan.shared.utils.data import add_completed_status, toml_to_markdown
from uplan.shared.utils.display import (
    display_json_panel,
    display_text_panel,
)
from uplan.shared.utils.logging import (
    get_logger,
    log_async_function,
    trace_function,
)
from uplan.shared.utils.stream import StreamController
from uplan.shared.utils.text import dict_to_xml, extract_code_block, optimize_for_prompt

# Initialize logger
logger = get_logger()


@log_async_function
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
    stream_controller: Optional[StreamController] = None,
    **litellm_kwargs,
) -> dict:
    """Run LLM inference with streaming support."""
    logger.info(
        f"Starting LLM inference",
        extra={"model": model, "prompt_title": prompt_title},
    )
    display_json_panel(prompt, title=prompt_title, border_style="green")

    optimized_prompt = dict_to_xml(prompt)
    optimized_prompt = optimize_for_prompt(optimized_prompt)

    if debug:
        display_text_panel(optimized_prompt, title=prompt_title, border_style="green")

    # Get controller from AppState if not provided
    controller = stream_controller or AppState.get_instance().stream_controller

    async def process_stream(response: AsyncIterator[Any]) -> str:
        """Process streaming response and update UI."""
        full_text = ""
        try:
            async for chunk in response:
                # Check for cancellation
                if controller.stop_requested:
                    if hasattr(response, "aclose"):
                        await response.aclose()
                    return full_text

                if chunk and chunk.choices and chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    full_text += text_chunk
                    if stream_handler:
                        try:
                            await stream_handler(full_text)
                        except TypeError:
                            pass
        except asyncio.CancelledError:
            return full_text

        return full_text

    for attempt in range(1, max_retries + 1):
        try:
            # Define reusable stop response
            stop_response = {
                "status": "stopped",
                "message": "Processing stopped by user",
            }

            # Check if cancelled before starting
            if controller.stop_requested:
                return stop_response

            # Create task and wrap with controller
            response_llm = litellm.acompletion(
                model=model,
                messages=[{"content": optimized_prompt, "role": "user"}],
                stream=stream,
                **litellm_kwargs,
            )

            try:
                # Process the LLM response with timeout
                response = await asyncio.wait_for(response_llm, timeout=120)

                # Handle streaming or non-streaming response
                if stream:
                    text = await controller.run_cancellable(process_stream(response))
                    if controller.stop_requested:
                        return stop_response
                else:
                    text = response.choices[0].message.content
            except asyncio.CancelledError:
                return stop_response

            dict_block = extract_code_block(text)
            json_block = json.loads(dict_block)

            if validate_model:
                validate_model.model_validate(json_block)

            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "wb") as f:
                tomli_w.dump(json_block, f)

            return {"status": "success", "data": json_block, "output_file": output_file}

        except Exception as e:
            raise

        if attempt < max_retries:
            display_text_panel(text=f"Retrying ({attempt}/{max_retries})...")

    display_text_panel(text=f"Failed to process response after {max_retries} attempts.")
    raise Exception("Max retries exceeded")


@log_async_function
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
    logger.info(
        "Starting plan generation process",
        extra={"model": model, "retry": retry},
    )

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
        logger.info(
            "Plan generation completed",
            extra={
                "output_file": str(output_folder / "plan.toml"),
            },
        )
        return response
    except Exception as e:
        return {"status": "error", "message": str(e)}


@log_async_function
async def get_todo(
    output_folder: Path,
    model: str,
    retry: int,
    todo: dict,
    stream_handler: Optional[Callable[[str], Awaitable[Any]]] = None,
    **litellm_kwargs,
) -> dict:
    """Execute todo generation process."""
    logger.info(
        "Starting todo generation process",
        extra={"model": model, "retry": retry},
    )

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

        logger.info(
            "Todo generation completed",
            extra={
                "output_files": [
                    str(output_folder / "todo.toml"),
                    str(output_folder / "todo.md"),
                    str(output_folder / "todo.json"),
                ],
            },
        )
        return response
    except Exception as e:
        return {"status": "error", "message": str(e)}


@trace_function
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


@trace_function
def prepare_answers(input_folder: Path) -> dict:
    """
    Read and validate the plan form from input folder.

    Creates a default plan if the file doesn't exist.

    Args:
        input_folder: Path to the input folder containing plan.toml

    Returns:
        dict: The answers data dictionary
    """
    plan_file = input_folder / "plan.toml"

    # if not plan_file.exists():
    #     logger.warning(
    #         f"plan.toml not found in {input_folder}, using default template",
    #         extra={"input_path": str(input_folder)},
    #     )
    #     # Return a minimal default plan structure
    #     return {
    #         "project": {
    #             "name": "New Project",
    #             "description": "Default project template",
    #         },
    #         "settings": {"language": "python", "framework": "none"},
    #     }

    try:
        with open(plan_file, "rb") as f:
            answers_data = tomllib.load(f)
        return answers_data
    except Exception as e:
        raise logger.error(f"Error reading plan.toml: {str(e)}")
        # raise


@log_async_function
async def get_all(
    input_folder: Path,
    output_folder: Path,
    model: str,
    retry: int,
    stream_handler: Optional[Callable[[str], Awaitable[Any]]] = None,
    **litellm_kwargs,
) -> Tuple[dict, dict]:
    """Generate both plan and todo documents in sequence with streaming support."""
    logger.info(
        "Starting combined plan and todo generation",
        extra={
            "model": model,
            "retry": retry,
            "input_folder": str(input_folder),
            "output_folder": str(output_folder),
        },
    )

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
    if plan_response.get("status") in ["exit", "error", "stopped"]:
        logger.warning(
            "Plan generation stopped or failed",
            extra={"status": plan_response.get("status")},
        )
        return plan_response, {"status": "skipped"}

    # Check if streaming was stopped during plan generation
    state = AppState.get_instance()
    if state.stop_requested:
        logger.info(
            "Processing stopped by user during plan generation",
        )
        return plan_response, {"status": "stopped"}

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

    logger.info(
        "Combined generation completed",
        extra={
            "plan_status": plan_response.get("status"),
            "todo_status": todo_response.get("status"),
        },
    )
    return plan_response, todo_response
