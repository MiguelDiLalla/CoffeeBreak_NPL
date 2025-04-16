CoffeeBreak_NPL/
│
├── scraping/
│   ├── __init__.py
│   ├── base_scraper.py               # Funciones reutilizables
│   ├── episodes_index_scraper.py    # Accede al índice general
│   ├── episode_parser_v1.py         # Parser para episodios nuevos (con timestamps)
│   ├── episode_parser_legacy.py     # Parser para temporadas viejas
│   └── utils_html.py                # Funciones con BeautifulSoup / lxml
│
├── data/
│   ├── raw_html/                     # Copias originales por si cambia el site
│   ├── parsed_json/                 # JSON estructurado con: título, fecha, temas, timestamps, links, contertulios
│   └── audio_files/                 # (opcional) si decides descargar los audios
│
├── database/
│   └── episodes.db                  # SQLite (o puedes usar PostgreSQL más adelante)
│
├── notebooks/
│   └── analysis_example.ipynb       # Exploración inicial y pruebas
│
├── nlp_pipeline/
│   ├── __init__.py
│   ├── tokenizer.py
│   ├── spacy_analysis.py
│   └── diarization.py               # Interfaz con pyannote o whisper
│
├── tests/
│   └── test_parsers.py              # Pruebas para cada tipo de parser
│
├── cli.py                           # Entrada CLI si decides automatizar scraping/transcripción
├── config.py                        # Parámetros generales del proyecto
├── README.md                        # Explicación de objetivos
└── requirements.txt                 # Dependencias del proyecto
