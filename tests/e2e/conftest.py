"""Test configuration and fixtures."""

import asyncio
import multiprocessing
import pytest
import time
from pathlib import Path

from uplan.gui import main as gui_main


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


def run_gui_server():
    """Run the GUI server in a separate process."""
    gui_main()


@pytest.fixture(scope="session")
def gui_server():
    """Start the GUI server for testing."""
    # Start the server in a separate process
    server = multiprocessing.Process(target=run_gui_server)
    server.start()

    # Wait for server to be ready
    time.sleep(2)

    yield server

    # Cleanup
    server.terminate()
    server.join()


@pytest.fixture(autouse=True)
def test_env(gui_server, tmp_path):
    """Set up test environment."""
    # Create temporary input/output directories
    input_dir = tmp_path / "input" / "dev"
    output_dir = tmp_path / "output" / "dev"

    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    # Environment setup
    return {"input_dir": input_dir, "output_dir": output_dir}
