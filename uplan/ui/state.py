"""Application state management.

This module implements a reactive singleton state pattern for the application.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, ClassVar, Callable
from uplan.utils.stream import StreamController


@dataclass
class AppState:
    """Single source of truth for application state.

    Implements the singleton pattern to ensure only one state instance exists.
    Provides reactive updates through a callback system.
    """

    # Singleton instance
    _instance: ClassVar[Optional["AppState"]] = None

    # Model and execution configuration
    provider: Optional[str] = None  # Added provider
    model: Optional[str] = (
        None  # Changed default to None, will be set by UI/OptionService
    )
    category: Optional[str] = None  # Added category
    input_path: Optional[str] = None  # Changed default to None
    output_path: Optional[str] = None  # Changed default to None
    max_retries: Optional[int] = 5  # Added max_retries (renamed from retry for clarity)
    operation_type: Optional[str] = None  # Added operation_type

    # Processing state
    processing: bool = False
    error_message: Optional[str] = None
    current_task: Optional[Callable] = None

    # Stream controller for managing streaming operations
    stream_controller: StreamController = field(default_factory=StreamController)

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
        """Reset processing state completely."""
        logging.debug("Resetting processing state")
        self.processing = False
        self.error_message = None
        self.stream_controller.reset()

        for callback in self._on_update_callbacks.values():
            callback(self)

    @property
    def stop_streaming(self) -> bool:
        """Backward compatibility for stop_streaming property."""
        return self.stream_controller.stop_requested

    @stop_streaming.setter
    def stop_streaming(self, value: bool) -> None:
        """Backward compatibility setter for stop_streaming."""
        if value:
            self.stream_controller.request_stop()
        else:
            self.stream_controller.reset()
