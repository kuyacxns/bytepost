# BytePost

Deutsche Tech-News täglich in 5 Minuten — statische Website (Vanilla HTML/CSS/JS) + Python-Generator.

Ausführliche Projektdokumentation: siehe [PROJEKT.md](./PROJEKT.md).

## ⚠️ Sicherheitshinweis: API-Keys rotieren

In früheren Versionen dieses Repositories waren API-Keys **im Klartext in `generator.py`** enthalten
(Voyage AI und Unsplash). Diese Keys sind über die Git-Historie weiterhin einsehbar und **müssen
rotiert (neu erstellt und die alten widerrufen) werden**:

- **Voyage AI:** https://dash.voyageai.com → alten Key löschen, neuen erstellen
- **Unsplash:** https://unsplash.com/oauth/applications → Access Key neu generieren

Das kann nur der Account-Inhaber selbst tun.

## Setup

```bash
pip install requests feedparser beautifulsoup4 Pillow

cp .env.example .env   # Keys eintragen — .env ist gitignored
python generator.py    # täglicher Lauf: Feeds → Artikel → data.json
```

Alle drei Keys (`GROQ_API_KEY`, `VOYAGE_API_KEY`, `UNSPLASH_ACCESS_KEY`) sind Pflicht;
ohne sie bricht der Generator mit einer Fehlermeldung ab.

## KI-Erklärmodi (Frontend)

Die On-Demand-Generierung („Einfach erklärt" / „Für Profis") läuft über einen
Cloudflare Worker als Proxy — der Groq-Key liegt **nicht** mehr im Frontend.
Deploy-Anleitung: [worker/README.md](./worker/README.md).
