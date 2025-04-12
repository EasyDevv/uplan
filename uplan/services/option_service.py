"""Service for managing UI options like categories and models."""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from uplan.config import INPUT_BASE_DIR, OUTPUT_BASE_DIR  # Import config constants
from pyhunt import trace

# Define path relative to the configured input directory
MODEL_INFO_PATH = INPUT_BASE_DIR / "model_info.json"


class OptionService:
    """Manages retrieval and updates for UI options."""

    def __init__(self):
        """Initialize the OptionService and load model data."""
        self.model_data = self._load_model_data()
        self.providers = sorted(list(self.model_data.keys()))

    @trace
    def _load_model_data(self) -> Dict[str, List[str]]:
        """Loads model information from the JSON file."""
        if MODEL_INFO_PATH.exists():
            try:
                with open(MODEL_INFO_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Basic validation: ensure it's a dict with list values
                    if isinstance(data, dict) and all(
                        isinstance(v, list) for v in data.values()
                    ):
                        return data
                    else:
                        pass
            except (json.JSONDecodeError, IOError) as e:
                pass
        else:
            pass

        # Fallback data
        return {"ollama": ["gemma3:1b"]}
        pass

    @trace
    def get_providers(self) -> List[str]:
        """Returns the list of available providers."""
        return self.providers

    @trace
    def get_default_provider_and_models(self) -> Tuple[Optional[str], List[str]]:
        """Gets the default provider and its corresponding models."""
        default_provider = (
            "ollama"
            if "ollama" in self.providers
            else (self.providers[0] if self.providers else None)
        )
        default_models = sorted(self.model_data.get(default_provider, []))
        return default_provider, default_models

    @trace
    def get_default_model(self, models: List[str]) -> Optional[str]:
        """Gets the default model from a list, preferring 'gemma3:1b'."""
        default_model = (
            "gemma3:1b" if "gemma3:1b" in models else (models[0] if models else None)
        )
        return default_model

    @trace
    def get_models_for_provider(self, provider: Optional[str]) -> List[str]:
        """Returns a sorted list of models for the given provider."""
        if not provider:
            return []
        models = sorted(self.model_data.get(provider, []))
        return models

    @trace
    def get_category_options(self, input_base_path: Path = INPUT_BASE_DIR) -> List[str]:
        """Gets a list of directory names (categories) from the input path."""
        categories = []
        if input_base_path.is_dir():
            try:
                categories = sorted(
                    [item.name for item in input_base_path.iterdir() if item.is_dir()]
                )
            except OSError as e:
                pass
        else:
            pass

        if not categories:
            pass
            return ["dev"]  # Fallback
        return categories

    @trace
    def get_default_category(self, categories: List[str]) -> Optional[str]:
        """Gets the default category, preferring 'dev'."""
        default_category = (
            "dev" if "dev" in categories else (categories[0] if categories else None)
        )
        return default_category

    @trace
    def get_input_path_for_category(
        self, category: Optional[str], input_base_path: Path = INPUT_BASE_DIR
    ) -> str:
        """Constructs the input path string for a given category."""
        if not category:
            return str(input_base_path)
        path = str(input_base_path / category)
        return path

    @trace
    def get_default_output_path(self, output_base_path: Path) -> str:
        """Returns the default output path string."""
        path = str(output_base_path)
        return path
