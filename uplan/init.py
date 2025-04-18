# uplan/init.py
# Handles application initialization, form copying, and validation.
#
import shutil
import tomllib
from pathlib import Path

# Use aiofiles for async file operations where appropriate (though less needed here now)
# import aiofiles
from uplan.models.todo import TodoModel
from uplan.services.litellm_service import (  # Import from the new service
    update_litellm_models,
)
from pyhunt import trace

# --- Configuration Paths ---
# Keep paths relevant to this module's responsibilities
DEFAULT_CONFIG_DIR = Path.cwd() / "input"
FORMS_DIR = Path(__file__).parent / "forms"
DEFAULT_FORM_SUBDIR = "dev"

#


@trace
def _copy_forms(target_dir: Path, source_dir: Path, force: bool) -> None:
    """Copies form files from source to target directory."""
    if target_dir.exists():
        if not force:
            return  # Skip copying if not forcing
        else:
            try:
                shutil.rmtree(target_dir)
            except OSError as e:
                raise e

    # Proceed with copying if directory doesn't exist or was just removed
    try:
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, target_dir)
    except Exception as e:
        raise e


@trace
async def initialize(
    force: bool = False, form_dir: str = DEFAULT_FORM_SUBDIR
) -> None:  # Make initialize async
    """
    Initializes the application configuration.

    - Copies necessary form files from the specified form directory.
    - Updates LiteLLM model data asynchronously.

    Args:
        force (bool): If True, overwrite existing form directories and LiteLLM data.
        form_dir (str): The subdirectory within 'uplan/forms' to copy from.
    """
    # 1. Copy form files (Synchronous)
    try:
        source_form_dir = FORMS_DIR / form_dir
        if not source_form_dir.is_dir():
            raise ValueError(
                f"Form directory '{form_dir}' not found or is not a directory in {FORMS_DIR}"
            )

        target_form_dir = DEFAULT_CONFIG_DIR / form_dir
        _copy_forms(target_form_dir, source_form_dir, force)

    except Exception as e:
        raise e

    # 2. Run async LiteLLM update tasks
    try:
        # Await the async update function directly since we are in an async context
        await update_litellm_models(force)
    except RuntimeError as e:
        if "cannot run loop while another loop is running" in str(e):
            pass
        else:
            raise
    except Exception as e:
        raise e


@trace
def validate_forms(category: str) -> None:
    """Validates TOML files in the specified input category directory."""
    input_dir = DEFAULT_CONFIG_DIR / category
    try:
        if not input_dir.is_dir():
            raise ValueError(
                f"Input directory '{input_dir}' not found or is not a directory."
            )

        toml_files_found = False
        for file_path in input_dir.glob("*.toml"):
            toml_files_found = True
            # Reading TOML files synchronously is often acceptable
            with open(file_path, "rb") as f:
                data = tomllib.load(f)

            # Specific validation for todo.toml using Pydantic model
            if file_path.name == "todo.toml":
                # Extract the 'template' section before validation
                template_data = data.get("template", {})
                if not isinstance(template_data, dict):
                    raise TypeError("Expected 'template' section to be a dictionary.")

                TodoModel(template_data)  # Validate only the template data

    except Exception as e:
        raise e
