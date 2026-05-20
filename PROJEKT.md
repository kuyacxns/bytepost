# BytePost — Projektdokumentation

> Deutscher Tech-News-Newsletter · täglich in 5 Minuten · bytepost.de

---

## Überblick

BytePost ist eine statische Website (kein Backend), die täglich kuratierte Tech-News auf Deutsch veröffentlicht. Artikel werden automatisch via Python-Script aus RSS-Feeds bezogen, von einer KI (Groq / Llama) zusammengefasst und in `data.json` gespeichert. Die Website liest diese Datei clientseitig per JavaScript.

---

## Dateistruktur

```
bytepost/
├── index.html          # Hauptseite: News-Feed
├── dashboard.html      # Live-Dashboard (GitHub, HN, PyPI, Security, KI-Modelle)
├── impressum.html      # Impressum (Platzhalter müssen noch ausgefüllt werden)
├── favicon.svg         # Logo/Icon
├── data.json           # Alle Artikel (1,7 MB, von generator.py befüllt)
├── models.json         # Manuell gepflegte KI-Modell-Übersicht
├── generator.py        # Python-Script zur Artikel-Generierung
├── images/             # Lokale Artikel-Bilder (von Unsplash heruntergeladen)
└── config.js           # (optional) Groq API-Key für clientseitige KI-Features
                        # → window.BYTEPOST_CONFIG = { groqKey: "gsk_..." }
```

---

## Technologie-Stack

| Bereich | Technologie |
|---|---|
| Frontend | Vanilla HTML/CSS/JS (keine Frameworks) |
| Fonts | Space Mono, Syne, DM Sans (Google Fonts) |
| Artikel-KI | Groq API (`llama-3.3-70b-versatile`) |
| Embeddings | Voyage AI (`voyage-3-lite`) — für "Ähnliche Artikel" |
| Bilder | Unsplash API (automatisch heruntergeladen) |
| RSS-Parsing | Python `feedparser` + `beautifulsoup4` |
| Deployment | Statisch (z. B. GitHub Pages, Netlify, Vercel) |

---

## generator.py — Artikel-Generierung

### Umgebungsvariablen
```bash
export GROQ_API_KEY="gsk_..."       # Pflicht — kostenlos: console.groq.com
export VOYAGE_API_KEY="pa-..."      # Optional — für semantische Embeddings
# UNSPLASH_KEY ist direkt im Script hardcoded
```

### Ablauf eines Laufs
1. Lädt `data.json` (oder erstellt eine neue)
2. Backfill-Embeddings für Artikel ohne Vektor
3. Prüft Tageslimit (`MAX_PER_DAY = 15`)
4. Sammelt neue Artikel aus RSS-Feeds (balanciert über Kategorien)
5. Für jeden Artikel: Artikel-Text scrapen → Groq-Zusammenfassung → Unsplash-Bild → Embedding
6. KI wählt "Pick of the Day" (mit Begründung)
7. BytePulse (Sentiment-Statistik) berechnen
8. `data.json` speichern

### Limits (Cost Protection)
```python
MAX_PER_RUN      = 10   # max. neue Artikel pro Lauf
MAX_PER_DAY      = 15   # max. neue Artikel pro Tag
MAX_PER_CATEGORY = 2    # max. pro Feed-Kategorie pro Lauf
MAX_ERRORS       = 3    # Circuit Breaker
```

### RSS-Feed-Kategorien
`gaming`, `ai_ml`, `dev`, `data`, `cloud_devops`, `security`, `engineering_blogs`, `languages`, `tech_de`, `business`, `hardware`

### Groq-Prompt erzeugt je Artikel
- `content` — Vollständiger Artikel auf Deutsch (400–600 Wörter, HTML)
- `content_simple` — Einfach erklärt (150–200 Wörter, kein Jargon)
- `content_pro` — Technische Tiefenversion für Entwickler (250–350 Wörter)

---

## data.json — Datenstruktur

```json
{
  "articles": [
    {
      "id": "a1b2c3d4",          // hex, 8 Zeichen (os.urandom(4).hex())
      "title": "...",
      "cat": ["ki", "dev"],       // Array, 1-3 Kategorien
      "icon": "🤖",
      "source": "TechCrunch",
      "url": "https://...",
      "date": "20.05.2026",       // Format: DD.MM.YYYY
      "read": "3 Min",
      "sentiment": "positiv",     // positiv | neutral | kritisch
      "pick": true,               // nur einer pro Tag
      "pick_reason": "...",       // KI-Teaser für Hero-Sektion
      "content": "<p>...</p>",    // HTML
      "content_simple": "...",    // HTML
      "content_pro": "...",       // HTML
      "image_local": "images/a1b2c3d4.jpg",
      "embedding": [0.123, ...],  // Voyage-AI-Vektor (512 Dimensionen)
      "related": ["id1", "id2"],  // verknüpfte Artikel-IDs
      "reactions": {"fire":0, "think":0, "bulb":0, "sleep":0}
    }
  ],
  "bytepulse": {
    "date": "20.05.2026",
    "positiv": 60,
    "neutral": 30,
    "kritisch": 10,
    "total": 10
  }
}
```

