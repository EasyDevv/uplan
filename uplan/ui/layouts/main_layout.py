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
    # Apply global styles
    ui.add_head_html("""
        <style>
            /* DaisyUI Theme System */
            :root {
                /* Base Colors */
                --color-base-100: oklch(25.33% 0.016 252.42);
                --color-base-200: oklch(23.26% 0.014 253.1);
                --color-base-300: oklch(21.15% 0.012 254.09);
                --color-base-content: oklch(97.807% 0.029 256.847);

                /* Theme Colors */
                --color-primary: oklch(58% 0.233 277.117);
                --color-primary-content: oklch(96% 0.018 272.314);
                --color-secondary: oklch(65% 0.241 354.308);
                --color-secondary-content: oklch(94% 0.028 342.258);
                --color-accent: oklch(77% 0.152 181.912);
                --color-accent-content: oklch(38% 0.063 188.416);
                --color-neutral: oklch(14% 0.005 285.823);
                --color-neutral-content: oklch(92% 0.004 286.32);

                /* Design Tokens */
                --radius-box: 0.5rem;
                --radius-field: 0.25rem;
                --border-width: 1px;
                --depth: 1;
            }

            /* Base styles */
            body {
                background-color: var(--color-base-100);
                color: var(--color-base-content);
            }

            /* Typography */
            h1, h2, h3, h4, h5, h6 {
                color: var(--color-base-content);
            }

            /* Components */
            .response-card {
                background-color: var(--color-base-200);
                border: var(--border-width) solid var(--color-base-300);
                border-radius: var(--radius-box);
                box-shadow: 0 calc(var(--depth) * 2px) calc(var(--depth) * 4px) rgba(0, 0, 0, 0.1);
            }

            /* Interactive Elements */
            .q-btn {
                background-color: var(--color-primary) !important;
                color: var(--color-primary-content) !important;
                border-radius: var(--radius-field);
                transition: all 0.2s ease;
            }
            .q-btn:hover {
                background-color: var(--color-secondary) !important;
                color: var(--color-secondary-content) !important;
                transform: translateY(-1px);
            }
        </style>
    """)

    # Header with project name and GitHub link
    with ui.header().classes(
        "bg-[var(--color-base-200)] text-[var(--color-base-content)]"
    ):
        with ui.row().classes("w-full items-center justify-between p-4"):
            ui.label("UPlan - Project Planning Assistant").classes(
                "text-xl font-bold text-[var(--color-base-content)]"
            )
            ui.button(
                icon="mdi-github",
            ).classes("text-white")

    # Left drawer for Questions panel
    with ui.left_drawer(top_corner=True, bottom_corner=True).classes(
        "bg-[var(--color-base-200)] w-64 p-4 border-r border-[var(--color-base-300)]"
    ):
        ui.label("Questions").classes("text-xl font-bold mb-4")

    # Right drawer for Options panel
    with ui.right_drawer(top_corner=True, bottom_corner=True).classes(
        "bg-[var(--color-base-200)] w-64 p-4 border-l border-[var(--color-base-300)]"
    ):
        ui.label("Options").classes("text-xl font-bold mb-4")

    # Main content area for LLM Response
    with ui.column().classes("w-full p-4 flex-grow"):
        with ui.card().classes(
            "response-card w-full h-full bg-[var(--color-base-200)]"
        ):
            ui.label("Generated Content").classes(
                "text-xl font-bold mb-4 text-[var(--color-base-content)]"
            )
            with ui.scroll_area().classes("h-full"):
                ui.markdown("No plan generated yet...").bind_content_from(
                    state, "plan_content"
                )
                ui.markdown("No todo list generated yet...").bind_content_from(
                    state, "todo_content"
                )

    # Footer
    with ui.footer().classes(
        "bg-[var(--color-base-200)] text-[var(--color-neutral-content)] border-t border-[var(--color-base-300)] flex justify-center items-center p-2"
    ):
        ui.label("© 2025 UPlan").classes("text-sm")
