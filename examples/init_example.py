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

# Ensure the 'uplan' package is in the Python path
# This is often needed when running examples from a subdirectory
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the necessary functions/modules AFTER adjusting sys.path
try:
    from uplan.init import initialize, validate_forms
    from uplan.services.litellm_service import get_models_by_provider
except ImportError as e:
    raise

from pyhunt import trace


@trace
async def main():
    """Main asynchronous function to run the tests."""

    # --- Test 1: Run Initialization ---
    # Set force=True to ensure files are downloaded/copied even if they exist.
    # Set force=False to test the skipping logic if files already exist.
    force_init = False
    form_category = "dev"
    try:
        # initialize() is now async, so we await it directly within our async main()
        await initialize(force=force_init, form_dir=form_category)
    except Exception as e:
        raise
        # Decide if the script should stop if initialization fails

    # --- Test 2: Validate Forms ---
    try:
        validate_forms(category=form_category)
        # Note: This will still log errors for invalid files (like the Pydantic error seen before)
    except Exception as e:
        raise

    # --- Test 3: Get Models by Provider (Optional) ---
    provider_to_test = "openai"
    try:
        # get_models_by_provider is async, so needs await
        models = await get_models_by_provider(provider_to_test)
        if not models:
            pass
    except FileNotFoundError:
        raise
    except Exception as e:
        raise

    # --- Test 4: Get Models by Provider (Ollama - Local API) ---
    provider_to_test = "ollama"
    try:
        # get_models_by_provider is async, so needs await
        models = await get_models_by_provider(provider_to_test)
        if not models:
            pass
    except Exception as e:
        raise


if __name__ == "__main__":
    # Run the main async function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        raise
    except Exception as e:
        raise
