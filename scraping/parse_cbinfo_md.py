"""
parse_cbinfo_md.py - Parser for cbinfo.md episode metadata (Coffee Break)

Extracts episode structure, contertulios, and topic timestamps from cbinfo.md.
Outputs structured JSON for downstream analysis and DB ingestion.

Usage:
    python parse_cbinfo_md.py [--force] [--dry-run] [--verbose] [--refine-guests] [--help]

Options:
    --force          Force re-parse, even if no changes detected.
    --dry-run        Show what would change, but do not write files.
    --verbose        Enable detailed logging output.
    --refine-guests  Refine contertulios for missing entries using fuzzy search.
    --help           Show this help message and exit.

Author: Miguel Di Lalla (2025)
"""
import os
import sys
import json
import hashlib
import argparse
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple

try:
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from rapidfuzz import fuzz, process

# --- Configurable paths (import from config.py) ---
try:
    from config import ENCODING, LOG_LEVEL
except ImportError:
    ENCODING = "utf-8"
    LOG_LEVEL = "INFO"

CBINFO_MD = os.path.join("data", "cbinfo.md")
CBINFO_JSON = os.path.join("data", "parsed_json", "cbinfo_index.json")

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
    return logging.getLogger("parse_cbinfo_md")

# --- Utility functions ---
def file_hash(path: str, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def is_json_outdated(md_path: str, json_path: str) -> bool:
    if not os.path.exists(json_path):
        return True
    return os.path.getmtime(json_path) < os.path.getmtime(md_path)

# --- Helper functions ---
def parse_contertulios(line: str) -> List[str]:
    """Extract and clean guest list from a line."""
    match = re.search(r"Contertulios: (.+?)(?:\.|$)", line)
    if not match:
        return []
    guest_list = [c.strip().strip('.') for c in match.group(1).split(',') if c.strip()]
    # Remove trailing roles or credits
    guest_list = [re.sub(r"\s*Imagen.*", "", g).strip() for g in guest_list]
    return [g for g in guest_list if g]

def cleanse_guest_list(guest_list):
    """
    Clean and normalize a list of guest names.
    - Remove substrings in parentheses and extra whitespace.
    - Split on ' y ' or ';' if present.
    """
    cleaned = []
    for name in guest_list:
        # Remove substrings in parentheses
        name = re.sub(r"\([^)]*\)", "", name)
        # Split on ' y ' or ';'
        parts = re.split(r"\s+y\s+|;", name)
        for part in parts:
            part = part.strip()
            if part:
                cleaned.append(part)
    return cleaned

def parse_topic_line(line: str) -> Optional[Dict[str, Optional[str]]]:
    """Parse a topic line, extracting title and timestamp if present."""
    # Accepts: -Title (mm:ss), -Title (hh:mm:ss), -Title
    match = re.match(r"^-([^-].*?)(?:\((\d{1,2}:\d{2}(?::\d{2})?)\))?\s*$", line)
    if not match:
        return None
    topic_title = match.group(1).strip()
    timestamp = match.group(2)
    return {"title": topic_title, "timestamp": timestamp}

def detect_entry_type(title: str, desc_lines: List[str]) -> str:
    """Classify entry as 'episode', 'extract', or 'special'."""
    if re.match(r"^Ep\d{3,4}(?:_[AB])?:", title):
        return "episode"
    if any("extracto" in l.lower() or "extract" in l.lower() for l in desc_lines):
        return "extract"
    if "especial" in title.lower():
        return "special"
    return "other"

def parse_episode_block(block_lines: List[str]) -> Dict:
    """Parse a block of lines corresponding to a single entry (episode/extract/special)."""
    title_line = block_lines[0].strip()
    entry_type = detect_entry_type(title_line, block_lines)
    episode_id = None
    cara = None
    topics = []
    contertulios = []
    # Try to extract episode_id
    ep_match = re.match(r"^(Ep\d{3,4}(?:_[AB])?):?", title_line)
    if ep_match:
        episode_id = ep_match.group(1)
    # Try to extract cara
    for l in block_lines:
        cara_match = re.match(r"^Cara ([AB]):?", l.strip())
        if cara_match:
            cara = cara_match.group(1)
            break
    # Parse topics
    for l in block_lines:
        topic = parse_topic_line(l.strip())
        if topic:
            topics.append(topic)
    # Parse contertulios
    for l in block_lines:
        guests = parse_contertulios(l)
        if guests:
            contertulios = guests
            break
    # Detect if multiple timestamps
    has_multiple_timestamps = sum(1 for t in topics if t["timestamp"]) > 1
    return {
        "episode_id": episode_id,
        "title": title_line,
        "cara": cara,
        "topics": topics,
        "contertulios": contertulios,
        "raw_description": "\n".join(block_lines),
        "entry_type": entry_type,
        "has_multiple_timestamps": has_multiple_timestamps
    }

def split_blocks(lines: List[str]) -> List[List[str]]:
    """Split the cbinfo.md into blocks, one per entry (episode/extract/special)."""
    blocks = []
    current = []
    for line in lines:
        if re.match(r"^Ep\d{3,4}(?:_[AB])?:", line.strip()) and current:
            blocks.append(current)
            current = [line.rstrip("\n")]
        else:
            current.append(line.rstrip("\n"))
    if current:
        blocks.append(current)
    return blocks

# --- Parsing logic (refactored) ---
def parse_cbinfo_md(md_path: str) -> List[Dict]:
    """
    Parse cbinfo.md and return a list of structured entries (episodes, extracts, specials).
    """
    with open(md_path, "r", encoding=ENCODING) as f:
        lines = f.readlines()
    blocks = split_blocks(lines)
    entries = []
    for block in blocks:
        entry = parse_episode_block(block)
        entries.append(entry)
    return entries

def refine_guests_with_fuzzy_search(entries, logger, dry_run=False):
    """
    Refine contertulios for entries with empty guest lists using fuzzy search on raw_description.
    Args:
        entries (list): List of episode dicts.
        logger (logging.Logger): Logger for reporting changes.
        dry_run (bool): If True, do not write changes.
    Returns:
        int: Number of entries updated.
    """
    updated = 0
    for entry in entries:
        if entry.get("contertulios"):
            continue
        raw_desc = entry.get("raw_description", "")
        lines = raw_desc.split("\n")
        best_score = 0
        best_line = None
        # Search for best fuzzy match to 'contertulios' or 'Héctor Socas.'
        for line in lines:
            score1 = fuzz.partial_ratio(line.lower(), "contertulios")
            score2 = fuzz.partial_ratio(line.lower(), "héctor socas.")
            score = max(score1, score2)
            if score > best_score:
                best_score = score
                best_line = line
        if best_score >= 80 and best_line:
            # Try to extract guests from the best line
            guests = parse_contertulios(best_line)
            if not guests:
                # Try fallback: extract names from photo credits (common pattern)
                match = re.search(r"(?:en la foto|en la imagen)[^:]*:([^\.]+)", best_line, re.IGNORECASE)
                if match:
                    guests = [g.strip().strip('.') for g in match.group(1).split(',') if g.strip()]
            if guests:
                guests = cleanse_guest_list(guests)
                logger.info(f"[REFINE] {entry.get('episode_id') or entry.get('title')}: guests set to {guests}")
                if not dry_run:
                    entry["contertulios"] = guests
                updated += 1
    return updated

# --- Main pipeline ---
def main(force=False, dry_run=False, verbose=False, refine_guests=False):
    logger = setup_logger(verbose)
    logger.info("☕ Coffee Break cbinfo.md Parser")
    logger.info(f"Source: {CBINFO_MD}")
    logger.info(f"Output JSON: {CBINFO_JSON}")
    # Step 1: Check for changes
    md_exists = os.path.exists(CBINFO_MD)
    if not md_exists:
        logger.error(f"cbinfo.md not found: {CBINFO_MD}")
        sys.exit(1)
    md_hash = file_hash(CBINFO_MD)
    logger.debug(f"cbinfo.md hash: {md_hash}")
    json_exists = os.path.exists(CBINFO_JSON)
    need_parse = force or not json_exists or is_json_outdated(CBINFO_MD, CBINFO_JSON)
    if not need_parse and not refine_guests:
        logger.info("JSON index is up to date. No parsing needed.")
        logger.info("✅ Pipeline complete.")
        return
    # Step 2: Parse cbinfo.md
    if need_parse:
        logger.info("Parsing cbinfo.md to JSON index...")
        episodes = parse_cbinfo_md(CBINFO_MD)
        if dry_run:
            logger.info(f"[DRY RUN] Would write {len(episodes)} episodes to JSON: {CBINFO_JSON}")
        else:
            os.makedirs(os.path.dirname(CBINFO_JSON), exist_ok=True)
            with open(CBINFO_JSON, "w", encoding=ENCODING) as f:
                json.dump(episodes, f, indent=2, ensure_ascii=False)
            logger.info(f"Wrote {len(episodes)} episodes to JSON: {CBINFO_JSON}")
        # Prompt for immediate refinement if --force is used
        if force:
            try:
                user_input = input("Run --refine-guests now? [Enter=Yes, q=Quit]: ").strip().lower()
            except EOFError:
                user_input = 'q'
            if user_input != 'q':
                logger.info("Proceeding with guest refinement...")
                refine_guests = True
            else:
                logger.info("Guest refinement skipped by user.")
    else:
        # Load existing JSON for refinement
        with open(CBINFO_JSON, "r", encoding=ENCODING) as f:
            episodes = json.load(f)
    # Step 3: Refine guests if requested
    if refine_guests:
        logger.info("Refining contertulios using fuzzy search...")
        updated = refine_guests_with_fuzzy_search(episodes, logger, dry_run=dry_run)
        if updated:
            logger.info(f"Refined guests in {updated} entries.")
            if not dry_run:
                with open(CBINFO_JSON, "w", encoding=ENCODING) as f:
                    json.dump(episodes, f, indent=2, ensure_ascii=False)
                logger.info(f"Updated JSON written: {CBINFO_JSON}")
        else:
            logger.info("No entries required guest refinement.")
    logger.info("✅ Pipeline complete.")

# --- CLI entrypoint ---
def cli():
    parser = argparse.ArgumentParser(
        description="Parse cbinfo.md to structured JSON for Coffee Break episodes.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Pipeline steps:
  1. Check if cbinfo.md changed (by hash or mtime).
  2. Parse cbinfo.md to JSON if needed.
  3. Optionally refine contertulios using fuzzy search.
  4. Log/report all actions and changes.

Examples:
  python parse_cbinfo_md.py --dry-run
  python parse_cbinfo_md.py --force --verbose
  python parse_cbinfo_md.py --refine-guests --verbose
        """
    )
    parser.add_argument("--force", action="store_true", help="Force re-parse, even if no changes detected.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change, but do not write files.")
    parser.add_argument("--verbose", action="store_true", help="Enable detailed logging output.")
    parser.add_argument("--refine-guests", action="store_true", help="Refine contertulios for missing entries using fuzzy search.")
    args = parser.parse_args()
    main(force=args.force, dry_run=args.dry_run, verbose=args.verbose, refine_guests=args.refine_guests)

if __name__ == "__main__":
    cli()
