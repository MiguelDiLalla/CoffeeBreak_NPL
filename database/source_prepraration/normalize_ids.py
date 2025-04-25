#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
normalize_ids.py - A utility to standardize episode IDs across JSON database files.

This script provides functionality to:
1. Display episode IDs from different source databases
2. Normalize episode IDs to follow the "Ep###_A|B|Supl" format

Usage:
    python normalize_ids.py --display [audiofeed|cbinfo|web|all]
    python normalize_ids.py --normalize [audiofeed|cbinfo|web|all]

Author: Miguel Di Lalla 
Date: April 25, 2025
"""

import os
import re
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from rich.console import Console
from rich.table import Table
from rich.progress import track

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("normalize_ids")
console = Console()

# Import project's configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    import config
except ImportError:
    logger.error("Could not import config module. Make sure you're running from the project root.")
    sys.exit(1)

# Define paths to JSON files
DATA_DIR = Path(config.DATA_DIR)
AUDIOFEED_JSON = DATA_DIR / "parsed_json" / "audiofeed_index.json"
CBINFO_JSON = DATA_DIR / "parsed_json" / "cbinfo_index.json"
WEB_PARSE_JSON = DATA_DIR / "parsed_json" / "web_parse.json"


def load_json_data(file_path: Path) -> List[Dict]:
    """
    Load data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of dictionaries containing the data
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    try:
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return []
        
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error loading {file_path}: {str(e)}")
        return []


