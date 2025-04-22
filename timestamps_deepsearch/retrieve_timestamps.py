"""
retrieve_timestamps.py - Retrieve missing topic timestamps from raw descriptions

Scans cbinfo_index.json for episodes that have raw timestamps but no stored topics,
extracts titles and timestamps from raw_description lines, fills in the topics list,
and updates has_multiple_timestamps. Reports actions via rich logging and table.
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

# Regex to find timestamps in raw description, allows optional 'min'
TIMESTAMP_RE = re.compile(r"\((?P<ts>\d{1,2}:\d{2}(?::\d{1,2})?)(?:\s*min)?\)")

def setup_logger(verbose: bool) -> logging.Logger:
    """Configure rich logger."""
    level = logging.DEBUG if verbose else getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True)],
        force=True,
    )
    return logging.getLogger("retrieve_timestamps")


def extract_topics_from_raw(raw: str) -> list[dict]:
    """Extract topic entries by chunking around timestamps for robust title extraction."""
    topics: list[dict] = []
    prev_end = 0
    for m in TIMESTAMP_RE.finditer(raw):
        start, end = m.span()
        ts = m.group('ts')
        # segment between last timestamp end and this timestamp start
        chunk = raw[prev_end:start]
        # get last line or statement in chunk
        if '\n' in chunk:
            line = chunk.splitlines()[-1]
        else:
            line = chunk
        # clean up bullets, whitespace, punctuation
        title = re.sub(r"^[-–—\s]+", "", line).strip()
        title = title.rstrip('.:; ')  # remove trailing delimiters
        if title:
            topics.append({"title": title, "timestamp": ts})
        prev_end = end
    return topics


def main(verbose: bool, dry_run: bool) -> None:
    logger = setup_logger(verbose)
    console = Console()
    logger.info("🐢 Retrieving missing timestamps from raw descriptions...")

    if not JSON_PATH.exists():
        logger.error(f"JSON index not found: {JSON_PATH}")
        return

    entries = json.loads(JSON_PATH.read_text(encoding=ENCODING))
    total_eps = 0
    raw_ts_only = 0
    updated = 0
    extraction_failures: list[str] = []

    for entry in entries:
        if entry.get("entry_type") != "episode":
            continue
        total_eps += 1
        topics = entry.get("topics", [])
        raw = entry.get("raw_description", "")
        # count episodes with raw timestamps but no stored topics
        raw_times = TIMESTAMP_RE.findall(raw)
        if topics:
            continue
        if raw_times:
            raw_ts_only += 1
        else:
            continue
        # attempt extraction
        new_topics = extract_topics_from_raw(raw)
        if not new_topics:
            extraction_failures.append(entry.get("episode_id") or entry.get("title"))
            logger.warning(
                f"[FAIL] {entry.get('episode_id') or entry.get('title')} -> no topics extracted"
            )
            continue
        # Update entry
        entry["topics"] = new_topics
        entry["has_multiple_timestamps"] = len(new_topics) > 1
        updated += 1
        logger.info(
            f"[UPDATE] {entry.get('episode_id') or entry.get('title')} -> extracted {len(new_topics)} topics"
        )

    if updated == 0:
        logger.info("No episodes required timestamp retrieval.")
    else:
        if dry_run:
            logger.info(f"[DRY RUN] Would update {updated} episodes out of {total_eps}.")
        else:
            JSON_PATH.write_text(
                json.dumps(entries, indent=2, ensure_ascii=False),
                encoding=ENCODING,
            )
            logger.info(f"Updated {updated} episodes in JSON index.")

    # Summary
    table = Table(title="Timestamp Retrieval Summary", show_edge=False)
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("Episodes processed", str(total_eps))
    table.add_row(
        "Episodes with raw timestamps & no topics",
        str(raw_ts_only)
    )
    table.add_row("Episodes updated", str(updated))
    table.add_row(
        "Extraction failures", str(len(extraction_failures))
    )
    console.print(table)
    if extraction_failures:
        console.print("[bold red]Failed to extract for episodes:[/bold red]")
        for eid in extraction_failures:
            console.print(f" - [red]{eid}[/red]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Retrieve missing topic timestamps into cbinfo_index.json",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show actions without writing changes"
    )
    args = parser.parse_args()
    main(verbose=args.verbose, dry_run=args.dry_run)
