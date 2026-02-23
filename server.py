"""
server.py — REST API mode.

Run with: python main.py serve
Exposes Extracto as an HTTP API so other apps can call it.

Endpoints:
    POST /scrape — submit a scrape job, returns results as JSON
    GET  /health — quick health check
"""

from __future__ import annotations

import logging
import time
from typing import Any

from config import CrawlerConfig
from crawler_engine import CrawlerEngine

logger = logging.getLogger(__name__)


def create_app():
    """
    Create and return a FastAPI app. Import happens lazily so users
    who don't use API mode don't need fastapi installed.
    """
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel, Field
    except ImportError:
        raise ImportError(
            "API mode requires fastapi and uvicorn.\n"
            "Install with: pip install fastapi uvicorn"
        )

    app = FastAPI(
        title="Extracto API",
        description="AI-powered web scraper — give it a URL and tell it what to extract",
        version="3.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class ScrapeRequest(BaseModel):
        url: str = Field(..., description="URL to scrape")
        urls: list[str] = Field(default=[], description="Multiple URLs (batch mode)")
        prompt: str = Field(..., description="What data to extract")
        format: str = Field(default="json", description="Output format")
        depth: int = Field(default=0, description="Crawl depth")
        scope: str = Field(default="same_domain", description="Crawl scope")
        provider: str = Field(default="mistral", description="LLM provider")
        model: str = Field(default="", description="LLM model")
        schema_def: str = Field(default="", description="JSON schema for structured output", alias="schema")
        use_sitemap: bool = Field(default=False, description="Auto-discover from sitemap.xml")
        cache: bool = Field(default=False, description="Cache rendered pages")

    class ScrapeResponse(BaseModel):
        success: bool
        pages_scraped: int
        pages_failed: int
        elapsed_seconds: float
        data: list[dict[str, Any]]
        errors: list[str] = []

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "3.0.0"}

    @app.post("/scrape", response_model=ScrapeResponse)
    async def scrape(req: ScrapeRequest):
        start = time.time()

        start_urls = req.urls if req.urls else [req.url]

        config = CrawlerConfig(
            start_url=start_urls[0],
            start_urls=start_urls,
            user_prompt=req.prompt,
            output_format=req.format,
            max_depth=req.depth,
            crawl_scope=req.scope,
            llm_provider=req.provider,
            llm_model=req.model,
            schema=req.schema_def,
            use_sitemap=req.use_sitemap,
            cache=req.cache,
        )

        try:
            engine = CrawlerEngine(config)
            results = await engine.run()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        elapsed = time.time() - start

        # flatten results for API response
        flat_data = []
        for r in results:
            d = r["data"]
            if isinstance(d, list):
                flat_data.extend(d)
            elif isinstance(d, dict):
                flat_data.append(d)
            else:
                flat_data.append({"value": d})

        return ScrapeResponse(
            success=True,
            pages_scraped=len(results),
            pages_failed=len(engine.failed_urls),
            elapsed_seconds=round(elapsed, 2),
            data=flat_data,
            errors=engine.failed_urls,
        )

    return app


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the API server."""
    try:
        import uvicorn
    except ImportError:
        raise ImportError("API mode requires uvicorn. Install with: pip install uvicorn")

    app = create_app()
    print(f"\n🚀 API server starting on http://{host}:{port}")
    print(f"   Docs: http://{host}:{port}/docs\n")
    uvicorn.run(app, host=host, port=port, log_level="info")
