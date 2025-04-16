#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cbinfo_validate.py - Validation script for analyzing CoffeeBreak podcast metadata

This script analyzes the cbinfo_index.json file to report on:
- How many episodes have contertulios (guests) data
- How many episodes have timestamps data
- Complete list of all stored contertulios

The results are saved to a markdown file for easy sharing and persistence.
"""

import json
import os
import sys
import argparse
from collections import Counter
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Any, Tuple, Counter as CounterType

from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich.panel import Panel
from rich import box

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR

# Initialize Rich console
console = Console()

def load_cbinfo_data(file_path: str = None) -> List[Dict[str, Any]]:
    """
    Load the cbinfo_index.json data
    
    Args:
        file_path: Optional custom path to the JSON file
        
    Returns:
        List of episode data dictionaries
    """
    if not file_path:
        file_path = os.path.join(DATA_DIR, "parsed_json", "cbinfo_index.json")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        console.print(f"[bold red]Error:[/bold red] Invalid JSON in file: {file_path}")
        sys.exit(1)

def analyze_episodes(episodes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze the episodes data to extract completion metrics
    
    Args:
        episodes_data: List of episode data dictionaries
        
    Returns:
        Dictionary with analysis results
    """
    results = {
        "total_episodes": 0,
        "episodes_with_contertulios": 0,
        "episodes_with_timestamps": 0,
        "entry_types": Counter(),
        "contertulios_set": set(),
        "contertulios_count": Counter(),
        "timestamps_by_entry_type": {},
        "contertulios_by_entry_type": {},
    }
    
    # Filter out non-episode entries
    episodes = [ep for ep in episodes_data if ep.get("entry_type") == "episode"]
    results["total_episodes"] = len(episodes)
    
    # Count entry types
    for episode in episodes_data:
        entry_type = episode.get("entry_type", "unknown")
        results["entry_types"][entry_type] += 1
    
    for episode in track(episodes, description="Analyzing episodes"):
        # Count episodes with contertulios
        contertulios = episode.get("contertulios", [])
        if contertulios and len(contertulios) > 0:
            results["episodes_with_contertulios"] += 1
            
            # Add to unique contertulios set
            for contertulio in contertulios:
                results["contertulios_set"].add(contertulio)
                results["contertulios_count"][contertulio] += 1
        
        # Count episodes with timestamps
        has_timestamps = episode.get("has_multiple_timestamps", False)
        if has_timestamps:
            results["episodes_with_timestamps"] += 1
        
        # Organize by entry type
        entry_type = episode.get("entry_type", "unknown")
        if entry_type not in results["timestamps_by_entry_type"]:
            results["timestamps_by_entry_type"][entry_type] = {"total": 0, "with_timestamps": 0}
            results["contertulios_by_entry_type"][entry_type] = {"total": 0, "with_contertulios": 0}
        
        results["timestamps_by_entry_type"][entry_type]["total"] += 1
        results["contertulios_by_entry_type"][entry_type]["total"] += 1
        
        if has_timestamps:
            results["timestamps_by_entry_type"][entry_type]["with_timestamps"] += 1
        
        if contertulios and len(contertulios) > 0:
            results["contertulios_by_entry_type"][entry_type]["with_contertulios"] += 1
    
    return results

