"""
links_retrieval/clean_links.py

Clean and filter episode links based on occurrence counts and excluded domains.

Process:
1. Remove links appearing in >3 episodes automatically.
2. For links in exactly 3 episodes, prompt user (default yes) to remove.
3. For domains in exclusion list, summarize and prompt to remove domain links (default yes).
4. Save cleaned web_parse.json.
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse

from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Confirm

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


def load_json(path: Path):
    if not path.exists():
        logging.critical(f"File not found: {path}")
        sys.exit(1)
    return json.loads(path.read_text(encoding=config.ENCODING))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding=config.ENCODING) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved cleaned JSON to {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Clean parsed episode links by frequency and excluded domains",
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable debug logging')
    parser.add_argument('-c', '--check-domain', type=str, metavar='DOMAIN',
                        help='Fuzzy-search for a specific domain and remove its links')
    args = parser.parse_args()

    setup_logging(args.verbose)
    console = Console()

    web_parse_path = Path(config.DATA_DIR) / 'parsed_json' / 'web_parse.json'
    exclusion_path = Path(__file__).parent / 'links_domain_exclusion_list.json'

    data = load_json(web_parse_path)
    exclusions = load_json(exclusion_path) if exclusion_path.exists() else []

    # optional check for specific domain pattern
    if args.check_domain:
        pattern = args.check_domain.lower()
        matching_links = set()
        for ep, meta in data.items():
            for link in meta.get('ep_links', []):
                dom = urlparse(link).netloc.lower()
                if pattern in dom:
                    matching_links.add(link)
        if matching_links:
            console.print(f"Found {len(matching_links)} links matching domain pattern '{pattern}':")
            for l in sorted(matching_links):
                console.print(f"  - {l}")
            if Confirm.ask(f"Remove all links matching domain pattern '{pattern}'?", default=False):
                logging.info(f"Removing links for pattern '{pattern}'")
                for ep, meta in data.items():
                    meta['ep_links'] = [l for l in meta.get('ep_links', []) if pattern not in urlparse(l).netloc.lower()]
        else:
            console.print(f"No links matching domain pattern '{pattern}' found.")

    # step 3: domain exclusions
    if exclusions:
        # aggregate domain stats
        domain_stats = {dom: {'links': set(), 'eps': set()} for dom in exclusions}
        for ep, meta in data.items():
            for link in meta.get('ep_links', []):
                dom = urlparse(link).netloc.lower()
                if dom in domain_stats:
                    domain_stats[dom]['links'].add(link)
                    domain_stats[dom]['eps'].add(ep)
        for dom, stats in domain_stats.items():
            total_links = len(stats['links'])
            total_eps = len(stats['eps'])
            console.print(f"Domain [bold]{dom}[/]: {total_links} unique links in {total_eps} episodes")
            console.print("Links:")
            for l in sorted(stats['links']):
                console.print(f"  - {l}")
            if Confirm.ask(f"Remove all links from domain {dom}?", default=True):
                logging.info(f"Removing domain links for {dom}")
                # remove any link with this domain
                for ep, meta in data.items():
                    meta['ep_links'] = [l for l in meta.get('ep_links', []) if urlparse(l).netloc.lower() != dom]

    # save cleaned JSON
    save_json(web_parse_path, data)

if __name__ == '__main__':
    main()