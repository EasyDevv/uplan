"""State management service for the application.

Provides centralized state management and UI update functionality.
"""

from typing import Any, Callable, Optional

from nicegui import app

from uplan.ui.state import AppState
from uplan.utils.logging import trace


@trace
class StateService:
    """Service for managing application state and UI updates."""

    def __init__(self):
        """Initialize the state service.

        Sets up the state instance and registers with app services.
        """
        self.state = AppState.get_instance()

        # Initialize services dictionary if needed and register service
        if not hasattr(app, "services"):
            app.services = {}
        app.services["state"] = self

    async def update_state(self, **kwargs) -> None:
        """Update state and trigger UI updates.

        Args:
            **kwargs: State attributes to update
        """
        self.state.update(**kwargs)

    async def subscribe_ui_element(
        self,
        element_id: str,
        prop: str,
        state_key: str,
        transform: Optional[Callable[[Any], Any]] = None,
    ) -> None:
        """Subscribe UI element to state changes.

        Args:
            element_id: ID of the UI element to update
            prop: Property of the element to update
            state_key: Key in state to watch
            transform: Optional function to transform state value before update
        """

        def state_callback(state: AppState) -> None:
            value = getattr(state, state_key, None)
            if value is not None:
                if transform:
                    value = transform(value)

                # Update element property through app storage
                if element_id in app.storage.user:
                    app.storage.user[element_id][prop] = value

        # Register the callback
        callback_key = f"{element_id}_{prop}"
        self.state.register_callback(callback_key, state_callback)

    def unsubscribe_ui_element(self, element_id: str, prop: str) -> None:
        """Remove UI element subscription.

        Args:
            element_id: ID of the UI element
            prop: Property that was being updated
        """
        callback_key = f"{element_id}_{prop}"
        self.state.unregister_callback(callback_key)

    async def bind_form_data(self, form_id: str, data: dict) -> None:
        """Bind form data to state.

        Args:
            form_id: Identifier for the form
            data: Form data to store
        """
        form_data = self.state.form_data.copy()
        form_data[form_id] = data
        await self.update_state(form_data=form_data)

    async def get_form_data(self, form_id: str) -> Optional[dict]:
        """Retrieve form data from state.

        Args:
            form_id: Identifier for the form

        Returns:
            Optional[dict]: Form data if found
        """
        return self.state.form_data.get(form_id)

    async def clear_form_data(self, form_id: str) -> None:
        """Clear stored form data.

        Args:
            form_id: Identifier for the form to clear
        """
        form_data = self.state.form_data.copy()
        form_data.pop(form_id, None)
        await self.update_state(form_data=form_data)
