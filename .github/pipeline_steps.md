# 🧪 Coffee Break Scraper & NLP Pipeline

Este documento describe el flujo general de trabajo para el proyecto de scraping y procesamiento de datos del pódcast *Coffee Break: Señal y Ruido*. El objetivo es extraer metadatos útiles, analizar el contenido con herramientas NLP y almacenar todo en una base de datos escalable.

---

## 🚀 Objetivo General

> Crear un sistema modular capaz de recorrer todos los episodios publicados, extraer metadatos (temas, tiempos, contertulios, enlaces), guardar versiones limpias y analizables del contenido, y permitir el procesamiento con NLP y diarización cuando se disponga del audio.

---

## 🧭 Etapas del Pipeline

### 1. 🛰️ Descubrimiento de episodios
- Scrapeo de la página principal o índice de episodios.
- Extracción de: `título`, `URL`, `fecha`, `ID`.
- Guarda un archivo de control de episodios disponibles (`episodes_index.json`).

🔧 Archivo: `scraping/episodes_index_scraper.py`

---

### 2. 💾 Descarga del HTML
- Descarga el HTML completo de cada página de episodio.
- Almacena en: `data/raw_html/epXXX.html`
- Previene la dependencia futura del contenido online (versión offline).

🔧 Archivo: `scraping/base_scraper.py`

---

### 3. 🧹 Parsing del HTML → JSON estructurado
- Extrae de cada episodio:
  - `título`, `fecha`, `cara A / B`, `temas`, `timestamps`
  - `contertulios`, `referencias`, `enlaces externos`
- Guarda como JSON limpio en `data/parsed_json/epXXX.json`
- Admite diferentes parsers para distintas estructuras de episodios.

🔧 Archivos:
- `scraping/episode_parser_v1.py` (episodios recientes)
- `scraping/episode_parser_legacy.py` (estructuras antiguas)

---

### 4. 🛢️ Ingesta en base de datos
- Inserta los datos parseados en `episodes.db` (SQLite por defecto).
- Permite búsquedas rápidas, agregaciones, consultas.
- Limpieza de duplicados / control de versiones si hay cambios.

🔧 Archivo sugerido: `utils/db.py`

---

### 5. 🔊 Transcripción y diarización (opcional)
- Para episodios con acceso al audio:
  - Diarización con `pyannote.audio` (detecta quién habla y cuándo)
  - Transcripción con `whisper` (segmenta en texto por hablante)
- Resultado: texto con timestamp + nombre de hablante estimado.

🔧 Archivos:
- `nlp_pipeline/diarization.py`
- `nlp_pipeline/transcriber.py`

---

### 6. 🧠 Análisis NLP
- Procesamiento con `spaCy` (modelo español `es_core_news_md`):
  - Tokenización
  - Detección de entidades (PERSON, LOC, ORG...)
  - Extracción de temas y relaciones semánticas
- Opcional: vectorización semántica (BERT, sentence-transformers)

🔧 Archivos:
- `nlp_pipeline/spacy_analysis.py`
- `notebooks/analysis_example.ipynb`

---

### 7. 🧪 Visualización y exploración de resultados
- Reportes interactivos, visuales y exportables.
- Exploración de episodios por tema, contertulio, año...
- Soporte para gráficos y exportación a `.csv`, `.json`, `.md` o `.html`

📓 Usar: `Jupyter`, `Altair`, `Plotly`, `Streamlit` *(en etapas futuras)*

---

### 8. 🔁 Orquestación CLI
- Automatiza tareas con comandos como:
```bash
python cli.py download-index
python cli.py fetch-html --episode 505
python cli.py parse-episode --episode 505
python cli.py populate-db
```

🔧 Archivo: `cli.py`

---

## 📂 Sugerencia de carpetas

```plaintext
coffee_scraper_project/
├── scraping/
├── data/
│   ├── raw_html/
│   ├── parsed_json/
│   └── audio_files/
├── database/
├── nlp_pipeline/
├── notebooks/
├── tests/
├── cli.py
├── config.py
├── requirements.txt
└── README.md
```

---

## ✨ Posibles mejoras futuras
- 🧠 Búsqueda semántica por temas (FAISS / ChromaDB)
- 🎧 Descarga automática del audio y transcripción masiva
- 📈 Dashboard con Streamlit
- 📚 Entrenamiento de modelo personalizado para detección de tópicos
- 📤 Exportación pública de los datos parseados (API, CSV, etc.)

---

¿Listo para comenzar? Puedes empezar desde `episodes_index_scraper.py` o el parser del episodio que ya tenemos (505).

