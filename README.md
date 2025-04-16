# ☕ Coffee Break: Scraper & NLP Project

Este proyecto es una herramienta de scraping y análisis de datos centrada en el pódcast científico **"Coffee Break: Señal y Ruido"**. Su propósito es extraer y estructurar metadatos clave (temas, timestamps, participantes, enlaces) de los episodios para su posterior análisis con técnicas de procesamiento de lenguaje natural (NLP).

---

## 🎯 Objetivos

- Extraer metadatos de cada episodio del sitio oficial.
- Estructurar temas y timestamps para consulta rápida.
- Identificar y registrar los contertulios de cada episodio.
- Vincular referencias científicas y enlaces mencionados.
- Analizar el lenguaje utilizado mediante herramientas NLP.
- Preparar una base de datos reutilizable y expandible.

---

## 🚦 Estado actual del proyecto

- [x] Definición de estructura de carpetas
- [x] Creación de scaffolding automatizado (`scaffold.py`)
- [x] Diseño del pipeline general (`pipeline_steps.md`)
- [ ] Scraper de índice de episodios
- [ ] Parsers de HTML para distintos formatos de episodio
- [ ] Sistema de base de datos (SQLite)
- [ ] Integración de Whisper y diarización
- [ ] Análisis NLP con spaCy
- [ ] CLI para automatizar tareas

---

## 📁 Estructura del repositorio

```bash
coffee_scraper_project/
├── scraping/               # Scrapers de HTML y parsers por tipo de episodio
├── data/                   # HTML crudo, JSON estructurado, y audio
├── database/               # SQLite o PostgreSQL
├── nlp_pipeline/           # spaCy, Whisper, pyannote
├── notebooks/              # Exploración y análisis visual
├── tests/                  # Pruebas automatizadas
├── cli.py                  # Entrada por línea de comandos
├── config.py               # Configuración global
├── scaffold.py             # Script para crear estructura
├── requirements.txt        # Dependencias
└── README.md               # Este documento
```

---

## 🛠️ Instalación y entorno

1. Crea un entorno conda o virtualenv:
```bash
conda create -n coffee_nlp python=3.10
conda activate coffee_nlp
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. (Opcional) Instala paquetes pesados para NLP/audio:
```bash
pip install spacy whisper pyannote.audio
```

---

## 🧪 Comandos sugeridos (CLI futuro)

```bash
python cli.py download-index
python cli.py fetch-html --episode 505
python cli.py parse-episode --episode 505
python cli.py populate-db
python cli.py analyze --episode 505
```

---

## 🤖 Dependencias clave

| Área        | Herramientas                     |
|-------------|----------------------------------|
| Scraping    | `requests`, `beautifulsoup4`, `lxml` |
| Parsing     | `re`, `json`, `html.parser`     |
| NLP         | `spaCy`, `whisper`, `pyannote`   |
| DB          | `sqlite3`, `sqlalchemy` (futuro) |
| Utils       | `argparse`, `typer` (futuro)     |

---

## 📚 Recursos relacionados
- Podcast oficial: https://señalyruido.com
- Código del pipeline: [`pipeline_steps.md`](./pipeline_steps.md)
- HTML de ejemplo: ver `data/raw_html/ep505.html`

---

## ✨ Autor

Proyecto mantenido por [Miguel Di Lalla](https://github.com/MiguelDiLalla)

¿Comentarios o sugerencias? ¡Haz un PR o abre una issue! 🚀

