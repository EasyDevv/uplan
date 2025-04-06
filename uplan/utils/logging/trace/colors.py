from typing import List

DEPTH_COLORS: List[str] = [
    "#b9e97c",
    "#f0e6a8",
    "#fdbb6f",
    "#f58fa8",
    "#99d4f0",
    "#c1a6ff",
    "#f58f8f",
    "#f0e6a8",
    "#b9e97c",
    "#99d4f0",
]


def get_color(depth: int) -> str:
    """Return color hex code based on call depth (1-based)."""
    return DEPTH_COLORS[(depth - 1) % len(DEPTH_COLORS)]


def build_indent(depth: int) -> str:
    """
    Build indentation string with vertical bars and colors based on depth.

    Args:
        depth: Call depth (1-based).

    Returns:
        Indentation string with color-coded bars.
    """
    if depth <= 1:
        return ""
    return "".join(f"[{get_color(i)}]│   [/] " for i in range(1, depth))
