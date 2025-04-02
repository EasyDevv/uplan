# examples/test_initialization.py
"""
Example script to test the application initialization process.

This script demonstrates how to:
1. Run the main initialization function (`initialize`) which copies forms
   and updates LiteLLM model data.
2. Run the form validation function (`validate_forms`).
3. Optionally, fetch models for a specific provider using the service.
"""

import asyncio
import sys
from pathlib import Path
import logging

# Ensure the 'uplan' package is in the Python path
# This is often needed when running examples from a subdirectory
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the necessary functions/modules AFTER adjusting sys.path
try:
    from uplan.init import initialize, validate_forms
    from uplan.services.litellm_service import get_models_by_provider
    from uplan.utils.logging import setup_logging  # Assuming setup_logging exists

    # Configure logging for the example
    setup_logging()
    logger = logging.getLogger(__name__)  # Use standard logging after setup

except ImportError as e:
    print(f"Error importing uplan modules: {e}")
    print(
        "Ensure you are running this script from the project root directory or have the 'uplan' package installed."
    )
    sys.exit(1)


async def main():
    """Main asynchronous function to run the tests."""
    logger.info("--- Starting Initialization Test ---")

    # --- Test 1: Run Initialization ---
    # Set force=True to ensure files are downloaded/copied even if they exist.
    # Set force=False to test the skipping logic if files already exist.
    force_init = False
    form_category = "dev"
    try:
        # initialize() is now async, so we await it directly within our async main()
        await initialize(force=force_init, form_dir=form_category)
    except Exception as e:
        logger.exception(f"Initialization failed: {e}")
        # Decide if the script should stop if initialization fails

    logger.info("-" * 20)

    # --- Test 2: Validate Forms ---
    logger.info(f"Running validate_forms(category='{form_category}')...")
    try:
        validate_forms(category=form_category)
        # Note: This will still log errors for invalid files (like the Pydantic error seen before)
    except Exception as e:
        logger.exception(f"Form validation failed: {e}")

    logger.info("-" * 20)

    # --- Test 3: Get Models by Provider (Optional) ---
    provider_to_test = "openai"
    logger.info(f"Attempting to get models for provider: '{provider_to_test}'...")
    try:
        # get_models_by_provider is async, so needs await
        models = await get_models_by_provider(provider_to_test)
        if models:
            logger.info(f"Found models for '{provider_to_test}': {models}")
        else:
            logger.warning(
                f"No models found for '{provider_to_test}' or file missing/invalid."
            )
    except FileNotFoundError:
        logger.error("LiteLLM models file not found. Run initialize() first.")
    except Exception as e:
        logger.exception(f"Error getting models for provider '{provider_to_test}': {e}")

    logger.info("--- Initialization Test Finished ---")


if __name__ == "__main__":
    # Run the main async function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Script interrupted by user.")
    except Exception as e:
        logger.exception(
            f"An unexpected error occurred in the main execution block: {e}"
        )
