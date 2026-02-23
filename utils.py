"""
utils.py — terminal UI stuff.

All the Rich-powered pretty printing lives here so the rest of the
codebase doesn't need to care about formatting.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.text import Text

console = Console()


def print_banner(config) -> None:
    """Show a quick summary of what we're about to do."""
    lines = [
        f"[bold]URL:[/]         {config.start_url}",
        f"[bold]Prompt:[/]      {config.user_prompt}",
        f"[bold]Format:[/]      {config.output_format}",
        f"[bold]Depth:[/]       {config.max_depth}",
        f"[bold]Scope:[/]       {config.crawl_scope}",
        f"[bold]Provider:[/]    {config.llm_provider} ({config.llm_model})",
    ]
    panel = Panel(
        "\n".join(lines),
        title="[bold cyan]crawl4ai[/]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)


def create_progress() -> Progress:
    """Reusable progress bar with spinner."""
    return Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("[cyan]{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    )


def print_results_preview(data: list[dict], max_rows: int = 8) -> None:
    """Show a quick table preview of what we extracted."""
    if not data:
        console.print("[yellow]No data to preview.[/]")
        return

    # figure out columns from the first item
    sample = data[0] if isinstance(data[0], dict) else {"value": data[0]}
    cols = list(sample.keys())[:6]  # cap at 6 columns so it fits the terminal

    table = Table(
        title="Extracted Data (preview)",
        show_lines=True,
        border_style="dim",
        title_style="bold",
    )
    for col in cols:
        table.add_column(col, overflow="fold", max_width=50)

    for row in data[:max_rows]:
        if not isinstance(row, dict):
            row = {"value": row}
        table.add_row(*[str(row.get(c, ""))[:50] for c in cols])

    if len(data) > max_rows:
        table.add_row(*[f"... +{len(data) - max_rows} more" if i == 0 else "" for i in range(len(cols))])

    console.print(table)


def print_success(path: str, pages: int, elapsed: float) -> None:
    """Green box saying we're done."""
    msg = Text()
    msg.append("✓ ", style="bold green")
    msg.append(f"Exported {pages} page(s) → ")
    msg.append(path, style="bold underline")
    msg.append(f"  ({elapsed:.1f}s)")
    console.print(Panel(msg, border_style="green"))


def print_error(message: str) -> None:
    """Red error panel."""
    console.print(Panel(f"[bold red]Error:[/] {message}", border_style="red"))


def print_warn(message: str) -> None:
    """Yellow warning."""
    console.print(f"[yellow]⚠ {message}[/]")
