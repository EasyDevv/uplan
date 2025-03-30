import json

from rich.console import Console
from rich.json import JSON
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from typing import Dict


def display_streaming(stream):
    text = Text()
    panel = Panel(text, title="Streaming Response", border_style="blue")

    with Live(panel, vertical_overflow="visible", refresh_per_second=1) as live:
        for chunk in stream:
            if chunk.choices[0].delta.content:
                text.append(chunk.choices[0].delta.content)
                live.update(panel)

    return text.plain


def display_text_panel(text, **panel_kwargs):
    """
    Display text in a colorful panel using Rich library.

    Args:
        text: The text to be displayed
        **panel_kwargs: Additional keyword arguments for Panel.
            - title (str): The title of the panel (default: None).
            - border_style (str): The style of the panel border (default: "blue").
            - width (int): The width of the panel.
            - height (int): The height of the panel.
            - highlight (bool): Whether to enable text highlighting.

    Returns:
        None: Prints the formatted panel to the console
    """
    console = Console()
    panel = Panel(text, **panel_kwargs)
    console.print(panel)


def display_syntax_panel(
    code: str,
    lexer="python",
    theme="DEFAULT_THEME",
    dedent: bool = True,
    word_wrap: bool = True,
    title: str = "Syntax Data",
    border_style: str = "blue",
):
    """
    Display text in a colorful panel using Rich library.

    Args:
        text: The text to be displayed
        title: The title of the panel (default: "Text Data")
        border_style: The style of the panel border (default: "blue")

    Returns:
        None: Prints the formatted panel to the console
    """
    console = Console()

    syntax = Syntax(code, lexer, theme=theme, dedent=dedent, word_wrap=word_wrap)
    panel = Panel(syntax, title=title, border_style=border_style)
    console.print(panel)


def display_json_panel(data: Dict, **panel_kwargs) -> str:
    """
    Display JSON data in a colorful panel using Rich library.

    Args:
        data: The data to be displayed (will be converted to JSON)
        title: The title of the panel (default: "JSON Data")
        border_style: The style of the panel border (default: "green")

    Returns:
        None: Prints the formatted panel to the console
    """
    console = Console()

    dumped = json.dumps(data)
    json_display = JSON(dumped)
    console.print(Panel(json_display, **panel_kwargs))

    return dumped
