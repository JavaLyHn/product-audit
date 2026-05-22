"""Playwright wrapper used by audit.py.

Provides a simple, audit-friendly browser abstraction that:
- Manages page lifecycle (open/close/screenshot)
- Auto-numbers screenshots
- Captures basic page metadata (title, URL, performance)
- Handles credentials in memory only (never persisted)
"""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


@dataclass
class BrowserSession:
    """One audit run = one BrowserSession.

    Holds Playwright handles + screenshot counter + workspace ref.
    Do NOT persist credentials anywhere on this object beyond the in-memory
    `context` (Playwright's storage). Discard via close().

    If `storage_state` is provided (path to a JSON file produced by
    capture_login.py), the context starts with that cookies/localStorage,
    enabling audits of logged-in-only pages.
    """

    workspace: Path
    headless: bool = True
    screenshot_counter: int = 0
    figs_dir: Path = field(init=False)
    storage_state: Optional[Path] = None

    def __post_init__(self):
        self.figs_dir = self.workspace / "figs"
        self.figs_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        self._browser: Browser = self._playwright.chromium.launch(headless=self.headless)
        context_kwargs = dict(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 product-audit/1.0"
            ),
        )
        if self.storage_state and Path(self.storage_state).exists():
            context_kwargs["storage_state"] = str(self.storage_state)
        self._context: BrowserContext = self._browser.new_context(**context_kwargs)
        self._page: Page = self._context.new_page()

    @property
    def page(self) -> Page:
        return self._page

    def navigate(self, url: str, wait_for: str = "networkidle", timeout_ms: int = 30000) -> dict:
        """Navigate and return basic metadata."""
        start = time.time()
        response = self._page.goto(url, wait_until=wait_for, timeout=timeout_ms)
        load_ms = int((time.time() - start) * 1000)
        return {
            "url": self._page.url,
            "title": self._page.title(),
            "status": response.status if response else None,
            "load_ms": load_ms,
        }

    def screenshot(self, name: str, full_page: bool = False) -> Path:
        """Take a screenshot with auto-numbered semantic name.

        name: semantic slug (e.g., 'c1-homepage', 's3-integrations').
              Auto-prefixed with counter to ensure ordering.
        """
        self.screenshot_counter += 1
        filename = f"{self.screenshot_counter:02d}-{name}.png"
        path = self.figs_dir / filename
        self._page.screenshot(path=str(path), full_page=full_page)
        return path

    def login(self, email_env: str = "AUDIT_USER", password_env: str = "AUDIT_PWD",
              email_selector: str = "input[type=email]",
              password_selector: str = "input[type=password]",
              submit_selector: str = "button[type=submit]") -> bool:
        """Attempt login using credentials from env vars only.

        Returns True on success, False on failure. Does NOT retry.
        Credentials are read from env and never stored / logged.
        """
        email = os.environ.get(email_env)
        password = os.environ.get(password_env)
        if not email or not password:
            return False
        try:
            self._page.fill(email_selector, email)
            self._page.fill(password_selector, password)
            self._page.click(submit_selector)
            # Wait for navigation away from login or for a known logged-in marker
            self._page.wait_for_load_state("networkidle", timeout=15000)
            # Heuristic: if still on a page with password field, login failed
            return self._page.locator(password_selector).count() == 0
        except Exception:
            return False

    def get_text(self, selector: str = "body", limit: int = 5000) -> str:
        """Extract trimmed text content for LLM interpretation."""
        try:
            text = self._page.locator(selector).inner_text(timeout=5000)
            return text[:limit]
        except Exception:
            return ""

    def get_links(self, container_selector: str = "footer") -> list[dict]:
        """Extract links from a container (e.g., footer)."""
        try:
            elements = self._page.locator(f"{container_selector} a").all()
            return [
                {"text": el.inner_text(timeout=1000)[:80], "href": el.get_attribute("href") or ""}
                for el in elements
                if el.get_attribute("href")
            ][:50]
        except Exception:
            return []

    def close(self):
        """Clean up Playwright resources. Discards credential context."""
        try:
            self._context.close()
            self._browser.close()
            self._playwright.stop()
        except Exception:
            pass
