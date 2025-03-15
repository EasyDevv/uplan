"""
Module for handling LLM API configuration and setup.
"""

import os
from typing import Dict, List, Tuple

import litellm
from dotenv import load_dotenv

load_dotenv()

# Define service configurations
SERVICE_CONFIGS: Dict[str, List[str]] = {
    "OPENAI": ["API_KEY"],
    "ANTHROPIC": ["API_KEY"],
    "GEMINI": ["API_KEY"],
    "DEEPSEEK": ["API_KEY"],
    "XAI": ["API_KEY"],
    "VERTEX": ["PROJECT", "LOCATION"],
    "NVIDIA_NIM": ["API_KEY", "API_BASE"],
    "HUGGINGFACE": ["API_KEY"],
    "AZURE": ["API_KEY", "API_BASE", "API_VERSION"],
    "OPENROUTER": ["API_KEY"],
}


def setup_env(verbose: bool = False) -> None:
    """Set up LLM API environment variables and configurations."""
    for service, required_configs in SERVICE_CONFIGS.items():
        missing_configs = []
        for config in required_configs:
            env_key = f"{service}_{config}"
            env_value = os.getenv(env_key)

            if env_value:
                os.environ[env_key] = env_value
            else:
                missing_configs.append(env_key)

        if missing_configs and verbose:
            print(
                f"Warning: Missing configurations for {service}: {', '.join(missing_configs)}"
            )


def check_model_support(model_name: str) -> Tuple[bool, str]:
    """
    Check if a given model is supported by litellm and has required environment variables.

    Args:
        model_name: Name of the model to check

    Returns:
        Tuple[bool, str]: (True, '') if model is supported and configured,
                         (False, error_message) otherwise
    """
    try:
        # Get model provider details
        model_details = litellm.get_llm_provider(model_name)
        if not model_details or len(model_details) != 4:
            return False, f"Model '{model_name}' is not supported by litellm"

        model, provider, _, _ = model_details

        if provider == "ollama":
            return True, f"Model: {model}, Provider: {provider}"

        if not provider:
            return False, f"Model '{model_name}' is not supported by litellm"

        # Extract provider key and check configuration
        provider_key = provider.upper().split("_")[0]
        if provider_key not in SERVICE_CONFIGS:
            return False, f"Provider '{provider}' is not supported"

        missing_vars = [
            f"{provider_key}_{config}"
            for config in SERVICE_CONFIGS[provider_key]
            if os.getenv(f"{provider_key}_{config}") is None
        ]

        if missing_vars:
            return (
                False,
                f"Missing required environment variables: {', '.join(missing_vars)}. Add them to your .env file.",
            )

        return True, f"Model: {model}, Provider: {provider}"

    except (AttributeError, TypeError) as e:
        return False, f"Invalid model format: {str(e)}"
    except Exception as e:
        return False, f"Error checking model support: {str(e)}"