def generate_results_markdown(results: Dict[str, Any], output_path: str = None) -> None:
    """
    Generate a markdown file with the analysis results
    
    Args:
        results: Dictionary with analysis results
        output_path: Path to save the markdown file (defaults to DATA_DIR/cbinfo-validations.md)
    """
    if not output_path:
        output_path = os.path.join(DATA_DIR, "cbinfo-validations.md")
    
    # Create markdown content
    md_content = []
    
    # Add header with timestamp
    md_content.append("# CoffeeBreak Metadata Validation Report")
    md_content.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    md_content.append("")
    
    # Summary section
    md_content.append("## Summary")
    md_content.append("")
    md_content.append(f"- **Total Episodes**: {results['total_episodes']}")
    
    contertulios_ratio = results['episodes_with_contertulios'] / results['total_episodes'] * 100 if results['total_episodes'] > 0 else 0
    md_content.append(f"- **Episodes with Contertulios**: {results['episodes_with_contertulios']}/{results['total_episodes']} ({contertulios_ratio:.1f}%)")
    
    timestamps_ratio = results['episodes_with_timestamps'] / results['total_episodes'] * 100 if results['total_episodes'] > 0 else 0
    md_content.append(f"- **Episodes with Timestamps**: {results['episodes_with_timestamps']}/{results['total_episodes']} ({timestamps_ratio:.1f}%)")
    md_content.append(f"- **Unique Contertulios**: {len(results['contertulios_set'])}")
    md_content.append("")
    
    # Entry types breakdown
    md_content.append("## Entry Types Breakdown")
    md_content.append("")
    md_content.append("| Entry Type | Count | Percentage |")
    md_content.append("| --- | ---: | ---: |")
    
    total_entries = sum(results['entry_types'].values())
    for entry_type, count in results['entry_types'].most_common():
        percentage = (count / total_entries * 100) if total_entries > 0 else 0
        md_content.append(f"| {entry_type} | {count} | {percentage:.1f}% |")
    md_content.append("")
    
    # Detailed breakdown by entry type
    md_content.append("## Detailed Breakdown by Entry Type")
    md_content.append("")
    
    for entry_type, data in results["timestamps_by_entry_type"].items():
        if data["total"] == 0:
            continue
            
        md_content.append(f"### {entry_type.capitalize()}")
        md_content.append("")
        md_content.append("| Metric | Value | Percentage |")
        md_content.append("| --- | ---: | ---: |")
        
        timestamps_ratio = (data["with_timestamps"] / data["total"] * 100) if data["total"] > 0 else 0
        contertulios_data = results["contertulios_by_entry_type"].get(entry_type, {"total": 0, "with_contertulios": 0})
        contertulios_ratio = (contertulios_data["with_contertulios"] / contertulios_data["total"] * 100) if contertulios_data["total"] > 0 else 0
        
        md_content.append(f"| Total | {data['total']} | 100% |")
        md_content.append(f"| With Timestamps | {data['with_timestamps']} | {timestamps_ratio:.1f}% |")
        md_content.append(f"| With Contertulios | {contertulios_data['with_contertulios']} | {contertulios_ratio:.1f}% |")
        md_content.append("")
    
    # Contertulios list
    md_content.append("## Contertulios List")
    md_content.append("")
    md_content.append("| Name | Appearances |")
    md_content.append("| --- | ---: |")
    
    for name, count in results["contertulios_count"].most_common():
        md_content.append(f"| {name} | {count} |")
    
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))
    
    return output_path

