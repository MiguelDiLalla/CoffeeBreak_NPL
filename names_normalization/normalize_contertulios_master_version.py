#!/usr/bin/env python3
"""
normalize_contertulios_master_version.py

CLI tool for normalization and assisted completion of 'contertulios' (guests/panelists) in CoffeeBreak_NPL podcast metadata,
specifically for the master_scrapping_data.json format which contains episode parts with raw_description text fields.

This script focuses on the --assisted-completion functionality to specifically:
1. Find episodes with Parts that have empty Contertulios lists
2. Extract potential names from each part's raw_description field 
3. Suggest normalized names based on fuzzy matching
4. Allow interactive approval of suggested names

During interactive mode, for each suggested name you'll be prompted with options:
- Press 'y': Add the suggested name to contertulios (default)
- Press 'n': Skip this suggestion
- Press 'q': Skip remaining suggestions for this episode

Names highlighted in green (multi-word) are more likely to be valid contertulios.
Names highlighted in red (single-word) may be false positives.
Suggestions with only red words (single-word names) are automatically skipped.

Usage:
    python -m names_normalization.normalize_contertulios_master_version --assisted-completion [--verbose] [--output PATH] [--config PATH]

See --help for details.

Author: Miguel Di Lalla (2025)
"""
import argparse
import json
import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel
import logging
import re
from rapidfuzz import fuzz, process
import shutil
import datetime

# Import config for paths
try:
    import config
except ImportError:
    config = None

# ========== Logging Setup ==========
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[RichHandler(console=console)]
)
logger = logging.getLogger("normalize_contertulios_master")

# Default similarity threshold for fuzzy matching
DEFAULT_SIMILARITY_THRESHOLD = 70.0

# ========== Helper Functions ==========
def get_contertulios_path() -> Path:
    """Get the path to contertulios.json using config or fallback."""    
    if config and hasattr(config, 'CONTERTULIOS_PATH'):
        return Path(config.CONTERTULIOS_PATH)
    return Path(__file__).parent / 'contertulios.json'

def get_master_data_path() -> Path:
    """Get the path to master_scrapping_data.json using config or fallback."""    
    if config and hasattr(config, 'MASTER_DATA_PATH'):
        return Path(config.MASTER_DATA_PATH)
    return Path(__file__).parent.parent / 'database' / 'master_scrapping_data.json'

