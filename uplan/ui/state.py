"""Application state management."""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class AppState:
    """Application state container.

    Manages global application state including:
    - Model configuration
    - Processing status
    - Error states
    - LLM response data
    """

    # Model configuration
    model: str = "ollama/qwq"
    input_path: str = "./input"
    output_path: str = "./output"
    retry: int = 5

    # Processing state
    processing: bool = False
    error_message: Optional[str] = None

    # Response data
    llm_response: Dict = field(default_factory=dict)
