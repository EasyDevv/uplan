# uplan/init.py
# Handles application initialization, form copying, and validation.

import asyncio
import shutil
import tomllib
from pathlib import Path
from typing import List

# Use aiofiles for async file operations where appropriate (though less needed here now)
# import aiofiles
from uplan.models.todo import TodoModel
from uplan.services.litellm_service import (  # Import from the new service
    update_litellm_models,
    get_models_by_provider,  # Keep this if needed elsewhere, otherwise remove
)
from uplan.utils.logging import get_logger, trace

# Use rich logger from utils
logger = get_logger()

# --- Configuration Paths ---
# Keep paths relevant to this module's responsibilities
DEFAULT_CONFIG_DIR = Path.cwd() / "input"
FORMS_DIR = Path(__file__).parent / "forms"
DEFAULT_FORM_SUBDIR = "dev"


@trace
def _copy_forms(target_dir: Path, source_dir: Path, force: bool) -> None:
    """Copies form files from source to target directory."""
    if target_dir.exists():
        if not force:
            logger.info(
                f"Form directory {target_dir} already exists. Skipping copy.",
                extra={"target_dir": str(target_dir), "force": force},
            )
            return  # Skip copying if not forcing
        else:
            logger.info(
                f"Removing existing form directory {target_dir} due to force=True.",
                extra={"target_dir": str(target_dir), "force": force},
            )
            try:
                shutil.rmtree(target_dir)
            except OSError as e:
                logger.error(
                    f"Error removing directory {target_dir}: {e}",
                    extra={"target_dir": str(target_dir)},
                )
                raise  # Re-raise error if removal fails

    # Proceed with copying if directory doesn't exist or was just removed
    logger.info(
        f"Copying form directory from {source_dir} to {target_dir}...",
        extra={
            "source_dir": str(source_dir),
            "target_dir": str(target_dir),
        },
    )
    try:
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, target_dir)
        logger.info(
            f"Successfully copied forms to {target_dir}",
            extra={"target_dir": str(target_dir)},
        )
    except Exception as e:
        logger.exception(
            f"Failed to copy forms from {source_dir} to {target_dir}",
            extra={"source_dir": str(source_dir), "target_dir": str(target_dir)},
        )
        raise  # Re-raise copy error


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
    logger.info(
        f"Initializing configuration (force={force}, form_dir='{form_dir}')...",
        extra={"force": force, "form_dir": form_dir},
    )

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
        logger.exception(
            f"Form initialization failed for form_dir '{form_dir}': {e}",
            extra={"form_dir": form_dir},
        )
        # Decide if we should stop initialization or continue
        # For now, log and continue to LiteLLM update

    # 2. Run async LiteLLM update tasks
    try:
        logger.info("Starting async LiteLLM model update...")
        # Await the async update function directly since we are in an async context
        await update_litellm_models(force)
        logger.info("Async LiteLLM model update finished.")
    except RuntimeError as e:
        if "cannot run loop while another loop is running" in str(e):
            logger.warning(
                "Asyncio loop already running. Cannot run LiteLLM update from this context. "
                "Consider calling update_litellm_models directly from an async context if needed.",
                extra={"error": str(e)},
            )
        else:
            logger.error(
                f"RuntimeError during async LiteLLM update: {e}",
                extra={"error": str(e)},
            )
            # Decide if this is critical and should raise
    except Exception as task_error:
        logger.error(
            f"Error during async LiteLLM update: {task_error}",
            extra={"error": str(task_error)},
        )
        # Decide if this is critical and should raise

    logger.info("Initialization process completed.")


@trace
def validate_forms(category: str) -> None:
    """Validates TOML files in the specified input category directory."""
    input_dir = DEFAULT_CONFIG_DIR / category
    logger.info(
        f"Validating TOML files in directory: {input_dir}",
        extra={"input_dir": str(input_dir), "category": category},
    )

    try:
        if not input_dir.is_dir():
            raise ValueError(
                f"Input directory '{input_dir}' not found or is not a directory."
            )

        toml_files_found = False
        for file_path in input_dir.glob("*.toml"):
            toml_files_found = True
            logger.debug(
                f"Validating file: {file_path}", extra={"file_path": str(file_path)}
            )
            try:
                # Reading TOML files synchronously is often acceptable
                with open(file_path, "rb") as f:
                    data = tomllib.load(f)
                logger.info(
                    f"Successfully parsed TOML file: {file_path.name}",
                    extra={"file_path": str(file_path)},
                )

                # Specific validation for todo.toml using Pydantic model
                if file_path.name == "todo.toml":
                    logger.debug(
                        f"Performing Pydantic validation for {file_path.name} using TodoModel...",
                        extra={"file_path": str(file_path)},
                    )
                    try:
                        # Extract the 'template' section before validation
                        template_data = data.get("template", {})
                        if not isinstance(template_data, dict):
                            raise TypeError(
                                "Expected 'template' section to be a dictionary."
                            )

                        TodoModel(template_data)  # Validate only the template data
                        logger.info(
                            f"Pydantic validation successful for template section in {file_path.name}",
                            extra={"file_path": str(file_path)},
                        )
                    except (
                        Exception
                    ) as pydantic_error:  # Catch generic Exception for Pydantic errors
                        logger.error(
                            f"Pydantic validation failed for {file_path.name}: {pydantic_error}",
                            extra={
                                "file_path": str(file_path),
                                "error": str(
                                    pydantic_error
                                ),  # Log the specific Pydantic error
                            },
                        )
                        # Optionally re-raise or handle validation failure

            except tomllib.TOMLDecodeError as e:
                logger.error(
                    f"Invalid TOML format in {file_path}: {e}",
                    extra={"file_path": str(file_path)},
                )
            except IOError as e:
                logger.error(
                    f"Could not read file {file_path}: {e}",
                    extra={"file_path": str(file_path)},
                )
            except Exception as e:
                logger.exception(
                    f"An unexpected error occurred while validating {file_path}",
                    extra={"file_path": str(file_path)},
                )

        if not toml_files_found:
            logger.warning(
                f"No .toml files found in directory: {input_dir}",
                extra={"input_dir": str(input_dir)},
            )

    except ValueError as e:
        logger.error(f"Validation setup failed: {e}", extra={"category": category})
        # raise # Re-raise if directory not found is critical
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred during the validation process for category '{category}'",
            extra={"category": category},
        )


# Note: get_models_by_provider is now in litellm_service.py and should be imported/used from there if needed.
# The if __name__ == "__main__": block has been removed.
# Use CLI commands or dedicated test scripts for execution.
