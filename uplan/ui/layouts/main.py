"""Main layout that composes all UI components."""

from nicegui import ui

from uplan.ui.state import AppState
from uplan.ui.theme.styles import apply_global_styles
from uplan.ui.components.header import create_header
from uplan.ui.components.questions import create_questions
from uplan.ui.components.content import create_content
from uplan.ui.components.options import create_options


def create_main_layout(state: AppState) -> None:
    """Create the main two-panel layout.

    Args:
        state: Application state instance
    """
    # Apply theme configuration
    apply_global_styles()

    # Create main container
    with ui.element("div").classes("flex w-full h-screen"):
        # Create layout components
        create_header()

        # Main content wrapper
        with ui.element("div").classes("flex grow"):
            create_questions()
            create_content()
            create_options()
