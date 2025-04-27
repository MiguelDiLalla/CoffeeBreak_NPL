"""
retrieve_timestamps_master_version.py - Retrieve missing topic timestamps from raw descriptions in master data

Scans master_scrapping_data.json for episode parts that have empty Topics lists but contain
timestamps in their raw_description. Extracts titles and timestamps from raw_description lines,
fills in the Topics list for each part, and reports actions via rich logging and table.

This is similar to retrieve_timestamps.py but works on the master_scrapping_data.json file
instead of cbinfo_index.json, and focuses on episode Parts with empty Topics.
"""
import json
import re
import argparse
import logging
from pathlib import Path
import shutil
from datetime import datetime

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
    / "database"
    / "master_scrapping_data.json"
)

# Regex to find timestamps in raw description, allows optional 'min'
TIMESTAMP_RE = re.compile(r"\((?P<ts>\d{1,2}:\d{2}(?::\d{1,2})?)(?:\s*min)?\)")

def setup_logger(verbose: bool) -> logging.Logger:
    """
    Configure rich logger with appropriate verbosity level.
    
    Args:
        verbose: If True, sets logging level to DEBUG, otherwise uses LOG_LEVEL
        
    Returns:
        Configured logger instance
    """
    level = logging.DEBUG if verbose else getattr(logging, LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True)],
        force=True,
    )
    return logging.getLogger("retrieve_timestamps_master")


def extract_topics_from_raw(raw: str) -> list[dict]:
    """
    Extract topic entries by chunking around timestamps for robust title extraction.
    
    Args:
        raw: Raw description text containing timestamp markers
        
    Returns:
        List of topic dictionaries with title and timestamp
    """
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


def create_backup(json_path: Path) -> Path:
    """
    Create a timestamped backup of the JSON file.
    
    Args:
        json_path: Path to the JSON file to back up
        
    Returns:
        Path to the created backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = json_path.with_suffix(f".{timestamp}.bak")
    shutil.copy2(json_path, backup_path)
    return backup_path


def main(verbose: bool, dry_run: bool) -> None:
    """
    Main function that orchestrates the timestamp extraction process.
    
    Args:
        verbose: If True, enables verbose logging
        dry_run: If True, shows what would change without writing to files
    """
    logger = setup_logger(verbose)
    console = Console()
    logger.info("🔍 Scanning master_scrapping_data.json for episode parts with missing topic timestamps...")

    if not JSON_PATH.exists():
        logger.error(f"JSON file not found: {JSON_PATH}")
        return

    # Load the JSON data
    entries = json.loads(JSON_PATH.read_text(encoding=ENCODING))
    
    # Statistics tracking
    total_entries = len(entries)
    entries_with_parts = 0
    parts_total = 0
    parts_with_empty_topics = 0
    parts_with_timestamps = 0
    parts_updated = 0
    extraction_failures: list[str] = []

    # Process entries
    for i, entry in enumerate(entries):
        # Check if entry has Parts key
        if not isinstance(entry.get("Parts"), list):
            continue
        
        if entry.get("Parts"):  # Has non-empty Parts list
            entries_with_parts += 1
            
        for part in entry.get("Parts", []):
            parts_total += 1
            
            # Skip parts without raw_description
            if not part.get("raw_description"):
                continue
                
            # Check if Topics is empty
            if not part.get("Topics", []):
                parts_with_empty_topics += 1
                
                # Check for timestamps in raw_description
                raw = part.get("raw_description", "")
                raw_times = TIMESTAMP_RE.findall(raw)
                
                if raw_times:
                    parts_with_timestamps += 1
                    
                    # Try to extract topics
                    new_topics = extract_topics_from_raw(raw)
                    
                    if not new_topics:
                        episode_id = part.get("Episode_ID", f"Unknown-{i}")
                        extraction_failures.append(episode_id)
                        logger.warning(
                            f"[FAIL] {episode_id} -> no topics extracted"
                        )
                        continue
                    
                    # Update part
                    part_id = part.get("Episode_ID", f"Unknown-{i}")
                    part["Topics"] = new_topics
                    parts_updated += 1
                    
                    logger.info(
                        f"[UPDATE] {part_id} -> extracted {len(new_topics)} topics"
                    )
    
    # Report results
    if parts_updated == 0:
        logger.info("No episode parts required timestamp retrieval.")
    else:
        if dry_run:
            logger.info(f"[DRY RUN] Would update {parts_updated} episode parts.")
        else:
            # Create backup before saving changes
            backup_path = create_backup(JSON_PATH)
            logger.info(f"Created backup at {backup_path}")
            
            # Write updated data back to file
            JSON_PATH.write_text(
                json.dumps(entries, indent=2, ensure_ascii=False),
                encoding=ENCODING,
            )
            logger.info(f"Updated {parts_updated} episode parts in {JSON_PATH}")
    
    # Summary table
    table = Table(title="Master Timestamp Retrieval Summary", show_edge=False)
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    
    table.add_row("Total entries in master data", str(total_entries))
    table.add_row("Entries containing Parts", str(entries_with_parts))
    table.add_row("Total Parts found", str(parts_total))
    table.add_row("Parts with empty Topics", str(parts_with_empty_topics))
    table.add_row("Parts with timestamps in raw_description", str(parts_with_timestamps))
    table.add_row("Parts updated with extracted topics", str(parts_updated))
    table.add_row("Extraction failures", str(len(extraction_failures)))
    
    console.print(table)
    
    if extraction_failures:
        console.print("[bold red]Failed to extract topics for episode parts:[/bold red]")
        for part_id in extraction_failures:
            console.print(f" - [red]{part_id}[/red]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Retrieve missing topic timestamps from master_scrapping_data.json",
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