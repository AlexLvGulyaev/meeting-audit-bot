"""E2E screenshots for meeting-audit-bot admin UI."""
from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

BASE_URL = "https://meeting-audit-bot.alex-n8n.site"
ADMIN_DEMO_TOKEN = "test-demo-token-2b5d"

SCREENSHOTS_DIR = Path(__file__).resolve().parents[1] / "docs" / "screenshots"


def _target(name: str) -> Path:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    return SCREENSHOTS_DIR / name


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 900})
        page = await context.new_page()

        # Public landing page
        await page.goto(BASE_URL, wait_until="networkidle")
        await page.screenshot(path=str(_target("01-public-landing.png")), full_page=False)

        # Admin login page
        await page.goto(f"{BASE_URL}/admin/login", wait_until="networkidle")
        await page.screenshot(path=str(_target("02-admin-login.png")), full_page=False)

        # Demo login via server-side endpoint
        await page.goto(f"{BASE_URL}/admin/login/demo", wait_until="networkidle")
        # The endpoint sets cookie and redirects to /admin; we now have a demo session.

        # Admin dashboard
        await page.goto(f"{BASE_URL}/admin", wait_until="networkidle")
        await page.screenshot(path=str(_target("03-admin-dashboard.png")), full_page=False)

        # Executions (operational logs)
        await page.goto(f"{BASE_URL}/admin/executions", wait_until="networkidle")
        await asyncio.sleep(0.5)
        await page.screenshot(path=str(_target("04-admin-executions.png")), full_page=False)

        # Audit
        await page.goto(f"{BASE_URL}/admin/audit", wait_until="networkidle")
        await asyncio.sleep(0.5)
        await page.screenshot(path=str(_target("05-admin-audit.png")), full_page=False)

        await browser.close()
        print("Screenshots saved to", SCREENSHOTS_DIR)


if __name__ == "__main__":
    asyncio.run(main())
