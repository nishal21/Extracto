"""
sitemap.py — auto-discover pages from sitemap.xml.

Parses standard XML sitemaps and sitemap indexes.
If a site has a sitemap, this is way faster than crawling
because you get all URLs upfront without rendering anything.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

# namespace used in standard sitemap XML
_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


async def discover_sitemap_urls(base_url: str, max_urls: int = 500) -> list[str]:
    """
    Try to fetch and parse sitemap.xml for the given URL.
    Returns a list of page URLs found, or empty list if no sitemap.
    """
    sitemap_url = urljoin(base_url, "/sitemap.xml")
    urls: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(sitemap_url)
            if resp.status_code != 200:
                logger.debug("No sitemap at %s (status=%d)", sitemap_url, resp.status_code)
                return []

            urls = _parse_sitemap(resp.text, client, max_urls)

    except Exception as e:
        logger.debug("Sitemap fetch failed for %s: %s", base_url, e)
        return []

    logger.info("Sitemap: found %d URLs from %s", len(urls), sitemap_url)
    return urls[:max_urls]


def _parse_sitemap(xml_text: str, client: Optional[httpx.AsyncClient] = None, max_urls: int = 500) -> list[str]:
    """Parse a sitemap XML string. Handles both urlset and sitemapindex."""
    urls = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.warning("Invalid sitemap XML: %s", e)
        return []

    tag = root.tag.lower()

    # regular sitemap — grab all <loc> inside <url>
    if "urlset" in tag:
        for url_el in root.findall(".//sm:url/sm:loc", _NS):
            if url_el.text:
                urls.append(url_el.text.strip())
        # also try without namespace (some sites don't use it)
        if not urls:
            for url_el in root.iter():
                if url_el.tag.endswith("loc") and url_el.text:
                    urls.append(url_el.text.strip())

    # sitemap index — lists other sitemaps (we just grab the URLs, not recursive)
    elif "sitemapindex" in tag:
        for loc_el in root.findall(".//sm:sitemap/sm:loc", _NS):
            if loc_el.text:
                urls.append(loc_el.text.strip())
        if not urls:
            for el in root.iter():
                if el.tag.endswith("loc") and el.text:
                    urls.append(el.text.strip())

    return urls[:max_urls]
