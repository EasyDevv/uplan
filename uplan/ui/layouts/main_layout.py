"""Main layout component for the UPlan GUI."""

from pathlib import Path

from nicegui import ui

from uplan.ui.state import AppState
from uplan.utils.data import toml_to_markdown


def create_main_layout(state: AppState) -> None:
    """Create the main two-panel layout.

    Args:
        state: Application state instance
    """
    ui.colors(
        primary="oklch(58% 0.233 277.117)",
        secondary="oklch(65% 0.241 354.308)",
        accent="oklch(77% 0.152 181.912)",
        dark="oklch(14% 0.005 285.823)",
        dark_page="oklch(25.33% 0.016 252.42)",
        positive="oklch(76% 0.177 163.223)",
        negative="oklch(71% 0.194 13.428)",
        info="oklch(74% 0.16 232.661)",
        warning="oklch(82% 0.189 84.429)",
        base_100="oklch(25.33% 0.016 252.42)",
        base_200="oklch(23.26% 0.014 253.1)",
        base_300="oklch(21.15% 0.012 254.09)",
        base_content="oklch(97.807% 0.029 256.847)",
        primary_content="oklch(96% 0.018 272.314)",
        secondary_content="oklch(94% 0.028 342.258)",
        accent_content="oklch(38% 0.063 188.416)",
        neutral_content="oklch(92% 0.004 286.32)",
        info_content="oklch(29% 0.066 243.157)",
        success_content="oklch(37% 0.077 168.94)",
        warning_content="oklch(41% 0.112 45.904)",
        error_content="oklch(27% 0.105 12.094)",
    )

    # Apply global styles
    ui.add_head_html("""
        <style type="text/tailwindcss">
            :root {
                --radius-selector: 0.5rem;
                --radius-field: 0.25rem;
                --radius-box: 0.5rem;
                --size-selector: 0.25rem;
                --size-field: 0.25rem;
                --border: 1px;
                --depth: 1;
                --noise: 0;
            }
        </style>
    """)
    ui.card.default_classes(
        replace="block p-6 shadow-sm bg-base-200 border-base-300 border-radius-box"
    )

    ui.button.default_classes(replace="shadow-sm")

    # Header with project name and GitHub link
    with ui.header().classes("bg-base-200"):
        with ui.row().classes("w-full justify-between"):
            ui.label("UPlan - Project Planning Assistant").classes("text-xl font-bold")
            ui.button(icon="home")

    # Left drawer for Questions panel
    with ui.left_drawer(top_corner=True, bottom_corner=True).classes(
        "drawer-side bg-base-200 w-64"
    ):
        ui.label("Questions").classes("drawer-title text-xl font-bold")

    # Right drawer for Options panel
    with ui.right_drawer(top_corner=True, bottom_corner=True).classes(
        "drawer-side bg-base-200 w-64"
    ):
        ui.label("Options").classes("drawer-title text-xl font-bold")

    # Main content area for LLM Response
    with ui.column().classes("p-4 bg-base-100 w-full"):
        # with ui.element("div").classes("card w-full"):
        with ui.card().classes("w-full"):
            ui.label("Generated Content").classes("card-title")

    # Footer
    with ui.footer().classes(
        "footer footer-center bg-base-200 text-base-content border-t border-base-300 p-2"
    ):
        ui.label("© 2025 UPlan").classes("text-sm")