---

## Kategorien & Farben

| Key | Label | Farbe |
|---|---|---|
| `ki` | KI | `#0071e3` (Blau) |
| `dev` | Dev | `#22c55e` (Grün) |
| `hardware` | Hardware | `#f97316` (Orange) |
| `security` | Security | `#ef4444` (Rot) |
| `business` | Business | `#a855f7` (Lila) |
| `gaming` | Gaming | `#ec4899` (Pink) |
| `data` | Data | `#f59e0b` (Gelb) |
| `cloud` | Cloud | `#06b6d4` (Cyan) |
| `tech` | Tech | `#6366f1` (Indigo) |

---

## index.html — Hauptseite

### Features
- **Dark/Light Mode** — Toggle, gespeichert in `localStorage` (`bp_theme`)
- **Edition Header** — heutiges Datum + Anzahl neuer Artikel
- **Category Filter Bar** — filterbare Tabs, URL-Hash (`#ki,dev`)
- **Pick of the Day** — großer Hero mit Bild, Kategorie-Badge, "Warum?"-Box
- **Card Grid** — responsiv 1/2/3 Spalten, alle anderen Artikel
- **Modal / Artikel-Detail** — Öffnet per Klick, zeigt Volltext
  - 3 Erklärungs-Modi: **Einfach** / **Standard** / **Für Profis**
  - On-demand-Generierung via Groq (wenn `config.js` vorhanden)
  - Cached in `explainCache` (Session-Memory)
  - Scroll-Position wird pro Artikel gemerkt
- **Ähnliche Artikel ("Kontext-Kette")** — Cosine-Similarity auf Embeddings (Threshold 0.87)
  - Fallback: seltene Keyword-Überschneidung im Titel
- **Keyboard-Shortcut** — `Escape` schließt Modal
- **URL-Hash-Routing** — `#ki`, `#dev,security` etc. filtern beim Laden

---

## dashboard.html — Tech Dashboard

Widgets mit 5-Minuten Auto-Refresh und sessionStorage-Cache:

| Widget | Datenquelle |
|---|---|
| GitHub Trending | GitHub Search API (neue Repos, letzte 7 Tage) |
| Hacker News Top 10 | HN Firebase API |
| BytePost Stats | `data.json` — Artikel-Anzahl + Kategorie-Donut |
| Python Packages | PyPI JSON API (requests, numpy, pandas, fastapi, …) |
| Security Alerts | Heise Security RSS via allorigins.win Proxy |
| KI-Modell Tracker | `models.json` (manuell gepflegt) |

---

## models.json — KI-Modell Tracker

Manuell aktualisierte Liste mit Feldern: `name`, `company`, `released`, `type`, `highlight`.

Bekannte Firmen-Farben: OpenAI `#10a37f`, Anthropic `#d4613a`, Google `#4285f4`, Meta `#0866ff`, xAI `#e7e7e7`, Mistral `#ff6b00`, Alibaba `#ff6a00`.

---

## Design-System

```css
/* Fonts */
--mono:    'Space Mono', monospace    /* Labels, Meta, Badges */
--display: 'Syne', sans-serif         /* Headlines, Titel */
--body:    'DM Sans', sans-serif      /* Fließtext */

/* Farben (Dark Mode) */
--bg:      #0a0a0a
--bg-card: #141414
--text:    #f5f5f7
--accent:  #0071e3

/* Farben (Light Mode) */
--bg:      #f5f5f7
--bg-card: #ffffff
--text:    #1d1d1f

--radius: 14px
```

---

## Impressum

`impressum.html` ist vorhanden, aber **Platzhalter müssen noch ausgefüllt werden**:
- Vorname Nachname
- Adresse (Straße, PLZ, Ort)
- E-Mail (aktuell: `kontakt@bytepost.de`)

---

## Offene Punkte / TODOs

- [ ] Impressum-Platzhalter mit echten Daten füllen
- [ ] `config.js` für Produktiv-Deployment einrichten (Groq API-Key)
- [ ] Voyage AI API-Key aus `generator.py` in Umgebungsvariable auslagern (aktuell hardcoded)
- [ ] Unsplash API-Key aus `generator.py` in Umgebungsvariable auslagern (aktuell hardcoded)
- [ ] Automatisierung von `generator.py` (z. B. GitHub Actions Cron)
- [ ] `data.json` wächst unbegrenzt — Archivierungsstrategie fehlt
