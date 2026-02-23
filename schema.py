"""
schema.py — optional structured output with Pydantic.

If the user provides a JSON schema or Pydantic-style field definitions,
we tell the LLM to output exactly that shape. Makes results predictable
instead of hoping the LLM guesses what you want.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


def load_schema(path_or_json: str) -> Optional[dict]:
    """
    Load a schema from either:
    - a .json file path
    - an inline JSON string

    Returns a dict describing the expected output shape, or None.
    """
    if not path_or_json:
        return None

    # try as file first
    if os.path.isfile(path_or_json):
        try:
            with open(path_or_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Couldn't parse schema file %s: %s", path_or_json, e)
            return None

    # try as inline JSON
    try:
        return json.loads(path_or_json)
    except json.JSONDecodeError:
        logger.warning("Schema string isn't valid JSON: %s", path_or_json[:100])
        return None


def schema_to_prompt(schema: dict) -> str:
    """
    Convert a schema dict into a prompt suffix that tells the LLM
    exactly what shape to return.

    Supports two formats:
    1. Simple field list: {"name": "str", "price": "float", "in_stock": "bool"}
    2. Full JSON schema: {"type": "array", "items": {"type": "object", "properties": {...}}}
    """
    # detect if it's a simple field map vs full JSON schema
    if "type" in schema and "properties" in schema.get("items", schema):
        # full JSON schema — just dump it
        return (
            "\n\nYou MUST return data matching this exact JSON schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```\n"
            "Return ONLY valid JSON, no explanations."
        )

    # simple field map — more common for CLI usage
    fields = []
    for name, typ in schema.items():
        fields.append(f"  - {name}: {typ}")

    return (
        "\n\nReturn the data as a JSON array of objects with EXACTLY these fields:\n"
        + "\n".join(fields)
        + "\n\nReturn ONLY the JSON array, nothing else."
    )
