"""
utils_normalization.py - Utilities for normalizing and extracting names from podcast metadata

This module provides functions to extract, normalize and manage guest names (contertulios)
from the CoffeeBreak podcast episodes.
"""
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Set, Optional

# Add project root to path to allow importing config
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

def extract_unique_contertulios(source_json_path: Optional[str] = None, 
                              target_json_path: Optional[str] = None) -> List[str]:
    """
    Extract all unique contertulio names from the cbinfo_index.json file
    and write them to the contertulios.json file under 'raw_uniques' key.
    
    Args:
        source_json_path: Path to the source JSON file. If None, uses default path.
        target_json_path: Path to the target JSON file. If None, uses default path.
        
    Returns:
        List of unique contertulio names found in the source file
    """
    # Use default paths if not specified
    if source_json_path is None:
        source_json_path = os.path.join(config.DATA_DIR, "parsed_json", "cbinfo_index.json")
        
    if target_json_path is None:
        target_json_path = os.path.join(config.PROJECT_ROOT, "names_normalization", "contertulios.json")
    
    # Load source data
    try:
        with open(source_json_path, 'r', encoding=config.ENCODING) as f:
            episodes_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Source file {source_json_path} not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Source file {source_json_path} contains invalid JSON.")
        return []
    
    # Extract unique contertulios
    unique_contertulios = set()
    for episode in episodes_data:
        if "contertulios" in episode and episode["contertulios"]:
            for contertulio in episode["contertulios"]:
                if contertulio and contertulio.strip():
                    unique_contertulios.add(contertulio.strip())
    
    # Sort the names alphabetically
    sorted_contertulios = sorted(list(unique_contertulios))
    
    # Prepare output structure
    output_data = {
        "raw_uniques": sorted_contertulios,
        "normalized": {},  # Empty dict for future normalized names
        "aliases": {}  # Empty dict for aliases
    }
    
    # Write to target file
    try:
        with open(target_json_path, 'w', encoding=config.ENCODING) as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error writing to {target_json_path}: {str(e)}")
    
    print(f"Extracted {len(sorted_contertulios)} unique contertulios to {target_json_path}")
    return sorted_contertulios

def assisted_normalization(contertulios_json_path: Optional[str] = None) -> None:
    """
    Interactively suggest and assign normalized names to aliases using RapidFuzz similarity.
    Updates the 'aliases' key in contertulios.json.
    Args:
        contertulios_json_path: Path to the contertulios.json file. If None, uses default path.
    """
    try:
        from rapidfuzz import process, fuzz
    except ImportError:
        print("[ERROR] rapidfuzz is required. Install with: pip install rapidfuzz")
        return
    try:
        from rich.console import Console
        from rich.prompt import Prompt
        from rich.text import Text
        from rich.panel import Panel
        from rich.theme import Theme
    except ImportError:
        print("[ERROR] rich is required. Install with: pip install rich")
        return

    console = Console(theme=Theme({
        "name": "bold yellow",
        "suggestion": "cyan",
        "instruction": "green",
        "skip": "dim",
        "accepted": "bold green",
        "set": "bold blue"
    }))

    if contertulios_json_path is None:
        contertulios_json_path = os.path.join(config.PROJECT_ROOT, "names_normalization", "contertulios.json")

    # Load contertulios.json
    try:
        with open(contertulios_json_path, 'r', encoding=config.ENCODING) as f:
            data = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading {contertulios_json_path}: {e}")
        return

    raw_uniques = data.get("raw_uniques", [])
    normalized = data.get("normalized", {})
    aliases = data.get("aliases", {})

    console.print(Panel("[instruction]For each name, you'll be shown the most similar existing names.\n"
                        "Type [bold][1-3][/bold] to select a suggestion, type a normalized name, or just press [bold]Enter[/bold] to set as canonical (self-alias, skip future review).",
                        title="[bold green]Assisted Normalization[/bold green]", expand=False))

    # Build canonical set (normalized names + raw_uniques)
    normalized_values = set(normalized.values())
    canonical_names = set(normalized.values()) | set(raw_uniques)
    canonical_names = sorted(canonical_names)

    for name in raw_uniques:
        # Skip if already reviewed (in aliases) or already canonical (in normalized values)
        if name in aliases or name in normalized.values():
            if name in normalized.values() and name not in aliases:
                console.print(f"[skip]  Skipped '{name}' (already canonical).[/skip]")
            continue
        choices = [n for n in canonical_names if n != name]
        if not choices:
            aliases[name] = name
            normalized[name] = name
            canonical_names.append(name)
            continue
        matches = process.extract(name, choices, scorer=fuzz.ratio, limit=3)
        suggestion, score = matches[0][0], matches[0][1] if matches else (name, 100)
        console.print(f"\n[name]Name:[/name] [bold yellow]{name}[/bold yellow]")
        console.print("[instruction]Top suggestions:")
        # Recompute normalized_values for up-to-date magenta highlighting
        normalized_values = set(normalized.values())
        for i, (cand, sc, _) in enumerate(matches):
            color = "magenta" if cand in normalized_values else "suggestion"
            console.print(f"  [bold][{i+1}][/bold] [{color}]{cand}[/{color}] [dim](score: {sc})[/dim]")
        console.print("[instruction]Type [bold][1-3][/bold] to select a suggestion, type a name, or just press [bold]Enter[/bold] to set as canonical (self-alias, skip future review).")
        user_input = Prompt.ask("  Normalize as", default="", show_default=False).strip()
        if user_input == '':
            aliases[name] = name
            normalized[name] = name
            canonical_names.append(name)
            console.print("[skip]  Set as canonical (self-alias, will be skipped in future rounds).[/skip]\n")
            continue
        elif user_input in {'1', '2', '3'}:
            idx = int(user_input) - 1
            if 0 <= idx < len(matches):
                selected = matches[idx][0]
                aliases[name] = selected
                normalized[name] = selected
                canonical_names.append(selected)
                console.print(f"[accepted]  Accepted: {selected} (now canonical, will be suggested in future rounds)[/accepted]\n")
            else:
                console.print(f"[red]  Invalid selection. Skipped.[/red]\n")
                continue
        else:
            aliases[name] = user_input
            normalized[name] = user_input
            canonical_names.append(user_input)
            console.print(f"[set]  Set as: {user_input} (now canonical, will be suggested in future rounds)[/set]\n")

    data["aliases"] = aliases
    # Set normalized as a sorted list of unique canonical names
    data["normalized"] = sorted(set(aliases.values()))
    with open(contertulios_json_path, 'w', encoding=config.ENCODING) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"\n[bold green]Done:[/bold green] Aliases updated in [bold]{contertulios_json_path}[/bold]\n")

