import json
from pathlib import Path
from typing import Dict, List

import aiofiles
import httpx

from uplan.utils.logging import get_logger, trace

logger = get_logger()

# --- Configuration Paths (Relative to project root or input dir) ---
# Consider moving these to a central config if used elsewhere
DEFAULT_CONFIG_DIR = Path.cwd() / "input"  # Assuming input dir is standard
OUTPUT_DIR = Path.cwd() / "output"

# --- LiteLLM Model Data ---
LITELLM_MODELS_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
LITELLM_MODELS_FILENAME = "litellm_models.json"
LITELLM_MODELS_PATH = DEFAULT_CONFIG_DIR / LITELLM_MODELS_FILENAME
PROVIDER_MAP_FILENAME = "model_info.json"
PROVIDER_MAP_PATH = DEFAULT_CONFIG_DIR / PROVIDER_MAP_FILENAME


@trace
async def _download_file_async(url: str) -> bytes:
    """Downloads data asynchronously from the specified URL and returns bytes."""
    logger.info(f"Downloading data from {url}...", extra={"url": url})
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
        logger.info(f"Successfully downloaded data from {url}", extra={"url": url})
        return response.content
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error downloading {url}: {e.response.status_code} - {e.response.text}",
            extra={"url": url, "status_code": e.response.status_code},
        )
        raise
    except httpx.RequestError as e:
        logger.error(f"Network error downloading {url}: {e}", extra={"url": url})
        raise
    except Exception:
        logger.exception(
            f"An unexpected error occurred during download of {url}", extra={"url": url}
        )
        raise  # Re-raise unexpected errors


@trace
async def _generate_provider_model_map_file(
    model_data_content: bytes, output_path: Path
) -> None:
    """Generates a JSON file mapping providers to their models from provided content."""
    logger.info(
        f"Generating provider-model map file at {output_path}...",
        extra={"output_path": str(output_path)},
    )

    provider_map: Dict[str, List[str]] = {}
    try:
        model_data = json.loads(model_data_content.decode("utf-8"))

        if isinstance(model_data, dict):
            for model_name, details in model_data.items():
                if (
                    isinstance(details, dict)
                    and (provider := details.get("litellm_provider"))
                    and details.get("mode") == "chat"  # Filter for chat models
                ):
                    if provider not in provider_map:
                        provider_map[provider] = []
                    provider_map[provider].append(model_name)
            # Sort models within each provider for consistency
            for provider in provider_map:
                provider_map[provider].sort()
        else:
            logger.warning(
                f"Expected dict structure in provided model data, got {type(model_data)}.",
                extra={
                    "output_path": str(output_path),
                    "data_type": str(type(model_data)),
                },
            )
            return  # Cannot proceed if structure is wrong

        # --- Remove any existing 'ollama' entry from downloaded data ---
        if "ollama" in provider_map:
            logger.debug("Removing 'ollama' models derived from downloaded list.")
            del provider_map["ollama"]

        # --- Fetch local Ollama models and add them if found ---
        logger.debug("Attempting to fetch local Ollama models to add to map...")
        local_ollama_models = await _get_local_ollama_models()
        if local_ollama_models:
            # Add the locally found models under the 'ollama' key.
            # Models from _get_local_ollama_models are already sorted.
            provider_map["ollama"] = local_ollama_models
            logger.info(
                f"Added {len(local_ollama_models)} locally detected Ollama models to the provider map.",
                extra={"count": len(local_ollama_models)},
            )
        else:
            logger.info("No local Ollama models found or Ollama API not reachable.")
        # --- End Ollama merge ---

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the map to the output file asynchronously
        async with aiofiles.open(output_path, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(provider_map, indent=4, sort_keys=True))
        logger.info(
            f"Successfully generated provider-model map file: {output_path.name}",
            extra={"output_path": str(output_path)},
        )

    except (IOError, json.JSONDecodeError) as e:
        logger.error(
            f"Error processing model data or writing {output_path}: {e}",
            extra={"output_path": str(output_path)},
        )
        # Decide whether to raise or just log based on application needs
    except Exception as e:
        logger.exception(
            f"Unexpected error generating provider-model map file: {e}",
            extra={"output_path": str(output_path)},
        )
        # Decide whether to raise or just log