def print_results(results: Dict[str, Any], detailed: bool = False) -> None:
    """
    Print the analysis results using Rich formatting
    
    Args:
        results: Dictionary with analysis results
        detailed: Whether to show detailed output
    """
    # Summary panel
    summary = Table.grid()
    summary.add_column()
    summary.add_column()
    
    summary.add_row("Total Episodes:", f"[yellow]{results['total_episodes']}[/yellow]")
    
    contertulios_ratio = results['episodes_with_contertulios'] / results['total_episodes'] * 100 if results['total_episodes'] > 0 else 0
    summary.add_row(
        "Episodes with Contertulios:",
        f"[green]{results['episodes_with_contertulios']}[/green]/[yellow]{results['total_episodes']}[/yellow] " +
        f"([cyan]{contertulios_ratio:.1f}%[/cyan])"
    )
    
    timestamps_ratio = results['episodes_with_timestamps'] / results['total_episodes'] * 100 if results['total_episodes'] > 0 else 0
    summary.add_row(
        "Episodes with Timestamps:",
        f"[green]{results['episodes_with_timestamps']}[/green]/[yellow]{results['total_episodes']}[/yellow] " +
        f"([cyan]{timestamps_ratio:.1f}%[/cyan])"
    )
    
    summary.add_row("Unique Contertulios:", f"[green]{len(results['contertulios_set'])}[/green]")
    
    console.print(Panel(summary, title="CoffeeBreak Metadata Summary", border_style="blue"))
    
    # Entry types breakdown
    entry_table = Table(title="Entry Types Breakdown", box=box.SIMPLE)
    entry_table.add_column("Entry Type", style="cyan")
    entry_table.add_column("Count", justify="right", style="yellow")
    entry_table.add_column("Percentage", justify="right", style="green")
    
    total_entries = sum(results['entry_types'].values())
    for entry_type, count in results['entry_types'].most_common():
        percentage = (count / total_entries * 100) if total_entries > 0 else 0
        entry_table.add_row(entry_type, str(count), f"{percentage:.1f}%")
    
    console.print(entry_table)
    
    # Contertulios list
    contertulios_table = Table(title="Contertulios List", box=box.SIMPLE)
    contertulios_table.add_column("Name", style="cyan")
    contertulios_table.add_column("Appearances", justify="right", style="yellow")
    
    for name, count in results['contertulios_count'].most_common():
        contertulios_table.add_row(name, str(count))
    
    console.print(contertulios_table)
    
    if detailed:
        # Entry type detailed breakdown
        console.print("\n[bold blue]Detailed Breakdown by Entry Type[/bold blue]")
        
        for entry_type, data in results["timestamps_by_entry_type"].items():
            if data["total"] == 0:
                continue
                
            detail_table = Table(title=f"Entry Type: {entry_type}", box=box.SIMPLE)
            detail_table.add_column("Metric")
            detail_table.add_column("Value", justify="right")
            detail_table.add_column("Percentage", justify="right")
            
            timestamps_ratio = (data["with_timestamps"] / data["total"] * 100) if data["total"] > 0 else 0
            contertulios_data = results["contertulios_by_entry_type"].get(entry_type, {"total": 0, "with_contertulios": 0})
            contertulios_ratio = (contertulios_data["with_contertulios"] / contertulios_data["total"] * 100) if contertulios_data["total"] > 0 else 0
            
            detail_table.add_row("Total", str(data["total"]), "100%")
            detail_table.add_row("With Timestamps", str(data["with_timestamps"]), f"{timestamps_ratio:.1f}%")
            detail_table.add_row("With Contertulios", str(contertulios_data["with_contertulios"]), f"{contertulios_ratio:.1f}%")
            
            console.print(detail_table)

def get_cli_args() -> argparse.Namespace:
    """Process command line arguments"""
    parser = argparse.ArgumentParser(
        description="Analyze and report on CoffeeBreak podcast metadata from cbinfo_index.json"
    )
    parser.add_argument(
        '-f', '--file', 
        help='Custom path to cbinfo_index.json file',
        default=None
    )
    parser.add_argument(
        '-d', '--detailed',
        help='Show detailed breakdown by entry type',
        action='store_true'
    )
    parser.add_argument(
        '-o', '--output',
        help='Path for the output markdown file (default: DATA_DIR/cbinfo-validations.md)',
        default=None
    )
    parser.add_argument(
        '-q', '--quiet',
        help='Suppress console output, only generate markdown file',
        action='store_true'
    )
    return parser.parse_args()

def main() -> None:
    """Main function"""
    args = get_cli_args()
    
    if not args.quiet:
        console.print(
            Panel.fit(
                "[bold]CoffeeBreak Metadata Validator[/bold]",
                subtitle="Analyzing podcast metadata completion ratios",
                border_style="blue"
            )
        )
    
    file_path = args.file
    if not args.quiet:
        console.print(f"Loading data from [cyan]{file_path if file_path else 'default location'}[/cyan]...")
    
    episodes_data = load_cbinfo_data(file_path)
    if not args.quiet:
        console.print(f"Loaded [green]{len(episodes_data)}[/green] entries")
    
    results = analyze_episodes(episodes_data)
    
    # Generate markdown file
    output_path = generate_results_markdown(results, args.output)
    if not args.quiet:
        console.print(f"Results saved to [cyan]{output_path}[/cyan]")
    
    # Display results in console if not in quiet mode
    if not args.quiet:
        print_results(results, detailed=args.detailed)

if __name__ == "__main__":
    main()