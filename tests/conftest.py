"""Test configuration and fixtures."""

import multiprocessing
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page

from uplan.gui import main as gui_main


@pytest.fixture(scope="session")
def gui_url() -> str:
    """Return the URL for the GUI."""
    return "http://127.0.0.1:8080"


@pytest.fixture(scope="session")
def gui_server(gui_url):
    """Start the GUI server for testing."""
    # Start the server in a separate process
    server = multiprocessing.Process(target=gui_main)
    server.start()

    # Wait longer for server to be ready
    for _ in range(30):  # 30 seconds timeout
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("127.0.0.1", 8080))
            sock.close()
            if result == 0:  # Port is open
                break
        except socket.error:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Server failed to start within 30 seconds")

    # Additional wait for server initialization
    time.sleep(2)

    yield gui_url

    # Cleanup
    server.terminate()
    server.join()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context."""
    return {
        **browser_context_args,
        "viewport": {
            "width": 1280,
            "height": 720,
        },
    }


@pytest.fixture
def test_page(page: Page, gui_server: str) -> Page:
    """Create a page with the GUI server already loaded."""
    page.goto(gui_server)
    # Wait for main layout to be visible
    page.wait_for_selector("text=Generated Content", state="visible", timeout=5000)
    return page


@pytest.fixture(autouse=True)
def test_env(tmp_path: Path):
    """Set up test environment."""
    # Create temporary input/output directories
    input_dir = tmp_path / "input" / "dev"
    output_dir = tmp_path / "output" / "dev"

    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    # Return environment configuration
    return {"input_dir": input_dir, "output_dir": output_dir}
