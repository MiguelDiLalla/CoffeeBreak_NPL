#!/usr/bin/env python3
"""
database/master_refine.py - Refine and augment master JSON data for Coffee Break podcast

This script processes the master_scrapping_data.json file to add derived fields,
such as consolidated publication dates and total episode durations.
It provides a rich CLI interface with options for specific refinement tasks.

Usage:
    python master_refine.py [--add-dates] [--add-total-duration] [--verbose] [--dry-run]

Options:
    --add-dates         Extract earliest date from parts and add to episode level (DD/MM/YYYY)
    --add-total-duration Calculate total duration in seconds from all parts
    --dry-run           Show what would change but don't write to file
    --verbose           Enable detailed logging output
    --help              Show this help message and exit

Author: Miguel Di Lalla (2025)
"""

import os
import sys
import json
import argparse
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.table import Table
    from rich.progress import track
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Add project root to path for importing config
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config import ENCODING, LOG_LEVEL
except ImportError:
    ENCODING = "utf-8"
    LOG_LEVEL = "INFO"

# --- Paths ---
MASTER_JSON_PATH = Path(__file__).parent / "master_scrapping_data.json"
BACKUP_JSON_PATH = Path(__file__).parent / "master_scrapping_data.json.bak"

# --- Logging setup ---
def setup_logger(verbose: bool = False) -> logging.Logger:
    """Configure rich logger with appropriate verbosity level."""
    level = logging.DEBUG if verbose else getattr(logging, LOG_LEVEL, logging.INFO)
    
    if RICH_AVAILABLE:
        logging.basicConfig(
            level=level,
            format="%(message)s",
            handlers=[RichHandler(rich_tracebacks=True)],
            force=True,
        )
    else:
        logging.basicConfig(
            level=level,
            format="[%(levelname)s] %(message)s",
            force=True,
        )
        
    return logging.getLogger("master_refine")

# --- Utility functions ---
def parse_duration(duration_str: str) -> int:
    """
    Parse a duration string in format "HH:MM:SS" or "MM:SS" to seconds.
    
    Args:
        duration_str: String in format "HH:MM:SS" or "MM:SS"
        
    Returns:
        Total duration in seconds (int)
    """
    if not duration_str:
        return 0
        
    parts = duration_str.strip().split(":")
    
    if len(parts) == 3:  # HH:MM:SS
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    elif len(parts) == 2:  # MM:SS
        minutes, seconds = parts
        return int(minutes) * 60 + int(seconds)
    else:
        return 0  # Invalid format

def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse a date string in common formats to a datetime object.
    
    Args:
        date_str: String in various date formats
        
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None
        
    # Common date formats used in the dataset
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",  # Thu, 03 Apr 2025 20:41:51 +0200
        "%a, %d %b %Y %H:%M:%S",     # Thu, 03 Apr 2025 20:41:51
        "%Y-%m-%d %H:%M:%S",         # 2025-04-03 20:41:51
        "%Y-%m-%d",                  # 2025-04-03
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None

def get_date_string(dt: datetime) -> str:
    """
    Format datetime as DD/MM/YYYY string.
    
    Args:
        dt: datetime object
        
    Returns:
        String in format DD/MM/YYYY
    """
    if dt:
        return dt.strftime("%d/%m/%Y")
    return ""

def backup_json(json_path: Path, backup_path: Path) -> bool:
    """
    Create backup of original JSON file.
    
    Args:
        json_path: Path to original JSON
        backup_path: Path for backup file
        
    Returns:
        True if backup was successful
    """
    try:
        with json_path.open('rb') as src, backup_path.open('wb') as dst:
            dst.write(src.read())
        return True
    except Exception as e:
        logging.error(f"Failed to create backup: {e}")
        return False

# --- Processing functions ---
def add_episode_dates(data: List[Dict[str, Any]], logger: logging.Logger) -> Tuple[List[Dict[str, Any]], int]:
    """
    Add publication_date field to episode entries based on the earliest date in parts.
    The date is formatted as DD/MM/YYYY.
    
    Args:
        data: List of episode data dictionaries
        logger: Logger instance
        
    Returns:
        Tuple of (updated data, count of updates)
    """
    updated_count = 0
    
    for episode in track(data, description="Processing episode dates..."):
        parts = episode.get("Parts", [])
        dates = []
        
        # Extract valid dates from all parts
        for part in parts:
            date_str = part.get("Date")
            if date_str:
                date_obj = parse_date(date_str)
                if date_obj:
                    dates.append(date_obj)
        
        # If we found any dates, use the earliest one
        if dates:
            earliest_date = min(dates)
            date_str = get_date_string(earliest_date)
            
            # Only update if needed
            if episode.get("publication_date") != date_str:
                episode["publication_date"] = date_str
                updated_count += 1
                logger.debug(f"Added date {date_str} to episode {episode.get('Episode number', 'Unknown')}")
    
    return data, updated_count

