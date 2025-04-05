import pytest
from uplan.services.llm_service import LLMService
from uplan.ui.state import AppState
from uplan.services.stream_service import StreamService


@pytest.fixture
def app_state():
    """Fixture to create a fresh AppState instance."""
    return AppState.get_instance()


@pytest.fixture
def llm_service(app_state):
    """Fixture to create an LLMService instance."""
    stream_service = (
        StreamService()
    )  # Assuming StreamService can be initialized without parameters
    return LLMService(state=app_state, stream_service=stream_service)


def test_llm_service_initialization(llm_service):
    """Test that LLMService initializes correctly."""
    assert llm_service is not None
    assert isinstance(llm_service.state, AppState)
    assert isinstance(llm_service.stream_service, StreamService)


def test_llm_service_process_request(llm_service):
    """Test that LLMService can process a request without errors."""
    # Here we would normally mock the stream_service and its methods
    # For now, we will just call the method to ensure it doesn't raise an error
    try:
        llm_service.process_request()
    except Exception as e:
        pytest.fail(f"LLMService raised an exception: {e}")
