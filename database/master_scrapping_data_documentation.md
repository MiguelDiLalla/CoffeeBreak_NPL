# Coffee Break NPL: Master Scrapping Data Documentation

## Overview

This document explains the structure and formatting of the `master_scrapping_data.json` file, which serves as the central repository for podcast episode metadata in the CoffeeBreak_NPL project. The file is organized as a JSON array containing metadata for each episode of the "Coffee Break: Señal y Ruido" podcast series.

## File Structure

The `master_scrapping_data.json` file is organized as an array of JSON objects:

```json
[
  {
    // Episode 1 metadata
  },
  {
    // Episode 2 metadata
  },
  // ...more episodes
]
```

## Episode Object Structure

Each episode object contains the following common properties:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `Episode number` | String | The episode number | `"001"`, `"256"` |
| `Episode class` | String | Classification of the episode | `"Single"`, `"Dual"` |
| `Title` | String | Full title of the episode | `"Ep256: Coronavirus; Cosmología; Nefertiti..."` |
| `Image_url` | String | URL to the episode's cover image | `"https://static-1.ivoox.com/audios/..."` |
| `web_link` | String | Link to the episode's web page | `"https://señalyruido.com/?p=2002"` |
| `ref_links` | Array | Array of reference links mentioned in the episode | `["https://www.nature.com/articles/...", ...]` |
| `Parts` | Array | Array of parts constituting the episode | See "Parts Structure" section |
| `publication_date` | String | Date the episode was published | `"26/05/2015"` |
| `total_duration_seconds` | Number | Total duration in seconds | `11651` |

## Parts Structure

The `Parts` array contains objects that represent different segments of an episode. This is especially relevant for "Dual" episodes, which are split into parts (typically A and B). Each part object may contain:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `Episode_ID` | String | Identifier for the episode part | `"Ep500_A"` |
| `Part_class` | String | Classification of the part | `"A"`, `"B"`, `"Only"` |
| `Date` | String | Date and time of the part | `"Fri, 21 Feb 2025 20:23:18 +0200"` |
| `Duration` | String | Duration in HH:MM:SS format | `"57:03"` |
| `raw_description` | String | Raw description text of the episode | `"La tertulia semanal en la que repasamos..."` |
| `Audio_URL` | String | URL to the audio file | `"https://www.ivoox.com/..."` |
| `Ivoox_link` | String | Link to the episode on Ivoox | `"https://www.ivoox.com/..."` |
| `Topics` | Array | Array of topics covered with timestamps | See "Topics Structure" section |
| `Contertulios` | Array | Array of participants/speakers | `["Héctor Socas", "Juan Carlos Gil", ...]` |

## Topics Structure

The `Topics` array contains objects that represent individual discussion topics in an episode part:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `title` | String | Title of the topic | `"Regalo: Arranca "El Café de Ganimedes", nuestro nuevo pódcast"` |
| `timestamp` | String | Timestamp when the topic starts | `"5:00"` |

## Episode Class Values

The `Episode class` field can have the following values:

- `"Single"`: A standalone episode
- `"Dual"`: An episode split into two parts (typically A and B)

## Part Class Values

The `Part_class` field can have the following values:

- `"A"`: First part of a dual episode
- `"B"`: Second part of a dual episode
- `"Only"`: A single-part episode

## Data Evolution

The format of entries has evolved over time:
- Early episodes (1-~450) have basic metadata
- Later episodes (450+) have more comprehensive metadata including detailed parts, topics, and participants
- Recent episodes have enriched reference links and cross-references

## Usage Notes

1. **Duration formats**: The `total_duration_seconds` is an integer, while `Duration` in Parts is a string in "HH:MM:SS" format.
2. **Optional fields**: Not all episodes have all fields populated, especially older episodes.
3. **Nested arrays**: The `Parts`, `Topics`, and `ref_links` fields are arrays that may contain multiple elements.
4. **Unicode characters**: Text fields may contain Spanish language characters and symbols.

## Example Episode Object

```json
{
  "Episode number": "500",
  "Episode class": "Dual",
  "Title": "Ep500_B: Petaneutrino; Escribas; Primeras Ciudades; Trilobites; Einstein Ring; Ganimedismo",
  "Image_url": "https://static-1.ivoox.com/audios/6/a/2/e/6a2ee6cd356a8d2f76918590320c6679_XXL.jpg",
  "web_link": "https://señalyruido.com/?p=3155",
  "ref_links": [
    "https://www.cea.fr/english/Pages/News/nuclear-fusion-west-beats-the-world-record-for-plasma-duration.aspx",
    "https://bigthink.com/starts-with-a-bang/ligo-most-important-gravitational-wave-ever/"
  ],
  "Parts": [
    {
      "Episode_ID": "Ep500_A",
      "Part_class": "A",
      "Date": "Fri, 21 Feb 2025 20:23:18 +0200",
      "Duration": "57:03",
      "raw_description": "La tertulia semanal en la que repasamos las últimas noticias de la actualidad científica...",
      "Audio_URL": "https://www.ivoox.com/ep500-a-petaneutrino-escribas-primeras-ciudades-trilobites-einstein-ring_mf_140280359_feed_1.mp3",
      "Ivoox_link": "https://www.ivoox.com/ep500-a-petaneutrino-escribas-primeras-ciudades-trilobites-einstein-ring-audios-mp3_rf_140280359_1.html",
      "Topics": [
        {
          "title": "Regalo: Arranca "El Café de Ganimedes", nuestro nuevo pódcast",
          "timestamp": "5:00"
        }
      ],
      "Contertulios": [
        "Héctor Socas",
        "Juan Carlos Gil",
        "Francis Villatoro",
        "María Ribes",
        "Sara Robisco"
      ]
    },
    {
      "Episode_ID": "Ep500_B",
      "Part_class": "B",
      "Date": "Fri, 21 Feb 2025 20:35:13 +0200",
      "Duration": "02:28:05",
      "raw_description": "La tertulia semanal en la que repasamos las últimas noticias de la actualidad científica...",
      "Audio_URL": "https://www.ivoox.com/ep500-b-petaneutrino-escribas-primeras-ciudades-trilobites-einstein-ring_mf_140280604_feed_1.mp3",
      "Ivoox_link": "https://www.ivoox.com/ep500-b-petaneutrino-escribas-primeras-ciudades-trilobites-einstein-ring-audios-mp3_rf_140280604_1.html",
      "Topics": [
        {
          "title": "El petaneutrino de KM3NET",
          "timestamp": "10:56"
        },
        {
          "title": "¿Quién construyó las primeras ciudades de Europa?",
          "timestamp": "40:56"
        }
      ],
      "Contertulios": [
        "Héctor Socas",
        "Juan Carlos Gil",
        "Francis Villatoro",
        "María Ribes",
        "Sara Robisco"
      ]
    }
  ],
  "publication_date": "21/02/2025",
  "total_duration_seconds": 12308
}
```

## Working with the Data

When working with the `master_scrapping_data.json` file:

- Use JSON parsers that properly handle Unicode characters
- Check for the existence of optional fields before accessing them
- Be aware that the structure has evolved over time
- For duration calculations, rely on the `total_duration_seconds` field
- Cross-reference with the original audio sources when in doubt

This documentation provides a guide to understand and work with the podcast metadata structure used in the Coffee Break NPL project.