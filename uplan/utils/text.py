"""
Module for text processing and code extraction.
"""

import re


def extract_code_block(doc: str) -> str | None:
    """
    Extract the content between triple backticks in the given document.

    Args:
        doc (str): The contents of the document.

    Returns:
        str | None: The extracted content (trimmed) or None if no code block is found.
    """
    pattern = r"```(?:\w+\n)?(.*?)```"
    match = re.search(pattern, doc, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def dict_to_xml(d, xml_indent=""):
    result = ""

    for key, value in d.items():
        result += f"{xml_indent}<{key}>"
        result += str(value)

        result += f"</{key}>\n"

    return result


def optimize_for_prompt(text: str) -> str:
    text = re.sub(r"\s+", "", text)

    return text