def add_total_durations(data: List[Dict[str, Any]], logger: logging.Logger) -> Tuple[List[Dict[str, Any]], int]:
    """
    Add total_duration_seconds field to episode entries based on part durations.
    The duration is stored as an integer representing seconds.
    
    Args:
        data: List of episode data dictionaries
        logger: Logger instance
        
    Returns:
        Tuple of (updated data, count of updates)
    """
    updated_count = 0
    
    for episode in track(data, description="Calculating episode durations..."):
        parts = episode.get("Parts", [])
        total_seconds = 0
        
        # Sum durations from all parts
        for part in parts:
            duration_str = part.get("Duration")
            if duration_str:
                duration_seconds = parse_duration(duration_str)
                total_seconds += duration_seconds
        
        # Only update if there are parts with durations and total > 0
        if total_seconds > 0:
            # Only update if different from existing value
            if episode.get("total_duration_seconds") != total_seconds:
                episode["total_duration_seconds"] = total_seconds
                updated_count += 1
                logger.debug(f"Added total duration {total_seconds}s to episode {episode.get('Episode number', 'Unknown')}")
    
    return data, updated_count

# --- Main function ---
def main(add_dates: bool = False, add_duration: bool = False, 
         dry_run: bool = False, verbose: bool = False) -> None:
    """
    Main processing function with command-line arguments.
    
    Args:
        add_dates: Whether to add publication dates
        add_duration: Whether to add total durations
        dry_run: Whether to perform a dry run without writing changes
        verbose: Whether to enable verbose logging
    """
    logger = setup_logger(verbose)
    console = Console()
    
    logger.info("🔍 Coffee Break JSON Master Refiner")
    
    if not any([add_dates, add_duration]):
        logger.warning("No refinement tasks specified. Nothing to do!")
        console.print("\n[yellow]Hint:[/yellow] Use --add-dates or --add-total-duration to specify tasks.")
        return
    
    if not MASTER_JSON_PATH.exists():
        logger.error(f"Master JSON not found at: {MASTER_JSON_PATH}")
        return
    
    # Load master data
    try:
        data = json.loads(MASTER_JSON_PATH.read_text(encoding=ENCODING))
        logger.info(f"Loaded {len(data)} episode entries from {MASTER_JSON_PATH}")
    except Exception as e:
        logger.error(f"Failed to load JSON: {e}")
        return
    
    # Create backup unless dry run
    if not dry_run:
        if backup_json(MASTER_JSON_PATH, BACKUP_JSON_PATH):
            logger.info(f"Created backup at {BACKUP_JSON_PATH}")
        else:
            if not console.input("[bold red]Failed to create backup. Continue? (y/N): [/bold red]").lower() == 'y':
                logger.info("Aborted.")
                return
    
    updates_made = False
    stats = {"episodes": len(data), "updates": 0}
    
    # Process dates if requested
    if add_dates:
        data, date_updates = add_episode_dates(data, logger)
        updates_made = updates_made or date_updates > 0
        stats["date_updates"] = date_updates
        logger.info(f"Added dates to {date_updates} episodes")
    
    # Process durations if requested
    if add_duration:
        data, duration_updates = add_total_durations(data, logger)
        updates_made = updates_made or duration_updates > 0
        stats["duration_updates"] = duration_updates
        logger.info(f"Added durations to {duration_updates} episodes")
    
    # Save updates unless dry run
    if updates_made:
        if dry_run:
            logger.info("[DRY RUN] Would write updated JSON to file")
        else:
            try:
                MASTER_JSON_PATH.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding=ENCODING
                )
                logger.info(f"Successfully wrote updated JSON to {MASTER_JSON_PATH}")
            except Exception as e:
                logger.error(f"Failed to write JSON: {e}")
    else:
        logger.info("No updates were needed.")
    
    # Print final statistics
    table = Table(title="Master JSON Refinement Results")
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    
    table.add_row("Total episodes", str(stats["episodes"]))
    
    if add_dates:
        table.add_row(
            "Episodes with added/updated dates", 
            f"{stats['date_updates']} ({stats['date_updates'] / stats['episodes'] * 100:.1f}%)"
        )
    
    if add_duration:
        table.add_row(
            "Episodes with added/updated durations", 
            f"{stats['duration_updates']} ({stats['duration_updates'] / stats['episodes'] * 100:.1f}%)"
        )
    
    console.print(table)

# --- CLI entrypoint ---
def cli():
    """Command-line interface entrypoint."""
    parser = argparse.ArgumentParser(
        description="Refine and augment master JSON data for Coffee Break podcast",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python master_refine.py --add-dates
  python master_refine.py --add-total-duration
  python master_refine.py --add-dates --add-total-duration --dry-run
  python master_refine.py --add-dates --add-total-duration --verbose
        """
    )
    
    parser.add_argument(
        "--add-dates", 
        action="store_true", 
        help="Extract earliest date from parts and add to episode level"
    )
    parser.add_argument(
        "--add-total-duration", 
        action="store_true", 
        help="Calculate total duration in seconds from all parts"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would change but don't write to file"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable detailed logging output"
    )
    
    args = parser.parse_args()
    
    main(
        add_dates=args.add_dates,
        add_duration=args.add_total_duration,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

# --- Script entrypoint ---
if __name__ == "__main__":
    cli()