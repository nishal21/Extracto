"""
cache.py — page cache so you don't re-render the same URL twice.

Stores rendered markdown on disk keyed by URL hash.
Useful when you want to run different prompts against the same pages
without re-crawling — saves both time and API costs.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class PageCache:
    """
    Simple file-based cache. Stores page markdown in a directory,
    keyed by a hash of the URL. No TTL or eviction — just raw files.
    """

    def __init__(self, cache_dir: str = ".cache") -> None:
        self._dir = cache_dir
        os.makedirs(self._dir, exist_ok=True)

    @staticmethod
    def _key(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def get(self, url: str) -> Optional[str]:
        """Return cached markdown for a URL, or None if not cached."""
        path = os.path.join(self._dir, self._key(url) + ".md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.debug("Cache hit: %s", url)
            return content
        return None

    def put(self, url: str, markdown: str) -> None:
        """Store rendered markdown for a URL."""
        path = os.path.join(self._dir, self._key(url) + ".md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(markdown)
        logger.debug("Cached: %s", url)

    def has(self, url: str) -> bool:
        return os.path.exists(os.path.join(self._dir, self._key(url) + ".md"))

    @property
    def size(self) -> int:
        """Number of cached pages."""
        return len([f for f in os.listdir(self._dir) if f.endswith(".md")])
