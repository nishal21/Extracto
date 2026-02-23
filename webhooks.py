"""
webhooks.py — send notifications when a crawl finishes.

Supports Discord, Slack, and generic webhook URLs.
Keeps it simple: just POST a JSON payload with the results summary.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


async def send_webhook(
    url: str,
    pages_scraped: int,
    pages_failed: int,
    elapsed: float,
    output_path: str,
    errors: list[str] | None = None,
) -> bool:
    """
    Send a crawl completion notification to a webhook URL.
    Auto-detects Discord/Slack by URL pattern and formats accordingly.
    Returns True if successful.
    """
    if not url:
        return False

    url_lower = url.lower()

    if "discord.com/api/webhooks" in url_lower:
        payload = _discord_payload(pages_scraped, pages_failed, elapsed, output_path, errors)
    elif "hooks.slack.com" in url_lower:
        payload = _slack_payload(pages_scraped, pages_failed, elapsed, output_path, errors)
    else:
        payload = _generic_payload(pages_scraped, pages_failed, elapsed, output_path, errors)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code < 300:
                logger.info("Webhook sent to %s", url[:50])
                return True
            else:
                logger.warning("Webhook failed (%d): %s", resp.status_code, resp.text[:200])
                return False
    except Exception as e:
        logger.warning("Webhook error: %s", e)
        return False


def _discord_payload(scraped: int, failed: int, elapsed: float, path: str, errors: list[str] | None) -> dict:
    """Discord webhook format with embed."""
    status = "✅ Success" if failed == 0 else f"⚠️ Partial ({failed} failed)"
    return {
        "embeds": [{
            "title": "🕷️ Extracto — Crawl Complete",
            "color": 0x00ff88 if failed == 0 else 0xffaa00,
            "fields": [
                {"name": "Status", "value": status, "inline": True},
                {"name": "Pages", "value": str(scraped), "inline": True},
                {"name": "Time", "value": f"{elapsed:.1f}s", "inline": True},
                {"name": "Output", "value": f"`{path}`", "inline": False},
            ],
        }],
    }


def _slack_payload(scraped: int, failed: int, elapsed: float, path: str, errors: list[str] | None) -> dict:
    """Slack webhook format."""
    status = "✅ Success" if failed == 0 else f"⚠️ {failed} page(s) failed"
    return {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "🕷️ Extracto — Crawl Complete"}},
            {"type": "section", "text": {"type": "mrkdwn",
                "text": f"*Status:* {status}\n*Pages:* {scraped}\n*Time:* {elapsed:.1f}s\n*Output:* `{path}`"
            }},
        ],
    }


def _generic_payload(scraped: int, failed: int, elapsed: float, path: str, errors: list[str] | None) -> dict:
    """Generic JSON payload for any webhook."""
    return {
        "event": "crawl_complete",
        "pages_scraped": scraped,
        "pages_failed": failed,
        "elapsed_seconds": round(elapsed, 2),
        "output_path": path,
        "errors": errors or [],
    }
