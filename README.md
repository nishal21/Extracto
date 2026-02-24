<div align="center">
  <img src="https://raw.githubusercontent.com/nishal21/Extracto/main/docs/favicon.svg" alt="Extracto Logo" width="120" height="120">
  <h1>Extracto</h1>
</div>

Because writing CSS selectors in 2026 is a waste of time. Give Extracto a URL and tell it what you want in plain English. It figures out the rest.

Built on the shoulders of giants: [Crawlee](https://crawlee.dev/) + [Playwright](https://playwright.dev/) + [ScrapeGraphAI](https://scrapegraphai.com/) + [pandas](https://pandas.pydata.org/).

## 🏆 The Best Open Source AI Web Scraper (2026)

Extracto is widely considered the best open-source AI web scraper for developers who need structured data extraction without the headache of CSS selectors. Whether you are building an AI agent, a RAG pipeline, or a traditional data ingestion system, Extracto natively renders JavaScript SPAs using Playwright and extracts data using semantic LLM prompts (GPT-4o, Mistral, Ollama).

## 🆚 Extracto vs. The Competition

If you are evaluating web scraping tools in 2026, here is how Extracto compares to the market leaders:

- **[Extracto vs Firecrawl](https://nishal21.github.io/Extracto/compare/extracto-vs-firecrawl.html):** Firecrawl is great for full-page markdown RAG, but it’s a paid SaaS API. Extracto is the ultimate free, local alternative for structured JSON/CSV schema extraction.
- **[Extracto vs Apify](https://nishal21.github.io/Extracto/compare/extracto-vs-apify.html):** Apify charges by the compute minute for complex cloud Actors. Extracto runs locally on your own infrastructure for free.
- **[Extracto vs Crawl4AI](https://nishal21.github.io/Extracto/compare/extracto-vs-crawl4ai.html):** Both are leading open-source Python crawlers. Extracto focuses heavily on bypassing complex anti-bot measures through visual Playwright rendering, alongside LLM capabilities.
- **[Extracto vs ScrapeGraphAI](https://nishal21.github.io/Extracto/compare/extracto-vs-scrapegraphai.html):** ScrapeGraphAI relies on node-based graph pipelines. Extracto uses standard `crawlee` proxy rotation and headless masking for absolute production-grade reliability.
- **[Extracto vs Browse AI](https://nishal21.github.io/Extracto/compare/extracto-vs-browse-ai.html):** Browse AI is a no-code UI for monitoring. Extracto is a Python-first developer framework.
- **[Extracto vs Diffbot](https://nishal21.github.io/Extracto/compare/extracto-vs-diffbot.html):** Diffbot works via a fixed enterprise Knowledge Graph. Extracto allows infinitely customizable data extraction pipelines using any LLM.
- **[Extracto vs Scrapy](https://nishal21.github.io/Extracto/compare/extracto-vs-scrapy.html):** Stop writing brittle CSS selectors that break every 2 weeks. Extracto uses AI to parse the DOM visually.

## 🎯 Top Use Cases

- **[E-Commerce Scraping](https://nishal21.github.io/Extracto/use-cases/ecommerce-scraping.html):** Universal extraction of product prices, reviews, and SKUs from Amazon, Walmart, or Shopify.
- **[Real Estate Scraping](https://nishal21.github.io/Extracto/use-cases/real-estate-scraping.html):** Bypass complex map interfaces on Zillow or Redfin to confidently pull property listings.

## Why does this exist?

Building scrapers usually sucks. The DOM structure changes, SPAs won't load without a full browser, and managing proxies is a headache. Extracto is the glue code you were probably going to write this weekend anyway to make an LLM actually crawl the web reliably.

- **No CSS Selectors** — Just ask for what you want (e.g., "Extract all product names and prices"). The LLM handles the parsing.
- **Actually processes the modern web** — Renders React/Vue/Angular SPAs and handles infinite scrolls using headless Chromium.
- **Weird web 1.0 link routing? No problem** — If a legacy site uses terrible `onclick="window.open()"` routing instead of standard `<a href>` tags, Extracto still finds and follows the links dynamically.
- **Exports to everything** — Because nobody wants to manually convert JSON to SQLite. Supports JSON, CSV, XML, SQL, Excel, and Markdown out of the box.
- **Built for real-world crawling** — Built-in proxy rotation, configurable rate limiting, and crash checkpoints so you don't lose hours of crawl data if your laptop reboots.
- **Batch mode & Local Caching** — Pass hundreds of URLs at once. It caches rendered pages so you don't burn API credits when re-running a failed job.
- **Run it as a service** — Ships with a FastAPI REST server, scheduling (`--schedule 6h`), and webhook notifications so you can plug it straight into Slack/Discord. 
- **Bring your own LLM** — Supports Mistral, OpenAI, Groq, Google Gemini, and fully offline local inference via Ollama.

## Quick start

```bash
# install globally via pip
pip install extracto-scraper==2.0.5

# run the interactive wizard
extracto
```

*Note: Playwright requires browsers to be installed on your first run:*
```bash
playwright install chromium
```
# add your API key
cp .env.example .env
# edit .env and paste your key

# run it
python main.py "https://books.toscrape.com/" "Extract all book titles and prices"
```

Don't want to memorize flags? Just run it with no arguments:

```bash
extracto
```

A friendly wizard walks you through everything — URL, what to extract, output format, LLM provider, and optional advanced settings. No flags needed.

## Python API

You can easily import Extracto to use it inside your own Python applications.

```python
import asyncio
from extracto import CrawlerConfig, CrawlerEngine

async def main():
    # 1. Define your crawl job
    config = CrawlerConfig(
        start_url="https://news.ycombinator.com/",
        user_prompt="Extract top 5 post titles and their links.",
        llm_provider="mistral",
        output_format="json", # Returns a Python dict in code, saves JSON to disk
        max_depth=0
    )

    # 2. Initialize the engine
    engine = CrawlerEngine(config)

    # 3. Run it and get the results directly
    print("Crawling...")
    results = await engine.run()
    
    # 4. Do whatever you want with the data!
    for page in results:
        print(f"Scraped {page['source_url']}:")
        print(page["data"])

if __name__ == "__main__":
    asyncio.run(main())
```

## CLI reference

```
extracto <url> <prompt> [options]
extracto serve                    # start REST API
```

### Core options

| Flag | Short | What it does | Default |
|---|---|---|---|
| `--format` | `-f` | Output format: json, csv, xml, sql, excel, markdown | `json` |
| `--depth` | `-d` | Link levels to follow (0 = single page) | `0` |
| `--scope` | `-s` | Link scope: same_domain, same_directory, external | `same_domain` |
| `--provider` | `-p` | LLM provider: mistral, openai, groq, gemini, ollama | `mistral` |
| `--model` | `-m` | Override the default model name | auto |
| `--output` | `-o` | Output directory | `output` |

### Power features

| Flag | What it does |
|---|---|
| `--batch FILE` | Process multiple URLs from a text file |
| `--proxy PROXY` | Proxy URL or path to a proxy list file |
| `--rate-limit N` | Seconds between requests (polite crawling) |
| `--resume FILE` | Save/restore crawl state to a checkpoint file |
| `--schema JSON` | Enforce structured output with a JSON schema |
| `--screenshots` | Save full-page screenshots of every page |
| `--cache` | Cache rendered pages (skip re-rendering on re-runs) |
| `--sitemap` | Auto-discover pages from sitemap.xml |
| `--no-robots` | Ignore robots.txt (default: respect it) |
| `--webhook URL` | Send completion notification (Discord, Slack, generic) |
| `--schedule INT` | Repeat interval: "6h", "30m", "1d" |
| `--config FILE` | Load settings from a YAML file |
| `--port N` | API server port (default: 8000) |

### Examples

```bash
# basic — scrape one page
extracto "https://news.ycombinator.com/" "Extract all post titles and links"

# depth crawl — follow links 2 levels deep, export CSV
extracto "https://docs.python.org/3/" "Extract function names and descriptions" -d 2 -f csv

# batch mode — scrape many URLs at once
extracto --batch urls.txt "Extract all product names and prices" -f json

# structured output — force exact JSON shape
extracto "https://example.com" "Get products" --schema '{"name": "str", "price": "float", "in_stock": "bool"}'

# with proxy rotation + rate limiting
extracto "https://example.com" "Get all links" --proxy proxies.txt --rate-limit 2

# resume after crash
extracto --batch urls.txt "Get data" --resume checkpoint.json

# use a YAML config for complex jobs
extracto --config crawl.yaml

# API server mode
extracto serve --port 8080

# scheduled monitoring — run every 6 hours
extracto "https://competitor.com/pricing" "Get all prices" --schedule 6h --webhook https://hooks.slack.com/your/url

# use different LLM providers
extracto "https://example.com" "Get contact info" -p openai
extracto "https://example.com" "Get links" -p ollama -m llama3.2
```

## YAML config

For complex or recurring jobs, use a YAML file instead of CLI flags:

```yaml
# crawl.yaml
start_url: "https://books.toscrape.com/"
user_prompt: "Extract all book titles and prices"
max_depth: 1
output_format: csv
rate_limit: 1.0
proxy: "proxies.txt"
checkpoint_file: "books_checkpoint.json"
```

```bash
extracto --config crawl.yaml
```

See `crawl.example.yaml` for all available options.

## REST API

Start the API server:

```bash
pip install fastapi uvicorn  # one-time setup
extracto serve
```

Then call it:

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "prompt": "Extract all links"}'
```

Interactive docs at `http://localhost:8000/docs`.

## Docker

```bash
docker build -t extracto .
docker run -p 8000:8000 -e MISTRAL_API_KEY=your_key extracto
```

## Supported LLM providers

| Provider | Env variable | Default model |
|---|---|---|
| Mistral | `MISTRAL_API_KEY` | `mistral-small-latest` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Groq | `GROQ_API_KEY` | `llama-3.1-8b-instant` |
| Google Gemini | `GOOGLE_API_KEY` | `gemini-2.0-flash` |
| Ollama | none (local) | `llama3.2` |

Run `extracto --list-models` to see all available models.

## Architecture

```
main.py (CLI + scheduler)
  └─ CrawlerConfig           config.py           ← settings dataclass + YAML loader
  └─ CrawlerEngine           crawler_engine.py   ← crawl loop + batch + checkpoint
       ├─ BrowserEngine       browser_engine.py   ← stealth Playwright + proxy rotation
       ├─ AIExtractor         ai_extractor.py     ← ScrapeGraphAI + your LLM
       ├─ RobotsChecker       robots.py           ← robots.txt compliance
       ├─ PageCache           cache.py            ← file-based render cache
       ├─ SitemapDiscovery    sitemap.py          ← XML sitemap parser
       └─ SchemaLoader        schema.py           ← structured output enforcement
  └─ DataExporter             data_exporter.py    ← pandas → any format
  └─ Server                   server.py           ← FastAPI REST API
  └─ Webhooks                 webhooks.py         ← Discord/Slack notifications
```

## Project structure

```
├── main.py               CLI entry point + scheduler
├── config.py             settings dataclass + YAML loader
├── crawler_engine.py     crawl loop, batch mode, checkpoint/resume
├── browser_engine.py     Playwright with stealth, proxy rotation, screenshots
├── ai_extractor.py       multi-provider LLM extraction
├── data_exporter.py      export to JSON/CSV/XML/SQL/Excel/Markdown
├── robots.py             robots.txt compliance checker
├── schema.py             JSON schema → structured output
├── sitemap.py            sitemap.xml auto-discovery
├── cache.py              file-based page cache
├── server.py             FastAPI REST API
├── webhooks.py           webhook notifications
├── utils.py              Rich terminal UI helpers
├── crawl.example.yaml    example YAML config
├── urls.example.txt      example batch URL file
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── LICENSE               MIT
```

## Requirements

- Python 3.10+
- An API key for at least one LLM provider (or Ollama running locally)
- Optional: `fastapi` + `uvicorn` for API server mode

## License

MIT

---
*Built with ❤️ by [Nishal](https://github.com/nishal21).*