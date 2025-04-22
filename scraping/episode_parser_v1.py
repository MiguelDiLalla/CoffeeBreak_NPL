"""
scraping/episode_parser_v1.py

Parse raw HTML episodes and extract metadata into a JSON index.
"""
import argparse
import json
import logging
import sys
import re
from pathlib import Path

# add project root to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from rich.logging import RichHandler

import config


def setup_logging(level: int) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )


def parse_episode(html_path: Path) -> dict:
    """
    Parse a single episode HTML file and extract metadata.

    Returns:
        dict: {ep_id, ep_title, ep_web_link, ep_text_content, ep_links}
    """
    text = html_path.read_text(encoding=config.ENCODING)
    soup = BeautifulSoup(text, "lxml")

    ep_id = html_path.stem  # e.g. 'Ep506'

    title_tag = soup.select_one("h1.entry-title")
    ep_title = title_tag.text.strip() if title_tag else ''

    canonical_tag = soup.find("link", rel="canonical")
    ep_web_link = canonical_tag['href'] if canonical_tag and canonical_tag.has_attr('href') else ''

    content_div = soup.select_one("div.entry-content")
    if content_div:
        # flatten text: replace tags and line breaks with spaces, collapse whitespace
        raw_text = content_div.get_text(separator=" ")
        ep_text_content = re.sub(r"\s+", " ", raw_text).strip()
        # collect links from <a> tags
        a_links = [a['href'] for a in content_div.find_all("a", href=True)]
        # extract plaintext http(s) links
        text_links = re.findall(r"https?://[^\s'\"<>]+", ep_text_content)
        # dedupe preserving order
        seen = set()
        ep_links = []
        for link in a_links + text_links:
            if link not in seen:
                seen.add(link)
                ep_links.append(link)
    else:
        ep_text_content = ''
        ep_links = []

    return {
        'ep_id': ep_id,
        'ep_title': ep_title,
        'ep_web_link': ep_web_link,
        'ep_text_content': ep_text_content,
        'ep_links': ep_links,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse Coffee Break raw HTML episodes into structured JSON."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "-o", "--output", type=str,
        help="Output JSON file (default: data/parsed_json/web_parse.json)"
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level)

    episodes_dir = Path(config.DATA_DIR) / "raw_html" / "episodes"
    output_file = Path(args.output) if args.output else Path(config.DATA_DIR) / "parsed_json" / "web_parse.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    parsed = {}
    for html_file in sorted(episodes_dir.glob('*.html')):
        try:
            meta = parse_episode(html_file)
            parsed[meta['ep_id']] = meta
            logging.info(f"Parsed {meta['ep_id']}")
        except Exception as e:
            logging.error(f"Error parsing {html_file.name}: {e}")

    with output_file.open('w', encoding=config.ENCODING) as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)
    logging.info(f"Written parsed data to {output_file}")


if __name__ == "__main__":
    main()
