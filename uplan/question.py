from typing import Any, Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from uplan.utils.display import display_text_panel


class QuestionBuilder:
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def ask_question_with_panel(
        self,
        question: str,
        description: str,
        default: str,
        required: bool = False,
        title: str = "Question",
        **panel_kwargs,
    ) -> str:
        """질문을 패널 형태로 출력하고 사용자 입력을 받음"""
        content = f"{question}{f'\n[dim]- {description}[/dim]' if description else ''}"
        panel = Panel(content, title=title, **panel_kwargs)
        self.console.print(panel)

        prompt_text = f"[dim]default: [blue]{default}[/blue][/dim]"

        while True:
            answer = Prompt.ask(
                prompt_text, default=default, show_default=False
            ).strip()

            if answer == default:
                return False, default

            return True, answer


def collect_answers(
    template: Dict[str, Any],
    default_value: str = "<select>",
    question_builder: Optional[QuestionBuilder] = None,
):
    qb = question_builder or QuestionBuilder()
    responses = {}
    only_answers = {}

    for section, questions in template.items():
        responses[section] = {}
        for key, q in questions.items():
            ask = q.get("ask", key)
            required = q.get("required", False)
            default = q.get("default", default_value)
            description = q.get("description", "")

            if not required:
                responses[section][key] = default + f" (e.g., {description})"

            else:
                status, answer = qb.ask_question_with_panel(
                    title=section,
                    question=ask,
                    description=description,
                    default=default,
                    required=required,
                )

                if status:
                    if section not in only_answers:
                        only_answers[section] = {}
                    only_answers[section][key] = answer

                responses[section][key] = default + f" (e.g., {description})"

    return responses, only_answers


def select_option(choices, text, **panel_kwargs):
    display_text_panel(text=text, **panel_kwargs)

    prompt_text = f"[dim]default: [blue]{choices[0]}[/blue][/dim]"

    answer = Prompt.ask(
        prompt_text,
        choices=choices,
        default=choices[0],
        case_sensitive=False,
        show_choices=False,
        show_default=False,
    )
    return answer


if __name__ == "__main__":
    # import tomllib
    # import json
    # from rich.json import JSON
    # from rich import print

    # with open("./templates/dev/plan.toml", "rb") as f:
    #     data = tomllib.load(f)

    # # print(data.get("questions"))

    # response = collect_answers_from_template(data.get("questions"))

    # dumped = json.dumps(response)
    # string = JSON(dumped)
    # print(Panel(string, title="responses", border_style="green"))
    answer = select_option(
        text="생성된 문서를 검토해주세요 [dim]\n- 진행 : Enter or Y \n- 재생성 : R \n- 종료 : X[dim]",
        choices=["y", "r", "x"],
    )
    print(answer)