@trace
async def update_litellm_models(force: bool = False) -> None:
    """
    Downloads the latest LiteLLM model data, saves it, and generates the
    provider-to-model mapping file.
    """
    logger.info(
        f"Starting LiteLLM model update process (force={force})...",
        extra={"force": force},
    )
    model_content: bytes | None = None
    try:
        # 1. Download LiteLLM models data
        model_content = await _download_file_async(LITELLM_MODELS_URL)

        # 2. Save the downloaded content to LITELLM_MODELS_PATH
        save_required = True
        if LITELLM_MODELS_PATH.exists():
            if force:
                logger.info(
                    f"Removing existing {LITELLM_MODELS_PATH.name} due to force=True.",
                    extra={"file_path": str(LITELLM_MODELS_PATH), "force": force},
                )
                try:
                    LITELLM_MODELS_PATH.unlink()
                except OSError as e:
                    logger.error(
                        f"Error removing existing file {LITELLM_MODELS_PATH}: {e}",
                        extra={"file_path": str(LITELLM_MODELS_PATH)},
                    )
                    # Decide if we should proceed or raise. Let's proceed but log error.
            else:
                logger.info(
                    f"{LITELLM_MODELS_PATH.name} already exists. Skipping save.",
                    extra={"file_path": str(LITELLM_MODELS_PATH)},
                )
                save_required = False

        if save_required and model_content:
            try:
                LITELLM_MODELS_PATH.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(LITELLM_MODELS_PATH, "wb") as f:
                    await f.write(model_content)
                logger.info(
                    f"Successfully saved downloaded data to {LITELLM_MODELS_PATH.name}",
                    extra={"file_path": str(LITELLM_MODELS_PATH)},
                )
            except IOError as e:
                logger.error(
                    f"File error writing to {LITELLM_MODELS_PATH}: {e}",
                    extra={"file_path": str(LITELLM_MODELS_PATH)},
                )
                # Log error but proceed to map generation if content is available

        # 3. Generate the provider-model map file using the downloaded content
        # Ensure we have content, read from file if it wasn't freshly downloaded/saved
        if not model_content and LITELLM_MODELS_PATH.exists():
            try:
                async with aiofiles.open(LITELLM_MODELS_PATH, "rb") as f:
                    model_content = await f.read()
                logger.debug(
                    f"Read existing content from {LITELLM_MODELS_PATH.name} for map generation.",
                    extra={"file_path": str(LITELLM_MODELS_PATH)},
                )
            except IOError as e:
                logger.error(
                    f"Could not read existing {LITELLM_MODELS_PATH} for map generation: {e}",
                    extra={"file_path": str(LITELLM_MODELS_PATH)},
                )
                model_content = None  # Ensure it's None if read fails

        if model_content:
            await _generate_provider_model_map_file(model_content, PROVIDER_MAP_PATH)
        else:
            logger.error(
                "Could not obtain model content to generate provider map file.",
                extra={"output_path": str(PROVIDER_MAP_PATH)},
            )
        logger.info("LiteLLM model update process finished.")

    except Exception as e:
        logger.exception(
            f"An error occurred during the LiteLLM model update process: {e}",
            extra={"force": force},
        )
        # Depending on severity, might want to raise here


