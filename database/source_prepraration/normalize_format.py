"""
normalize_format.py - Module to normalize web_parse.json to list format

This module loads the web_parse.json file (a dict keyed by episode IDs),
converts it into a list of episode metadata dicts, and saves it back.
Supports CLI execution and importable use. Uses rich logging for visibility.
"""
import argparse
import json
import logging
from pathlib import Path
import sys  # needed to adjust module path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # add project root to PYTHONPATH

from rich.logging import RichHandler

import config


def normalize_web_parse(input_path: Path, output_path: Path) -> None:
    """
    Convert web_parse.json from a dict keyed by ep_id to a list of entry dicts.

    Parameters:
        input_path: Path to the original web_parse.json file.
        output_path: Path where the normalized JSON list will be written.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Loading web parse data from {input_path}")
    with input_path.open("r", encoding=config.ENCODING) as f:
        data = json.load(f)
    if isinstance(data, dict):
        entries = list(data.values())
        logger.debug(f"Converted {len(entries)} entries from dict to list")
    else:
        logger.warning("Input JSON is not a dict; no conversion applied.")
        entries = data
    logger.info(f"Writing normalized data to {output_path}")
    with output_path.open("w", encoding=config.ENCODING) as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    logger.info("Normalization complete.")


def main() -> None:
    """CLI entry point for normalize_format script."""
    parser = argparse.ArgumentParser(
        description="Normalize web_parse.json to a list of episode entries"
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=config.PROJECT_ROOT / "data" / "parsed_json" / "web_parse.json",
        help="Path to input web_parse.json",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=config.PROJECT_ROOT / "data" / "parsed_json" / "web_parse.json",
        help="Path to output normalized JSON",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    normalize_web_parse(args.input, args.output)


if __name__ == "__main__":
    main()
