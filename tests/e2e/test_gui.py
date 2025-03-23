"""End-to-end tests for the GUI interface."""

import pytest
from playwright.sync_api import expect


@pytest.mark.gui
def test_gui_initial_load(test_page):
    """Test initial page load and layout structure."""
    # Check main layout elements
    expect(test_page.locator("text=Generated Content")).to_be_visible()
    expect(test_page.locator("text=Project Information")).to_be_visible()

    # Verify tabs exist
    expect(test_page.locator('role=tab[name="Plan"]')).to_be_visible()
    expect(test_page.locator('role=tab[name="Todo"]')).to_be_visible()

    # Check form elements
    expect(test_page.locator("text=Project Name")).to_be_visible()
    expect(test_page.locator("text=Project Description")).to_be_visible()
    expect(test_page.locator("text=Form Category")).to_be_visible()
    expect(test_page.locator("text=Model Name")).to_be_visible()


@pytest.mark.gui
@pytest.mark.asyncio
async def test_form_submission(test_page):
    """Test form submission and response handling."""
    # Fill out the form
    test_page.fill('input[aria-label="Project Name"]', "Test Project")
    test_page.fill(
        'textarea[aria-label="Project Description"]', "A test project description"
    )
    test_page.select_option("select", "dev")

    # Submit the form
    test_page.click('button:has-text("Generate")')

    # Wait for success notification
    expect(test_page.locator(".positive")).to_be_visible()

    # Verify content is updated
    expect(test_page.locator('text="No plan generated yet..."')).not_to_be_visible()


@pytest.mark.gui
@pytest.mark.asyncio
async def test_tab_switching(test_page):
    """Test tab switching between Plan and Todo views."""
    # Initial tab should be Plan
    expect(test_page.locator("role=tab[selected=true]")).to_have_text("Plan")

    # Switch to Todo tab
    test_page.click('role=tab[name="Todo"]')
    expect(test_page.locator("role=tab[selected=true]")).to_have_text("Todo")

    # Switch back to Plan tab
    test_page.click('role=tab[name="Plan"]')
    expect(test_page.locator("role=tab[selected=true]")).to_have_text("Plan")


@pytest.mark.gui
@pytest.mark.asyncio
async def test_error_handling(test_page):
    """Test error handling and display."""
    # Submit form without required fields
    test_page.click('button:has-text("Generate")')

    # Check for validation messages
    expect(test_page.locator("text=required")).to_be_visible()

    # Fill invalid model
    test_page.fill('input[aria-label="Project Name"]', "Test Project")
    test_page.fill('textarea[aria-label="Project Description"]', "Description")
    test_page.fill('input[aria-label="Model Name"]', "invalid_model")

    # Submit and check for error
    test_page.click('button:has-text("Generate")')
    expect(test_page.locator(".negative")).to_be_visible()
