"""hitl_console — Rich terminal UI for triaging Galaxy Brain opportunities."""

from __future__ import annotations

import webbrowser

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from sniper.n0_target_ingest import load_config
from sniper.n1_graphql_fetch import fetch_unanswered_discussions
from sniper.n2_relevance_score import rank_discussions
from sniper.n3_triage_queue import upsert_discussions, get_actionable, mark_status


console = Console()


def run_pipeline() -> None:
    """Execute the full fetch-score-triage pipeline."""
    config = load_config()
    all_discussions = []

    console.print("[bold]Fetching discussions...[/bold]")
    for repo in config.target_repos:
        console.print(f"  {repo.full_name}...", end=" ")
        discussions = fetch_unanswered_discussions(repo)
        console.print(f"{len(discussions)} unanswered")
        all_discussions.extend(discussions)

    console.print(f"\n[bold]Scoring {len(all_discussions)} discussions...[/bold]")
    ranked = rank_discussions(all_discussions, config.expertise_matrix)
    new_count = upsert_discussions(ranked)
    console.print(f"  {len(ranked)} above threshold, {new_count} new\n")


def show_queue() -> None:
    """Display the current triage queue."""
    items = get_actionable(limit=15)
    if not items:
        console.print("[dim]Queue is empty. Run [bold]fetch[/bold] first.[/dim]")
        return

    table = Table(title="Galaxy Brain Opportunities", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Score", style="bold cyan", width=6)
    table.add_column("Repo", width=25)
    table.add_column("Title", width=60)
    table.add_column("Domains", width=30)

    for i, item in enumerate(items, 1):
        table.add_row(
            str(i),
            str(item["score"]),
            item["repo"],
            item["title"][:58],
            ", ".join(item["matched_domains"]),
        )

    console.print(table)
    return items


def interactive_loop() -> None:
    """Main interactive loop."""
    console.print(Panel("[bold]gh-galaxy-quest[/bold] — Galaxy Brain opportunity finder"))
    console.print("Commands: [bold]fetch[/bold] | [bold]list[/bold] | [bold]open N[/bold] | [bold]ignore N[/bold] | [bold]answered N[/bold] | [bold]quit[/bold]\n")

    items: list[dict] | None = None

    while True:
        cmd = Prompt.ask("[bold]>[/bold]").strip().lower()

        if cmd == "quit" or cmd == "q":
            break
        elif cmd == "fetch":
            run_pipeline()
        elif cmd == "list":
            items = show_queue()
        elif cmd.startswith("open "):
            if items is None:
                items = get_actionable(limit=15)
            try:
                idx = int(cmd.split()[1]) - 1
                url = items[idx]["url"]
                console.print(f"Opening: {url}")
                webbrowser.open(url)
                mark_status(items[idx]["id"], "opened")
            except (IndexError, ValueError):
                console.print("[red]Invalid number[/red]")
        elif cmd.startswith("ignore "):
            if items is None:
                items = get_actionable(limit=15)
            try:
                idx = int(cmd.split()[1]) - 1
                mark_status(items[idx]["id"], "ignored")
                console.print(f"[dim]Ignored: {items[idx]['title'][:50]}[/dim]")
            except (IndexError, ValueError):
                console.print("[red]Invalid number[/red]")
        elif cmd.startswith("answered "):
            if items is None:
                items = get_actionable(limit=15)
            try:
                idx = int(cmd.split()[1]) - 1
                mark_status(items[idx]["id"], "answered")
                console.print(f"[green]Marked answered: {items[idx]['title'][:50]}[/green]")
            except (IndexError, ValueError):
                console.print("[red]Invalid number[/red]")
        else:
            console.print("[dim]Unknown command. Try: fetch, list, open N, ignore N, answered N, quit[/dim]")


if __name__ == "__main__":
    interactive_loop()
