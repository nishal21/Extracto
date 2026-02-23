"""
crawler_engine.py — the main crawl loop.

Built on Crawlee's PlaywrightCrawler. Handles:
- batch URLs (scrape a list of pages in one run)
- depth tracking per request
- scope filtering (same domain, same directory, or everything)
- URL deduplication
- link cleanup (filtering out garbage hrefs)
- rate limiting between requests
- checkpoint/resume (save state to disk, pick up where you left off)
- per-page metadata for the exporter
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import timedelta
from urllib.parse import urlparse, urljoin, urldefrag
from typing import Any

from crawlee import Request
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

from config import CrawlerConfig
from browser_engine import BrowserEngine
from ai_extractor import AIExtractor
from cache import PageCache
from schema import load_schema, schema_to_prompt
from sitemap import discover_sitemap_urls
from robots import RobotsChecker

logger = logging.getLogger(__name__)

# URLs matching these patterns are never worth following
_SKIP_EXTENSIONS = re.compile(
    r"\.(jpg|jpeg|png|gif|svg|webp|ico|pdf|zip|tar|gz|mp3|mp4|avi|mov|exe|dmg|css|js|woff2?|ttf|eot)$",
    re.IGNORECASE,
)
_SKIP_SCHEMES = {"javascript", "mailto", "tel", "data", "blob", "ftp"}


def _is_junk_url(url: str) -> bool:
    """Quick check for URLs that aren't real pages."""
    parsed = urlparse(url)
    if parsed.scheme.lower() in _SKIP_SCHEMES:
        return True
    if not parsed.scheme.startswith("http"):
        return True
    if _SKIP_EXTENSIONS.search(parsed.path):
        return True
    # pure fragment links
    if not parsed.netloc and not parsed.path:
        return True
    return False


