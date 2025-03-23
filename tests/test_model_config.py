"""Test suite for model configuration validation and handling."""

import pytest
from uplan.utils.model_config import (
    validate_model,
    get_provider,
    get_model_config,
    get_available_models,
    DEFAULT_MODEL,
    SUPPORTED_MODELS,
)


# Test model validation
def test_validate_model_success():
    """Test successful model validation for supported models."""
    # Test OpenAI model
    is_valid, error = validate_model("gpt-3.5-turbo")
    assert is_valid is True
    assert error == ""

    # Test Ollama model
    is_valid, error = validate_model("qwq")
    assert is_valid is True
    assert error == ""


def test_validate_model_unsupported():
    """Test validation for unsupported models."""
    is_valid, error = validate_model("unsupported-model")
    assert is_valid is False
    assert "not supported" in error
    assert str(SUPPORTED_MODELS) in error


def test_validate_model_empty():
    """Test validation with empty model name."""
    is_valid, error = validate_model("")
    assert is_valid is False
    assert error == "Model name cannot be empty"


def test_validate_model_case_sensitivity():
    """Test model name case sensitivity."""
    is_valid, error = validate_model("GPT-3.5-TURBO")
    assert is_valid is False
    assert "not supported" in error


# Test provider detection
def test_get_provider_success():
    """Test successful provider detection."""
    assert get_provider("gpt-3.5-turbo") == "openai"
    assert get_provider("qwq") == "ollama"


def test_get_provider_unsupported():
    """Test provider detection for unsupported models."""
    assert get_provider("unsupported-model") is None
    assert get_provider("") is None


# Test model configuration
def test_get_model_config_default():
    """Test retrieval of default model configuration."""
    config = get_model_config()
    assert config["provider"] == "openai"
    assert "temperature" in config
    assert "max_tokens" in config


def test_get_model_config_specific():
    """Test retrieval of specific model configurations."""
    # Test OpenAI model config
    config = get_model_config("gpt-3.5-turbo")
    assert config["provider"] == "openai"
    assert config["temperature"] == 0.7
    assert config["max_tokens"] == 2000

    # Test Ollama model config
    config = get_model_config("qwq")
    assert config["provider"] == "ollama"
    assert config["temperature"] == 0.7
    assert config["max_tokens"] == 2000


def test_get_model_config_unsupported():
    """Test configuration retrieval for unsupported models."""
    config = get_model_config("unsupported-model")
    assert config == get_model_config(DEFAULT_MODEL)


def test_get_model_config_none():
    """Test configuration retrieval with None model."""
    config = get_model_config(None)
    assert config == get_model_config(DEFAULT_MODEL)


# Test available models
def test_get_available_models():
    """Test retrieval of available models."""
    models = get_available_models()
    assert "openai" in models
    assert "ollama" in models
    assert "gpt-3.5-turbo" in models["openai"]
    assert "qwq" in models["ollama"]

    # Verify it returns a copy
    original = SUPPORTED_MODELS.copy()
    models["new_provider"] = ["new_model"]
    assert models != SUPPORTED_MODELS
    assert SUPPORTED_MODELS == original
