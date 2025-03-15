from typing import Dict


def add_completed_status(data: Dict) -> Dict:
    for section in data:
        if "tasks" in data[section]:
            data[section]["tasks"] = [
                {"task": task, "completed": False} for task in data[section]["tasks"]
            ]

    return data


def toml_to_markdown(data) -> str:
    """
    Convert TOML data structure to a formatted Markdown string.

    This function dynamically processes TOML data and converts it into a well-structured
    Markdown format with appropriate headers, lists, and formatting based on the content type.

    Args:
        toml_data (dict): A dictionary containing parsed TOML data

    Returns:
        str: A formatted Markdown string representation of the input TOML data
    """
    markdown = ""

    # Iterate through each section
    for section, content in data.items():
        # Convert section name to markdown header (e.g., "environment_setup" -> "Environment Setup")
        section_name = " ".join(word.capitalize() for word in section.split("_"))
        markdown += f"## {section_name}\n\n"

        # Dynamically process section content
        if isinstance(content, dict):
            for key, value in content.items():
                # Format key name (e.g., "frameworks" -> "Frameworks")
                key_name = key.capitalize()
                markdown += f"**{key_name}:**\n"

                # Process arrays as lists
                if isinstance(value, list):
                    for item in value:
                        # Add checkboxes for task lists, use regular bullet points for other lists
                        if key.lower() == "tasks":
                            markdown += f"- [ ] {item}\n"
                        else:
                            markdown += f"- {item}\n"
                # Process single values as plain text
                else:
                    markdown += f"{value}\n"
                markdown += "\n"
        # Handle non-dictionary values
        elif content is not None:
            markdown += f"{content}\n\n"

    return markdown
