"""
config.py - Centralized configuration for CoffeeBreak_NPL project

This module defines all key paths and settings for scraping, parsing, and analysis pipelines.
Import this module to avoid hardcoding and to enable scalable, testable code.
"""
import os
from pathlib import Path

# --- Directory Settings ---

#: Project root directory (absolute path)
PROJECT_ROOT = Path(__file__).parent.absolute()

#: Data directory (absolute path)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# --- RSS Feed Scraper/Parser Settings ---

#: Remote RSS feed URL for Coffee Break podcast
FEED_URL = "https://feeds.feedburner.com/PodcastCoffeeBreak"

#: Local path for downloaded RSS XML (relative to project root)
FEED_PATH = os.path.join("data", "rss", "audiofeedcoffeebreak.xml")

#: Local path for parsed JSON index (relative to project root)
OUTPUT_JSON = os.path.join("data", "parsed_json", "audiofeed_index.json")

#: HTTP request timeout in seconds
TIMEOUT = 30

#: Hash algorithm for change detection
HASH_ALGO = "sha256"

#: Default logging level ("INFO", "DEBUG", etc.)
LOG_LEVEL = "INFO"

#: Custom User-Agent for HTTP requests (optional)
USER_AGENT = "CoffeeBreakNPL/1.0"

#: Number of retries for failed downloads (optional)
RETRY_COUNT = 3

#: Default encoding for file operations
ENCODING = "utf-8"

# --- Add more config variables as needed for other modules ---
