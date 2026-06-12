# Changelog — BytePost Verbesserungen (Juni 2026)

Alle Änderungen der 8 Phasen, je Phase ein Commit.

## Phase 1 — Sicherheit
- Hardcodierte Voyage-/Unsplash-Keys aus `generator.py` entfernt; alle drei Keys
  (`GROQ_API_KEY`, `VOYAGE_API_KEY`, `UNSPLASH_ACCESS_KEY`) kommen nur noch aus
  Umgebungsvariablen bzw. `.env` (minimaler Loader, kein python-dotenv nötig).
  Fehlende Keys → Abbruch mit klarer Fehlermeldung.
- `.env.example` angelegt; `.env`, `config.js`, `embeddings.json` in `.gitignore`.
- Cloudflare Worker (`worker/`) als Groq-Proxy: nimmt nur `{id, mode}` entgegen
  (keine freien Prompts), Key als Worker-Secret, Rate-Limit 10 Req/Min pro IP,
  CORS nur für bytepost.de. Frontend ruft `EXPLAIN_API_URL` statt Groq direkt;
  `config.js`-Einbindung entfernt.

## Phase 2 — Bugfixes
- `dashboard.html` `loadBP()`: liest jetzt `cat` (statt nicht existentem
  `categories`), mit Normalisierung wie in `index.html`.
- `newestDate`: echter `DD.MM.YYYY`-Parser statt String-Vergleich, formatierte
  Anzeige im Widget (war vorher gar nicht sichtbar).
- `find_related()` in `generator.py`: toter Code ersetzt durch Cosine Similarity
  auf Embeddings (Schwelle 0.87, max. 3 Treffer, mit `reason`-Label).

## Phase 3 — data.json verschlankt
- Embeddings in separater `embeddings.json` (gitignored, nicht deployt).
- `related` wird serverseitig beim Generator-Lauf berechnet: `[{id, reason}]`.
- `migrate_embeddings.py` (einmalig, self-contained, keine Keys nötig) hat die
  Migration durchgeführt: **data.json von 1,8 MB → 0,88 MB**.
- Frontend: clientseitige Cosine-/Keyword-Logik entfernt, Kontext-Kette rendert
  aus `article.related`. Groq-Archiv-Block aus dem Prompt entfernt (spart Tokens).

## Phase 4 — Rechtliches & Attribution
- Generator-Prompt: eigenständige Zusammenfassung (max. 250 Wörter) statt
  Vollübersetzung; keine wörtlichen Zitate > 15 Wörter; motiviert zum Original.
  `content_simple` 100–130, `content_pro` 150–220 Wörter.
- Unsplash-Attribution: `image_credit_name`/`image_credit_url` (mit UTM-Parametern)
  werden gespeichert; Anzeige unter dem Modal-Bild und als Hero-Overlay;
  Download-Endpoint wird API-konform getriggert.

## Phase 5 — Teilen, SEO, RSS
- Artikel-Deeplinks: `#a=<id>` öffnet das Modal (auch beim Laden), `#cat=ki,dev`
  für Filter, Legacy-Hashes (`#ki,dev`) funktionieren weiter; Back/Forward
  synchronisiert das Modal; „Link kopieren"-Button (Clipboard API + Fallback).
- Statische SEO-Seiten: `artikel/<id>.html` pro Artikel (eigene OG-Tags,
  Canonical, Content, CTA zur Hauptseite) + `sitemap.xml`. 185 Seiten generiert.
- `feed.xml` (RSS 2.0, letzte 30 Artikel), verlinkt im `<head>` und Footer.
- Neuer Generator-Modus: `python generator.py --outputs-only` (keine Keys nötig).

## Phase 6 — Frontend-Features
- Suche in der Filter-Bar: live über Titel+Content, 200 ms Debounce,
  Treffer-Anzeige, kombinierbar mit Kategorien, mobile eigene Zeile.
