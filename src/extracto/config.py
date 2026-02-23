"""
config.py — all the knobs in one place.

Every module reads from this dataclass instead of having their own
config scattered everywhere. Edit defaults here or pass values from CLI.
Also supports loading from a YAML config file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv

load_dotenv()  # load .env if it exists, otherwise no-op

# models people can pick from — first one in each list is the default
AVAILABLE_MODELS = {
    "mistral": [
        "mistral-small-latest",       # fast, cheap, good enough for most scraping
        "mistral-large-latest",       # best quality from mistral
        "mistral-small-3.2",          # newest small
        "codestral-latest",           # code-focused
        "open-mistral-nemo",          # 12B, open weights
    ],
    "openai": [
        "gpt-4.1-mini",              # best bang for buck
        "gpt-4.1",                   # strong all-rounder
        "gpt-4o-mini",               # still works via API
        "gpt-4o",                    # multimodal
        "gpt-5-mini",               # latest gen, fast
        "o3-mini",                   # reasoning model
    ],
    "groq": [
        "llama-3.3-70b-versatile",   # best quality on groq
        "llama-3.1-8b-instant",      # fastest
        "deepseek-r1-distill-llama-70b",  # reasoning
        "gemma2-9b-it",              # google's open model
        "mixtral-8x7b-32768",        # MoE
    ],
    "gemini": [
        "gemini-2.5-flash",          # fast + smart, best default
        "gemini-2.5-pro",            # highest quality
        "gemini-2.0-flash",          # still works, retiring mid-2026
        "gemini-3-flash",            # newest gen
        "gemini-3-pro",              # newest gen, top tier
    ],
    "ollama": [
        "llama3.2",                  # good general purpose 3B
        "llama3.3",                  # 70B, needs beefy GPU
        "deepseek-r1:8b",            # reasoning, runs on most hardware
        "qwen2.5:7b",               # strong all-rounder
        "gemma3:4b",                 # lightweight
        "phi3",                       # microsoft, small + capable
        "mistral",                   # 7B classic
    ],
}


@dataclass
class CrawlerConfig:
    # what to scrape — can be a single URL or list (batch mode)
    start_url: str = "https://books.toscrape.com/"
    start_urls: list[str] = field(default_factory=list)  # batch mode
    user_prompt: str = "Extract all book titles and prices."

    # output
    output_format: Literal["json", "csv", "xml", "sql", "excel", "markdown"] = "json"
    output_dir: str = "output"

    # crawl behavior
    max_depth: int = 0
    crawl_scope: Literal["same_domain", "same_directory", "external"] = "same_domain"

    # browser
    headless: bool = True
    request_timeout_ms: int = 60_000
    viewport_width: int = 1920
    viewport_height: int = 1080

    # LLM — pick your provider
    llm_provider: Literal["mistral", "openai", "groq", "gemini", "ollama"] = "mistral"
    llm_model: str = ""  # blank = use provider default
    llm_api_key: str = ""  # blank = read from env
    llm_temperature: float = 0.0

    # crawl limits
    max_concurrency: int = 5
    max_requests_per_crawl: int = 100

    # proxy — single URL or path to a txt file with one proxy per line
    proxy: str = ""

    # rate limiting — seconds between requests (0 = no delay)
    rate_limit: float = 0.0

    # resume — save/restore crawl state to this file
    checkpoint_file: str = ""

    # schema — path to a .json file or inline JSON for structured output
    schema: str = ""

    # screenshots — save a screenshot of every page
    screenshots: bool = False

    # cache — cache rendered pages to skip re-rendering on re-runs
    cache: bool = False

    # sitemap — auto-discover pages from sitemap.xml
    use_sitemap: bool = False

    # robots.txt — respect robots.txt rules (default: True)
    respect_robots: bool = True

    # misc
    verbose: bool = False

    def __post_init__(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)

        # if start_urls is empty but start_url is set, use that
        if not self.start_urls and self.start_url:
            self.start_urls = [self.start_url]
        elif self.start_urls:
            self.start_url = self.start_urls[0]

        # resolve API key from env if not explicitly set
        if not self.llm_api_key:
            env_map = {
                "mistral": "MISTRAL_API_KEY",
                "openai": "OPENAI_API_KEY",
                "groq": "GROQ_API_KEY",
                "gemini": "GOOGLE_API_KEY",
                "ollama": "",
            }
            env_var = env_map.get(self.llm_provider, "")
            if env_var:
                self.llm_api_key = os.getenv(env_var, "")

        # provider-specific model defaults so users don't have to remember model names
        if not self.llm_model:
            defaults = {
                "mistral": "mistral-small-latest",
                "openai": "gpt-4.1-mini",
                "groq": "llama-3.3-70b-versatile",
                "gemini": "gemini-2.5-flash",
                "ollama": "llama3.2",
            }
            self.llm_model = defaults.get(self.llm_provider, "mistral-small-latest")

    @classmethod
    def from_yaml(cls, path: str, **overrides) -> "CrawlerConfig":
        """
        Load config from a YAML file. CLI args can override specific fields.
        Missing fields fall back to dataclass defaults.
        """
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # flatten nested sections if the YAML uses them
        flat = {}
        for key, val in data.items():
            if isinstance(val, dict):
                flat.update(val)
            else:
                flat[key] = val

        # CLI overrides take priority
        flat.update({k: v for k, v in overrides.items() if v is not None and v != ""})

        # only pass keys that CrawlerConfig actually knows about
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in flat.items() if k in valid}

        return cls(**filtered)

    def get_proxy_list(self) -> list[str]:
        """
        Resolve the proxy field — could be a single URL or a path to a .txt file.
        Returns a list of proxy URLs (empty if no proxy configured).
        """
        if not self.proxy:
            return []

        if os.path.isfile(self.proxy):
            with open(self.proxy, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip() and not line.startswith("#")]

        # single proxy URL
        return [self.proxy]
