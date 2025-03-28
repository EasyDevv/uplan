"""Test suite for the UPlanApp class."""

from pathlib import Path

import pytest

from uplan.app import create_app, UPlanApp


@pytest.fixture
def app():
    """Provide a fresh UPlanApp instance for each test."""
    return create_app()


def test_app_creation():
    """Test basic app creation and initialization."""
    app = create_app()
    assert isinstance(app, UPlanApp)
    assert app.services is not None
    assert "state" in app.services
    assert "stream" in app.services
    assert "llm" in app.services


def test_folder_setup(app, tmp_path):
    """Test input/output folder setup."""
    # Setup test paths
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    category = "test"

    # Test folder creation
    input_folder, output_folder = app.setup_folders(
        str(input_root), str(output_root), category
    )

    assert isinstance(input_folder, Path)
    assert isinstance(output_folder, Path)
    assert output_folder.exists()
    assert output_folder.is_dir()

    # Verify paths are correct
    assert input_folder == input_root / category
    assert output_folder == output_root / category


def test_model_validation(app):
    """Test LLM model validation."""
    # Test with a known valid model
    assert app.validate_model("ollama/qwq") is True

    # Test with an invalid model
    assert app.validate_model("invalid/model") is False


@pytest.mark.asyncio
async def test_service_initialization(app):
    """Test service initialization and registration."""
    # Verify all core services are initialized
    assert app.services["state"] is not None
    assert app.services["stream"] is not None
    assert app.services["llm"] is not None

    # Test state service
    state_service = app.services["state"]
    assert state_service.state is not None

    # Test stream service
    stream_service = app.services["stream"]
    assert stream_service.stream_controller is not None

    # Test LLM service
    llm_service = app.services["llm"]
    assert llm_service.state is not None
    assert llm_service.stream_service is not None
