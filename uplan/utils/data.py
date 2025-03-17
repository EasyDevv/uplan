from typing import Dict


def add_completed_status(data: Dict) -> Dict:
    """
    Add 'completed' status to all tasks in the data structure.

    This function traverses the data structure and transforms task entries
    by adding a 'completed: False' status to each task. It handles both
    category-based task organization and direct task lists.

    Args:
        data: A dictionary containing sections with tasks or categories of tasks

    Returns:
        The modified dictionary with 'completed' status added to all tasks
    """
    # Iterate through each section in the data
    paths = [
        lambda d, section: d[section]["categories"],
        lambda d, section: [d[section]],
    ]

    for section in data:
        for path_func in paths:
            try:
                containers = path_func(data, section)
                for container in containers:
                    if "tasks" in container:
                        container["tasks"] = [
                            {"task": task, "completed": False}
                            for task in container["tasks"]
                        ]
            except (KeyError, TypeError):
                continue

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
                markdown += f"### {key_name}\n\n"

                # Process arrays as lists
                if isinstance(value, list):
                    # Special handling for categories
                    if key.lower() == "categories":
                        for category in value:
                            if isinstance(category, dict) and "title" in category:
                                markdown += f"\n#### {category['title']}\n"
                                if "tasks" in category:
                                    for task in category["tasks"]:
                                        markdown += f"- [ ] {task}\n"
                                markdown += "\n"
                    # Regular list processing
                    else:
                        for item in value:
                            markdown += f"- {item}\n"
                # Process single values as plain text
                else:
                    markdown += f"{value}\n"
                markdown += "\n"
        # Handle non-dictionary values
        elif content is not None:
            markdown += f"{content}\n\n"

    return markdown
