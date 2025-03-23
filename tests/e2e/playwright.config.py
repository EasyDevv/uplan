"""
Playwright configuration for E2E tests.
"""

def pytest_configure(config):
    """Configure Playwright for testing."""
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")

def pytest_addoption(parser):
    """Add command line options for E2E tests."""
    parser.addoption(
        "--browser", 
        default="chromium", 
        help="Browser to use for tests: chromium, firefox, or webkit"
    )
    parser.addoption(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode"
    )
