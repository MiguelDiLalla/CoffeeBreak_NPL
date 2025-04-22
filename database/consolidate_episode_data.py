#!/usr/bin/env python3
"""
consolidate_episode_data.py - Merge parsed JSON feeds into a master JSON database

This script reads three parsed JSON sources:
  - audiofeed_index.json   (RSS audio feed metadata)
  - cbinfo_index.json      (CBInfo episode topics, timestamps, participants)
  - web_parse.json         (web page links, raw HTML/text content)

It normalizes episode IDs, merges data around canonical RSS episodes,
outputs a master JSON to `database/master_scrapping_data.json`,
and exports per-episode raw description Markdown files to `data/raw_descriptions/`.

Usage:
    python consolidate_episode_data.py [--audio-json PATH] [--cbinfo-json PATH]
        [--web-json PATH] [--output-json PATH] [--raw-desc-dir DIR] [-v|--verbose]

Options:
  --audio-json       Path to audiofeed_index.json
  --cbinfo-json      Path to cbinfo_index.json
  --web-json         Path to web_parse.json
  --output-json      Path for master JSON output
  --raw-desc-dir     Directory for per-episode .md files
  -v, --verbose      Enable DEBUG-level logging

Example:
    python consolidate_episode_data.py --verbose

"""
import argparse
import json
from json import JSONDecodeError
import logging
import re
from pathlib import Path
import sys
# Ensure project root is on sys.path for config import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Any, Dict, List

import config
from rich.logging import RichHandler

# Optional json5 for JSON with comments/trailing commas
try:
    import json5
    _json_load = json5.load
    _json_loads = json5.loads
    HAS_JSON5 = True
except ImportError:
    _json_load = json.load
    _json_loads = json.loads
    HAS_JSON5 = False

# Configure rich logging
logger = logging.getLogger("consolidate_episode_data")
logger.setLevel(logging.DEBUG)
handler = RichHandler(rich_tracebacks=True)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)


def normalize_episode_id(raw_id: str) -> str:
    """
    Normalize episode IDs to form Ep### or Ep###_A/B.
    - Trim whitespace and punctuation
    - Ensure 'Ep' prefix
    - Zero-pad numeric part to 3 digits
    - Upper-case suffix 'A' or 'B' if present

    Args:
        raw_id: raw episode identifier (e.g. 'EP105 ', 'Ep7_A')
    Returns:
        normalized ID (e.g. 'Ep105', 'Ep007_A')
    """
    tid = raw_id.strip().rstrip('. ,;:_-')
    pattern = re.compile(r"(?i)ep\s*0*(\d+)(?:[_\s-]*([AB]))?$")
    m = pattern.match(tid)
    if not m:
        logger.warning(f"Could not normalize episode ID '{raw_id}', using raw value.")
        return tid
    num, cara = m.groups()
    epnum = num.zfill(3)
    result = f"Ep{epnum}"
    if cara:
        result += f"_{cara.upper()}"
    return result


def load_json(path: Path) -> Dict[str, Any]:
    """
    Load a JSON file from the given path, with error handling for invalid JSON.
    Supports lenient parsing via json5 if installed.
    """
    logger.debug(f"Loading JSON from {path} (json5={'enabled' if HAS_JSON5 else 'disabled'})")
    try:
        with path.open('r', encoding=config.ENCODING) as f:
            return _json_load(f)
    except JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON from {path}: {e}")
        logger.info("Attempting to clean comments and trailing commas and retry parsing JSON.")
        original = path.read_text(encoding=config.ENCODING)
        # Remove JavaScript-style comments
        no_comments = re.sub(r'//.*', '', original)
        # Remove trailing commas before } or ]
        cleaned = re.sub(r',(?=\s*[}\]])', '', no_comments)
        try:
            return _json_loads(cleaned)
        except JSONDecodeError as e2:
            logger.error(f"Retry failed, invalid JSON in {path}: {e2}")
            sys.exit(1)


