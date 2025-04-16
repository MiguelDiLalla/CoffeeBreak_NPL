"""
parse_audiofeed.py - Robust RSS feed updater and parser for Coffee Break podcast

This script checks for updates from the remote RSS feed, compares with the local XML,
updates only if necessary, and parses to JSON only if needed. It provides a rich CLI
with logging, dry-run, force, and verbose options.

Usage:
    python parse_audiofeed.py [--force] [--dry-run] [--verbose] [--help]

Options:
    --force      Force re-download and re-parse, even if no changes detected.
    --dry-run    Show what would change, but do not write files.
    --verbose    Enable detailed logging output.
    --help       Show this help message and exit.

Pipeline:
    1. Download remote RSS feed.
    2. Compare with local XML (by hash).
    3. Overwrite local XML only if changed (or --force).
    4. Parse XML to JSON only if XML changed or JSON missing/outdated.
    5. Log/report all actions and changes.

Requirements:
    - requests
    - rich (optional, for pretty logging)

Author: Miguel Di Lalla (2025)
"""
import os
import sys
import json
import hashlib
import argparse
import logging
from datetime import datetime
from xml.etree import ElementTree as ET

try:
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import requests
except ImportError:
    print("[ERROR] 'requests' is required. Install with: pip install requests")
    sys.exit(1)

# --- Configurable paths (import from config.py) ---
try:
    from config import FEED_URL, FEED_PATH, OUTPUT_JSON, TIMEOUT, HASH_ALGO, LOG_LEVEL, USER_AGENT, RETRY_COUNT, ENCODING
except ImportError:
    # Fallback defaults if config.py is missing or incomplete
    FEED_URL = "https://feeds.feedburner.com/PodcastCoffeeBreak"
    FEED_PATH = os.path.join("data", "rss", "audiofeedcoffeebreak.xml")
    OUTPUT_JSON = os.path.join("data", "parsed_json", "audiofeed_index.json")
    TIMEOUT = 30
    HASH_ALGO = "sha256"
    LOG_LEVEL = "INFO"
    USER_AGENT = "CoffeeBreakNPL/1.0"
    RETRY_COUNT = 3
    ENCODING = "utf-8"

# --- Logging setup ---
def setup_logger(verbose: bool = False):
    level = logging.DEBUG if verbose else getattr(logging, LOG_LEVEL, logging.INFO)
    handlers = [RichHandler(rich_tracebacks=True)] if RICH_AVAILABLE else None
    logging.basicConfig(
        level=level,
        format="%(message)s" if RICH_AVAILABLE else "[%(levelname)s] %(message)s",
        handlers=handlers,
        force=True,
    )
    return logging.getLogger("parse_audiofeed")

# --- Utility functions ---
def file_hash(path: str, algo: str = None) -> str:
    """Compute hash of a file (for change detection)."""
    h = hashlib.new(algo or HASH_ALGO)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def content_hash(content: bytes, algo: str = None) -> str:
    h = hashlib.new(algo or HASH_ALGO)
    h.update(content)
    return h.hexdigest()

def download_feed(url: str) -> bytes:
    """Download remote RSS feed as bytes, with retries and custom User-Agent."""
    headers = {"User-Agent": USER_AGENT}
    last_exc = None
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            resp = requests.get(url, timeout=TIMEOUT, headers=headers)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            last_exc = exc
            if attempt < RETRY_COUNT:
                continue
            else:
                raise last_exc

def is_json_outdated(xml_path: str, json_path: str) -> bool:
    """Check if JSON is missing or older than XML."""
    if not os.path.exists(json_path):
        return True
    return os.path.getmtime(json_path) < os.path.getmtime(xml_path)

