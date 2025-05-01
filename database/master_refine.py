#!/usr/bin/env python3
"""
database/master_refine.py - Refine and augment master JSON data for Coffee Break podcast

This script processes the master_scrapping_data.json file to add derived fields,
such as consolidated publication dates and total episode durations.
It provides a rich CLI interface with options for specific refinement tasks.

Usage:
    python master_refine.py [--add-dates] [--add-total-duration] [--clean-promo-links] [--verbose] [--dry-run]

Options:
    --add-dates         Extract earliest date from parts and add to episode level (DD/MM/YYYY)
    --add-total-duration Calculate total duration in seconds from all parts
    --clean-promo-links Remove promotional links from episodes (defined in promo-links-list.json)
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
MASTER_JSON_PATH = Path("database/master_scrapping_data.json")
BACKUP_JSON_PATH = MASTER_JSON_PATH.with_suffix(".bak")
PROMO_LINKS_PATH = Path("links_retrieval/promo-links-list.json")

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

def load_promo_links() -> List[str]:
    """
    Load promotional links from promo-links-list.json.
    
    Returns:
        List of promotional links (strings)
    """
    try:
        with PROMO_LINKS_PATH.open('r', encoding=ENCODING) as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load promo links: {e}")
        return []

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

def clean_promo_links(data: List[Dict[str, Any]], logger: logging.Logger) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Remove promotional links from episode ref_links.
    
    Args:
        data: List of episode data dictionaries
        logger: Logger instance
        
    Returns:
        Tuple of (updated data, dict with link cleaning statistics)
    """
    promo_links = load_promo_links()
    if not promo_links:
        logger.error("No promotional links loaded. Skipping link cleaning.")
        return data, {}
    
    logger.info(f"Loaded {len(promo_links)} promotional links to remove")
    
    # Statistics dictionary to track removals by episode
    stats = {}
    
    for episode in track(data, description="Cleaning promotional links..."):
        episode_num = episode.get("Episode number", "Unknown")
        ref_links = episode.get("ref_links", [])
        
        if not ref_links:
            continue
            
        # Find promotional links in this episode
        original_count = len(ref_links)
        cleaned_links = [link for link in ref_links if link not in promo_links]
        removed_count = original_count - len(cleaned_links)
        
        # Only update if links were removed
        if removed_count > 0:
            episode["ref_links"] = cleaned_links
            stats[episode_num] = removed_count
            logger.debug(f"Removed {removed_count} promo links from episode {episode_num}")
    
    total_removed = sum(stats.values())
    logger.info(f"Removed {total_removed} promotional links across {len(stats)} episodes")
    
    return data, stats

