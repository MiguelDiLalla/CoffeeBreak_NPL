"""
links_retrieval/create_exclusion_list.py

Interactively build a JSON list of domains to exclude from link retrieval.

Loads the parsed episodes JSON index, aggregates all unique HTTP(s) links by domain,
and prompts the user to include domains in an exclusion list for future filtering.

Usage:
    python links_retrieval/create_exclusion_list.py [--verbose]

Outputs:
    links_retrieval/links_domain_exclusion_list.json
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich.logging import RichHandler

# ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
import config


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


def load_parsed_json(path: Path) -> dict:
    """Load the parsed episodes JSON index."""
    if not path.exists():
        logging.critical(f"Parsed JSON not found: {path}")
        sys.exit(1)
    with path.open(encoding=config.ENCODING) as f:
        return json.load(f)


def load_existing_exclusions(path: Path) -> list[str]:
    """Load existing exclusion list or return empty if none."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding=config.ENCODING))
        except Exception as e:
            logging.error(f"Error reading existing exclusion list: {e}")
    return []


def save_exclusions(path: Path, domains: list[str]) -> None:
    """Save the exclusion domains list to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding=config.ENCODING) as f:
        json.dump(domains, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(domains)} excluded domains to {path}")


def aggregate_domains(parsed: dict) -> dict[str, set[str]]:
    """Aggregate unique links by domain."""
    domain_links: dict[str, set[str]] = {}
    for epid, meta in parsed.items():
        for link in meta.get('ep_links', []):
            try:
                domain = urlparse(link).netloc.lower()
            except Exception:
                continue
            domain_links.setdefault(domain, set()).add(link)
    return domain_links


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactively create domain exclusion list from web-parse JSON."
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable debug logging'
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    console = Console()

    # Paths
    parsed_path = Path(config.DATA_DIR) / 'parsed_json' / 'web_parse.json'
    exclude_path = Path(__file__).parent / 'links_domain_exclusion_list.json'

    # Load data
    parsed = load_parsed_json(parsed_path)
    existing = load_existing_exclusions(exclude_path)
    domain_links = aggregate_domains(parsed)

    # Build sorted list by count descending
    domains_sorted = sorted(
        domain_links.items(), key=lambda item: len(item[1]), reverse=True
    )

    console.print(f"Found [bold]{len(domains_sorted)}[/bold] domains in parsed JSON.")
    new_exclusions = existing.copy()

    table = Table(title="Domain Link Counts")
    table.add_column("Domain", style="cyan")
    table.add_column("# Links", style="magenta")
    table.add_column("Excluded?", style="red")

    for domain, links in domains_sorted:
        excluded = domain in existing
        table.add_row(domain, str(len(links)), 'yes' if excluded else 'no')
    console.print(table)

    # Interactive prompt
    for domain, links in domains_sorted:
        if domain in existing:
            continue
        prompt = f"Exclude domain '{domain}' with {len(links)} links?"
        if Confirm.ask(prompt, default=False):
            logging.info(f"Excluding domain: {domain}")
            new_exclusions.append(domain)

    # Deduplicate and sort
    final = sorted(set(new_exclusions))
    save_exclusions(exclude_path, final)

    # Final report
    console.rule("Summary")
    console.print(f"Total domains processed: [bold]{len(domains_sorted)}[/bold]")
    console.print(f"New exclusions added: [bold]{len(final) - len(existing)}[/bold]")
    console.print(f"Total excluded domains: [bold]{len(final)}[/bold]")


if __name__ == '__main__':
    main()
