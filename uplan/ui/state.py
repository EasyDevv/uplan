"""Application state management.

This module implements a reactive singleton state pattern for the application.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, ClassVar, Callable


@dataclass
class AppState:
    """Single source of truth for application state.

    Implements the singleton pattern to ensure only one state instance exists.
    Provides reactive updates through a callback system.
    """

    # Singleton instance
    _instance: ClassVar[Optional["AppState"]] = None

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

    # UI state data
    form_data: Dict = field(default_factory=dict)

    # Event callbacks
    _on_update_callbacks: Dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize callback storage."""
        if not hasattr(self, "_on_update_callbacks"):
            self._on_update_callbacks = {}

    @classmethod
    def get_instance(cls) -> "AppState":
        """Get or create the singleton instance.

        Returns:
            AppState: The singleton state instance
        """
        if cls._instance is None:
            cls._instance = AppState()
        return cls._instance

    def register_callback(
        self, key: str, callback: Callable[["AppState"], None]
    ) -> None:
        """Register a callback for state updates.

        Args:
            key: Unique identifier for the callback
            callback: Function to call when state updates
        """
        self._on_update_callbacks[key] = callback

    def unregister_callback(self, key: str) -> None:
        """Remove a registered callback.

        Args:
            key: Identifier of callback to remove
        """
        self._on_update_callbacks.pop(key, None)

    def update(self, **kwargs) -> None:
        """Update state and trigger UI updates.

        Args:
            **kwargs: State attributes to update
        """
        # Update state attributes
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Notify all registered callbacks
        for callback in self._on_update_callbacks.values():
            callback(self)

    def clear_error(self) -> None:
        """Clear any error state."""
        self.error_message = None

    def reset_processing(self) -> None:
        """Reset processing state."""
        self.processing = False
        self.error_message = None
