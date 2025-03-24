"""Main layout component for the UPlan GUI."""

from pathlib import Path

from nicegui import ui

from uplan.ui.state import AppState
from uplan.utils.data import toml_to_markdown, load_toml_file


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
                     
            .nicegui-content {
                padding: 0;
                overflow: hidden;
            }
                     
            .scroll-container {
                overflow-y: auto;
                height: 100vh;
                width: 100%;
                padding: 1rem;
            }
                             
        </style>
    """)

    # ui.query(".nicegui-content").classes("p-0")
    ui.card.default_classes(
        replace="block p-1 shadow-sm bg-base-200 border-base-300 border-radius-box"
    )

    ui.input.default_props("outlined")

    # Main container
    with ui.element("div").classes("flex flex-col h-screen w-full"):
        # Header (10% height)
        # with ui.element("div").classes(
        #     "w-full h-[4%] bg-base-300 flex items-center justify-center"
        # ):
        #     ui.label("UPlan - Project Planning Assistant").classes("text-xl font-bold")

        # Content area with sidebars
        with ui.element("div").classes("flex flex-grow"):
            # Left sidebar (20% width)
            with ui.element("div").classes("w-[30%] bg-base-200 p-4"):
                ui.label("Questions").classes("text-xl font-bold p-1")

                # Load form structure from TOML
                form_data = load_toml_file(Path("uplan/forms/dev/plan.toml"))

                # Create a scrollable container for the form
                with ui.element("div").classes("scroll-container"):
                    with ui.element("div").classes("mb-20"):
                        # Organize questions by section
                        sections = {}
                        for key, value in form_data.get("form", {}).items():
                            section_name = key
                            if isinstance(value, dict):
                                sections[section_name] = value

                        # Create expansion panels for each section
                        for section_name, section_data in sections.items():
                            with ui.expansion(
                                f"{section_name.replace('_', ' ').title()}", value=True
                            ).classes("w-full"):
                                for field_name, field_data in section_data.items():
                                    # Create a card for each question
                                    with ui.card().classes("w-full"):
                                        ui.label(field_data.get("ask", "")).classes(
                                            "text-sm font-medium mb-1"
                                        )
                                        if field_data.get("description"):
                                            desc = field_data.get("description", "")
                                            ui.label(desc).classes(
                                                "text-x mb-4 text-gray-300 hover:text-clip"
                                            ).tooltip(desc)
                                        ui.input(placeholder="AI will select").classes(
                                            "w-full"
                                        )
                                        if field_data.get("required", False):
                                            ui.label("Recommended input").classes(
                                                "text-xs mt-2 text-warning"
                                            )

            # Main content area (60% width)
            with ui.element("div").classes("w-[40%] flex flex-col"):
                # Main content
                with ui.element("div").classes("flex-grow bg-base-100 p-4"):
                    with ui.card().classes("w-full h-full"):
                        ui.label("Generated Content").classes("card-title")
                # Footer (10% height)
                with ui.element("div").classes(
                    "h-[4%] bg-base-300 flex items-center justify-center"
                ):
                    ui.label("© 2025 UPlan").classes("text-sm")

            # Right sidebar (20% width)
            with ui.element("div").classes("w-[30%] bg-base-200 p-4"):
                ui.label("Options").classes("text-xl font-bold")

        # Footer
        # with ui.element("footer").classes(
        #     "col-span-full bg-base-200 text-base-content p-2 text-center"
        # ):
        #     ui.label("© 2025 UPlan").classes("text-sm")
