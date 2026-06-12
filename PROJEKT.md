# BytePost — Projektdokumentation

> Deutscher Tech-News-Newsletter · täglich in 5 Minuten · bytepost.de
> Stand: Juni 2026 (nach Verbesserungs-Runde, siehe CHANGELOG.md)

---

## Überblick

BytePost ist eine statische Website (kein Backend), die täglich kuratierte Tech-News auf Deutsch veröffentlicht. Artikel werden automatisch via Python-Script aus RSS-Feeds bezogen, von einer KI (Groq / Llama) zusammengefasst und in `data.json` gespeichert. Die Website liest diese Datei clientseitig per JavaScript. On-Demand-KI-Erklärungen laufen über einen Cloudflare Worker (Key liegt nicht im Frontend).

---

## Dateistruktur

```
bytepost/
├── index.html             # Hauptseite: Feed (nur letzte 7 Tage), Modal, Filter, Suche, Merkliste
├── archiv.html            # Archiv: alle älteren Artikel, A-Z nach Titel, Live-Suche
├── dashboard.html         # Live-Dashboard (GitHub, HN, Stats, PyPI, Security)
├── impressum.html         # Impressum (Platzhalter müssen noch ausgefüllt werden)
├── favicon.svg            # Logo/Icon
├── data.json              # Artikel-Datenbank (~0,9 MB, ohne Embeddings)
├── embeddings.json        # id → Vektor (GITIGNORED, nicht deployt!)
├── generator.py           # Generator: RSS → Groq → data.json + Outputs
├── migrate_embeddings.py  # Einmalige Migration (bereits ausgeführt)
├── artikel/<id>.html      # Statische SEO-Seiten (vom Generator erzeugt)
├── feed.xml               # Eigener RSS-Feed (letzte 30 Artikel)
├── sitemap.xml            # Sitemap (Homepage + Artikel-Seiten)
├── worker/                # Cloudflare Worker: Groq-Proxy für Erklärmodi
│   ├── worker.js          #   nur {id, mode}, Rate-Limit, CORS bytepost.de
│   ├── wrangler.toml
│   └── README.md          #   Deploy-Anleitung
├── styles/base.css        # Gemeinsame Basis: Design-Tokens, Reset, Nav
├── images/                # Artikel-Bilder (neu: WebP + <id>-sm.webp 400px)
├── .env.example           # Vorlage für API-Keys (.env ist gitignored)
├── README.md              # Setup + Hinweis auf Key-Rotation
└── CHANGELOG.md           # Alle Änderungen + offene manuelle Schritte
```

`models.json` und `config.js` existieren **nicht mehr**.

---

## Technologie-Stack

| Bereich | Technologie |
|---|---|
| Frontend | Vanilla HTML/CSS/JS (keine Frameworks) |
| Fonts | Inter (Body), Bricolage Grotesque (Headlines), JetBrains Mono (nur Code/Zahlen) — Google Fonts |
| Artikel-KI | Groq API (`llama-3.3-70b-versatile`) |
| Erklärmodi-Proxy | Cloudflare Worker (`worker/`) |
| Embeddings | Voyage AI (`voyage-3-lite`) — Dedupe + Related |
| Bilder | Unsplash API → WebP via Pillow (mit Attribution) |
| RSS-Parsing | Python `feedparser` + `beautifulsoup4` (lazy imports) |
| Deployment | Statisch (z. B. GitHub Pages, Netlify, Vercel) |

---

## generator.py

### Umgebungsvariablen (alle Pflicht, via env oder `.env`)
```bash
GROQ_API_KEY=gsk_...        # console.groq.com
VOYAGE_API_KEY=pa-...       # voyageai.com
UNSPLASH_ACCESS_KEY=...     # unsplash.com/developers
```

### Modi
```bash
python generator.py                 # voller Lauf (braucht Keys)
python generator.py --outputs-only  # nur artikel/, sitemap.xml, feed.xml (keine Keys)
```

### Ablauf eines Laufs
1. `data.json` + `embeddings.json` laden
2. Embedding-Backfill für Artikel ohne Vektor; `related` für Alt-Artikel nachziehen
3. Tageslimit prüfen (`MAX_PER_DAY = 15`)
4. Kandidaten aus RSS-Feeds sammeln (balanciert über Kategorien)
5. **Dedupe:** Kandidaten-Embedding vs. Bestand, Similarity > 0.92 → Skip
6. Pro Artikel: Scrapen → Groq-Zusammenfassung → Unsplash-Bild (WebP voll + 400px small, mit Credit) → Embedding in Store
7. „Pick of the Day" (KI wählt + begründet)
8. `related` für neue Artikel (Cosine ≥ 0.87, max. 3)
9. BytePulse + `bytepulse_history` (max. 90 Tage)
10. `data.json` speichern + `write_outputs()`: Artikel-Seiten, Sitemap, RSS

### Prompt-Richtlinie (Urheberrecht!)
Eigenständige Zusammenfassung, **max. 250 Wörter**, keine Zitate > 15 Wörter, motiviert zum Original. `content_simple` 100–130, `content_pro` 150–220 Wörter.

---

## data.json — Datenstruktur

