"""
normalize_contertulios.py

CLI tool for normalization and assisted completion of 'contertulios' (guests/panelists) in CoffeeBreak_NPL podcast metadata.

Provides three main operations:
    --substitute-aliases: Replace aliases in cbinfo_index.json with canonical names.
    --assisted-completion: Suggest normalized names for empty contertulios via fuzzy matching.
    --validate: Check for missing normalized names in filled contertulios via fuzzy matching.

Usage:
    python -m names_normalization.normalize_contertulios [--substitute-aliases | --assisted-completion | --validate] [--verbose] [--output PATH] [--config PATH]

See --help for details.
"""
import argparse
import json
import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Set
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Prompt
import logging
import re
from rapidfuzz import fuzz, process

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
logger = logging.getLogger("normalize_contertulios")

# Default similarity threshold for fuzzy matching
DEFAULT_SIMILARITY_THRESHOLD = 70.0

# ========== Helper Functions ==========
def get_contertulios_path() -> Path:
    """Get the path to contertulios.json using config or fallback."""
    if config and hasattr(config, 'CONTERTULIOS_PATH'):
        return Path(config.CONTERTULIOS_PATH)
    return Path(__file__).parent / 'contertulios.json'

def get_cbinfo_index_path() -> Path:
    """Get the path to cbinfo_index.json using config or fallback."""
    if config and hasattr(config, 'CBINFO_INDEX_PATH'):
        return Path(config.CBINFO_INDEX_PATH)
    return Path(__file__).parent.parent / 'data' / 'parsed_json' / 'cbinfo_index.json'

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
        raw_description (str): The raw description text from an episode
        
    Returns:
        Set[str]: Set of potential name mentions
    """
    # Split text by common separators and get words that could be names
    # (capitalized words not at the beginning of sentences)
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

# ========== Main Operations ==========
def substitute_aliases(episodes: List[Dict], normalized_names: Dict[str, List[str]]) -> List[Dict]:
    """
    Replace aliases in episode contertulios lists with their canonical normalized names.
    
    Args:
        episodes (List[Dict]): List of episode dictionaries from cbinfo_index.json
        normalized_names (Dict[str, List[str]]): Dictionary of normalized names and their aliases
        
    Returns:
        List[Dict]: Updated episodes with normalized contertulios names
    """
    normalized_episodes = []
    changes_count = 0
    
    # Create a flat lookup dictionary for faster alias resolution
    alias_to_normalized = {}
    for norm, aliases in normalized_names.items():
        for alias in aliases:
            alias_to_normalized[alias.lower()] = norm
    
    # Add normalized names themselves to the lookup
    for norm in normalized_names:
        alias_to_normalized[norm.lower()] = norm
    
    for episode in episodes:
        # Skip if no contertulios
        if 'contertulios' not in episode or not episode['contertulios']:
            normalized_episodes.append(episode)
            continue
        
        # Check each contertulio name for possible normalization
        normalized_contertulios = []
        for name in episode['contertulios']:
            lower_name = name.lower()
            if lower_name in alias_to_normalized:
                normalized_name = alias_to_normalized[lower_name]
                if normalized_name != name:
                    logger.debug(f"Normalized '{name}' to '{normalized_name}' in episode {episode.get('episode_id', 'unknown')}")
                    changes_count += 1
                normalized_contertulios.append(normalized_name)
            else:
                normalized_contertulios.append(name)
        
        # Replace with normalized list
        updated_episode = {**episode, 'contertulios': normalized_contertulios}
        normalized_episodes.append(updated_episode)
    
    logger.info(f"Normalized {changes_count} contertulios names across {len(episodes)} episodes")
    return normalized_episodes

def assisted_completion(episodes: List[Dict], normalized_names: Dict[str, List[str]], 
                        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
                        non_interactive: bool = False) -> List[Dict]:
    """
    For episodes with empty contertulios, suggest normalized names via fuzzy matching of their raw_description.
    Avoid suggesting names already present. Log multiple raw names mapping to the same normalized suggestion.
    
    Args:
        episodes (List[Dict]): List of episode dictionaries from cbinfo_index.json
        normalized_names (Dict[str, List[str]]): Dictionary of normalized names and their aliases
        threshold (float): Minimum similarity score to consider a match (0-100)
        non_interactive (bool): If True, run in batch mode without prompts
        
    Returns:
        List[Dict]: Updated episodes with user-approved normalized contertulios
    """
    updated_episodes = []
    completion_count = 0
    for episode in episodes:
        # Skip if not an episode or already has contertulios
        if (episode.get('entry_type') != 'episode' or 
            'contertulios' not in episode or 
            episode['contertulios']):
            updated_episodes.append(episode)
            continue
        raw_description = episode.get('raw_description', '')
        if not raw_description:
            updated_episodes.append(episode)
            continue
        # Extract potential names from the raw description
        potential_names = extract_names_from_description(raw_description)
        if not potential_names:
            updated_episodes.append(episode)
            continue
        # Track which normalized names are suggested and which raw names map to them
        norm_to_raws = {}
        for name in potential_names:
            best_match = find_best_normalized_match(name, normalized_names, threshold)
            if best_match:
                norm_to_raws.setdefault(best_match, []).append(name)
        # Remove normalized names already present (case-insensitive)
        already_present = set(n.lower() for n in episode.get('contertulios', []))
        # Discard suggestions with only one raw match and that match is a non-spaced option
        filtered_norm_to_raws = {
            norm: raws for norm, raws in norm_to_raws.items()
            if not (len(raws) == 1 and ' ' not in raws[0])
        }
        suggestions = [norm for norm in filtered_norm_to_raws if norm.lower() not in already_present]
        # Log multiple raw names mapping to the same normalized suggestion
        for norm, raws in norm_to_raws.items():
            if len(raws) > 1:
                logger.info(f"Multiple extracted names {raws} map to normalized '{norm}' in episode {episode.get('episode_id')}")
        if not suggestions:
            updated_episodes.append(episode)
            continue
        console.print(f"\n[bold cyan]Episode:[/bold cyan] {episode.get('episode_id', 'unknown')} - {episode.get('title', 'No title')}")
        console.print(f"[dim]{raw_description[:200]}...[/dim]")
        console.print("[yellow]This episode has no contertulios. Potential matches found:[/yellow]")
        suggested_contertulios = []
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
                logger.debug(f"Auto-added {norm} for extracted {raw_names} in non-interactive mode, episode {episode.get('episode_id')}")
            else:
                choice = Prompt.ask(f"Add this contertulio?", choices=["y", "n", "q"], default="y") # default to yes, thancks
                if choice.lower() == "y":
                    suggested_contertulios.append(norm)
                    console.print(f"[green]Added {norm}[/green]")
                elif choice.lower() == "q":
                    console.print("[yellow]Skipping remaining suggestions for this episode[/yellow]")
                    break
        if suggested_contertulios:
            updated_episode = {**episode, 'contertulios': suggested_contertulios}
            completion_count += 1
        else:
            updated_episode = episode
        updated_episodes.append(updated_episode)
    logger.info(f"Completed contertulios for {completion_count} episodes")
    return updated_episodes

def validate_contertulios(episodes: List[Dict], normalized_names: Dict[str, List[str]], 
                         threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
                         non_interactive: bool = False) -> List[Dict]:
    """
    For episodes that already have contertulios, check if any potential names in the
    raw_description are missing from the contertulios list.
    
    Args:
        episodes (List[Dict]): List of episode dictionaries from cbinfo_index.json
        normalized_names (Dict[str, List[str]]): Dictionary of normalized names and their aliases
        threshold (float): Minimum similarity score to consider a match (0-100)
        non_interactive (bool): If True, run in batch mode without prompts
        
    Returns:
        List[Dict]: Updated episodes with additional user-approved normalized contertulios
    """
    updated_episodes = []
    validated_count = 0
    
    for episode in episodes:
        # Skip if not an episode or no contertulios
        if (episode.get('entry_type') != 'episode' or 
            'contertulios' not in episode or 
            not episode['contertulios']):
            updated_episodes.append(episode)
            continue
        
        raw_description = episode.get('raw_description', '')
        if not raw_description:
            updated_episodes.append(episode)
            continue
        
        # Current contertulios (case-insensitive)
        current_contertulios = [name.lower() for name in episode['contertulios']]
        
        # Extract potential names from the raw description
        potential_names = extract_names_from_description(raw_description)
        
        if not potential_names:
            updated_episodes.append(episode)
            continue
        
        # Find potential missing contertulios
        missing_potential = []
        norm_to_raws = {}
        for name in potential_names:
            best_match = find_best_normalized_match(name, normalized_names, threshold)
            if best_match and best_match.lower() not in current_contertulios:
                norm_to_raws.setdefault(best_match, []).append(name)
        # Discard suggestions with only one raw match and that match is a non-spaced option
        filtered_norm_to_raws = {
            norm: raws for norm, raws in norm_to_raws.items()
            if not (len(raws) == 1 and ' ' not in raws[0])
        }
        for norm, raws in filtered_norm_to_raws.items():
            for raw in raws:
                missing_potential.append((raw, norm))
        
        if not missing_potential:
            updated_episodes.append(episode)
            continue
        
        # User interaction for validating missing contertulios
        console.print(f"\n[bold cyan]Episode:[/bold cyan] {episode.get('episode_id', 'unknown')} - {episode.get('title', 'No title')}")
        console.print(f"[bold]Current contertulios:[/bold] {', '.join(episode['contertulios'])}")
        console.print(f"[yellow]Potential missing contertulios found:[/yellow]")
        
        # Collect additional contertulios to add
        additional_contertulios = []
        for orig_name, norm_name in missing_potential:
            # Color: red if no spaces, bright green if contains spaces
            if ' ' in orig_name:
                colored_orig = f"[bright_green]{orig_name}[/bright_green]"
            else:
                colored_orig = f"[red]{orig_name}[/red]"
            console.print(f"Found potential missing contertulio: {colored_orig} -> [green]{norm_name}[/green]")
            if non_interactive:
                additional_contertulios.append(norm_name)
                logger.debug(f"Auto-added missing {norm_name} in non-interactive mode for episode {episode.get('episode_id')}")
            else:
                choice = Prompt.ask("Add this contertulio?", choices=["y", "n", "q"], default="y") # default to yes, thanks
                if choice.lower() == "y":
                    additional_contertulios.append(norm_name)
                    console.print(f"[green]Added {norm_name}[/green]")
                elif choice.lower() == "q":
                    console.print("[yellow]Skipping remaining validations for this episode[/yellow]")
                    break
        
        if additional_contertulios:
            updated_contertulios = episode['contertulios'] + additional_contertulios
            updated_episode = {**episode, 'contertulios': updated_contertulios}
            validated_count += 1
        else:
            updated_episode = episode
        
        updated_episodes.append(updated_episode)
    
    logger.info(f"Added missing contertulios to {validated_count} episodes")
    return updated_episodes

# ========== CLI Operations ==========
def substitute_aliases_cli(args):
    """CLI entrypoint for --substitute-aliases operation"""
    cbinfo_path = get_cbinfo_index_path()
    normalized_names = load_normalized_names()
    episodes = load_json(cbinfo_path)
    
    logger.info(f"Loaded {len(episodes)} episodes from {cbinfo_path}")
    logger.info(f"Loaded {len(normalized_names)} normalized names from {get_contertulios_path()}")
    
    updated_episodes = substitute_aliases(episodes, normalized_names)
    
    output_path = args.output if args.output else cbinfo_path
    save_json(updated_episodes, Path(output_path))
    logger.info(f"Saved updated episodes to {output_path}")

def assisted_completion_cli(args):
    """CLI entrypoint for --assisted-completion operation"""
    cbinfo_path = get_cbinfo_index_path()
    normalized_names = load_normalized_names()
    episodes = load_json(cbinfo_path)
    
    logger.info(f"Loaded {len(episodes)} episodes from {cbinfo_path}")
    logger.info(f"Loaded {len(normalized_names)} normalized names from {get_contertulios_path()}")
    
    updated_episodes = assisted_completion(episodes, normalized_names, threshold=args.threshold, non_interactive=args.non_interactive)
    
    output_path = args.output if args.output else cbinfo_path
    save_json(updated_episodes, Path(output_path))
    logger.info(f"Saved updated episodes to {output_path}")

def validate_contertulios_cli(args):
    """CLI entrypoint for --validate operation"""
    cbinfo_path = get_cbinfo_index_path()
    normalized_names = load_normalized_names()
    episodes = load_json(cbinfo_path)
    
    logger.info(f"Loaded {len(episodes)} episodes from {cbinfo_path}")
    logger.info(f"Loaded {len(normalized_names)} normalized names from {get_contertulios_path()}")
    
    updated_episodes = validate_contertulios(episodes, normalized_names, threshold=args.threshold, non_interactive=args.non_interactive)
    
    output_path = args.output if args.output else cbinfo_path
    save_json(updated_episodes, Path(output_path))
    logger.info(f"Saved updated episodes to {output_path}")

# ========== CLI Main ==========
def main():
    parser = argparse.ArgumentParser(
        description="Normalize and assist completion of 'contertulios' in CoffeeBreak_NPL metadata.",
        epilog="See project README for pipeline context."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--substitute-aliases', action='store_true', 
                      dest='substitute_aliases',
                      help="Replace aliases in cbinfo_index.json with canonical names.")
    group.add_argument('--assisted-completion', action='store_true', 
                      help="Suggest normalized names for empty contertulios via fuzzy matching.")
    group.add_argument('--validate', action='store_true', 
                      help="Check for missing normalized names in filled contertulios via fuzzy matching.")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose logging.")
    parser.add_argument('--output', '-o', type=str, help="Output file or directory.")
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

    # Execute operation
    if args.substitute_aliases:
        substitute_aliases_cli(args)
        sys.exit(0)
    elif args.assisted_completion:
        assisted_completion_cli(args)
        sys.exit(0)
    elif args.validate:
        validate_contertulios_cli(args)
        sys.exit(0)

if __name__ == "__main__":
    main()