def write_json(data: Any, path: Path) -> None:
    """
    Write Python object as pretty-printed JSON to specified path.
    """
    logger.info(f"Writing master JSON to {path}")
    with path.open('w', encoding=config.ENCODING) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_markdown(ep_id: str, record: Dict[str, Any], out_dir: Path) -> None:
    """
    Generate a Markdown file for one episode.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    # Sanitize ep_id for safe filename (replace invalid Windows filename chars)
    safe_id = re.sub(r'[<>:"/\\|?*]', '_', ep_id)
    md_path = out_dir / f"{safe_id}.md"
    logger.debug(f"Writing Markdown for {ep_id} to {md_path}")
    lines: List[str] = []
    lines.append(f"# {ep_id}  ")
    lines.append(f"**Title:** {record.get('title','')}  ")
    lines.append(f"**Date:** {record.get('date','')}  ")
    lines.append(f"**Duration:** {record.get('duration','')}  ")
    lines.append(f"**Audio URL:** {record.get('audio_url','')}  ")
    lines.append(f"**RSS Link:** {record.get('rss_link','')}  \n")
    for section in [
        ('RSS description', 'rss_description'),
        ('CBInfo raw description', 'cbinfo_raw'),
        ('Web parse content', 'web_raw'),
    ]:
        title, key = section
        lines.append(f"## {title}")
        lines.append(record.get(key, '') + "\n")
    if record.get('timestamps'):
        lines.append("## Timestamps")
        for ts in record['timestamps']:
            lines.append(f"- {ts.get('time','')} – {ts.get('label','')}")
    for sec in ['topics', 'contertulios', 'web_links']:
        if record.get(sec):
            sec_title = sec.replace('_',' ').title()
            lines.append(f"## {sec_title}")
            for item in record[sec]:
                lines.append(f"- {item}")
    md_content = '\n'.join(lines)
    md_path.write_text(md_content, encoding=config.ENCODING)


def main():
    parser = argparse.ArgumentParser(
        description="Consolidate parsed JSON data into master JSON and Markdown files."
    )
    parser.add_argument("--audio-json", type=Path,
                        default=config.PROJECT_ROOT / config.OUTPUT_JSON,
                        help="Path to audiofeed_index.json")
    parser.add_argument("--cbinfo-json", type=Path,
                        default=config.PROJECT_ROOT / "data/parsed_json/cbinfo_index.json",
                        help="Path to cbinfo_index.json")
    parser.add_argument("--web-json", type=Path,
                        default=config.PROJECT_ROOT / "data/parsed_json/web_parse.json",
                        help="Path to web_parse.json")
    parser.add_argument("--output-json", type=Path,
                        default=config.PROJECT_ROOT / "database/master_scrapping_data.json",
                        help="Output path for master JSON")
    parser.add_argument("--raw-desc-dir", type=Path,
                        default=config.PROJECT_ROOT / "data/raw_descriptions",
                        help="Directory for per-episode Markdown files")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable DEBUG logging level")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")
    else:
        logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    # Load inputs
    feed_map = load_json(args.audio_json)
    cb_map_raw = load_json(args.cbinfo_json)
    web_map_raw = load_json(args.web_json)

    master_records: List[Dict[str, Any]] = []

    # Normalize CBInfo map (cbinfo_index.json is a list of episode entries)
    cb_map: Dict[str, Dict[str, Any]] = {}
    for entry in cb_map_raw:
        raw_id = entry.get('episode_id')
        if not raw_id or entry.get('entry_type') != 'episode':
            continue
        nid = normalize_episode_id(raw_id)
        cb_map[nid] = entry

    # Normalize Web map
    web_map: Dict[str, Dict[str, Any]] = {}
    for raw_id, entry in web_map_raw.items():
        nid = normalize_episode_id(entry.get('ep_id', raw_id))
        web_map[nid] = entry

    # Merge around audiofeed episodes
    for base in feed_map:
        raw_id = base.get('episode_id') or base.get('ep_id') or base.get('id') or base.get('guid') or base.get('title', '')
        ep_id = normalize_episode_id(raw_id)
        logger.info(f"Processing episode {ep_id}")
        cb = cb_map.get(ep_id, {})
        web = web_map.get(ep_id, {})

        record: Dict[str, Any] = {
            'episode_id': ep_id,
            'title': base.get('title', ''),
            'date': base.get('date', ''),
            'duration': base.get('duration', ''),
            'audio_url': base.get('audio_url', ''),
            'rss_link': base.get('link', ''),
            'image_url': base.get('image_url', ''),
            'rss_description': base.get('description', ''),
            'topics': cb.get('topics', []),
            'contertulios': cb.get('contertulios', []),
            'timestamps': cb.get('timestamps', []),
            'cbinfo_raw': cb.get('raw_description', ''),
            'web_link': web.get('ep_web_link', ''),
            'web_raw': web.get('ep_text_content', ''),
            'web_links': web.get('ep_links', []),
        }
        master_records.append(record)

    # Write outputs
    write_json(master_records, args.output_json)
    for rec in master_records:
        write_markdown(rec['episode_id'], rec, args.raw_desc_dir)

    logger.info("Consolidation complete.")


if __name__ == '__main__':  # pragma: no cover
    main()
