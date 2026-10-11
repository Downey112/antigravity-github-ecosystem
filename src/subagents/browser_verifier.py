"""Browser Verification Subagent (`browser`).

Executes UI regression testing, smoke verification, and DOM inspection
using Playwright headless automation or HTTP diagnostics.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("browser")

class BrowserVerificationSubagent:
    """Subagent for verifying deployed web applications and staging previews."""

    def __init__(self, artifacts_dir: Optional[Path] = None):
        self.artifacts_dir = artifacts_dir or Path("./artifacts/browser")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    async def verify_endpoint(self, target_url: str, take_screenshot: bool = True) -> Dict[str, Any]:
        """Runs a headless browser check against target_url."""
        logger.info(f"Checking URL: {target_url}")
        
        # Try importing Playwright
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                errors: List[str] = []
                page.on("pageerror", lambda exc: errors.append(str(exc)))

                response = await page.goto(target_url, timeout=30000)
                status_code = response.status if response else 0
                title = await page.title()

                screenshot_path = ""
                if take_screenshot:
                    dest = self.artifacts_dir / "verification.png"
                    await page.screenshot(path=str(dest))
                    screenshot_path = str(dest)

                await browser.close()
                return {
                    "subagent": "browser",
                    "url": target_url,
                    "status_code": status_code,
                    "page_title": title,
                    "console_errors": errors,
                    "screenshot": screenshot_path,
                    "success": 200 <= status_code < 400 and len(errors) == 0,
                }
        except Exception as playwright_err:
            logger.info(f"Playwright unavailable or failed to launch ({playwright_err}). Falling back to HTTP check.")
            import httpx
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(target_url)
                    return {
                        "subagent": "browser",
                        "mode": "http-fallback",
                        "url": target_url,
                        "status_code": resp.status_code,
                        "content_length": len(resp.content),
                        "notice": f"Playwright skipped: {str(playwright_err).splitlines()[0]}",
                        "success": 200 <= resp.status_code < 400,
                    }
            except Exception as e:
                return {"subagent": "browser", "error": str(e), "success": False}
