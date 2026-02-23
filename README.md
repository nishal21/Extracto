<div align="center">
  <img src="docs/favicon.svg" alt="Extracto Logo" width="120" height="120">
  <h1>Extracto</h1>
</div>

AI-powered web scraper. Give it a URL and tell it what data you want — it handles the rest.

Built with [Crawlee](https://crawlee.dev/) + [Playwright](https://playwright.dev/) + [ScrapeGraphAI](https://scrapegraphai.com/) + [pandas](https://pandas.pydata.org/).

## What it does

- **Smart extraction** — describe what you want in plain English, the AI pulls exactly that
- **JavaScript rendering** — handles SPAs, dynamic content, infinite scroll
- **Multi-format export** — JSON, CSV, XML, SQLite, Excel, Markdown
- **Batch mode** — process hundreds of URLs from a file
- **Proxy rotation** — avoid IP bans with automatic proxy cycling
- **Resume/checkpoint** — crash-safe crawling, picks up where it left off
- **Scheduled runs** — repeat crawls on a timer (every 6h, daily, etc.)
- **REST API** — deploy as a service anyone on your team can use
- **Webhook notifications** — get pinged on Discord/Slack when a crawl finishes
- **robots.txt compliance** — respects site rules by default
- **5 LLM providers** — Mistral, OpenAI, Groq, Gemini, Ollama (local)

## Quick start

```bash
# install globally via pip
pip install extracto-scraper==2.0.2

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

## Interactive mode

Don't want to memorize flags? Just run it with no arguments:

```bash
python main.py
```

A friendly wizard walks you through everything — URL, what to extract, output format, LLM provider, and optional advanced settings. No flags needed.

## CLI reference

```
python main.py <url> <prompt> [options]
python main.py serve                    # start REST API
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
python main.py "https://news.ycombinator.com/" "Extract all post titles and links"

# depth crawl — follow links 2 levels deep, export CSV
python main.py "https://docs.python.org/3/" "Extract function names and descriptions" -d 2 -f csv

# batch mode — scrape many URLs at once
python main.py --batch urls.txt "Extract all product names and prices" -f json

# structured output — force exact JSON shape
python main.py "https://example.com" "Get products" --schema '{"name": "str", "price": "float", "in_stock": "bool"}'

# with proxy rotation + rate limiting
python main.py "https://example.com" "Get all links" --proxy proxies.txt --rate-limit 2

# resume after crash
python main.py --batch urls.txt "Get data" --resume checkpoint.json

# use a YAML config for complex jobs
python main.py --config crawl.yaml

# API server mode
python main.py serve --port 8080

# scheduled monitoring — run every 6 hours
python main.py "https://competitor.com/pricing" "Get all prices" --schedule 6h --webhook https://hooks.slack.com/your/url

# use different LLM providers
python main.py "https://example.com" "Get contact info" -p openai
python main.py "https://example.com" "Get links" -p ollama -m llama3.2
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
python main.py --config crawl.yaml
```

See `crawl.example.yaml` for all available options.

## REST API

Start the API server:

```bash
pip install fastapi uvicorn  # one-time setup
python main.py serve
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

Run `python main.py --list-models` to see all available models.

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