"""Model configuration and validation system for Uplan.

This module provides functionality for configuring and validating LLM models
from different providers like OpenAI and Ollama.
"""

from typing import Any

# Model provider constants
DEFAULT_MODEL = "gpt-3.5-turbo"
OPENAI_PROVIDER = "openai"
OLLAMA_PROVIDER = "ollama"

# Model configurations with proper litellm format
SUPPORTED_MODELS = {
    OPENAI_PROVIDER: [
        "gpt-3.5-turbo",
        "gpt-4",
    ],  # OpenAI models already have correct format
    OLLAMA_PROVIDER: ["ollama/qwq"],  # Prefix Ollama models with provider name
}

DEFAULT_MODEL_CONFIGS = {
    "gpt-3.5-turbo": {
        "provider": OPENAI_PROVIDER,
        "temperature": 0.7,
        "max_tokens": 2000,
    },
    "gpt-4": {
        "provider": OPENAI_PROVIDER,
        "temperature": 0.7,
        "max_tokens": 4000,
    },
    "ollama/qwq": {  # Updated to match litellm format
        "provider": OLLAMA_PROVIDER,
        "temperature": 0.7,
        "max_tokens": 2000,
    },
}


def validate_model(model: str) -> tuple[bool, str]:
    """Validate if the given model is supported.

    Args:
        model: Name of the model to validate

    Returns:
        tuple[bool, str]: (is_valid, error_message)
    """
    if not model:
        return False, "Model name cannot be empty"

    # Handle legacy model names (without provider prefix)
    if model == "qwq":
        model = "ollama/qwq"

    for provider, models in SUPPORTED_MODELS.items():
        if model in models:
            return True, ""

    return (
        False,
        f"Model {model} is not supported. Supported models: {SUPPORTED_MODELS}",
    )


def get_provider(model: str) -> str | None:
    """Get the provider for a given model.

    Args:
        model: Name of the model

    Returns:
        str | None: Provider name if found, None otherwise
    """
    # Handle legacy model names
    if model == "qwq":
        model = "ollama/qwq"

    for provider, models in SUPPORTED_MODELS.items():
        if model in models:
            return provider
    return None


def get_model_config(model: str | None = None) -> dict[str, Any]:
    """Get configuration for the specified model.

    Args:
        model: Name of the model (optional, uses DEFAULT_MODEL if not specified)

    Returns:
        dict: Model configuration with provider and parameters
    """
    model = model or DEFAULT_MODEL

    # Handle legacy model names
    if model == "qwq":
        model = "ollama/qwq"

    is_valid, error = validate_model(model)

    if not is_valid:
        return DEFAULT_MODEL_CONFIGS[DEFAULT_MODEL]

    return DEFAULT_MODEL_CONFIGS[model]


def get_available_models() -> dict[str, list[str]]:
    """Get all available models grouped by provider.

    Returns:
        dict: Provider -> list of model names mapping
    """
    return SUPPORTED_MODELS.copy()