def save_json_data(file_path: Path, data: List[Dict]) -> bool:
    """
    Save data to a JSON file.
    
    Args:
        file_path: Path to the JSON file
        data: List of dictionaries to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        logger.info(f"Successfully saved data to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving to {file_path}: {str(e)}")
        return False


def normalize_episode_id(episode_id: str) -> str:
    """
    Normalize an episode ID to the format "Ep###_A|B|Supl".
    
    Args:
        episode_id: The original episode ID
        
    Returns:
        The normalized episode ID
    """
    # Remove spaces
    episode_id = episode_id.replace(" ", "")
    
    # Extract the episode number
    match = re.search(r'[Ee][Pp]\.?(\d+)([_\-]?[A-Za-z]+)?', episode_id)
    if match:
        episode_num = match.group(1)
        suffix = match.group(2) if match.group(2) else ""
        
        # Standardize suffix format
        if suffix:
            # Handle various suffix formats
            if suffix.startswith('_') or suffix.startswith('-'):
                suffix = suffix[1:]  # Remove separator
            
            # If suffix is A or B, keep it as _A or _B
            if suffix.upper() in ['A', 'B']:
                suffix = f"_{suffix.upper()}"
            # If suffix indicates a supplement, normalize to _Supl
            elif any(s in suffix.lower() for s in ['supl', 'bonus', 'esp']):
                suffix = "_Supl"
        
        # Always use 'Ep' prefix and zero-pad the number to 3 digits
        normalized_id = f"Ep{int(episode_num):03d}{suffix}"
        return normalized_id
    
    # If no match, return the original ID
    return episode_id


def get_episode_id_field(source_type: str) -> str:
    """
    Get the field name for episode ID based on the source type.
    
    Args:
        source_type: Type of source data
        
    Returns:
        Field name for episode ID
    """
    if source_type == 'audiofeed':
        return 'episode_id'
    elif source_type == 'cbinfo':
        return 'episode_id'
    elif source_type == 'web':
        return 'ep_id'
    else:
        return 'episode_id'  # Default


def display_episode_ids(source_type: str) -> None:
    """
    Display episode IDs from the specified source.
    
    Args:
        source_type: Type of source data (audiofeed, cbinfo, web, or all)
    """
    if source_type not in ['audiofeed', 'cbinfo', 'web', 'all']:
        console.print(f"[red]Invalid source type: {source_type}[/red]")
        return
    
    sources = []
    if source_type == 'all':
        sources = [('audiofeed', AUDIOFEED_JSON), 
                  ('cbinfo', CBINFO_JSON), 
                  ('web', WEB_PARSE_JSON)]
    else:
        if source_type == 'audiofeed':
            sources = [('audiofeed', AUDIOFEED_JSON)]
        elif source_type == 'cbinfo':
            sources = [('cbinfo', CBINFO_JSON)]
        elif source_type == 'web':
            sources = [('web', WEB_PARSE_JSON)]
    
    for src_name, src_path in sources:
        data = load_json_data(src_path)
        if not data:
            console.print(f"[yellow]No data available for {src_name}[/yellow]")
            continue
        
        field_name = get_episode_id_field(src_name)
        
        # Create table for display
        table = Table(title=f"Episode IDs from {src_name}")
        table.add_column("Original ID", style="cyan")
        table.add_column("Normalized ID", style="green")
        
        # Add rows to the table
        for item in data:
            if field_name in item and item[field_name]:
                original_id = item[field_name]
                normalized_id = normalize_episode_id(original_id)
                table.add_row(original_id, normalized_id)
        
        # Display the table
        console.print(table)
        console.print(f"[blue]Total episodes in {src_name}: {len(data)}[/blue]\n")


def normalize_episode_ids(source_type: str) -> None:
    """
    Normalize episode IDs in the specified source.
    
    Args:
        source_type: Type of source data (audiofeed, cbinfo, web, or all)
    """
    if source_type not in ['audiofeed', 'cbinfo', 'web', 'all']:
        console.print(f"[red]Invalid source type: {source_type}[/red]")
        return
    
    sources = []
    if source_type == 'all':
        sources = [('audiofeed', AUDIOFEED_JSON), 
                  ('cbinfo', CBINFO_JSON), 
                  ('web', WEB_PARSE_JSON)]
    else:
        if source_type == 'audiofeed':
            sources = [('audiofeed', AUDIOFEED_JSON)]
        elif source_type == 'cbinfo':
            sources = [('cbinfo', CBINFO_JSON)]
        elif source_type == 'web':
            sources = [('web', WEB_PARSE_JSON)]
    
    for src_name, src_path in sources:
        data = load_json_data(src_path)
        if not data:
            console.print(f"[yellow]No data available for {src_name}[/yellow]")
            continue
        
        field_name = get_episode_id_field(src_name)
        changes_made = 0
        
        # Create a backup of the original file
        backup_path = src_path.with_suffix('.json.bak')
        try:
            if not backup_path.exists():
                with open(src_path, 'r', encoding='utf-8') as src_file:
                    with open(backup_path, 'w', encoding='utf-8') as bak_file:
                        bak_file.write(src_file.read())
                logger.info(f"Created backup at {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            console.print(f"[red]Failed to create backup for {src_name}. Operation aborted.[/red]")
            continue
        
        # Normalize episode IDs
        for item in track(data, description=f"Normalizing {src_name} IDs"):
            if field_name in item and item[field_name]:
                original_id = item[field_name]
                normalized_id = normalize_episode_id(original_id)
                
                if original_id != normalized_id:
                    item[field_name] = normalized_id
                    changes_made += 1
        
        # Save the changes
        if changes_made > 0:
            if save_json_data(src_path, data):
                console.print(f"[green]Successfully normalized {changes_made} episode IDs in {src_name}[/green]")
            else:
                console.print(f"[red]Failed to save changes to {src_name}[/red]")
        else:
            console.print(f"[blue]No changes needed for {src_name}[/blue]")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Utility to display and normalize episode IDs across JSON databases."
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--display", choices=["audiofeed", "cbinfo", "web", "all"], 
                       help="Display episode IDs from the specified JSON database")
    group.add_argument("--normalize", choices=["audiofeed", "cbinfo", "web", "all"], 
                       help="Normalize episode IDs in the specified JSON database")
    
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Execute the requested action
    if args.display:
        display_episode_ids(args.display)
    elif args.normalize:
        normalize_episode_ids(args.normalize)


if __name__ == "__main__":
    main()