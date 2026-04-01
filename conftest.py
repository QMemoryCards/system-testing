
import pytest
from playwright.sync_api import sync_playwright, Browser, Page


@pytest.fixture(scope="session")
def _playwright():
    """Start Playwright once per test session and stop it at the end."""
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(_playwright) -> Browser:
    """Launch a headless Chromium browser for the whole test session.

    If you prefer Firefox or WebKit, change `_playwright.chromium` to
    `_playwright.firefox` or `_playwright.webkit`.
    """
    browser = _playwright.chromium.launch(headless=True)
    yield browser
    try:
        browser.close()
    except Exception:
        # Best-effort cleanup
        pass


@pytest.fixture()
def page(browser) -> Page:
    """Provide a fresh browser context+page for each test and close the context afterwards.

    Tests can also use the `browser` fixture directly for multi-context scenarios
    (see test_scenario_8 which expects a `browser: Browser` fixture).
    """
    context = browser.new_context()
    page = context.new_page()
    yield page
    try:
        context.close()
    except Exception:
        pass
