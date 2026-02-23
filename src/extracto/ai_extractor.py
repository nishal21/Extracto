"""
ai_extractor.py — LLM-powered data extraction.

Feeds page markdown + a natural language prompt into ScrapeGraphAI
and gets structured data back. Supports multiple LLM providers
through a factory that picks the right LangChain chat class.
"""

from __future__ import annotations

import logging
from typing import Any

from scrapegraphai.graphs import SmartScraperGraph

from extracto.config import CrawlerConfig

logger = logging.getLogger(__name__)

# default context windows — not exact, but good enough for truncation
_MODEL_TOKENS = {
    "mistral": 32_000,
    "openai": 128_000,
    "groq": 8_000,
    "gemini": 1_000_000,
    "ollama": 8_000,
}


def create_llm(config: CrawlerConfig):
    """
    Build the right LangChain chat model based on config.llm_provider.

    We import each provider lazily so you only need the deps for
    the provider you're actually using.
    """
    provider = config.llm_provider
    model = config.llm_model
    key = config.llm_api_key
    temp = config.llm_temperature

    if provider == "mistral":
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(model=model, mistral_api_key=key, temperature=temp)

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, api_key=key, temperature=temp)

    elif provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model_name=model, groq_api_key=key, temperature=temp)

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, google_api_key=key, temperature=temp)

    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model, temperature=temp)

    else:
        raise ValueError(f"Unknown provider: {provider}. Use: mistral, openai, groq, gemini, ollama")


class AIExtractor:
    """Wraps ScrapeGraphAI to pull structured data from markdown."""

    def __init__(self, config: CrawlerConfig) -> None:
        self._config = config
        self._llm = create_llm(config)
        self._max_tokens = _MODEL_TOKENS.get(config.llm_provider, 32_000)

    def _graph_config(self) -> dict:
        return {
            "llm": {
                "model_instance": self._llm,
                "model_tokens": self._max_tokens,
            },
            "verbose": False,
            "headless": True,
        }

    def extract(self, markdown: str, url: str, user_prompt: str) -> Any:
        """
        Run the AI extraction. Returns whatever the LLM gives us — 
        usually a dict or list of dicts. Returns None on failure.
        """
        if not markdown.strip():
            logger.warning("Empty markdown for %s, skipping", url)
            return None

        # don't blow up the context window
        max_chars = min(self._max_tokens * 3, 300_000)
        source = markdown[:max_chars]

        graph = SmartScraperGraph(
            prompt=user_prompt,
            source=source,
            config=self._graph_config(),
        )

        # try twice — first attempt sometimes flakes on rate limits
        for attempt in range(2):
            try:
                result = graph.run()
                logger.info("Extracted from %s (type=%s)", url, type(result).__name__)
                return result
            except Exception:
                if attempt == 0:
                    logger.warning("Extraction failed for %s, retrying...", url)
                else:
                    logger.exception("Extraction failed for %s after retry", url)
                    return None
