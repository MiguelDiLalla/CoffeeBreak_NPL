#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script: consolidate_episode_data.py

Goal:
- Merge and consolidate information from three parsed JSON sources:
  - 'audiofeed_index.json' (audio metadata, parts structure)
  - 'cbinfo_index.json' (episode topics and contertulios)
  - 'web_parse.json' (external references and webpage link)
- Output a unified JSON file:
  - 'master_scrapping_data.json' under 'database/'

Episode Structure:
- Group by 3-digit episode number (e.g., '005', '172', '437').
- Handle multiple parts ('A', 'B', 'Supl', 'Only') correctly.
- Always preserve fallback: empty strings/lists if missing info.
- Ask user to resolve conflicting titles/images with rich CLI prompts.
- Report completion rate at the end.

Outputs:
- Unified JSON (`master_scrapping_data.json`).
- Rich CLI progress display and logging using `rich`.

Optional Flags:
- '--report-only' to scan existing `master_scrapping_data.json` and report data completeness without modifying anything.

"""
import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set

# Rich for pretty output
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.progress import track
from rich.panel import Panel
from rich.logging import RichHandler

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

try:
    import config
except ImportError:
    print("[ERROR] Could not import config module. Make sure you're running from the project root.")
    sys.exit(1)

# Initialize console and logger
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, console=console)]
)
logger = logging.getLogger("consolidate_episodes")

# File paths
DATA_DIR = Path(config.DATA_DIR)
AUDIOFEED_JSON = DATA_DIR / "parsed_json" / "audiofeed_index.json"
CBINFO_JSON = DATA_DIR / "parsed_json" / "cbinfo_index.json"
WEB_PARSE_JSON = DATA_DIR / "parsed_json" / "web_parse.json"
OUTPUT_PATH = Path(__file__).parent / "master_scrapping_data.json"

# Episode part types
PART_TYPES = ["A", "B", "Supl", "Only"]


def load_json_file(path: str) -> dict:
    """Load a JSON file and return as Python dictionary."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {path}: {str(e)}")
        sys.exit(1)


def group_audiofeed_by_episode(audiofeed_data: list) -> dict:
    """Group audiofeed entries into single episodes, based on their parts."""
    episodes = {}
    
    for entry in track(audiofeed_data, description="Grouping audio feed entries"):
        # Skip entries without episode_id
        if 'episode_id' not in entry:
            logger.warning(f"Entry missing episode_id: {entry}")
            continue
            
        ep_id = str(entry['episode_id'])  # Ensure ep_id is a string
        
        # Extract episode number and part
        match = re.search(r'Ep(\d+)(?:_([A-Za-z]+))?', ep_id)
        if not match:
            logger.warning(f"Could not parse episode ID: {ep_id}")
            continue
            
        ep_number = match.group(1).zfill(3)  # Pad to 3 digits
        ep_part = match.group(2) if match.group(2) else "Only"
        
        # Initialize episode group if not exists
        if ep_number not in episodes:
            episodes[ep_number] = {
                "Episode number": ep_number,
                "Episode class": "Single" if ep_part == "Only" else "Dual",
                "Title": "",
                "Image_url": "",
                "web_link": "",
                "ref_links": [],
                "Parts": []
            }
        elif episodes[ep_number]["Episode class"] == "Single" and ep_part != "Only":
            # Update to Dual if we have multiple parts
            episodes[ep_number]["Episode class"] = "Dual"
        
        # Add this part to the episode - use correct key names 'date' and 'link'
        entry_clean = {
            "Episode_ID": ep_id,
            "Part_class": ep_part,
            "Date": entry.get('date', ''),
            "Duration": entry.get('duration', ''),
            "raw_description": entry.get('description', ''),
            "Audio_URL": entry.get('audio_url', ''),
            "Ivoox_link": entry.get('link', ''),
            "Topics": [],
            "Contertulios": []
        }
        
        # Update title/image if not previously set
        if not episodes[ep_number]["Title"] and 'title' in entry and entry['title']:
            episodes[ep_number]["Title"] = entry['title']
            
        if not episodes[ep_number]["Image_url"] and 'image_url' in entry and entry['image_url']:
            episodes[ep_number]["Image_url"] = entry['image_url']
            
        episodes[ep_number]["Parts"].append(entry_clean)
    
    return episodes


