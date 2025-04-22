"""
clean_topics.py - Clean and fix topic titles and timestamps in cbinfo_index.json

Cleans trailing punctuation from topic titles, extracts embedded timestamps like '(min 1:00)',
and updates 'timestamp' fields. Reports episodes corrected and those still
having missing timestamps after cleaning.
"""
import json
import re
import argparse
import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

# Project config
try:
    from config import ENCODING, LOG_LEVEL
except ImportError:
    ENCODING = "utf-8"
    LOG_LEVEL = "INFO"

# Paths
JSON_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "parsed_json"
    / "cbinfo_index.json"
)

# Regex to find embedded 'min' timestamps in titles
EMBEDDED_TS_RE = re.compile(r"\(min\s*(?P<ts>\d{1,2}:\d{2}(?::\d{1,2})?)\)", re.IGNORECASE)
# Regex to strip trailing punctuation (keep ?, !, ))
TRAILING_PUNCT_RE = re.compile(r"[ \t]+$|[\.,;:]+$")


def setup_logger(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True)],
        force=True,
    )
    return logging.getLogger("clean_topics")


def clean_title(title: str) -> str:
    """Strip trailing whitespace and punctuation (. , ; :) from title."""
    # remove trailing spaces then punctuation
    t = re.sub(r"[ \t]+$", "", title)
    t = re.sub(r"[\.,;:]+$", "", t)
    return t


def main(verbose: bool, dry_run: bool) -> None:
    logger = setup_logger(verbose)
    console = Console()
    logger.info("🧹 Cleaning topic titles and timestamps...")

    if not JSON_PATH.exists():
        logger.error(f"JSON index not found: {JSON_PATH}")
        return

    data = json.loads(JSON_PATH.read_text(encoding=ENCODING))
    corrected = 0
    unparity_eps: list[str] = []

    for entry in data:
        if entry.get("entry_type") != "episode":
            continue
        ep_id = entry.get("episode_id") or entry.get("title")
        topics = entry.get("topics", [])
        entry_changed = False

        for topic in topics:
            title = topic.get("title", "")
            ts = topic.get("timestamp")
            # extract embedded timestamp
            m = EMBEDDED_TS_RE.search(title)
            if m:
                new_ts = m.group("ts")
                topic["timestamp"] = new_ts
                title = title[: m.start()] + title[m.end():]
                entry_changed = True
                logger.info(f"[EXTRACT] {ep_id}: found embedded ts {new_ts}")
            # clean trailing punctuation
            cleaned = clean_title(title)
            if cleaned != title:
                topic["title"] = cleaned
                entry_changed = True
                logger.info(f"[CLEAN] {ep_id}: '{title}' → '{cleaned}'")
        # record episodes with missing timestamps
        if any(not t.get("timestamp") for t in topics):
            unparity_eps.append(ep_id)
        if entry_changed:
            corrected += 1

    # write back if any corrections
    if corrected > 0:
        if dry_run:
            logger.info(f"[DRY RUN] Would correct {corrected} episodes")
        else:
            JSON_PATH.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding=ENCODING,
            )
            logger.info(f"Updated {corrected} episodes in JSON index.")
    else:
        logger.info("No corrections needed.")

    # Summary
    table = Table(title="Clean Topics Summary", show_edge=False)
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("Episodes corrected", str(corrected))
    table.add_row("Episodes with missing ts", str(len(unparity_eps)))
    console.print(table)

    if unparity_eps:
        console.print("[bold red]Episodes still missing timestamps:[/bold red]")
        for eid in unparity_eps:
            console.print(f" - [red]{eid}[/red]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clean topic titles and extract embedded timestamps in cbinfo_index.json",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose logging"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without writing"
    )
    args = parser.parse_args()
    main(verbose=args.verbose, dry_run=args.dry_run)