# --- Main function ---
def main(add_dates: bool = False, add_duration: bool = False, 
         clean_links: bool = False, dry_run: bool = False, verbose: bool = False) -> None:
    """
    Main processing function with command-line arguments.
    
    Args:
        add_dates: Whether to add publication dates
        add_duration: Whether to add total durations
        clean_links: Whether to clean promotional links
        dry_run: Whether to perform a dry run without writing changes
        verbose: Whether to enable verbose logging
    """
    logger = setup_logger(verbose)
    console = Console()
    
    logger.info("🔍 Coffee Break JSON Master Refiner")
    
    if not any([add_dates, add_duration, clean_links]):
        logger.warning("No refinement tasks specified. Nothing to do!")
        console.print("\n[yellow]Hint:[/yellow] Use --add-dates, --add-total-duration, or --clean-promo-links to specify tasks.")
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
    
    # Clean promotional links if requested
    if clean_links:
        data, link_stats = clean_promo_links(data, logger)
        updates_made = updates_made or bool(link_stats)
        stats["link_stats"] = link_stats
        stats["total_links_removed"] = sum(link_stats.values()) if link_stats else 0
        stats["episodes_cleaned"] = len(link_stats) if link_stats else 0
        logger.info(f"Cleaned links in {stats['episodes_cleaned']} episodes (removed {stats['total_links_removed']} links)")
    
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
    
    if clean_links and stats.get("link_stats"):
        table.add_row(
            "Episodes with cleaned links", 
            f"{stats['episodes_cleaned']} ({stats['episodes_cleaned'] / stats['episodes'] * 100:.1f}%)"
        )
        table.add_row("Total promotional links removed", str(stats['total_links_removed']))
        
        # Add detailed table for link removals if any occurred
        if stats['episodes_cleaned'] > 0:
            console.print(table)
            
            # Create a detailed table for link removals
            link_table = Table(title="Promotional Links Cleaned by Episode")
            link_table.add_column("Episode", style="cyan")
            link_table.add_column("Links Removed", justify="right", style="red")
            
            # Sort episodes by number for better display
            sorted_episodes = sorted(
                stats["link_stats"].items(), 
                key=lambda x: (int(x[0]) if x[0].isdigit() else float('inf'), x[0])
            )
            
            for episode_num, count in sorted_episodes:
                link_table.add_row(episode_num, str(count))
                
            console.print(link_table)
            return
    
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
  python master_refine.py --clean-promo-links
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
    parser.add_argument(
        "--clean-promo-links", 
        action="store_true", 
        help="Remove promotional links from episodes (defined in promo-links-list.json)"
    )
    # Add a new flag `--titles-table` to display a rich table with all episode titles
    parser.add_argument(
        "--titles-table",
        action="store_true",
        help="Display a rich table with all episode titles.",
    )
    # Add a new flag `--clean-titles` to clean episode titles of specific substrings
    parser.add_argument(
        "--clean-titles",
        action="store_true",
        help="Clean episode titles by removing specific substrings like 'Ep###_$: '.",
    )
    # Add a new flag `--clear-extractos` to remove specific Parts entries
    parser.add_argument(
        "--clear-extractos",
        action="store_true",
        help="Remove Parts entries of class 'Only' for episodes 473 to 483.",
    )
    
    args = parser.parse_args()
    
    # Initialize logger early for all CLI operations
    logger = setup_logger(args.verbose)
    
    if args.titles_table:
        if not RICH_AVAILABLE:
            print("The 'rich' library is required for this feature. Please install it using 'pip install rich'.")
            sys.exit(1)

        # Load the JSON data
        with MASTER_JSON_PATH.open("r", encoding=ENCODING) as file:
            data = json.load(file)

        # Display the titles table
        display_titles_table(data)
        sys.exit(0)
    
    # Add logic to handle the `--clean-titles` flag
    if args.clean_titles:
        # Create a backup of the original JSON file
        with MASTER_JSON_PATH.open("r", encoding=ENCODING) as original_file:
            with BACKUP_JSON_PATH.open("w", encoding=ENCODING) as backup_file:
                backup_file.write(original_file.read())

        print(f"Backup created at {BACKUP_JSON_PATH}")

        # Load the JSON data
        with MASTER_JSON_PATH.open("r", encoding=ENCODING) as file:
            data = json.load(file)

        # Update the regex pattern to handle cases with a space between "Ep" and the number
        pattern = re.compile(r"^Ep ?\d{2,3}(_[A-Za-z]+)?: ?")

        # Clean titles and track affected titles
        affected_titles = []
        for episode in data:
            title = episode.get("Title", "")
            if title and pattern.match(title):
                affected_titles.append(title)
                episode["Title"] = pattern.sub("", title)

        # Save the cleaned data back to the JSON file
        with MASTER_JSON_PATH.open("w", encoding=ENCODING) as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

        print("Titles cleaned successfully.")

        # Display the titles table with affected titles highlighted
        def display_titles_table_with_highlight(data: List[Dict[str, Any]], affected_titles: List[str]) -> None:
            """Display a rich table with all episode titles, highlighting affected titles."""
            console = Console()
            table = Table(title="Episode Titles")

            table.add_column("Episode Number", style="cyan", justify="center")
            table.add_column("Number of Parts", style="green", justify="center")
            table.add_column("Title", style="magenta")

            for episode in data:
                episode_number = episode.get("Episode number", "N/A")
                number_of_parts = str(len(episode.get("Parts", [])))
                title = episode.get("Title", "N/A")
                table.add_row(episode_number, number_of_parts, title)

            console.print(table)

        display_titles_table_with_highlight(data, affected_titles)
        sys.exit(0)

    # Enhance the `--clear-extractos` flag to include rich logging for actions taken
    if args.clear_extractos:
        if not RICH_AVAILABLE:
            print("The 'rich' library is required for this feature. Please install it using 'pip install rich'.")
            sys.exit(1)

        # Load the JSON data
        with MASTER_JSON_PATH.open("r", encoding=ENCODING) as file:
            data = json.load(file)

        # Define the range of episodes to process
        start_episode = 473
        end_episode = 483

        console = Console()
        table = Table(title="Clear Extractos Actions")
        table.add_column("Episode Number", style="cyan", justify="center")
        table.add_column("Original Parts Count", style="green", justify="center")
        table.add_column("Removed 'Only' Parts", style="red", justify="center")
        table.add_column("Remaining Parts Count", style="magenta", justify="center")

        # Process the specified range of episodes
        changes_made = False
        for episode in data:
            episode_number = int(episode.get("Episode number", 0))
            if start_episode <= episode_number <= end_episode:
                original_parts = episode.get("Parts", [])
                original_parts_count = len(original_parts)

                # Log details of parts before filtering
                for part in original_parts:
                    part_class = part.get("Part_class", "N/A")
                    logger.debug(f"Episode {episode_number}: Part class = {part_class}")

                filtered_parts = [
                    part for part in original_parts
                    if part.get("Part_class") != "Only"
                ]
                removed_parts_count = original_parts_count - len(filtered_parts)

                if removed_parts_count > 0:
                    changes_made = True
                    episode["Parts"] = filtered_parts
                    table.add_row(
                        str(episode_number),
                        str(original_parts_count),
                        str(removed_parts_count),
                        str(len(filtered_parts))
                    )

        if changes_made:
            # Save the cleaned data back to the JSON file
            with MASTER_JSON_PATH.open("w", encoding=ENCODING) as file:
                json.dump(data, file, ensure_ascii=False, indent=2)

            console.print(table)
            console.print("[green]Extractos cleared successfully.[/green]")
        else:
            console.print("[yellow]No changes were made. No 'Only' parts found in the specified range.[/yellow]")

        sys.exit(0)
    
    main(
        add_dates=args.add_dates,
        add_duration=args.add_total_duration,
        clean_links=args.clean_promo_links,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

# Update the `display_titles_table` function to include a column for the number of parts
def display_titles_table(data: List[Dict[str, Any]]) -> None:
    """Display a rich table with all episode titles and number of parts."""
    console = Console()
    table = Table(title="Episode Titles")

    table.add_column("Episode Number", style="cyan", justify="center")
    table.add_column("Number of Parts", style="green", justify="center")
    table.add_column("Title", style="magenta")

    for episode in data:
        episode_number = episode.get("Episode number", "N/A")
        number_of_parts = str(len(episode.get("Parts", [])))
        title = episode.get("Title", "N/A")
        table.add_row(episode_number, number_of_parts, title)

    console.print(table)

# --- Script entrypoint ---
if __name__ == "__main__":
    cli()