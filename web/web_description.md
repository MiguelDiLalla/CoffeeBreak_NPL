# Proyecto Web - Podcast Index & Player (Vanilla JS + Tailwind + JSON + Web APIs)

## Descripción General

Este proyecto es una aplicación web estática diseñada para explorar, buscar, reproducir y exportar clips de episodios de un podcast usando tecnologías 100% cliente. La base de datos es un archivo JSON que contiene información de cada episodio. El sitio está pensado para ser sencillo, ligero, responsive y compatible con todos los navegadores modernos.

**Tecnologías utilizadas:**
- **HTML5 + Tailwind CSS**
- **Vanilla JavaScript**
- **FlexSearch** para búsqueda avanzada
- **ffmpeg.wasm** para recorte/exportación de audio en cliente
- **LocalStorage** para historial de recortes
- **Deep Links (URL Parameters)** para compartir recortes

**Branding y Estilos:**
- **Colores:**
  - Background: `#18171a` (darkgrey from blue)
  - Main: `#37b827` (green)
  - Accents: `#abffd2` (aquamarine)
- **Tipografía:**
  - Títulos: Pattaya
  - Texto: Rokkitt
  - Implementación:
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Pattaya&family=Rokkitt:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet">
  ```

---

## Estructura Visual del Sitio (Diagrama General)

```plaintext
┌──────────────────────────┐
│        HEADER            │
│ Logo + Barra de búsqueda │
└──────────────────────────┘
┌──────────────────────────┐
│        GRID (Scrollable) │
│ [Episodio Card 1]        │
│ [Episodio Card 2]        │
│ [Episodio Card 3]        │
│   ...                    │
└──────────────────────────┘
┌──────────────────────────┐
│   BOTTOM AUDIO PLAYER    │
│ [Playback + Trim + Share]│
└──────────────────────────┘
```

---

## Componentes principales de la aplicación

### 1. Base de datos de episodios (`episodes.json`)

Contiene para cada episodio:

- Número y clase del episodio (Single, Dual, Only, Supl)
- Título
- Miniatura (imagen)
- Fecha de publicación
- Duración total (segundos)
- Partes (A, B, Only) con:
  - ID
  - Timestamps
  - URL de audio
- Tópicos por parte con timestamps
- Participantes (Contertulios)
- Referencias externas (URLs)
- Transcripción (próximamente)

---

### 2. Interfaz de usuario (Grid de exploración)

#### Header
- Logo
- Barra de búsqueda global (usa FlexSearch)

#### Grid Scrollable + Paginación

```plaintext
┌────────────┐   ┌────────────┐   ┌────────────┐
│  Episodio  │   │  Episodio  │   │  Episodio  │
│   Card     │   │   Card     │   │   Card     │
└────────────┘   └────────────┘   └────────────┘
```

#### Tarjetas de episodios ("Cards") en tres estados:

##### → Estado Base (Miniatura)
```plaintext
┌───────────────────┐
│ Thumbnail         │
│ Número - Fecha    │
│ Duración total    │
└───────────────────┘
```

##### → Estado Expandido (al hacer clic)
```plaintext
┌─────────────────────────┐
│ [Thumbnail grande]      │
│ [Botón Play]            │
│ Título                  │
│ Participantes           │
│ [Botón Más info]        │
└─────────────────────────┘
```

##### → Estado Detalle (Modal)
```plaintext
┌────────────────────────────┐
│   [Blur del Grid de fondo] │
│ ┌────────────────────────┐ │
│ │   Episodio Dashboard   │ │
│ │ Thumbnail + Título     │ │
│ │ Participantes          │ │
│ │ ┌────────┬───────────┐ │ │
│ │ │Tópicos │ Referencias│ │ │
│ │ └────────┴───────────┘ │ │
│ └────────────────────────┘ │
└────────────────────────────┘
```

---

### 3. Reproductor inferior (Bottom Player Interface Integrada)

```plaintext
┌──────────────────────────────────────────────────────┐
│ [Título - Num - Tópicos - Fecha (marquee animado)]   │
│ [|◁ (start)] --- [◉ cursor de reproducción] --- [▷| (end)] │
│ [Dropdown Part Selector]                             │
│ [x2 Velocidad] [◀ 15s] [▶ 15s] [Play/Pause]          │
│ [Descargar] [Compartir] [Historial]                  │
└──────────────────────────────────────────────────────┘
```

**Características:**

- La barra de reproducción tiene 3 diales:
  - Cursor de reproducción (normal)
  - Inicio (Start) → Marca el inicio del rango
  - Fin (End) → Marca el final del rango

- El rango delimitado:
  - Define el segmento para reproducir en loop
  - Define el segmento para compartir
  - Define el segmento para descargar

- Dropdown selector de partes → permite seleccionar y saltar rápidamente a partes A, B, Only, etc.

- Botones principales:
  - Velocidad → clic para alternar entre 1x y 2x (saltos de 0.2)
  - Retroceder 15 segundos
  - Avanzar 15 segundos
  - Play/Pause
  - Descargar → exportar el rango como MP3 usando ffmpeg.wasm
  - Compartir → abrir menú de opciones (WhatsApp, Mail, Twitter + Copiar link con notificación)
  - Historial → abrir panel con recortes compartidos previamente (guardados en LocalStorage)

- Texto animado superior (Marquee):
  - Muestra en bucle título, número, tópicos y fecha del episodio mientras se reproduce

---

### 4. Motor de búsqueda (FlexSearch)

- Indexación en tiempo de build (Node.js)
- Campos:
  - Título
  - Participantes
  - Tópicos
  - Transcripción (cuando esté disponible)
- Consultas en tiempo real en cliente
- Resultado reordena grid dinámicamente

---

### 5. Historial de recortes (LocalStorage)

Guardar recortes generados localmente:

```js
const clip = { episode: 42, start: 30, end: 120, timestamp: Date.now() };
let clips = JSON.parse(localStorage.getItem("clips") || "[]");
clips.push(clip);
localStorage.setItem("clips", JSON.stringify(clips));
```

- Solo se guardan recortes compartidos (acción Share)
- Listado en panel accesible desde el reproductor
- Cargar cualquier recorte → abrir episodio + setear sliders

---

### 6. Compartir recortes (Deep Links en URL)

```js
const url = new URL(window.location);
url.pathname = `/ep42`;
url.searchParams.set("start", 30);
url.searchParams.set("end", 120);
const shareLink = url.toString();
console.log(shareLink);
```

```js
const params = new URLSearchParams(window.location.search);
const start = params.get("start");
const end = params.get("end");
if (start && end) {
  setSliders(start, end);
  player.seek(start);
}
```

- Enlaces compatibles con copiar/pegar
- Al abrir: carga episodio y ajusta rango de sliders automáticamente

## 7. Estructura de la carpeta web/

```plaintext
📁 web
├── 📁 assets
│   ├── 📁 images
│   ├── 📁 icons
│   └── 📁 audio
├── 📁 css
│   └── tailwind.css
├── 📁 js
│   ├── app.js
│   ├── search.js
│   ├── player.js
│   ├── history.js
│   └── share.js
├── 📁 data
│   └── episodes.json
├── 📄 index.html
├── 📄 episode.html
└── 📄 README.md
```

Explicación de carpetas y archivos

📁 assets  
- **images/** → Miniaturas y recursos gráficos  
- **icons/**  → Iconos de UI (SVG, PNG)  
- **audio/**  → Fragmentos o caché temporal de audio (opcional)  

📁 css  
- **tailwind.css** → Archivo generado por Tailwind con los estilos del sitio  

📁 js  
- **app.js**     → Inicializa la aplicación y maneja vistas  
- **search.js**  → Motor de búsqueda con FlexSearch (transcripciones en el futuro)  
- **player.js**  → Control del reproductor (play, pause, trim, export)  
- **history.js** → Gestión de historial de recortes (LocalStorage)  
- **share.js**   → Generación de deep‐links y compartición en redes  

📁 data  
- **episodes.json** → Base de datos de episodios exportada desde el pipeline principal  

📄 index.html  
Página principal: grid de episodios + reproductor inferior siempre visible  

📄 episode.html (opcional)  
Vista individual de un episodio (puede omitirse según diseño final)  

📄 README.md  
Documentación básica de la carpeta `/web` y su uso  



## Extras y Futuro

- Favoritos / Recientes en LocalStorage (opcional)
- Compartir directamente en redes (WhatsApp, Twitter, Email)
- Sincronización audio <-> transcripción (highlight en vivo)
- Miniaturas automáticas para recortes exportados

---

## Consideraciones finales

- Compatible 100% con navegadores modernos
- Funciona como sitio estático
- Sin dependencias de servidor
- Sencillo de mantener, expandir y compartir

---

# Estado del proyecto

Este documento describe el **estado actual de diseño funcional** del proyecto Podcast Index & Player.  
Se recomienda seguir esta estructura para iniciar el desarrollo del MVP.

