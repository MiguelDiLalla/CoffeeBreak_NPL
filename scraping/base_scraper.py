"""
scraping/base_scraper.py

Module to scrape Coffee Break episodes HTML from category pages and save raw HTML for parsing.
"""
import sys
from pathlib import Path
# ensure project root is in sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import logging
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from rich.logging import RichHandler
import re

import config


def setup_logging(level):
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )


def scrape_category(base_url: str, output_dir: Path, timeout: int, retries: int):
    page = 1
    while True:
        url = base_url if page == 1 else f"{base_url}&paged={page}"
        logging.info(f"Parsing page {page}: {url}")
        try:
            resp = requests.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=timeout)
            resp.raise_for_status()
        except Exception as e:
            logging.error(f"Failed to fetch page {page}: {e}")
            break

        soup = BeautifulSoup(resp.text, "lxml")
        articles = soup.find_all("article", class_="post")
        if not articles:
            logging.info(f"No articles on page {page}, last reached.")
            break

        for art in articles:
            link_tag = art.select_one("h2.entry-title > a")
            if not link_tag:
                logging.warning("Article without link found, skipping.")
                continue
            link = link_tag["href"]
            title = link_tag.text.strip()
            # derive filename base from title
            if title.lower().startswith("ep"):
                # extract 'Ep' followed by digits
                m = re.match(r"(Ep\d+)", title, re.IGNORECASE)
                if m:
                    fname_base = m.group(1)
                else:
                    fname_base = title.split(":", 1)[0]
            else:
                # stop at colon or first punctuation
                if ":" in title:
                    frag = title.split(":", 1)[0]
                else:
                    frag = re.split(r"[\.,;\?!]", title)[0]
                fname_base = frag.strip().replace(" ", "_")
            filename = f"{fname_base}.html"
            out_path = output_dir / filename
            if out_path.exists():
                logging.info(f"{filename} already exists, skipping.")
                continue

            try:
                e_resp = requests.get(link, headers={"User-Agent": config.USER_AGENT}, timeout=timeout)
                e_resp.raise_for_status()
                out_path.write_text(e_resp.text, encoding=config.ENCODING)
                logging.info(f"Stored episode {fname_base} at {out_path}")
            except Exception as e:
                logging.error(f"Failed to fetch episode {fname_base}: {e}")

        page += 1

    logging.info(f"Scraping completed, last page processed: {page - 1}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape Coffee Break episodes category pages and download raw HTML."
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-o", "--output", type=str, help="Output directory for raw HTML files")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level)

    base_url = "https://xn--sealyruido-u9a.com/?cat=1"
    out_dir = Path(args.output) if args.output else Path(config.DATA_DIR) / "raw_html" / "episodes"
    out_dir.mkdir(parents=True, exist_ok=True)

    scrape_category(base_url, out_dir, config.TIMEOUT, config.RETRY_COUNT)


if __name__ == "__main__":
    main()