# --- Parsing logic ---
def parse_rss_to_json(xml_path):
    """Parse RSS XML to structured JSON episode list, including episode image URLs with fallback."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    ns = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
    items = root.findall("channel/item")

    # Fallback: get channel-level image (prefer itunes:image, else <image><url>)
    channel_image_url = None
    itunes_image = root.find("channel/itunes:image", ns)
    if itunes_image is not None and 'href' in itunes_image.attrib:
        channel_image_url = itunes_image.attrib['href']
    else:
        image_tag = root.find("channel/image/url")
        if image_tag is not None and image_tag.text:
            channel_image_url = image_tag.text.strip()

    episodes = []
    for item in items:
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="")
        pub_date = item.findtext("pubDate", default="")
        description = item.findtext("description", default="").strip()
        duration = item.findtext("itunes:duration", namespaces=ns)
        audio_url = item.find("enclosure").attrib.get("url") if item.find("enclosure") is not None else None
        # Detect episode_id from title (e.g. 'Ep505_A', 'Ep203')
        episode_id = None
        for word in title.split():
            if word.startswith("Ep"):
                episode_id = word.strip(":-_;")
                break
        # Extract episode image (prefer item-level itunes:image, fallback to channel)
        image_url = channel_image_url
        item_image = item.find("itunes:image", ns)
        if item_image is not None and 'href' in item_image.attrib:
            image_url = item_image.attrib['href']
        episodes.append({
            "episode_id": episode_id,
            "title": title,
            "date": pub_date,
            "duration": duration,
            "description": description,
            "audio_url": audio_url,
            "link": link,
            "image_url": image_url
        })
    return episodes

# --- Main pipeline ---
def main(force=False, dry_run=False, verbose=False):
    logger = setup_logger(verbose)
    logger.info("☕ Coffee Break Podcast RSS Updater")
    logger.info(f"Remote feed: {FEED_URL}")
    logger.info(f"Local XML:  {FEED_PATH}")
    logger.info(f"Output JSON: {OUTPUT_JSON}")
    # Step 1: Download remote feed
    try:
        remote_content = download_feed(FEED_URL)
        remote_hash = content_hash(remote_content)
        logger.debug(f"Remote feed hash: {remote_hash}")
    except Exception as e:
        logger.error(f"Failed to download remote feed: {e}")
        sys.exit(1)
    # Step 2: Compare with local XML
    xml_exists = os.path.exists(FEED_PATH)
    xml_changed = True
    if xml_exists:
        local_hash = file_hash(FEED_PATH)
        logger.debug(f"Local XML hash:  {local_hash}")
        if local_hash == remote_hash and not force:
            xml_changed = False
            logger.info("No changes detected in remote feed (hash match).")
        else:
            logger.info("Remote feed has changed (or --force set). Will update local XML.")
    else:
        logger.info("Local XML does not exist. Will create it.")
    # Step 3: Overwrite local XML if changed
    if xml_changed or force:
        if dry_run:
            logger.info("[DRY RUN] Would overwrite local XML with new feed.")
        else:
            os.makedirs(os.path.dirname(FEED_PATH), exist_ok=True)
            with open(FEED_PATH, "wb") as f:
                f.write(remote_content)
            logger.info(f"Local XML updated: {FEED_PATH}")
    # Step 4: Parse XML to JSON if needed
    need_parse = xml_changed or not os.path.exists(OUTPUT_JSON) or is_json_outdated(FEED_PATH, OUTPUT_JSON) or force
    if need_parse:
        logger.info("Parsing RSS XML to JSON index...")
        episodes = parse_rss_to_json(FEED_PATH)
        if dry_run:
            logger.info(f"[DRY RUN] Would write {len(episodes)} episodes to JSON: {OUTPUT_JSON}")
        else:
            os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
            with open(OUTPUT_JSON, "w", encoding=ENCODING) as f:
                json.dump(episodes, f, indent=2, ensure_ascii=False)
            logger.info(f"Wrote {len(episodes)} episodes to JSON: {OUTPUT_JSON}")
    else:
        logger.info("JSON index is up to date. No parsing needed.")
    logger.info("✅ Pipeline complete.")

# --- CLI entrypoint ---
def cli():
    parser = argparse.ArgumentParser(
        description="Update and parse Coffee Break podcast RSS feed efficiently.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Pipeline steps:
  1. Download remote RSS feed and compare with local XML (by hash).
  2. Overwrite local XML only if changed (or --force).
  3. Parse XML to JSON only if XML changed or JSON missing/outdated.
  4. Log/report all actions and changes.

Examples:
  python parse_audiofeed.py --dry-run
  python parse_audiofeed.py --force --verbose
        """
    )
    parser.add_argument("--force", action="store_true", help="Force re-download and re-parse, even if no changes detected.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change, but do not write files.")
    parser.add_argument("--verbose", action="store_true", help="Enable detailed logging output.")
    args = parser.parse_args()
    main(force=args.force, dry_run=args.dry_run, verbose=args.verbose)

if __name__ == "__main__":
    cli()
