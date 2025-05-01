# 🧠 GitHub Copilot Custom Instructions for `CoffeeBreak_NPL`

> Use these instructions to assist with code suggestions that are **modular**, **scalable**, and aligned with this project's current architecture and documentation.

---

## 📁 Project Folder Context

The project root is organized into clean, documented modules. See:

- `.github/pipeline_steps.md` → Defines modular pipeline steps
- `.github/initial-folders-tree.md` → Tracks the full structure and evolution
- `README.md` → Documents project goals and tech stack

---

## 🎯 Project Goals

- Extract and structure metadata from podcast episodes (titles, timestamps, guests, links)
- Parse variations across podcast seasons and HTML layouts
- Store parsed metadata in a queryable format (SQLite DB)
- Enable NLP analysis via spaCy and audio diarization via Whisper/pyannote
- Build a reproducible CLI tool for scraping, parsing, and analysis

---

## 🧑‍💻 Coding Standards

- Language: **Python 3.10**
- Style guide: **PEP8** + **Black** formatter
- Structure: Modular by concern (e.g., `scraping/`, `nlp_pipeline/`, `data/`, `tests/`)
- Variable naming: Clear, descriptive (e.g., `timestamp_dict`, `guest_list`)
- Avoid hardcoding file paths — use relative paths based on `config.py`
- All modules should support **importable use + CLI execution**
- Include docstrings for functions and classes
- Use logging over print for debugging (if needed)

---

## 🔁 Learning-Focused Practices

- Prioritize readability and explainability over premature optimization
- Encourage testable and reusable functions
- Make Copilot suggest helper functions over monolith blocks
- Avoid suggesting heavy frameworks unless required (keep it lightweight unless justified)

---

## ⚙️ Guidance for Suggestions

When proposing code completions:
- For HTML parsing, prefer `BeautifulSoup` with `lxml` parser or XPath via `lxml.html`
- For file saving/loading, always use UTF-8 and `.json` or `.md` extensions
- For database interaction, prefer structured ORM-style access (e.g., `sqlite3`, or `sqlalchemy` in future)
- When dealing with NLP, prefer `spaCy` and default to `es_core_news_md` for Spanish

---

## 📌 Preferred Copilot Completion Behavior

- ✅ Suggest scaffold-friendly functions
- ✅ Include error handling and fallbacks
- ✅ Align with project-specific filenames (`episode_parser_v1`, `episodes_index_scraper`, etc.)
- ❌ Avoid suggesting third-party scraper libraries (`selenium`, `scrapy`) unless explicitly invoked
- ❌ Avoid suggesting unrelated packages (`tensorflow`, `opencv`, etc.)

---

## 🖥️ CLI Implementation Standards

- Every script should implement CLI functionality using `argparse`
- Include comprehensive `--help` output with:
  - Clear description of the script's purpose
  - Explanation of each parameter/flag
  - Usage examples
  - How the script fits into the overall pipeline
- Standard flags across all scripts:
  - `--verbose` or `-v`: Control logging verbosity
  - `--output` or `-o`: Specify output file/directory
  - `--config` or `-c`: Path to configuration file (if applicable)
- Use subcommands for scripts with multiple operations

---

## 📊 Logging Standards

- Use the `rich` library for enhanced console output
- Implement structured logging with different levels:
  - DEBUG: Detailed troubleshooting
  - INFO: General operational events
  - WARNING: Unexpected but non-critical issues
  - ERROR: Failures that prevent specific operations
  - CRITICAL: Application-wide failures
- Include progress indicators for long-running operations
- Log both to console and file when appropriate
- Format log messages consistently with timestamps and log levels

---

## 📚 Documentation Requirements

- Each module should have a comprehensive module-level docstring explaining:
  - Purpose and functionality
  - Dependencies and prerequisites
  - How it fits into the overall pipeline
- All functions and classes require detailed docstrings including:
  - Parameters with types and descriptions
  - Return values with types and explanations
  - Exceptions that might be raised
  - Usage examples where appropriate
- Include inline comments for complex logic
- Add `README.md` files to each subdirectory explaining its contents

---

## 🌐 Web Development Best Practices
- Follow the `/web` folder structure: `assets/`, `css/`, `js/`, `data/`, `index.html`, `episode.html`.
- Use HTML5 semantic elements and ARIA roles for accessibility.
- Style with Tailwind CSS in utility-first approach; ensure responsive design mobile-first.
- Implement modular Vanilla JS in separate files: `app.js`, `search.js`, `player.js`, `history.js`, `share.js`.
- Load `data/episodes.json` via Fetch API; handle errors and use UTF-8 encoding.
- Integrate FlexSearch for client-side search; index on build and query at runtime.
- Use ffmpeg.wasm for in-browser audio trimming/export; guard fallbacks when unsupported.
- Persist clip history in LocalStorage; expose clear API in `history.js` module.
- Generate and parse deep links with URLSearchParams in `share.js`.
- Serve via simple HTTP server (e.g., `python -m http.server`) for local development; avoid CORS issues.
- Use a build script (Node.js or Makefile) to concatenate/minify assets if needed.
- Include a `/web/README.md` with setup and usage instructions; keep docs in sync with code.

---

## 📝 Notes

These instructions will evolve. All decisions and structural logic should trace back to the source docs in `.github/`.

---

_Maintained by Miguel Di Lalla – last updated: 2025-04-16_
