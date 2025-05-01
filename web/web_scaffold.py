import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if ROOT.name != "web":
    print("Este script debe ejecutarse desde dentro de la carpeta 'web'.")
    exit(1)

folders = [
    "assets/images",
    "assets/icons",
    "assets/audio",
    "css",
    "js",
    "data",
]

files = {
    "css/tailwind.css": "/* Tailwind placeholder */\n",
    "js/app.js": "// Main UI logic\n",
    "js/search.js": "// FlexSearch logic\n",
    "js/player.js": "// Audio player logic\n",
    "js/history.js": "// LocalStorage manager\n",
    "js/share.js": "// Sharing and Deep Link logic\n",
    "index.html": "<!-- Main grid UI -->\n<html><body><h1>Podcast Index</h1></body></html>",
    "episode.html": "<!-- Optional detailed episode page -->\n<html><body><h1>Episode Detail</h1></body></html>",
    "README.md": "# Web Folder\nStatic frontend interface for Podcast Index project.\n",
    "data/episodes.json": "{}"  # Empty placeholder
}

for folder in folders:
    path = ROOT / folder
    path.mkdir(parents=True, exist_ok=True)
    print(f"Directorio creado: {path}")

for filepath, content in files.items():
    path = ROOT / filepath
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Archivo creado: {path}")
    else:
        print(f"Archivo ya existe: {path}")

print("\nEstructura base del sitio web generada correctamente.")