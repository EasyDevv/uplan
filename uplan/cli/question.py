"""CLI specific question and prompting utilities."""

from typing import Any, Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# Removed: from uplan.question import QuestionBuilder (integrated below)
from uplan.utils.display import display_text_panel


class QuestionBuilder:
    """Builds and asks questions, potentially with rich formatting."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize QuestionBuilder.

        Args:
            console: Optional rich Console instance. Creates one if None.
        """
        self.console = console or Console()

    def ask_question_with_panel(
        self,
        question: str,
        description: str,
        default: str,
        required: bool = False,
        title: str = "Question",
        **panel_kwargs,
    ) -> tuple[bool, str]:
        """질문을 패널 형태로 출력하고 사용자 입력을 받음.

        Args:
            question: The main question text.
            description: Additional description or context for the question.
            default: The default value if the user provides no input.
            required: If True, indicates the question requires an answer (visual cue).
            title: The title of the panel.
            **panel_kwargs: Additional keyword arguments for rich.panel.Panel.

        Returns:
            A tuple containing:
            - bool: True if the user provided an answer different from the default, False otherwise.
            - str: The answer provided by the user (or the default).
        """
        content = f"{question}{f'\n[dim]- {description}[/dim]' if description else ''}"
        # Add required marker if applicable
        if required:
            title += " [bold red]*[/bold red]"  # Mark required questions

        # Use provided border_style or default to cyan
        border_style = panel_kwargs.pop("border_style", "cyan")
        panel = Panel(content, title=title, border_style=border_style, **panel_kwargs)
        self.console.print(panel)

        # Construct prompt text, clearly showing the default
        prompt_text = f"➡️ Your answer? [dim](default: [blue]{default}[/blue])[/dim] "

        # Loop for required questions? No, Prompt.ask handles default.
        # We just need to capture the input.
        answer = Prompt.ask(
            prompt_text,
            default=default,
            show_default=False,  # Default is shown in our custom prompt
        ).strip()

        # Determine if the user provided a non-default answer
        user_provided_answer = answer != default and answer != ""

        # Return status and the actual answer (could be the default)
        return user_provided_answer, answer


def collect_answers_cli(
    form: Dict[str, Any],
    default_value: str = "<select>",
    question_builder: Optional[QuestionBuilder] = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Collect answers for a form using CLI prompts."""
    qb = question_builder or QuestionBuilder()  # Uses the local QuestionBuilder
    responses = {}
    only_answers = {}

    for section, questions in form.items():
        responses[section] = {}
        for key, q in questions.items():
            ask = q.get("ask", key)
            required = q.get("required", False)
            default = q.get("default", default_value)
            description = q.get("description", "")
            choices = q.get("choices")  # Get choices if available

            # Always ask in CLI
            status, answer = qb.ask_question_with_panel(
                title=section,
                question=ask,
                description=description,
                default=default,
                required=required,
                border_style="blue",  # Consistent style for collect_answers_cli
                # Note: 'choices' are not directly used by ask_question_with_panel
                # If choices are needed, select_option or a modified ask method is required.
                # For now, assuming text input based on the original logic.
            )

            if status and answer != default:  # User provided a non-default answer
                if section not in only_answers:
                    only_answers[section] = {}
                only_answers[section][key] = answer
                responses[section][key] = answer
            else:
                # Use default or empty if user didn't provide a different answer
                responses[section][key] = default + (
                    f" (e.g., {description})" if description else ""
                )

    return responses, only_answers


def select_option(choices: list[str], text: str, **panel_kwargs) -> str:
    """Display options and get user selection via CLI prompt."""
    display_text_panel(text=text, **panel_kwargs)

    # Ensure choices are strings for Prompt.ask
    str_choices = [str(c) for c in choices]

    # Set default choice, ensuring it's in the list
    default_choice = str_choices[0] if str_choices else None

    prompt_text = f"[dim]Select an option ({'/'.join(str_choices)}) (default: [blue]{default_choice}[/blue]): [/dim]"

    # Handle case where there are no choices
    if not str_choices:
        print("[yellow]Warning: No choices provided for selection.[/yellow]")
        return ""  # Or raise an error

    answer = Prompt.ask(
        prompt_text,
        choices=str_choices,
        default=default_choice,
        show_choices=True,  # Show choices explicitly in CLI
        show_default=False,  # Default is shown in prompt_text
    ).strip()

    # Prompt.ask with choices handles validation
    return answer


# Example usage (for testing this module directly)
if __name__ == "__main__":
    console = Console()
    builder = QuestionBuilder(console)  # Uses the local QuestionBuilder

    # Example form for collect_answers_cli
    example_form = {
        "Project Info": {
            "project_name": {
                "ask": "Project Name?",
                "default": "MyProject",
                "description": "The name of your project",
            },
            "description": {
                "ask": "Project Description?",
                "default": "",
                "required": True,
            },
        },
        "Settings": {
            "language": {
                "ask": "Primary Language?",
                "default": "Python",
                "choices": [
                    "Python",
                    "JavaScript",
                    "Go",
                ],  # Note: collect_answers_cli doesn't use choices yet
            },
            "framework": {"ask": "Framework?", "default": "None"},
        },
    }

    print("[bold cyan]Testing collect_answers_cli:[/bold cyan]")
    all_responses, user_answers = collect_answers_cli(
        example_form, question_builder=builder
    )
    print("\n[bold green]All Responses (including defaults):[/bold green]")
    console.print(all_responses)
    print("\n[bold green]User Provided Answers:[/bold green]")
    console.print(user_answers)

    print("\n" + "=" * 30 + "\n")

    # Example for select_option
    print("[bold cyan]Testing select_option:[/bold cyan]")
    selected = select_option(
        choices=["yes", "no", "maybe"],
        text="Do you want to proceed?",
        title="Confirmation",
        border_style="yellow",
    )
    print(f"\n[bold green]Selected option:[/bold green] {selected}")

    selected_num = select_option(
        choices=["1", "2", "3"],
        text="Choose a number:",
        title="Number Selection",
        border_style="magenta",
    )
    print(f"\n[bold green]Selected number:[/bold green] {selected_num}")
