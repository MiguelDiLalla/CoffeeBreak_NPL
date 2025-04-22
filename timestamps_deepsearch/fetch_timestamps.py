import json
import re
from pathlib import Path

from rich.console import Console
from rich.columns import Columns
from rich.table import Table

CBINFO_JSON = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "parsed_json"
    / "cbinfo_index.json"
)

TIMESTAMP_RE = re.compile(r"\((\d{1,2}:\d{2}(?::\d{2})?)\)")


def extract_raw_timestamps(text: str) -> list[str]:
    """Find all timestamps in the form (mm:ss) or (hh:mm:ss) in the given text."""
    return TIMESTAMP_RE.findall(text)


def main():
    console = Console()
    data = json.loads(CBINFO_JSON.read_text(encoding="utf-8"))

    total_eps = 0
    with_topics = 0
    multi_flag = 0
    raw_ts_eps = 0
    missing_topics: list[str] = []
    bad_multi: list[str] = []

    # count parsed timestamps and topics without timestamps
    episodes_with_parsed_ts = 0
    topics_without_timestamps: list[str] = []

    for entry in data:
        if entry.get("entry_type") != "episode":
            continue
        total_eps += 1

        topics = entry.get("topics", [])
        has_multi = entry.get("has_multiple_timestamps", False)
        raw = entry.get("raw_description", "")
        found = extract_raw_timestamps(raw)

        # count parsed timestamps in topics
        parsed_ts_count = sum(1 for t in topics if t.get("timestamp"))
        if parsed_ts_count:
            episodes_with_parsed_ts += 1
        # detect topics entries lacking timestamps
        if topics and parsed_ts_count == 0:
            topics_without_timestamps.append(entry.get("episode_id") or entry.get("title", "—"))

        if topics:
            with_topics += 1
        if has_multi:
            multi_flag += 1

        if found:
            raw_ts_eps += 1
            if not topics:
                missing_topics.append(entry.get("episode_id") or entry.get("title", "—"))
            if has_multi and len(found) <= 1:
                bad_multi.append(entry.get("episode_id") or entry.get("title", "—"))

    # prepare rich console and table
    table = Table(title="Timestamp Extraction Report", show_edge=False, show_lines=True)
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Percent", justify="right")

    # add rows with percentages
    table.add_row("Total episodes", str(total_eps), "100%")
    table.add_row(
        "Episodes with parsed topics", str(with_topics), f"{with_topics/total_eps:.1%}" if total_eps else "N/A"
    )
    table.add_row(
        "Episodes flagged multiple timestamps", str(multi_flag), f"{multi_flag/total_eps:.1%}" if total_eps else "N/A"
    )
    table.add_row(
        "Episodes with raw timestamps", str(raw_ts_eps), f"{raw_ts_eps/total_eps:.1%}" if total_eps else "N/A"
    )
    table.add_row(
        "Episodes with parsed timestamps", str(episodes_with_parsed_ts),
        f"{episodes_with_parsed_ts/raw_ts_eps:.1%}" if raw_ts_eps else "N/A"
    )
    table.add_row(
        "Episodes missing parsed timestamps", str(raw_ts_eps - episodes_with_parsed_ts),
        f"{(raw_ts_eps - episodes_with_parsed_ts)/raw_ts_eps:.1%}" if raw_ts_eps else "N/A"
    )
    table.add_row(
        "Episodes with topics but no timestamps", str(len(topics_without_timestamps)),
        f"{len(topics_without_timestamps)/with_topics:.1%}" if with_topics else "N/A"
    )

    console.print(table)

    console.rule("[bold green]Episode Timestamp Summary[/bold green]")
    console.print(f"[bold]Total episodes:[/bold] {total_eps}")
    console.print(f"[bold]Episodes with parsed topics:[/bold] {with_topics}")
    console.print(f"[bold]Episodes flagged multiple:[/bold] {multi_flag}")
    console.print(f"[bold]Episodes with raw timestamps:[/bold] {raw_ts_eps}\n")

    # Display missing topics side by side
    console.print("[bold yellow]Episodes missing topics but have raw timestamps:[/bold yellow]")
    if missing_topics:
        console.print(
            Columns([f"[cyan]{eid}[/cyan]" for eid in missing_topics], expand=True)
        )
    else:
        console.print("  [green]None[/green]")

    console.print()  # blank line
    console.print("[bold yellow]Episodes flagged has_multiple but <2 raw timestamps:[/bold yellow]")
    for eid in bad_multi:
        console.print(f"  - [red]{eid}[/red]")


if __name__ == "__main__":
    main()