class Checkpoint:
    """
    Dead simple checkpoint — saves visited URLs and results to a JSON file.
    If the file exists on startup, we skip already-scraped pages.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        self.visited: set[str] = set()
        self.results: list[dict[str, Any]] = []
        self.failed: list[str] = []

    def load(self) -> bool:
        """Load previous state. Returns True if a checkpoint was found."""
        if not self._path or not os.path.exists(self._path):
            return False
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.visited = set(data.get("visited", []))
            self.results = data.get("results", [])
            self.failed = data.get("failed", [])
            logger.info("Resumed from checkpoint: %d pages done, %d failed", len(self.results), len(self.failed))
            return True
        except Exception as e:
            logger.warning("Couldn't load checkpoint: %s", e)
            return False

    def save(self) -> None:
        """Flush current state to disk."""
        if not self._path:
            return
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump({
                    "visited": list(self.visited),
                    "results": self.results,
                    "failed": self.failed,
                }, f, indent=2, default=str)
        except Exception as e:
            logger.warning("Couldn't save checkpoint: %s", e)

    def cleanup(self) -> None:
        """Delete the checkpoint file (called on successful completion)."""
        if self._path and os.path.exists(self._path):
            os.remove(self._path)
            logger.info("Checkpoint cleaned up")


class CrawlerEngine:
    """
    Orchestrates the whole crawl → render → extract pipeline.

    Supports batch mode (multiple seed URLs), rate limiting,
    and checkpoint/resume for long-running crawls.
    """

    def __init__(self, config: CrawlerConfig, progress_callback=None) -> None:
        self._config = config
        self._checkpoint = Checkpoint(config.checkpoint_file)
        self._visited: set[str] = set()
        self._results: list[dict[str, Any]] = []
        self._failed: list[str] = []
        self._browser_engine = BrowserEngine(config)
        self._ai_extractor = AIExtractor(config)
        self._progress_callback = progress_callback
        self._last_request_time = 0.0
        self._cache = PageCache() if config.cache else None
        self._robots = RobotsChecker(enabled=config.respect_robots)

        # build the actual prompt — append schema if configured
        self._prompt = config.user_prompt
        schema = load_schema(config.schema)
        if schema:
            self._prompt += schema_to_prompt(schema)
            logger.info("Schema loaded, prompt extended")

    @staticmethod
    def _normalize(url: str) -> str:
        clean, _ = urldefrag(url)
        return clean.rstrip("/")

    def _in_scope(self, url: str, seed_url: str) -> bool:
        """Check if URL is within scope relative to the given seed."""
        parsed = urlparse(url)
        seed = urlparse(seed_url)
        scope = self._config.crawl_scope

        if scope == "same_domain":
            return parsed.netloc == seed.netloc

        if scope == "same_directory":
            if parsed.netloc != seed.netloc:
                return False
            seed_dir = seed.path.rsplit("/", 1)[0] + "/"
            return parsed.path.startswith(seed_dir)

        return True  # external = no restrictions

    def _should_follow(self, url: str, depth: int, seed_url: str) -> bool:
        if _is_junk_url(url):
            return False
        if self._normalize(url) in self._visited:
            return False
        if depth > self._config.max_depth:
            return False
        return self._in_scope(url, seed_url)

    async def _rate_limit(self) -> None:
        """Wait if needed to respect the configured delay between requests."""
        if self._config.rate_limit <= 0:
            return
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._config.rate_limit:
            wait = self._config.rate_limit - elapsed
            logger.debug("Rate limiting: waiting %.1fs", wait)
            await asyncio.sleep(wait)
        self._last_request_time = time.time()

    async def run(self) -> list[dict[str, Any]]:
        """
        Run the crawl across all seed URLs and return results with metadata.
        Resumes from checkpoint if one exists.
        """
        # try to resume
        if self._checkpoint.load():
            self._visited = self._checkpoint.visited
            self._results = self._checkpoint.results
            self._failed = self._checkpoint.failed

        async with self._browser_engine:
            crawler = PlaywrightCrawler(
                headless=self._config.headless,
                max_requests_per_crawl=self._config.max_requests_per_crawl,
                max_crawl_depth=self._config.max_depth,
                request_handler_timeout=timedelta(minutes=5),
            )

            # keep track of which seed URL each request came from
            # so scope checks work correctly in batch mode

            @crawler.router.default_handler
            async def handle_page(ctx: PlaywrightCrawlingContext) -> None:
                url = ctx.request.url
                depth = ctx.request.user_data.get("depth", 0)
                seed = ctx.request.user_data.get("seed", url)
                norm = self._normalize(url)

                if norm in self._visited:
                    return
                self._visited.add(norm)

                logger.info("[depth=%d] %s", depth, url)

                # robots.txt check
                if not await self._robots.is_allowed(url):
                    logger.info("Skipped (robots.txt): %s", url)
                    return

                # rate limit
                await self._rate_limit()

                # render (with cache if enabled)
                ss_path = None
                try:
                    cached = self._cache.get(url) if self._cache else None
                    if cached:
                        markdown = cached
                        logger.info("Cache hit for %s", url)
                    elif self._config.screenshots:
                        # render + screenshot in one pass
                        html, ss_path = await self._browser_engine.render_and_capture(url)
                        markdown = self._browser_engine._h2t.handle(html)
                        if self._cache:
                            self._cache.put(url, markdown)
                    else:
                        markdown = await self._browser_engine.get_markdown(url)
                        if self._cache:
                            self._cache.put(url, markdown)
                except Exception as e:
                    logger.error("Render failed: %s — %s", url, e)
                    self._failed.append(url)
                    self._save_checkpoint()
                    return

                # extract using our (possibly schema-extended) prompt
                result = await asyncio.to_thread(
                    self._ai_extractor.extract, markdown, url, self._prompt
                )
                if result is not None:
                    entry = {
                        "data": result,
                        "source_url": url,
                        "depth": depth,
                    }
                    if ss_path:
                        entry["screenshot"] = ss_path
                    self._results.append(entry)
                else:
                    self._failed.append(url)

                # save checkpoint after each page so we can resume
                self._save_checkpoint()

                # progress callback for the UI
                if self._progress_callback:
                    self._progress_callback(url, depth, len(self._results))

                # discover links
                if depth < self._config.max_depth:
                    child_depth = depth + 1
                    try:
                        raw_links = await ctx.page.eval_on_selector_all(
                            "a[href]", "els => els.map(e => e.href)"
                        )
                    except Exception:
                        raw_links = []

                    enqueued = 0
                    for link in raw_links:
                        abs_url = urljoin(url, link)
                        if self._should_follow(abs_url, child_depth, seed):
                            await ctx.add_requests([
                                Request.from_url(abs_url, user_data={"depth": child_depth, "seed": seed})
                            ])
                            self._visited.add(self._normalize(abs_url))
                            enqueued += 1

                    if enqueued:
                        logger.info("Enqueued %d links (depth %d→%d)", enqueued, depth, child_depth)

            @crawler.failed_request_handler
            async def handle_failure(ctx, error) -> None:
                url = ctx.request.url
                logger.error("Request permanently failed: %s — %s", url, error)
                self._failed.append(url)
                self._save_checkpoint()

            # build seed requests — skip URLs we've already scraped (checkpoint)
            seeds = []
            for url in self._config.start_urls:
                norm = self._normalize(url)
                if norm not in self._visited:
                    seeds.append(Request.from_url(url, user_data={"depth": 0, "seed": url}))
                else:
                    logger.info("Skipping (already done): %s", url)

            # auto-discover URLs from sitemap if enabled
            if self._config.use_sitemap:
                for seed_url in self._config.start_urls:
                    try:
                        sitemap_urls = await discover_sitemap_urls(seed_url)
                        for sm_url in sitemap_urls:
                            norm = self._normalize(sm_url)
                            if norm not in self._visited:
                                seeds.append(Request.from_url(sm_url, user_data={"depth": 0, "seed": seed_url}))
                                self._visited.add(norm)  # mark to avoid duplication
                        if sitemap_urls:
                            logger.info("Sitemap: added %d URLs from %s", len(sitemap_urls), seed_url)
                    except Exception as e:
                        logger.warning("Sitemap discovery failed for %s: %s", seed_url, e)

            if seeds:
                await crawler.run(seeds)

        # clean up checkpoint on success
        self._checkpoint.cleanup()

        return self._results

    def _save_checkpoint(self) -> None:
        self._checkpoint.visited = self._visited
        self._checkpoint.results = self._results
        self._checkpoint.failed = self._failed
        self._checkpoint.save()

    @property
    def failed_urls(self) -> list[str]:
        return self._failed

    @property
    def pages_done(self) -> int:
        return len(self._results)