def calculate_alias_scores(contertulios_json_path: Optional[str] = None) -> None:
    """
    Calculate and report RapidFuzz similarity scores for each alias→canonical mapping in contertulios.json.
    Outputs statistics (min, max, mean, median, std).
    Args:
        contertulios_json_path: Path to the contertulios.json file. If None, uses default path.
    """
    import statistics
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    try:
        from rapidfuzz import fuzz
    except ImportError:
        print("[ERROR] rapidfuzz is required. Install with: pip install rapidfuzz")
        return

    console = Console()
    if contertulios_json_path is None:
        contertulios_json_path = os.path.join(config.PROJECT_ROOT, "names_normalization", "contertulios.json")
    if not os.path.exists(contertulios_json_path):
        console.print(f"[red]File not found:[/red] {contertulios_json_path}")
        return
    with open(contertulios_json_path, 'r', encoding=config.ENCODING) as f:
        data = json.load(f)
    aliases = data.get("aliases", {})
    canonicals = data.get("normalized", [])
    if not aliases or not canonicals:
        console.print(f"[red]contertulios.json must have both 'aliases' and 'normalized' populated.[/red]")
        return
    scores = []
    table = Table(title="Alias → Canonical Similarity Scores", show_lines=True)
    table.add_column("Alias", style="yellow")
    table.add_column("Canonical", style="cyan")
    table.add_column("Score", style="bold magenta")
    for alias, canonical in aliases.items():
        score = fuzz.ratio(alias, canonical)
        if score == 100:
            continue  # Skip perfect matches
        scores.append(score)
        table.add_row(alias, canonical, f"{score:.2f}")
    if not scores:
        console.print("[yellow]No alias mappings to score (all are perfect matches).[/yellow]")
        return
    stats = {
        "count": len(scores),
        "min": min(scores),
        "max": max(scores),
        "mean": statistics.mean(scores),
        "median": statistics.median(scores),
        "stdev": statistics.stdev(scores) if len(scores) > 1 else 0.0
    }
    console.print(table)
    console.print(Panel(f"[bold]Alias→Canonical Score Statistics[/bold]\n"
                       f"Count: {stats['count']}\n"
                       f"Min: {stats['min']:.2f}\n"
                       f"Max: {stats['max']:.2f}\n"
                       f"Mean: {stats['mean']:.2f}\n"
                       f"Median: {stats['median']:.2f}\n"
                       f"Std Dev: {stats['stdev']:.2f}",
                       title="[green]Score Report[/green]", expand=False))

def main():
    """Main function to run when script is executed directly"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract and normalize contertulio names')
    parser.add_argument('--extract-uniques', action='store_true', 
                        help='Extract unique contertulios from cbinfo_index.json')
    parser.add_argument('--assisted-normalization', action='store_true',
                        help='Interactively suggest and assign normalized names to aliases using RapidFuzz')
    parser.add_argument('--calculate-alias-scores', action='store_true',
                        help='Calculate and report similarity scores for alias→canonical mappings')
    args = parser.parse_args()
    
    if args.extract_uniques:
        extract_unique_contertulios()
    elif args.assisted_normalization:
        assisted_normalization()
        calculate_alias_scores()
    elif args.calculate_alias_scores:
        calculate_alias_scores()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()