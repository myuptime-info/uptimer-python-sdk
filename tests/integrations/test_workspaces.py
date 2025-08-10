from __future__ import annotations

import time

from playwright.sync_api import Page, expect

from tests.conftest import integration_test

from .conftest import get_client


def get_or_create_api_key(page: Page) -> str:
    """Create an API key if neccessary, return token."""
    # Look for existing API key "View Token" buttons
    page.wait_for_url("**/api_keys", timeout=2000)
    view_token_buttons = page.locator('[data-testid^="api-key-view-button-"]')

    if view_token_buttons.count() > 0:
        # Use the first existing API key
        first_button = view_token_buttons.first
        expect(first_button).to_be_visible()
        first_button.click()
        page.wait_for_load_state("networkidle")

        # Get the token from textarea
        token_textarea = page.locator('[data-testid="token-textarea"]')
        expect(token_textarea).to_be_visible()
        api_key = token_textarea.input_value()

        assert api_key, "API key should not be empty"
        return api_key
    # No existing API keys, create a new one
    create_key_button = page.get_by_test_id("new-api-key-button")
    expect(create_key_button).to_be_visible()
    create_key_button.click()
    page.wait_for_load_state("networkidle")

    # Fill in API key name
    name_input = page.locator('[data-testid="form-field-name"]')
    expect(name_input).to_be_visible()
    name_input.fill("Test API Key")

    # Submit the form
    submit_button = page.locator('[data-testid="submit-button"]')
    expect(submit_button).to_be_visible()
    submit_button.click()
    page.wait_for_load_state("networkidle")

    # Now get the newly created API key
    view_token_button = page.locator('[data-testid^="api-key-view-button-"]')
    expect(view_token_button).to_be_visible()
    view_token_button.click()
    page.wait_for_load_state("networkidle")

    # Get the token from textarea
    token_textarea = page.locator('[data-testid="token-textarea"]')
    expect(token_textarea).to_be_visible()
    api_key = token_textarea.input_value()

    assert api_key, "API key should not be empty"
    return api_key


def page_login(page: Page, uptimer_url: str) -> None:
    """Log in and get an API key, create a new one if necessary."""
    page.goto(uptimer_url)
    page.wait_for_load_state("networkidle")

    login_button = page.get_by_test_id("menu-login-btn")
    expect(login_button).to_be_visible()
    login_button.click()

    page.wait_for_load_state("networkidle")

    # Click on API Keys in sidebar
    api_keys_link = page.locator('[data-testid="api-keys-link"]')
    expect(api_keys_link).to_be_visible()
    api_keys_link.click()
    page.wait_for_load_state("networkidle")


def get_workspaces_from_sidebar(page: Page) -> list[str]:
    """Extract workspace names from the sidebar."""
    workspace_links = page.locator('[data-testid^="wslink-"] span')
    workspace_names = []

    for i in range(workspace_links.count()):
        name = workspace_links.nth(i).text_content()
        if name:
            workspace_names.append(name.strip())

    return workspace_names


def create_workspace_via_ui(page: Page, workspace_name: str) -> None:
    """Create a new workspace using the UI."""
    # Click create workspace button in the sidebar
    create_workspace_button = page.locator('[data-tooltip="Create workspace"]')
    expect(create_workspace_button).to_be_visible()
    create_workspace_button.click()
    page.wait_for_load_state("networkidle")

    # Fill workspace name
    name_input = page.locator('[data-testid="workspace-create-name"]')
    expect(name_input).to_be_visible()
    name_input.fill(workspace_name)

    # Submit the form
    submit_button = page.locator('[data-testid="workspace-create-submit"]')
    expect(submit_button).to_be_visible()
    submit_button.click()
    page.wait_for_load_state("networkidle")


def wait_for_workspace_in_sidebar(
    page: Page, workspace_name: str, timeout: int = 10000,
) -> None:
    """Wait for a workspace to appear in the sidebar menu."""
    workspace_locator = page.locator(
        f'[data-testid^="wslink-"] span:has-text("{workspace_name}")',
    )
    expect(workspace_locator).to_be_visible(timeout=timeout)


@integration_test
def test_workspaces_list(page: Page, uptimer_url: str):
    """Creates new workspace, compare workspaces from ui and api."""
    page_login(page, uptimer_url)
    api_key = get_or_create_api_key(page)

    # Create new workspace via UI
    new_workspace_name = f"Test Workspace {int(time.time())}"
    create_workspace_via_ui(page, new_workspace_name)

    # Wait for the new workspace to appear in the sidebar
    wait_for_workspace_in_sidebar(page, new_workspace_name)

    # Get updated workspaces from the sidebar
    updated_workspaces = get_workspaces_from_sidebar(page)

    # Verify new workspace appears in the sidebar
    assert new_workspace_name in updated_workspaces, (
        f"New workspace '{new_workspace_name}' should appear in sidebar"
    )

    # Verify via API
    client = get_client(api_key, uptimer_url)
    workspaces = client.v1.workspaces.all()
    api_workspace_names = [ws.name for ws in workspaces]
    assert set(updated_workspaces) == set(api_workspace_names)


