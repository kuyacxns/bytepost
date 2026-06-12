# BytePost Explain-Proxy (Cloudflare Worker)

Proxy für die On-Demand-KI-Erklärungen („Einfach erklärt" / „Für Profis").
Der Groq-Key liegt als Worker-Secret — **nicht** mehr im Frontend.

## Deploy

```bash
npm install -g wrangler
cd worker/
wrangler login
wrangler secret put GROQ_API_KEY   # Key eingeben, kommt von console.groq.com
wrangler deploy
```

Der Deploy gibt die Worker-URL aus, z.B.
`https://bytepost-explain.<account>.workers.dev`.

## Frontend verbinden

In `index.html` die Konstante am Anfang des `<script>`-Blocks anpassen:

```js
const EXPLAIN_API_URL = 'https://bytepost-explain.<account>.workers.dev';
```

## API

```
POST /
Content-Type: application/json

{ "id": "<8-stellige Artikel-ID>", "mode": "simple" | "pro" }

→ 200: { "content": "<html>" }
→ 400/403/404/429/502: { "error": "..." }
```

## Eigenschaften

- Nur die zwei festen Prompt-Typen — keine freien Prompts möglich
- Artikel-Inhalt wird serverseitig aus `https://bytepost.de/data.json` geladen (5 Min Edge-Cache)
- Rate-Limiting: 10 Requests/Minute pro IP (best-effort, pro Worker-Isolate)
- CORS nur für `bytepost.de` / `www.bytepost.de` (Liste in `worker.js` → `ALLOWED_ORIGINS`)
