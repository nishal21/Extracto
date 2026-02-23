"""
browser_engine.py — stealth Playwright renderer with proxy support.

Handles JS-heavy pages, rotates user agents, masks the webdriver flag,
retries on timeouts, and routes traffic through proxies when configured.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import random
import logging
from typing import Optional

import html2text
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error as PlaywrightError

from config import CrawlerConfig

logger = logging.getLogger(__name__)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

# stuff we inject into every page to look less like a bot
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = { runtime: {} };
"""


class BrowserEngine:
    """Playwright wrapper with retry, crash recovery, and proxy rotation."""

    def __init__(self, config: CrawlerConfig) -> None:
        self._config = config
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._proxies = config.get_proxy_list()
        self._proxy_index = 0
        self._h2t = html2text.HTML2Text()
        self._h2t.ignore_links = False
        self._h2t.ignore_images = True
        self._h2t.body_width = 0
        # screenshot dir
        if config.screenshots:
            self._ss_dir = os.path.join(config.output_dir, "screenshots")
            os.makedirs(self._ss_dir, exist_ok=True)
        else:
            self._ss_dir = ""

    def _next_proxy(self) -> Optional[dict]:
        """Round-robin through the proxy list. Returns None if no proxies."""
        if not self._proxies:
            return None
        proxy_url = self._proxies[self._proxy_index % len(self._proxies)]
        self._proxy_index += 1
        # playwright wants {"server": "http://..."} format
        return {"server": proxy_url}

    async def _launch_browser(self) -> None:
        """(Re)launch chromium. Called on init and after crashes."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass  # already dead, that's fine

        launch_opts = {
            "headless": self._config.headless,
            "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
        }

        # if we have proxies, set at browser level (context can override)
        proxy = self._next_proxy()
        if proxy:
            launch_opts["proxy"] = proxy
            logger.info("Using proxy: %s", proxy["server"])

        self._browser = await self._playwright.chromium.launch(**launch_opts)

    async def __aenter__(self) -> "BrowserEngine":
        self._playwright = await async_playwright().start()
        await self._launch_browser()
        logger.info("Browser started (headless=%s, proxies=%d)", self._config.headless, len(self._proxies))
        return self

    async def __aexit__(self, *exc) -> None:
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass  # don't let cleanup errors mask the real problem
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        logger.info("Browser shut down")

    async def render_page(self, url: str, retries: int = 3) -> str:
        """
        Navigate to url, wait for JS to settle, return HTML.
        Retries on timeout/crash with exponential backoff.
        Rotates proxy on each retry if proxies are configured.
        """
        last_error = None

        for attempt in range(retries):
            context: Optional[BrowserContext] = None
            try:
                ctx_opts = {
                    "user_agent": random.choice(_USER_AGENTS),
                    "viewport": {"width": self._config.viewport_width, "height": self._config.viewport_height},
                    "java_script_enabled": True,
                    "locale": "en-US",
                    "timezone_id": "America/New_York",
                }

                # rotate proxy per-context on retries
                if self._proxies and attempt > 0:
                    proxy = self._next_proxy()
                    if proxy:
                        ctx_opts["proxy"] = proxy
                        logger.info("Switching to proxy: %s", proxy["server"])

                context = await self._browser.new_context(**ctx_opts)
                await context.add_init_script(_STEALTH_SCRIPT)
                page: Page = await context.new_page()

                await page.goto(url, wait_until="domcontentloaded", timeout=self._config.request_timeout_ms)

                # give late-loading JS a moment
                try:
                    await page.wait_for_load_state("networkidle", timeout=10_000)
                except PlaywrightError:
                    pass  # some pages never fully settle, that's okay

                html = await page.content()
                logger.info("Rendered %s (%d chars)", url, len(html))
                return html

            except PlaywrightError as e:
                last_error = e
                wait = (attempt + 1) * 2  # 2s, 4s, 6s
                logger.warning("Attempt %d/%d failed for %s: %s. Retrying in %ds...", attempt + 1, retries, url, str(e)[:80], wait)
                await asyncio.sleep(wait)

                # browser might have died — try relaunching
                try:
                    await self._launch_browser()
                except Exception:
                    logger.warning("Browser relaunch failed, will retry anyway")

            finally:
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass

        logger.error("All %d attempts failed for %s", retries, url)
        raise last_error

    async def get_markdown(self, url: str) -> str:
        """Render the page and convert to markdown for AI processing."""
        html = await self.render_page(url)
        return self._h2t.handle(html)

    async def screenshot(self, url: str, page: Page) -> Optional[str]:
        """Save a screenshot if configured. Returns the file path or None."""
        if not self._ss_dir:
            return None
        try:
            name = hashlib.sha256(url.encode()).hexdigest()[:12] + ".png"
            path = os.path.join(self._ss_dir, name)
            await page.screenshot(path=path, full_page=True)
            logger.info("Screenshot: %s", path)
            return path
        except Exception as e:
            logger.warning("Screenshot failed for %s: %s", url, e)
            return None

    async def render_and_capture(self, url: str, retries: int = 3) -> tuple[str, Optional[str]]:
        """
        Like render_page but also takes a screenshot.
        Returns (html, screenshot_path).
        """
        last_error = None

        for attempt in range(retries):
            context: Optional[BrowserContext] = None
            try:
                ctx_opts = {
                    "user_agent": random.choice(_USER_AGENTS),
                    "viewport": {"width": self._config.viewport_width, "height": self._config.viewport_height},
                    "java_script_enabled": True,
                    "locale": "en-US",
                    "timezone_id": "America/New_York",
                }
                if self._proxies and attempt > 0:
                    proxy = self._next_proxy()
                    if proxy:
                        ctx_opts["proxy"] = proxy

                context = await self._browser.new_context(**ctx_opts)
                await context.add_init_script(_STEALTH_SCRIPT)
                page: Page = await context.new_page()

                await page.goto(url, wait_until="domcontentloaded", timeout=self._config.request_timeout_ms)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10_000)
                except PlaywrightError:
                    pass

                html = await page.content()
                ss_path = await self.screenshot(url, page)
                return html, ss_path

            except PlaywrightError as e:
                last_error = e
                wait = (attempt + 1) * 2
                logger.warning("Attempt %d/%d failed: %s", attempt + 1, retries, str(e)[:80])
                await asyncio.sleep(wait)
                try:
                    await self._launch_browser()
                except Exception:
                    pass
            finally:
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass

        raise last_error
