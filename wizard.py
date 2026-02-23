"""
wizard.py — interactive CLI wizard for Extracto.

When the user runs `python main.py` with no args, this guides them
through the setup with simple prompts instead of a wall of --help text.
Power users can still use all the flags directly.
"""

from __future__ import annotations

from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.text import Text

from config import CrawlerConfig, AVAILABLE_MODELS

console = Console()


def run_wizard() -> CrawlerConfig:
    """
    Interactive wizard that walks the user through building a CrawlerConfig.
    Returns a ready-to-use config.
    """
    console.print()
    title = Text("🕷️  Extracto — Interactive Setup", style="bold cyan")
    console.print(Panel(title, border_style="cyan", padding=(0, 2)))
    console.print()

    # ── 1. URL ──────────────────────────────────────────────
    url = Prompt.ask(
        "[bold green]URL to scrape[/]",
        default="https://books.toscrape.com/",
    )

    # ── 2. Prompt ───────────────────────────────────────────
    prompt = Prompt.ask(
        "[bold green]What data do you want?[/]  [dim](describe in plain English)[/]",
        default="Extract all product names and prices",
    )

    # ── 3. Output format ────────────────────────────────────
    console.print("\n[bold yellow]Output format:[/]")
    formats = ["json", "csv", "xml", "excel", "markdown", "sql"]
    for i, fmt in enumerate(formats, 1):
        console.print(f"  [cyan]{i}[/]. {fmt}")
    fmt_choice = Prompt.ask(
        "Choose", choices=[str(i) for i in range(1, len(formats) + 1)], default="1"
    )
    output_format = formats[int(fmt_choice) - 1]

    # ── 4. Crawl depth ──────────────────────────────────────
    console.print("\n[bold yellow]Crawl depth:[/]")
    console.print("  [dim]0 = just this page, 1 = follow links one level, 2+ = deeper[/]")
    depth = IntPrompt.ask("Depth", default=0)

    # ── 5. LLM provider ────────────────────────────────────
    console.print("\n[bold yellow]LLM Provider:[/]")
    providers = list(AVAILABLE_MODELS.keys())
    for i, prov in enumerate(providers, 1):
        models = ", ".join(AVAILABLE_MODELS[prov])
        console.print(f"  [cyan]{i}[/]. {prov}  [dim]({models})[/]")
    prov_choice = Prompt.ask(
        "Choose", choices=[str(i) for i in range(1, len(providers) + 1)], default="1"
    )
    provider = providers[int(prov_choice) - 1]

    # ── 6. Advanced options ─────────────────────────────────
    console.print()
    advanced = Confirm.ask("[bold yellow]Configure advanced options?[/]", default=False)

    rate_limit = 0.0
    proxy = ""
    screenshots = False
    cache = False
    use_sitemap = False
    headless = True

    if advanced:
        console.print()

        rate_limit_str = Prompt.ask(
            "  [green]Rate limit[/] [dim](seconds between requests, 0 = none)[/]",
            default="0",
        )
        rate_limit = float(rate_limit_str)

        proxy = Prompt.ask(
            "  [green]Proxy[/] [dim](URL or path to proxy list, blank = none)[/]",
            default="",
        )

        screenshots = Confirm.ask("  [green]Save screenshots?[/]", default=False)
        cache = Confirm.ask("  [green]Cache pages?[/] [dim](skip re-rendering on re-runs)[/]", default=False)
        use_sitemap = Confirm.ask("  [green]Use sitemap.xml?[/] [dim](auto-discover pages)[/]", default=False)
        headless = not Confirm.ask("  [green]Show browser window?[/]", default=False)

    # ── Build config ────────────────────────────────────────
    config = CrawlerConfig(
        start_url=url,
        user_prompt=prompt,
        output_format=output_format,
        max_depth=depth,
        llm_provider=provider,
        rate_limit=rate_limit,
        proxy=proxy,
        screenshots=screenshots,
        cache=cache,
        use_sitemap=use_sitemap,
        headless=headless,
    )

    # ── Summary ─────────────────────────────────────────────
    console.print()
    console.print(Panel.fit(
        f"[bold]URL:[/]       {url}\n"
        f"[bold]Prompt:[/]    {prompt}\n"
        f"[bold]Format:[/]    {output_format}\n"
        f"[bold]Depth:[/]     {depth}\n"
        f"[bold]Provider:[/]  {provider}\n"
        f"[bold]Rate limit:[/] {rate_limit}s"
        + (f"\n[bold]Proxy:[/]     {proxy}" if proxy else ""),
        title="[cyan]📋 Configuration[/]",
        border_style="green",
    ))
    console.print()

    go = Confirm.ask("[bold green]Start scraping?[/]", default=True)
    if not go:
        console.print("[yellow]Cancelled.[/]")
        raise SystemExit(0)

    return config
