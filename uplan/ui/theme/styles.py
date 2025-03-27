"""Global style configuration."""

from nicegui import ui


def apply_global_styles() -> None:
    """Apply global styles to the application."""
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

    # Add root CSS variables
    ui.add_head_html("""
        <style>          
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

    # Apply content styles
    ui.query(".nicegui-content").style("padding: 0; overflow: hidden;")
    ui.query(".scroll-container").style("overflow-y: auto; height: 100vh; width: 100%;")

    # Set default component styles
    ui.card.default_classes(
        replace="block p-1 shadow-sm bg-base-200 border-base-300 border-radius-box"
    )
    ui.input.default_props("outlined")
    ui.button.default_style(replace="")