```json
{
  "articles": [
    {
      "id": "a1b2c3d4",
      "title": "...",
      "cat": ["ki", "dev"],
      "icon": "🤖",
      "source": "TechCrunch",
      "url": "https://...",
      "date": "20.05.2026",
      "read": "3 Min",
      "sentiment": "positiv",
      "pick": true,
      "pick_reason": "...",
      "content": "<p>...</p>",
      "content_simple": "...",
      "content_pro": "...",
      "image_local": "images/a1b2c3d4.webp",
      "image_small": "images/a1b2c3d4-sm.webp",
      "image_credit_name": "Jane Doe",
      "image_credit_url": "https://unsplash.com/@jane?utm_source=bytepost&utm_medium=referral",
      "related": [{"id": "x", "reason": "Sehr ähnliches Thema"}]
    }
  ],
  "bytepulse": { "date": "...", "positiv": 60, "neutral": 30, "kritisch": 10, "total": 10 },
  "bytepulse_history": [ { "...": "ein Eintrag pro Tag, max. 90" } ]
}
```

**Nicht mehr vorhanden:** `embedding` (→ embeddings.json), `reactions` (gelöscht).
Alt-Artikel haben teils noch `.jpg`-Bilder und kein `image_small` — Frontend fällt zurück.

---

## Kategorien & Farben

| Key | Label | Farbe |
|---|---|---|
| `ki` | KI | `#0071e3` | 
| `dev` | Dev | `#22c55e` |
| `hardware` | Hardware | `#f97316` |
| `security` | Security | `#ef4444` |
| `business` | Business | `#a855f7` |
| `gaming` | Gaming | `#ec4899` |
| `data` | Data | `#f59e0b` |
| `cloud` | Cloud | `#06b6d4` |
| `tech` | Tech | `#6366f1` |

---

## index.html — Hauptseite

- **Letzte 7 Tage:** `RECENT_ARTICLES` = Artikel der letzten `RECENT_DAYS` (7) Tage,
  relativ zum neuesten Artikel (Fallback: 10 neueste). Pick of the Day, Filter-Tabs,
  Suche und Grid arbeiten auf `RECENT_ARTICLES`; `ARTICLES` (Gesamt-Set) bleibt für
  Modal/Kontext-Kette erhalten → `#a=<id>` öffnet auch archivierte Artikel.
  Älteres landet in `archiv.html`, Link „📚 X weitere Artikel im Archiv" unter dem
  Editions-Header.
- **Hash-Routing:** `#cat=ki,dev` (Filter, Legacy `#ki,dev` ok) + `#a=<id>` (Artikel-Deeplink, öffnet Modal; Back/Forward synchronisiert)
- **Filter-Bar:** fixed unter der Nav, versteckt sich beim Runterscrollen (rAF-throttled, 10px-Threshold), Spacer-Div hält Layout
- **Suche:** in der Filter-Bar, live (200ms Debounce), Titel + Content, Treffer-Anzeige
- **Merkliste:** ☆/★ auf Karten + Modal, Tab „★ Gemerkt" (`bp_bookmarks` in localStorage)
- **Gelesen-Status:** Karte abgedunkelt + ✓-Badge (`bp_read`)
- **Modal:** 3 Erklärmodi (Einfach/Standard/Pro) — on-demand via `EXPLAIN_API_URL` (Worker, Konstante am Script-Anfang!), „Link kopieren"-Button, Unsplash-Credit, Kontext-Kette aus `article.related`
- **A11y:** Karten/Hero `role=button`+Tastatur, Modal `role=dialog`+Fokus-Trap+Fokus-Rückgabe, alt-Texte
- **Bilder:** `srcset` (small/full), `loading=lazy` außer Hero, `decoding=async`
- **Theme:** Dark/Light via `bp_theme` in localStorage

---

## archiv.html — Artikel-Archiv

- Lädt `data.json`, ermittelt das Archiv-Set per `computeRecentArticles()`
  (identische Logik wie in `index.html`) und zeigt alles **außerhalb** der
  letzten `RECENT_DAYS` Tage.
- Sortierung alphabetisch nach Titel (`localeCompare(..., 'de')`), gruppiert
  nach Anfangsbuchstabe (A–Z, Sonderfälle unter „#"), mit Sprungleiste.
- Live-Suche (Titel, 200ms Debounce) + Kategorie-Badges + Datum pro Eintrag.
- Jeder Eintrag verlinkt auf `index.html#a=<id>` (öffnet das Modal dort, auch
  für archivierte Artikel, da `ARTICLES` in `index.html` das Gesamt-Set bleibt).

---

## dashboard.html — Tech Dashboard (5 Widgets)

| Widget | Datenquelle |
|---|---|
| GitHub Trending | GitHub Search API |
| Hacker News Top 10 | HN Firebase API |
| BytePost Stats | `data.json` — Donut + **14-Tage-Sentiment-Verlauf (SVG)** + neuester Artikel |
| Python Packages | PyPI JSON API |
| Security Alerts | Heise Security RSS via allorigins.win |

---

## Offene Punkte / TODOs

- [ ] **API-Keys rotieren** (alte Keys in Git-Historie — Voyage + Unsplash)
- [ ] **Worker deployen** + `EXPLAIN_API_URL` in index.html eintragen
- [ ] Impressum-Platzhalter mit echten Daten füllen
- [ ] `embeddings.json` lokal/CI sichern (gitignored — Verlust = teurer Re-Backfill)
- [ ] Automatisierung von `generator.py` (z. B. GitHub Actions Cron)
- [ ] Optional: alte JPG-Bilder nach WebP konvertieren