- Gelesen-Status (`bp_read`): Karte abgedunkelt + ✓-Badge.
- Merkliste (`bp_bookmarks`): ☆/★ auf Karten und im Modal, Filter-Tab „★ Gemerkt".
- Ungenutztes `reactions`-Feld aus Generator und allen Alt-Artikeln entfernt.

## Phase 7 — Accessibility & Performance
- Karten/Hero: `role="button"`, `tabindex="0"`, Enter/Space, Fokus-Outline.
- Modal: `role="dialog"`, `aria-modal`, `aria-labelledby`, Fokus-Trap,
  Fokus-Rückgabe beim Schließen.
- alt-Texte = Artikel-Titel auf allen Content-Bildern.
- Generator speichert WebP (voll + 400px-Card-Variante `image_small`, Pillow,
  JPG-Fallback); Frontend nutzt `srcset`/`sizes`, `loading="lazy"` (außer Hero),
  `decoding="async"`.

## Phase 8 — Generator-Qualität
- Dedupe: Kandidaten-Embedding gegen Bestand, bei Similarity > 0.92 übersprungen
  (geloggt).
- `bytepulse_history`: ein Eintrag pro Tag, max. 90 Tage; Dashboard zeigt
  14-Tage-Sentiment-Verlauf (SVG-Balken, keine Library).
- `models.json` + „KI-Modell Tracker"-Widget ersatzlos entfernt.

---

## Typografie-Überarbeitung (Juni 2026, 5 Commits)

- **Neue Schriften:** Inter (Body, 400/600) statt DM Sans, Bricolage Grotesque
  (Headlines, 600–800) statt Syne, JetBrains Mono (400/700) statt Space Mono —
  mit Fallback-Stacks und Preconnect zu fonts.gstatic.com.
- **Mono-Reduktion:** Mono nur noch für Code-Blöcke, Listen-Nummern und
  Paketnamen/Versionen; alle Meta-Zeilen, Buttons, Tabs, Badges und Labels
  in der Body-Schrift (Gewicht 600, Uppercase/Letter-Spacing bleibt).
- **Lesetypografie im Modal:** 17px (mobil 16px), line-height 1.7, max. 65ch
  Zeilenlänge, hyphens: auto, text-wrap pretty/balance, neue Variable
  `--text-read` (≥ 7:1 Kontrast); `--text-3` auf ≥ 4.5:1 korrigiert.
- **Größenskala:** `--fs-xxs` (11px) bis `--fs-xxl` als Variablen, nichts mehr
  unter 11px, Teaser 14px, Hero-/Editions-Titel mit `clamp()`.
- **`styles/base.css`:** gemeinsame Design-Tokens, Reset und Nav-Styles aus
  index.html + dashboard.html zusammengeführt (keine Duplizierung mehr).
- Nicht angefasst: `impressum.html` und das Generator-Template
  (`generator.py` → `artikel/*.html`) nutzen noch die alten Fonts.

---

## ⚠️ Offene manuelle Schritte

1. **API-Keys rotieren** (alte Keys stehen in der Git-Historie!):
   - Voyage AI: https://dash.voyageai.com
   - Unsplash: https://unsplash.com/oauth/applications
2. **Worker deployen:** `cd worker && wrangler secret put GROQ_API_KEY && wrangler deploy`
   (Anleitung: `worker/README.md`)
3. **Worker-URL eintragen:** in `index.html` die Konstante `EXPLAIN_API_URL`
   auf die deployte Worker-URL setzen.
4. **`.env` anlegen** (aus `.env.example`) für lokale Generator-Läufe.
5. **`embeddings.json` sichern:** Datei ist gitignored — bei Verlust werden beim
   nächsten Lauf alle Embeddings via Voyage neu erzeugt (Backfill, kostet API-Calls).
6. Optional: alte `images/*.jpg` nach WebP konvertieren (neue Artikel kommen
   automatisch als WebP + Small-Variante).
