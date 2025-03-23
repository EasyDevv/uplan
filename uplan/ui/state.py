from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppState:
    """Application state management.

    Manages the state of the application including input form data,
    LLM responses, and processing status.
    """

    current_input: dict = field(default_factory=dict)
    llm_response: dict | None = None
    processing: bool = False
    output_path: Path = field(default_factory=lambda: Path("./output"))
    form_category: str = "dev"
    model: str = "ollama/qwq"
    error_message: str | None = None
    plan_content: str = "No plan generated yet..."
    todo_content: str = "No todo list generated yet..."