@trace
async def _get_local_ollama_models() -> List[str]:
    """Retrieves the list of locally available Ollama models via the API."""
    ollama_api_url = "http://localhost:11434/api/tags"
    logger.debug(f"Attempting to fetch local Ollama models from {ollama_api_url}")
    local_models = []
    try:
        # Use a shorter timeout as it's a local request
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(ollama_api_url)
            response.raise_for_status()  # Raise exception for 4xx/5xx status codes
            data = response.json()
            if (
                isinstance(data, dict)
                and "models" in data
                and isinstance(data["models"], list)
            ):
                for model_info in data["models"]:
                    if isinstance(model_info, dict) and "name" in model_info:
                        # Ollama API returns names like 'llama3:latest', keep them as is.
                        local_models.append(model_info["name"])
                local_models.sort()  # Keep it sorted like other providers
                logger.info(
                    f"Found {len(local_models)} local Ollama models.",
                    extra={"count": len(local_models)},
                )
            else:
                logger.warning(
                    "Unexpected format received from Ollama API /api/tags.",
                    extra={"url": ollama_api_url, "response_type": type(data)},
                )

    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error accessing Ollama API at {ollama_api_url}: {e.response.status_code}",
            extra={"url": ollama_api_url, "status_code": e.response.status_code},
        )
        # Return empty list, maybe Ollama is running but API structure changed or error occurred
    except (httpx.RequestError, ConnectionRefusedError) as e:
        logger.warning(
            f"Could not connect to Ollama API at {ollama_api_url}. Is Ollama running? Error: {e}",
            extra={"url": ollama_api_url},
        )
        # Return empty list if Ollama isn't running or reachable
    except json.JSONDecodeError as e:
        logger.error(
            f"Error decoding JSON response from Ollama API {ollama_api_url}: {e}",
            extra={"url": ollama_api_url},
        )
    except Exception as e:
        logger.exception(
            f"Unexpected error fetching local Ollama models from {ollama_api_url}",
            extra={"url": ollama_api_url},
        )
        # Return empty list on other unexpected errors

    return local_models


@trace
async def get_models_by_provider(provider: str) -> List[str]:
    """
    Retrieves a list of model names for a given provider by reading the
    generated provider-model map file (model_info.json).

    This function relies on the `model_info.json` file being up-to-date,
    which is generated by the `update_litellm_models` function. It includes
    models from the downloaded LiteLLM data and any detected local Ollama models.

    Args:
        provider: The provider string (e.g., 'openai', 'anthropic', 'ollama').
                  Case-sensitive matching is performed against the keys in the map file.

    Returns:
        A sorted list of model names associated with the specified provider found
        in the `model_info.json` file.
        Returns an empty list if the map file doesn't exist, is invalid JSON,
        or the provider is not found in the map.

    Raises:
        IOError: If there's an error reading the `model_info.json` file.
        json.JSONDecodeError: If the `model_info.json` content is not valid JSON.
    """
    if not PROVIDER_MAP_PATH.exists():
        logger.warning(
            f"Provider map file not found at {PROVIDER_MAP_PATH}. Cannot get models for provider '{provider}'. Run initialization first.",
            extra={"file_path": str(PROVIDER_MAP_PATH), "provider": provider},
        )
        return []

    try:
        async with aiofiles.open(PROVIDER_MAP_PATH, mode="r", encoding="utf-8") as f:
            content = await f.read()
        provider_map: Dict[str, List[str]] = json.loads(content)
    except IOError as e:
        logger.error(
            f"Error reading provider map file {PROVIDER_MAP_PATH}: {e}",
            extra={"file_path": str(PROVIDER_MAP_PATH)},
        )
        raise  # Re-raise IO error
    except json.JSONDecodeError as e:
        logger.error(
            f"Error decoding JSON from {PROVIDER_MAP_PATH}: {e}",
            extra={"file_path": str(PROVIDER_MAP_PATH)},
        )
        raise  # Re-raise JSON error
    except Exception as e:
        logger.exception(
            f"Unexpected error loading provider map from {PROVIDER_MAP_PATH}",
            extra={"provider": provider, "file_path": str(PROVIDER_MAP_PATH)},
        )
        return []  # Return empty list on unexpected errors

    # Retrieve the list of models for the provider directly from the map
    # The map should already contain sorted lists per provider
    models = provider_map.get(provider, [])

    if not models:
        logger.info(
            f"No models found for provider '{provider}' in {PROVIDER_MAP_PATH.name}.",
            extra={"provider": provider, "file_path": str(PROVIDER_MAP_PATH)},
        )
    else:
        logger.debug(
            f"Found {len(models)} models for provider '{provider}' in {PROVIDER_MAP_PATH.name}.",
            extra={"provider": provider, "count": len(models)},
        )
        # Models should already be sorted from the generation step, but sorting again ensures consistency
        models.sort()

    return models
