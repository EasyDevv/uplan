import json
import os
from pathlib import Path
from typing import AsyncGenerator

import tomli_w
import tomllib
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from uplan.gui_process import get_plan, get_todo, prepare_todo

app = FastAPI()
ROOT_PATH = Path(__file__).parent

templates = Jinja2Templates(directory=ROOT_PATH / "templates")

if _debug := os.getenv("DEBUG"):
    import arel

    print("Debug mode is on")

    hot_reload = arel.HotReload(paths=[arel.Path(".")])
    app.add_websocket_route("/hot-reload", route=hot_reload, name="hot-reload")
    app.add_event_handler("startup", hot_reload.startup)
    app.add_event_handler("shutdown", hot_reload.shutdown)
    templates.env.globals["DEBUG"] = _debug
    templates.env.globals["hot_reload"] = hot_reload


# Load questions from plan.toml
PLAN_FORM = tomllib.load(open(ROOT_PATH / "forms/dev/plan.toml", "rb")).get("form", {})


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Renders the initial index page with the question form.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "form": PLAN_FORM,
            "plan": None,
            "todos": None,
        },
    )


async def stream_plan_generator(
    answers_data: dict, model: str, output_folder: Path
) -> AsyncGenerator[str, None]:
    """
    Generator for streaming plan generation results as SSE events.

    Args:
        answers_data: Dictionary containing form answers
        model: Name of the LLM model to use
        output_folder: Path where generated plan will be saved

    Yields:
        SSE formatted strings containing either:
        - Chunks of generated text
        - Error messages if something goes wrong
        - Done signal when generation is complete

    Format of SSE events:
        - Normal chunk: data: {"text": "chunk content"}
        - Error: data: {"error": "error message"}
        - Complete: data: {"done": true}
    """
    accumulated_text = ""

    def handle_stream(chunk: str) -> str:
        """Process each chunk from the LLM stream."""
        nonlocal accumulated_text
        accumulated_text += chunk
        return f"data: {json.dumps({'text': chunk})}\n\n"

    try:
        # Configure plan generation with streaming
        plan_response = get_plan(
            output_folder=output_folder,
            model=model,
            retry=3,
            answers_data=answers_data,
            stream=True,
            stream_handler=handle_stream,
        )

        # Handle any errors from plan generation
        if plan_response["status"] != "success":
            error_msg = plan_response.get(
                "message", "Unknown error during plan generation"
            )
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
            return

        # Signal successful completion
        yield 'data: {"done": true}\n\n'

    except Exception as e:
        # Handle any unexpected errors during streaming
        error_msg = f"Error during plan generation: {str(e)}"
        yield f"data: {json.dumps({'error': error_msg})}\n\n"


@app.post("/generate-plan")
async def generate_plan(request: Request):
    """
    Generates a new plan based on form data with server-sent events streaming.

    The endpoint:
    1. Processes form data to extract answers and model selection
    2. Sets up server-sent events streaming
    3. Returns a StreamingResponse that yields plan generation progress

    Returns:
        StreamingResponse: Server-sent events stream containing:
        - Generated text chunks
        - Error messages if generation fails
        - Completion signal when done
    """
    output_folder = Path(os.getenv("UPLAN_OUTPUT_FOLDER", "output/dev_kr"))

    # Get answers and model data from request body
    form_data = await request.form()
    answers_data = {}
    model = form_data.get("model", "gpt-3.5-turbo")

    # Extract answers from form data
    for key, value in form_data.items():
        if key.startswith("answers."):
            _, section, name = key.split(".", 2)
            if section not in answers_data:
                answers_data[section] = {}
            answers_data[section][name] = value

    # Return streaming response
    return StreamingResponse(
        stream_plan_generator(answers_data, model, output_folder),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )


@app.post("/update-plan/{section}")
async def update_plan_section(request: Request, section: str):
    """
    Updates a specific section of the plan with edited content.
    """
    output_folder = Path(os.getenv("UPLAN_OUTPUT_FOLDER", "output/dev_kr"))
    plan_file = output_folder / "plan.toml"

    try:
        # Read current plan
        current_plan = {}
        if plan_file.exists():
            with open(plan_file, "rb") as f:
                current_plan = tomllib.load(f)

        # Get updated content
        content = await request.body()
        updated_content = json.loads(content)

        # Update specific section
        current_plan[section] = updated_content

        # Save updated plan
        with open(plan_file, "w") as f:
            tomli_w.dump(current_plan, f)

        return templates.TemplateResponse(
            "plan.html", {"request": request, "plan": current_plan}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating plan: {str(e)}",
        )


@app.post("/generate-todo")
async def generate_todo(request: Request):
    """
    Generates todo items based on the current plan.
    """
    input_folder = Path(os.getenv("UPLAN_INPUT_FOLDER", "input/dev_kr"))
    output_folder = Path(os.getenv("UPLAN_OUTPUT_FOLDER", "output/dev_kr"))

    todo = prepare_todo(input_folder, output_folder)
    todo_response = get_todo(
        output_folder=output_folder, model="gpt-3.5-turbo", retry=3, todo=todo
    )

    if todo_response["status"] != "success":
        raise HTTPException(
            status_code=500,
            detail=f"Error generating todos: {todo_response.get('message', 'Unknown error')}",
        )

    return templates.TemplateResponse(
        "todo.html", {"request": request, "todos": todo_response["data"]}
    )


@app.post("/complete/{task_id}")
async def complete_task(task_id: int):
    """
    Marks a todo task as complete.
    """
    return Response(status_code=204)


# For development
if __name__ == "__main__":
    # print(f"{ROOT_PATH}/templates")

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        # reload_includes=["*.html", "*.css"],
    )