def resolve_conflicts(title_options: list, image_options: list) -> tuple:
    """Ask user to pick title/image if conflicts arise (defaults to first option if Enter)."""
    selected_title = title_options[0]
    selected_image = image_options[0]
    
    if len(title_options) > 1:
        console.print("\n[bold yellow]Title conflict detected:[/bold yellow]")
        for i, title in enumerate(title_options):
            console.print(f"[{i+1}] {title}")
        choice = Prompt.ask("Select title number", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(title_options):
                selected_title = title_options[idx]
        except ValueError:
            pass  # Default to first option
    
    if len(image_options) > 1:
        console.print("\n[bold yellow]Image URL conflict detected:[/bold yellow]")
        for i, image in enumerate(image_options):
            console.print(f"[{i+1}] {image}")
        choice = Prompt.ask("Select image number", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(image_options):
                selected_image = image_options[idx]
        except ValueError:
            pass  # Default to first option
    
    return selected_title, selected_image


def enrich_episode_with_webdata(episode_id: str, web_data: list) -> tuple:
    """Retrieve web_link and ref_links from web_parse.json based on episode number."""
    web_link = ""
    ref_links = []
    
    # Strip leading zeros to match possible variations in episode numbering
    clean_ep_id = f"Ep{episode_id.lstrip('0')}"
    
    for entry in web_data:
        if entry.get('ep_id', '').lower() == clean_ep_id.lower():
            web_link = entry.get('ep_web_link', '')
            ref_links = entry.get('ep_links', [])
            break
    
    return web_link, ref_links


def enrich_episode_with_cbinfo(episode_part_id: str, cbinfo_data: list) -> tuple:
    """Retrieve topics and contertulios for each part from cbinfo_index.json."""
    topics = []
    contertulios = []
    
    for entry in cbinfo_data:
        if entry.get('episode_id', '') == episode_part_id:
            topics = entry.get('topics', [])
            contertulios = entry.get('contertulios', [])
            break
    
    return topics, contertulios


def build_episode_structure(grouped_parts: dict, web_data: list, cbinfo_data: list) -> list:
    """Assemble final episode dict following target schema."""
    master_data = []
    
    for ep_num, episode in track(grouped_parts.items(), description="Building episode structure"):
        # Gather all titles and images from parts to resolve conflicts
        title_options = []
        image_options = []
        
        for part in episode["Parts"]:
            # Find web data
            web_link, ref_links = enrich_episode_with_webdata(ep_num, web_data)
            episode["web_link"] = web_link
            episode["ref_links"] = ref_links
            
            # Find cbinfo data for each part
            topics, contertulios = enrich_episode_with_cbinfo(part["Episode_ID"], cbinfo_data)
            part["Topics"] = topics
            part["Contertulios"] = contertulios
            
            # Add title and image for conflict resolution
            if "Title" in part and part["Title"] and part["Title"] not in title_options:
                title_options.append(part["Title"])
            if "Image_url" in part and part["Image_url"] and part["Image_url"] not in image_options:
                image_options.append(part["Image_url"])
        
        # Resolve any conflicts
        if len(title_options) > 1 or len(image_options) > 1:
            selected_title, selected_image = resolve_conflicts(title_options, image_options)
            episode["Title"] = selected_title
            episode["Image_url"] = selected_image
        
        # Sort parts in consistent order: A, B, Supl, Only
        episode["Parts"].sort(key=lambda x: PART_TYPES.index(x["Part_class"]) if x["Part_class"] in PART_TYPES else 999)
        
        # Ensure we're keeping all parts data intact
        cleaned_parts = []
        for part in episode["Parts"]:
            cleaned_part = {
                "Episode_ID": part.get("Episode_ID", ""),
                "Part_class": part.get("Part_class", ""),
                "Date": part.get("Date", ""),
                "Duration": part.get("Duration", ""),
                "raw_description": part.get("raw_description", ""),  # Preserve raw_description from audiofeed
                "Audio_URL": part.get("Audio_URL", ""),
                "Ivoox_link": part.get("Ivoox_link", ""),
                "Topics": part.get("Topics", []),
                "Contertulios": part.get("Contertulios", [])
            }
            cleaned_parts.append(cleaned_part)
            
        episode["Parts"] = cleaned_parts
        master_data.append(episode)
    
    # Sort episodes by number
    master_data.sort(key=lambda e: int(e["Episode number"]))
    return master_data


def save_master_data(master_data: list, output_path: str):
    """Save the unified master data to JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(master_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully saved master data to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save master data: {str(e)}")


def report_completion_rate(master_data: list):
    """Analyze and print missing fields per episode."""
    total_episodes = len(master_data)
    episodes_with_web_link = sum(1 for ep in master_data if ep["web_link"])
    episodes_with_ref_links = sum(1 for ep in master_data if ep["ref_links"])
    
    parts_with_topics = 0
    parts_with_contertulios = 0
    parts_with_date = 0
    parts_with_ivoox = 0
    total_parts = 0
    
    for episode in master_data:
        for part in episode["Parts"]:
            total_parts += 1
            if part.get("Topics", []):
                parts_with_topics += 1
            if part.get("Contertulios", []):
                parts_with_contertulios += 1
            if part.get("Date", ""):
                parts_with_date += 1
            if part.get("Ivoox_link", ""):
                parts_with_ivoox += 1
    
    # Create a table for reporting
    table = Table(title="Data Completion Report")
    
    table.add_column("Category", style="cyan")
    table.add_column("Complete", style="green")
    table.add_column("Missing", style="red")
    table.add_column("Completion %", style="yellow")
    
    # Add rows for each data type
    table.add_row(
        "Episodes with web_link",
        str(episodes_with_web_link),
        str(total_episodes - episodes_with_web_link),
        f"{(episodes_with_web_link / total_episodes) * 100:.1f}%"
    )
    table.add_row(
        "Episodes with ref_links",
        str(episodes_with_ref_links),
        str(total_episodes - episodes_with_ref_links),
        f"{(episodes_with_ref_links / total_episodes) * 100:.1f}%"
    )
    table.add_row(
        "Parts with Topics",
        str(parts_with_topics),
        str(total_parts - parts_with_topics),
        f"{(parts_with_topics / total_parts) * 100:.1f}%"
    )
    table.add_row(
        "Parts with Contertulios",
        str(parts_with_contertulios),
        str(total_parts - parts_with_contertulios),
        f"{(parts_with_contertulios / total_parts) * 100:.1f}%"
    )
    table.add_row(
        "Parts with Date",
        str(parts_with_date),
        str(total_parts - parts_with_date),
        f"{(parts_with_date / total_parts) * 100:.1f}%"
    )
    table.add_row(
        "Parts with Ivoox_link",
        str(parts_with_ivoox),
        str(total_parts - parts_with_ivoox),
        f"{(parts_with_ivoox / total_parts) * 100:.1f}%"
    )
    
    console.print(table)
    
    # Print overall stats
    console.print(f"\n[bold]Total Episodes:[/bold] {total_episodes}")
    console.print(f"[bold]Total Parts:[/bold] {total_parts}")


def main(report_only: bool = False):
    """Main entrypoint for script execution."""
    if report_only:
        try:
            console.print("[yellow]Running in report-only mode[/yellow]")
            master_data = load_json_file(OUTPUT_PATH)
            report_completion_rate(master_data)
        except Exception as e:
            logger.error(f"Failed to run report on existing data: {str(e)}")
        return
    
    # Load all three source files
    console.print("[bold]Loading source data...[/bold]")
    
    try:
        audiofeed_data = load_json_file(AUDIOFEED_JSON)
        cbinfo_data = load_json_file(CBINFO_JSON)
        web_data = load_json_file(WEB_PARSE_JSON)
    except Exception as e:
        logger.error(f"Failed to load required source files: {str(e)}")
        return
    
    # Group by episode
    console.print("[bold]Grouping episodes...[/bold]")
    grouped_parts = group_audiofeed_by_episode(audiofeed_data)
    
    # Consolidate parts
    console.print("[bold]Enriching with web and cbinfo data...[/bold]")
    master_data = build_episode_structure(grouped_parts, web_data, cbinfo_data)
    
    # Save output
    console.print("[bold]Saving output...[/bold]")
    save_master_data(master_data, OUTPUT_PATH)
    
    # Report completion rate
    console.print("[bold]Generating completion report...[/bold]")
    report_completion_rate(master_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Consolidate episode data from multiple sources into a unified JSON."
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only report on existing master_scrapping_data.json without modifying"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    console.print(Panel.fit(
        "[bold blue]CoffeeBreak_NPL - Episode Data Consolidation[/bold blue]\n"
        "Merging audiofeed_index.json, cbinfo_index.json, and web_parse.json",
        border_style="blue"
    ))
    
    main(report_only=args.report_only)