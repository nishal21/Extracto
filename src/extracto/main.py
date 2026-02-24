"""
main.py — CLI entry point.

Usage:
    python main.py "https://example.com" "Extract all products" --format csv --depth 1
    python main.py --batch urls.txt "Extract all products" --format json
    python main.py --config crawl.yaml
    python main.py serve             # start REST API server
    python main.py --list-models
    python main.py --help
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time

from extracto.config import CrawlerConfig, AVAILABLE_MODELS
from extracto.crawler_engine import CrawlerEngine
from extracto.data_exporter import DataExporter
from extracto.utils import console, print_banner, create_progress, print_results_preview, print_success, print_error, print_warn


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="extracto",
        description="AI-powered web scraper. Give it a URL and tell it what to extract.",
        epilog="Examples:\n"
               "  python main.py \"https://example.com\" \"Extract product names and prices\"\n"
               "  python main.py --batch urls.txt \"Extract all links\" -f csv\n"
               "  python main.py --config job.yaml\n"
               "  python main.py serve\n"
               "  python main.py --list-models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("url", nargs="?", help="Starting URL to crawl (or 'serve' for API mode)")
    p.add_argument("prompt", nargs="?", help="What data to extract (natural language)")

    # output
    p.add_argument("-f", "--format", default="json", choices=["json", "csv", "xml", "sql", "excel", "markdown"],
                   help="Output format (default: json)")
    p.add_argument("-o", "--output", default="output",
                   help="Output directory (default: output)")

    # crawl behavior
    p.add_argument("-d", "--depth", type=int, default=0,
                   help="How many link levels deep to crawl. 0 = just this page (default: 0)")
    p.add_argument("-s", "--scope", default="same_domain", choices=["same_domain", "same_directory", "external"],
                   help="Which links to follow (default: same_domain)")

    # LLM
    p.add_argument("-p", "--provider", default="mistral", choices=["mistral", "openai", "groq", "gemini", "ollama"],
                   help="LLM provider (default: mistral)")
    p.add_argument("-m", "--model", default="",
                   help="Model to use. Run --list-models to see options")

    # batch mode
    p.add_argument("--batch", metavar="FILE",
                   help="Path to a .txt file with one URL per line (batch mode)")

    # proxy
    p.add_argument("--proxy", default="",
                   help="Proxy URL or path to a .txt file with proxy list")

    # rate limiting
    p.add_argument("--rate-limit", type=float, default=0.0, metavar="SECS",
                   help="Seconds to wait between requests (default: 0 = no limit)")

    # resume
    p.add_argument("--resume", metavar="FILE", default="",
                   help="Checkpoint file for resume. If it exists, picks up where you left off")

    # Tier 2 features
    p.add_argument("--schema", default="",
                   help='JSON schema for structured output. Path to .json file or inline JSON like \'{"name": "str", "price": "float"}\'')
    p.add_argument("--screenshots", action="store_true",
                   help="Save a screenshot of every scraped page")
    p.add_argument("--cache", action="store_true",
                   help="Cache rendered pages locally. Re-runs with different prompts skip rendering")
    p.add_argument("--sitemap", action="store_true",
                   help="Auto-discover pages from sitemap.xml before crawling")
    p.add_argument("--no-robots", action="store_true",
                   help="Ignore robots.txt rules (default: respect them)")

    # Tier 3 features
    p.add_argument("--webhook", default="",
                   help="Webhook URL for completion notifications (Discord, Slack, or generic)")
    p.add_argument("--schedule", default="",
                   help='Repeat interval, e.g. "6h", "30m", "1d". Runs the crawl on a loop')
    p.add_argument("--port", type=int, default=8000,
                   help="Port for API server mode (default: 8000)")

    # config file
    p.add_argument("--config", metavar="YAML",
                   help="Load all settings from a YAML config file. CLI flags override YAML values")

    # browser
    p.add_argument("--headless", action="store_true", default=True,
                   help="Run browser in headless mode (default)")
    p.add_argument("--no-headless", action="store_false", dest="headless",
                   help="Show the browser window")

    # misc
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Enable debug logging")
    p.add_argument("--list-models", action="store_true",
                   help="Show available models for each provider and exit")

    return p.parse_args()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s │ %(levelname)-7s │ %(name)-22s │ %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    for name in ("httpx", "httpcore", "urllib3", "playwright", "asyncio", "crawlee"):
        logging.getLogger(name).setLevel(logging.WARNING)


def show_models() -> None:
    """Print all available models per provider and exit."""
    from rich.table import Table
    table = Table(title="Available Models", border_style="cyan", show_lines=True)
    table.add_column("Provider", style="bold")
    table.add_column("Models (first = default)")
    table.add_column("Env Variable")

    env_vars = {
        "mistral": "MISTRAL_API_KEY",
        "openai": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "ollama": "(none — local)",
    }
    for provider, models in AVAILABLE_MODELS.items():
        model_list = ", ".join(f"[bold]{m}[/]" if i == 0 else m for i, m in enumerate(models))
        table.add_row(provider, model_list, env_vars.get(provider, ""))

    console.print(table)
    console.print("\n[dim]Usage: python main.py <url> <prompt> -p <provider> -m <model>[/]")


def load_batch_urls(path: str) -> list[str]:
    """Read URLs from a text file, one per line. Skips blanks and comments."""
    urls = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def build_config(args: argparse.Namespace) -> CrawlerConfig:
    """
    Build a CrawlerConfig from CLI args, optionally layered on top of a YAML file.
    Priority: CLI args > YAML file > dataclass defaults.
    """
    if args.config:
        # load from YAML, then override with any CLI flags that were explicitly set
        config = CrawlerConfig.from_yaml(
            args.config,
            start_url=args.url or "",
            user_prompt=args.prompt or "",
            output_format=args.format,
            max_depth=args.depth,
            crawl_scope=args.scope,
            llm_provider=args.provider,
            llm_model=args.model,
            output_dir=args.output,
            headless=args.headless,
            verbose=args.verbose,
            proxy=args.proxy,
            rate_limit=args.rate_limit,
            checkpoint_file=args.resume,
            schema=args.schema,
            screenshots=args.screenshots,
            cache=args.cache,
            use_sitemap=args.sitemap,
            respect_robots=not args.no_robots,
        )
    else:
        # build from CLI args directly
        start_urls = []
        if args.batch:
            start_urls = load_batch_urls(args.batch)
            if not start_urls:
                print_error(f"No URLs found in {args.batch}")
                sys.exit(1)
            console.print(f"[cyan]Batch mode:[/] loaded {len(start_urls)} URLs from {args.batch}")

        config = CrawlerConfig(
            start_url=args.url or (start_urls[0] if start_urls else ""),
            start_urls=start_urls,
            user_prompt=args.prompt or "",
            output_format=args.format,
            max_depth=args.depth,
            crawl_scope=args.scope,
            llm_provider=args.provider,
            llm_model=args.model,
            output_dir=args.output,
            headless=args.headless,
            verbose=args.verbose,
            proxy=args.proxy,
            rate_limit=args.rate_limit,
            checkpoint_file=args.resume,
            schema=args.schema,
            screenshots=args.screenshots,
            cache=args.cache,
            use_sitemap=args.sitemap,
            respect_robots=not args.no_robots,
        )

    return config


async def main() -> None:
    args = parse_args()

    if args.list_models:
        show_models()
        return

    # API server mode
    if args.url == "serve":
        from extracto.server import run_server
        run_server(port=args.port)
        return

    # need at least a URL (or batch file or config) and a prompt
    has_urls = args.url or args.batch or args.config
    has_prompt = args.prompt or args.config
    if not has_urls or not has_prompt:
        # no args? launch the interactive wizard
        from extracto.wizard import run_wizard
        config = run_wizard()
        setup_logging(config.verbose)
    else:
        setup_logging(args.verbose)
        config = build_config(args)

    if not config.user_prompt:
        print_error("No prompt specified. Tell me what data to extract.")
        return

    print_banner(config)

    if config.rate_limit > 0:
        console.print(f"[dim]Rate limit: {config.rate_limit}s between requests[/]")
    if config.proxy:
        proxy_count = len(config.get_proxy_list())
        console.print(f"[dim]Proxies: {proxy_count} configured[/]")
    if config.checkpoint_file:
        console.print(f"[dim]Resume: checkpoint → {config.checkpoint_file}[/]")

    start_time = time.time()

    # crawl with a live progress display
    progress = create_progress()
    task_id = None

    def on_page(url: str, depth: int, total: int) -> None:
        nonlocal task_id
        if task_id is None:
            return
        progress.update(task_id, completed=total, description=f"[depth={depth}] {url[:60]}")

    with progress:
        task_id = progress.add_task("Starting...", total=None)

        try:
            engine = CrawlerEngine(config, progress_callback=on_page)
        except ValueError as e:
            progress.stop()
            print_error(str(e))
            return

        # if resuming, show how many we already had
        if engine.pages_done > 0:
            console.print(f"[cyan]Resuming:[/] {engine.pages_done} pages already done")
            progress.update(task_id, completed=engine.pages_done)

        results = await engine.run()

        progress.update(task_id, description="Done", completed=len(results))

    elapsed = time.time() - start_time

    # handle empty results
    if not results:
        print_error("No data extracted. Check your URL, prompt, or API key.")
        if engine.failed_urls:
            print_warn(f"Failed pages: {', '.join(engine.failed_urls[:5])}")
        return

    # export
    out_path = DataExporter.export(
        data=results,
        fmt=config.output_format,
        output_dir=config.output_dir,
    )

    # write run summary
    DataExporter.write_summary(
        output_dir=config.output_dir,
        pages_crawled=len(results),
        pages_failed=len(engine.failed_urls),
        elapsed=elapsed,
        output_path=out_path,
    )

    # preview what we got
    all_rows = []
    for r in results:
        d = r["data"]
        if isinstance(d, dict):
            lists = [v for v in d.values() if isinstance(v, list)]
            all_rows.extend(lists[0] if len(lists) == 1 else [d])
        elif isinstance(d, list):
            all_rows.extend(d)
        else:
            all_rows.append({"value": d})

    print_results_preview(all_rows)
    print_success(out_path, len(results), elapsed)

    if engine.failed_urls:
        print_warn(f"{len(engine.failed_urls)} page(s) failed: {', '.join(engine.failed_urls[:5])}")

    # send webhook notification if configured
    if args.webhook:
        from extracto.webhooks import send_webhook
        await send_webhook(
            url=args.webhook,
            pages_scraped=len(results),
            pages_failed=len(engine.failed_urls),
            elapsed=elapsed,
            output_path=out_path,
            errors=engine.failed_urls,
        )
        console.print(f"[dim]Webhook sent to {args.webhook[:40]}...[/]")


def parse_schedule(s: str) -> float:
    """Parse a schedule string like '6h', '30m', '1d' into seconds."""
    s = s.strip().lower()
    if s.endswith("d"):
        return float(s[:-1]) * 86400
    if s.endswith("h"):
        return float(s[:-1]) * 3600
    if s.endswith("m"):
        return float(s[:-1]) * 60
    return float(s)  # assume seconds


def cli_entry():
    args = parse_args()

    if args.schedule:
        interval = parse_schedule(args.schedule)
        console.print(f"[cyan]Scheduled mode:[/] running every {args.schedule}")
        while True:
            asyncio.run(main())
            console.print(f"\n[dim]Next run in {args.schedule}. Press Ctrl+C to stop.[/]")
            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                console.print("\n[yellow]Schedule stopped.[/]")
                break
    else:
        asyncio.run(main())

if __name__ == "__main__":
    cli_entry()
