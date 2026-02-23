"""
robots.py — robots.txt compliance checker.

Fetches and parses robots.txt before crawling. If a URL is disallowed
for our user-agent, we skip it. This keeps Extracto respectful and
prevents users from accidentally scraping pages they shouldn't.

Can be disabled with --no-robots if the user explicitly wants to ignore it.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class RobotsChecker:
    """
    Checks URLs against robots.txt rules.
    Caches the parsed robots.txt per domain so we only fetch it once.
    """

    USER_AGENT = "Extracto"

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._parsers: dict[str, Optional[RobotFileParser]] = {}

    async def is_allowed(self, url: str) -> bool:
        """
        Check if we're allowed to crawl this URL.
        Returns True if robots.txt allows it, or if robots checking is disabled.
        """
        if not self._enabled:
            return True

        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        # fetch + cache robots.txt for this domain
        if domain not in self._parsers:
            self._parsers[domain] = await self._fetch_robots(domain)

        parser = self._parsers[domain]
        if parser is None:
            return True  # no robots.txt = everything allowed

        allowed = parser.can_fetch(self.USER_AGENT, url)
        if not allowed:
            logger.info("Blocked by robots.txt: %s", url)
        return allowed

    async def _fetch_robots(self, domain: str) -> Optional[RobotFileParser]:
        """Fetch and parse robots.txt for a domain."""
        robots_url = f"{domain}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(robots_url)
                if resp.status_code != 200:
                    logger.debug("No robots.txt at %s (status=%d)", robots_url, resp.status_code)
                    return None

            parser = RobotFileParser()
            parser.parse(resp.text.splitlines())
            logger.info("Loaded robots.txt from %s", robots_url)
            return parser

        except Exception as e:
            logger.debug("Couldn't fetch robots.txt from %s: %s", robots_url, e)
            return None

    @property
    def domains_checked(self) -> int:
        return len(self._parsers)