def create_backup(file_path: Path) -> Path:
    """
    Create a backup of the specified file with timestamp.
    
    Args:
        file_path (Path): Path to the file to back up
        
    Returns:
        Path: Path to the created backup file
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(f'.{timestamp}.bak')
    
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup at {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {str(e)}")
        sys.exit(1)

def load_json(path: Path) -> Any:
    """Load a JSON file with UTF-8 encoding."""    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from {path}: {e}")
        sys.exit(1)

def save_json(data: Any, path: Path) -> None:
    """Save a JSON file with UTF-8 encoding."""    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save JSON to {path}: {e}")
        sys.exit(1)

def load_normalized_names() -> Dict[str, List[str]]:
    """
    Load normalized names and their aliases from contertulios.json.
    
    Returns:
        Dict mapping normalized names to lists of their aliases
    """
    contertulios_path = get_contertulios_path()
    data = load_json(contertulios_path)
    
    if 'normalized' in data and 'aliases' in data:
        normalized = data.get('normalized', [])
        aliases_field = data.get('aliases', {})
        
        # If aliases is a dict mapping raw->canonical, invert into lists per canonical
        if isinstance(aliases_field, dict):
            normalized_to_aliases = {norm: [] for norm in normalized}
            for raw, canon in aliases_field.items():
                if canon in normalized_to_aliases:
                    normalized_to_aliases[canon].append(raw)
            return normalized_to_aliases
        
        # Else, legacy format (list of parallel alias lists)
        alias_lists = aliases_field
        normalized_to_aliases = {}
        for i, norm in enumerate(normalized):
            alias_list = alias_lists[i] if i < len(alias_lists) else []
            if isinstance(alias_list, str):
                alias_list = [alias_list]
            normalized_to_aliases[norm] = alias_list
        return normalized_to_aliases
    elif 'canonical_dict' in data:
        # Handle canonical_dict format
        return data['canonical_dict']
    else:
        logger.warning("No valid normalized names found in contertulios.json")
        return {}

def extract_names_from_description(raw_description: str) -> Set[str]:
    """
    Extract potential name mentions from a raw description text.
    
    Args:
        raw_description (str): The raw description text from an episode part
        
    Returns:
        Set[str]: Set of potential name mentions
    """
    # Split text by common separators and get words that could be names
    words = re.split(r'[,.;:\n\t\(\)]', raw_description)
    potential_names = set()
    
    for word_group in words:
        # Look for capitalized words that aren't at the beginning of sentences
        word_group = word_group.strip()
        if not word_group:
            continue
            
        # Extract potential names (words starting with uppercase)
        matches = re.findall(r'\b[A-Z][a-zñáéíóúü]+\b', word_group)
        potential_names.update(matches)
        
        # Also look for full names (sequences of capitalized words)
        full_names = re.findall(r'\b[A-Z][a-zñáéíóúü]+(?:\s+[A-Z][a-zñáéíóúü]+)+\b', word_group)
        potential_names.update(full_names)
    
    return potential_names

def find_best_normalized_match(name: str, normalized_names: Dict[str, List[str]], 
                              threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> str:
    """
    Find the best normalized name match for a given name using fuzzy matching.
    
    Args:
        name (str): The name to find a match for
        normalized_names (Dict[str, List[str]]): Dictionary of normalized names and their aliases
        threshold (float): Minimum similarity score to consider a match (0-100)
        
    Returns:
        str: The best matching normalized name, or empty string if no match above threshold
    """
    best_score = 0
    best_match = ""
    
    # First try exact matches with normalized names
    if name in normalized_names:
        return name
    
    # Then check if name is in any alias list
    for norm, aliases in normalized_names.items():
        if name in aliases:
            return norm
    
    # If no exact match, try fuzzy matching with normalized names and aliases
    for norm, aliases in normalized_names.items():
        # Check similarity with the normalized name
        score = fuzz.ratio(name.lower(), norm.lower())
        if score > best_score and score >= threshold:
            best_score = score
            best_match = norm
        
        # Check similarity with each alias
        for alias in aliases:
            score = fuzz.ratio(name.lower(), alias.lower())
            if score > best_score and score >= threshold:
                best_score = score
                best_match = norm
    
    return best_match

def get_episode_identifier(episode: Dict) -> str:
    """
    Create a readable identifier for an episode.
    
    Args:
        episode (Dict): Episode dictionary
    
    Returns:
        str: A readable identifier like "Episode 001"
    """
    ep_num = episode.get("Episode number", "Unknown")
    return f"Episode {ep_num}"

def find_parts_without_contertulios(episodes: List[Dict]) -> List[Tuple[int, int, Dict, Dict]]:
    """
    Find all parts without contertulios across all episodes.
    
    Args:
        episodes (List[Dict]): List of episode dictionaries
    
    Returns:
        List[Tuple[int, int, Dict, Dict]]: List of (episode_index, part_index, episode, part) tuples
    """
    parts_without_contertulios = []
    
    for episode_idx, episode in enumerate(episodes):
        if "Parts" not in episode or not episode["Parts"]:
            continue
        
        for part_idx, part in enumerate(episode["Parts"]):
            # Check if Contertulios key exists and is empty
            contertulios_empty = "Contertulios" not in part or not part["Contertulios"]
            has_raw_description = "raw_description" in part and part["raw_description"]
            
            if contertulios_empty and has_raw_description:
                parts_without_contertulios.append((episode_idx, part_idx, episode, part))
    
    return parts_without_contertulios

def has_multiword_name(name_list: List[str]) -> bool:
    """
    Check if at least one name in the list contains multiple words.
    
    Args:
        name_list (List[str]): List of extracted name candidates
        
    Returns:
        bool: True if at least one name has multiple words, False otherwise
    """
    return any(' ' in name for name in name_list)

def sort_parts_chronologically(parts_list: List[Tuple[int, int, Dict, Dict]]) -> List[Tuple[int, int, Dict, Dict]]:
    """
    Sort parts by episode number (chronologically).
    
    Args:
        parts_list (List[Tuple[int, int, Dict, Dict]]): List of parts data
        
    Returns:
        List[Tuple[int, int, Dict, Dict]]: Sorted list of parts data
    """
    def get_episode_number(item):
        episode = item[2]  # The episode dict is the third element
        try:
            return int(episode.get("Episode number", "999"))
        except ValueError:
            return 999  # Default high value for episodes without a number
            
    return sorted(parts_list, key=get_episode_number)

def display_parts_table(parts_list: List[Tuple[int, int, Dict, Dict]]) -> None:
    """
    Display a formatted table of parts without contertulios.
    
    Args:
        parts_list (List[Tuple[int, int, Dict, Dict]]): List of parts data
    """
    table = Table(title="Parts Without Contertulios")
    
    table.add_column("Episode", style="cyan")
    table.add_column("Part #", style="magenta")
    table.add_column("Title", style="green")
    table.add_column("Description Preview", style="dim")
    
    for episode_idx, part_idx, episode, part in parts_list:
        ep_num = episode.get("Episode number", "Unknown")
        title = episode.get("Title", "No title")
        
        # Get a short preview of the raw description
        description_preview = part.get("raw_description", "")[:50]
        if description_preview and len(part.get("raw_description", "")) > 50:
            description_preview += "..."
            
        table.add_row(
            f"{ep_num}",
            f"{part_idx + 1}",
            title,
            description_preview
        )
    
    console.print(table)

def assisted_completion(episodes: List[Dict], normalized_names: Dict[str, List[str]], 
                       threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
                       non_interactive: bool = False) -> Tuple[List[Dict], Dict[str, int]]:
    """
    For episode parts with empty Contertulios lists, suggest normalized names via fuzzy matching of 
    raw_description text from each part. Avoids suggesting names already present.
    
    Args:
        episodes (List[Dict]): List of episode dictionaries from master_scrapping_data.json
        normalized_names (Dict[str, List[str]]): Dictionary of normalized names and their aliases
        threshold (float): Minimum similarity score to consider a match (0-100)
        non_interactive (bool): If True, run in batch mode without prompts
        
    Returns:
        Tuple[List[Dict], Dict[str, int]]: Updated episodes and statistics per part
    """
    # Create a copy of episodes to update
    updated_episodes = episodes.copy()
    
    # Find all parts without contertulios
    parts_without_contertulios = find_parts_without_contertulios(episodes)
    total_parts = len(parts_without_contertulios)
    
    if total_parts == 0:
        console.print("[yellow]No parts without contertulios found.[/yellow]")
        return updated_episodes, {}
        
    # Sort parts chronologically by episode number
    sorted_parts = sort_parts_chronologically(parts_without_contertulios)
    
    # Display parts table
    console.print(Panel.fit(
        f"[bold blue]Found {total_parts} parts without contertulios[/bold blue]\n"
        "These will be processed in chronological order (from earliest episode)",
        border_style="blue"
    ))
    display_parts_table(sorted_parts)
    
    if not non_interactive:
        proceed = Prompt.ask("\nProceed with processing these parts?", choices=["y", "n"], default="y")
        if proceed.lower() != "y":
            console.print("[yellow]Operation cancelled by user.[/yellow]")
            return episodes, {}
    
    # Track changes for reporting
    changes_stats = {}  # format: "episode_num|part_idx": num_added_contertulios
    skipped_single_word_count = 0
    processed_count = 0
    
    # Process each part
    for episode_idx, part_idx, episode, part in sorted_parts:
        ep_id = episode.get("Episode number", "Unknown")
        part_key = f"{ep_id}|{part_idx+1}"
        
        console.print(f"\n[bold cyan]Episode:[/bold cyan] {ep_id} - {episode.get('Title', 'No title')}")
        console.print(f"[magenta]Part {part_idx+1}:[/magenta]")
        console.print(f"[dim]{part.get('raw_description', '')[:200]}...[/dim]")
        
        # Extract potential names from the description
        potential_names = extract_names_from_description(part.get("raw_description", ""))
        if not potential_names:
            console.print("[yellow]No potential names found in description.[/yellow]")
            continue
            
        # Track which normalized names are suggested and which raw names map to them
        norm_to_raws = {}
        for name in potential_names:
            best_match = find_best_normalized_match(name, normalized_names, threshold)
            if best_match:
                norm_to_raws.setdefault(best_match, []).append(name)
        
        # Discard suggestions with only one raw match and that match is a non-spaced option
        filtered_norm_to_raws = {
            norm: raws for norm, raws in norm_to_raws.items()
            if not (len(raws) == 1 and ' ' not in raws[0])
        }
        
        # Further filter to remove suggestions where all extracted names are single words
        filtered_norm_to_raws = {
            norm: raws for norm, raws in filtered_norm_to_raws.items()
            if has_multiword_name(raws)
        }
        
        # Count how many were skipped due to only having single words
        skipped_single_word_count += len(norm_to_raws) - len(filtered_norm_to_raws)
        
        if not filtered_norm_to_raws:
            console.print("[yellow]No valid contertulios suggestions after filtering.[/yellow]")
            continue
            
        console.print("[yellow]Potential contertulios matches found:[/yellow]")
        
        # Process suggestions
        suggested_contertulios = []
        suggestions = list(filtered_norm_to_raws.keys())
        
        for norm in suggestions:
            raw_names = filtered_norm_to_raws[norm]
            
            # Color: red if no spaces, bright green if contains spaces
            colored_raws = []
            for raw in raw_names:
                if ' ' in raw:
                    colored_raws.append(f"[bright_green]{raw}[/bright_green]")
                else:
                    colored_raws.append(f"[red]{raw}[/red]")
            colored_raws_str = ', '.join(colored_raws)
            
            # Keep the normalized suggestion itself default color
            console.print(f"Suggested: [bold]{norm}[/bold] (from extracted: {colored_raws_str})")
            
            if non_interactive:
                suggested_contertulios.append(norm)
                logger.debug(f"Auto-added {norm} for extracted {raw_names} in non-interactive mode, episode {ep_id}, part {part_idx+1}")
            else:
                choice = Prompt.ask(f"Add this contertulio?", choices=["y", "n", "q"], default="y")
                if choice.lower() == "y":
                    suggested_contertulios.append(norm)
                    console.print(f"[green]Added {norm}[/green]")
                elif choice.lower() == "q":
                    console.print("[yellow]Skipping remaining suggestions for this part[/yellow]")
                    break
        
        # Update part with new contertulios if any were suggested
        if suggested_contertulios:
            # Initialize Contertulios list if it doesn't exist
            if "Contertulios" not in updated_episodes[episode_idx]["Parts"][part_idx]:
                updated_episodes[episode_idx]["Parts"][part_idx]["Contertulios"] = []
                
            # Set the suggested contertulios
            updated_episodes[episode_idx]["Parts"][part_idx]["Contertulios"] = suggested_contertulios
            changes_stats[part_key] = len(suggested_contertulios)
            processed_count += 1
            
            console.print(f"[green]Added {len(suggested_contertulios)} contertulios to Part {part_idx+1}[/green]")
        else:
            console.print("[yellow]No contertulios added to this part.[/yellow]")
    
    console.print(f"\n[bold green]Processed {processed_count} parts out of {total_parts}[/bold green]")
    console.print(f"[bold yellow]Auto-skipped {skipped_single_word_count} suggestions with only single-word names[/bold yellow]")
    
    return updated_episodes, changes_stats

def display_changes_report(changes_stats: Dict[str, int]) -> None:
    """
    Display a formatted report of changes made.
    
    Args:
        changes_stats (Dict[str, int]): Statistics of changes by part
    """
    if not changes_stats:
        console.print("[yellow]No changes were made.[/yellow]")
        return
        
    table = Table(title="Changes Summary")
    
    table.add_column("Episode|Part", style="cyan")
    table.add_column("Contertulios Added", style="green")
    
    total_added = 0
    for part_key, count in changes_stats.items():
        total_added += count
        table.add_row(part_key, str(count))
        
    console.print(table)
    console.print(f"[bold green]Total contertulios added: {total_added}[/bold green]")

# ========== CLI Operations ==========
def assisted_completion_cli(args):
    """CLI entrypoint for --assisted-completion operation"""
    master_path = get_master_data_path()
    normalized_names = load_normalized_names()
    
    # Display welcome message with keyboard controls
    console.print(Panel.fit(
        "[bold green]Coffee Break NPL - Contertulios Normalization Tool[/bold green]\n"
        "Add missing contertulios to episode parts based on text analysis",
        border_style="green"
    ))
    
    console.print("\n[bold]Keyboard Controls:[/bold]")
    console.print("  [cyan]y[/cyan] - Add the suggested name to Contertulios [default]")
    console.print("  [cyan]n[/cyan] - Skip this suggestion")
    console.print("  [cyan]q[/cyan] - Skip remaining suggestions for the current part\n")
    
    console.print("[bold]Color coding:[/bold]")
    console.print("  [bright_green]Green names[/bright_green] (multi-word) - More likely to be valid contertulios")
    console.print("  [red]Red names[/red] (single-word) - Possible false positives\n")
    
    # Load episodes
    episodes = load_json(master_path)
    logger.info(f"Loaded {len(episodes)} episodes from {master_path}")
    logger.info(f"Loaded {len(normalized_names)} normalized names from {get_contertulios_path()}")
    
    # Create backup before making changes
    console.print("[yellow]Creating backup of master data file...[/yellow]")
    backup_path = create_backup(master_path)
    console.print(f"[green]Backup created: {backup_path}[/green]\n")
    
    # Process episodes
    console.print("[bold yellow]Starting processing...[/bold yellow]")
    updated_episodes, changes_stats = assisted_completion(
        episodes, 
        normalized_names, 
        threshold=args.threshold, 
        non_interactive=args.non_interactive
    )
    
    # Display changes report
    console.print("\n[bold]Changes Report:[/bold]")
    display_changes_report(changes_stats)
    
    # Save changes
    output_path = args.output if args.output else master_path
    if changes_stats:  # Only save if changes were made
        console.print("\n[yellow]Saving changes...[/yellow]")
        save_json(updated_episodes, Path(output_path))
        console.print(f"[green]Saved updated episodes to {output_path}[/green]")
    else:
        console.print("\n[yellow]No changes to save.[/yellow]")
    
    console.print("\n[bold green]Process completed![/bold green]")

# ========== CLI Main ==========
def main():
    parser = argparse.ArgumentParser(
        description="Process and suggest contertulios in CoffeeBreak_NPL master data based on parts' raw_description text.",
        epilog="This tool processes the master_scrapping_data.json file, extracting potential names from each part's raw_description field."
    )
    # We're focusing only on assisted completion as per the user's requirements
    parser.add_argument('--assisted-completion', action='store_true', required=True,
                      help="Suggest normalized names for empty contertulios via fuzzy matching of raw_description fields.")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose logging.")
    parser.add_argument('--output', '-o', type=str, help="Output file path.")
    parser.add_argument('--config', '-c', type=str, help="Path to configuration file.")
    parser.add_argument('--non-interactive', action='store_true', help="Run in batch mode without prompts.")
    parser.add_argument('--log-file', type=str, help="Path to log output file.")
    parser.add_argument('--threshold', '-t', type=float, default=DEFAULT_SIMILARITY_THRESHOLD,
                      help=f"Similarity threshold (0-100) for fuzzy matching (default: {DEFAULT_SIMILARITY_THRESHOLD}).")
    args = parser.parse_args()

    # Setup logging verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Add file handler if requested
    if args.log_file:
        fh = logging.FileHandler(args.log_file)
        fh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S'))
        logger.addHandler(fh)

    # Load user config if provided
    if args.config:
        spec = importlib.util.spec_from_file_location("user_config", args.config)
        user_cfg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(user_cfg)
        global config
        config = user_cfg

    # Execute the assisted completion operation
    assisted_completion_cli(args)

if __name__ == "__main__":
    main()