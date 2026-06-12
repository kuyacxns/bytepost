/**
 * BytePost Explain-Proxy — Cloudflare Worker
 *
 * Proxy für Groq Chat Completions. Der Groq-Key liegt als Worker-Secret
 * (GROQ_API_KEY) und verlässt nie den Worker. Statt freier Prompts werden
 * nur Artikel-ID + Modus ("simple" | "pro") akzeptiert; der Prompt wird
 * serverseitig aus data.json gebaut.
 */

const ALLOWED_ORIGINS = [
    'https://bytepost.de',
    'https://www.bytepost.de',
];
const DATA_URL   = 'https://bytepost.de/data.json';
const GROQ_MODEL = 'llama-3.3-70b-versatile';

// Simples Rate-Limiting pro IP (best-effort, pro Worker-Isolate)
const RATE_LIMIT_MAX    = 10;        // Requests
const RATE_LIMIT_WINDOW = 60 * 1000; // pro Minute
const rateMap = new Map();           // ip -> [timestamps]

function rateLimited(ip) {
    const now = Date.now();
    const hits = (rateMap.get(ip) || []).filter(t => now - t < RATE_LIMIT_WINDOW);
    if (hits.length >= RATE_LIMIT_MAX) return true;
    hits.push(now);
    rateMap.set(ip, hits);
    if (rateMap.size > 5000) rateMap.clear(); // Speicher begrenzen
    return false;
}

function corsHeaders(origin) {
    const allowed = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
    return {
        'Access-Control-Allow-Origin': allowed,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400',
    };
}

function jsonResponse(body, status, origin) {
    return new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) },
    });
}

function buildPrompt(mode, article) {
    const plain = (article.content || '').replace(/<[^>]+>/g, '').slice(0, 1500);
    if (mode === 'simple') {
        return `Du erklärst Tech-Themen für Nicht-Techniker auf Deutsch. Erkläre diesen Artikel ohne Fachbegriffe, mit Alltagsvergleichen, kurzen Sätzen. Format: <p>, <ul>. 100-150 Wörter. Nur HTML.\n\nTitel: ${article.title}\nInhalt: ${plain}`;
    }
    return `Du bist Senior Engineer und erklärst Tech-News für Entwickler auf Deutsch. Füge technische Tiefe hinzu: Architektur, Protokolle, interne Abläufe, Metriken, Trade-offs und Implikationen für die Praxis. Nutze <h3>, <p>, <ul>. Füge NUR dann einen <pre><code>-Block hinzu, wenn im Originalartikel tatsächlich konkreter Code vorkommt – ansonsten lass ihn weg. Keine erfundenen Beispiele. 150-250 Wörter. Nur HTML.\n\nTitel: ${article.title}\nInhalt: ${plain}`;
}

export default {
    async fetch(request, env, ctx) {
        const origin = request.headers.get('Origin') || '';

        if (request.method === 'OPTIONS') {
            return new Response(null, { status: 204, headers: corsHeaders(origin) });
        }
        if (request.method !== 'POST') {
            return jsonResponse({ error: 'Method not allowed' }, 405, origin);
        }
        if (origin && !ALLOWED_ORIGINS.includes(origin)) {
            return jsonResponse({ error: 'Origin not allowed' }, 403, origin);
        }

        const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
        if (rateLimited(ip)) {
            return jsonResponse({ error: 'Rate limit — bitte kurz warten.' }, 429, origin);
        }

        let body;
        try { body = await request.json(); } catch {
            return jsonResponse({ error: 'Invalid JSON' }, 400, origin);
        }

        const { id, mode } = body || {};
        if (typeof id !== 'string' || !/^[a-f0-9]{8}$/.test(id) || !['simple', 'pro'].includes(mode)) {
            return jsonResponse({ error: 'Erwartet: { id: "<8 hex>", mode: "simple"|"pro" }' }, 400, origin);
        }

        // data.json laden (Edge-Cache, 5 Minuten)
        const dataRes = await fetch(DATA_URL, { cf: { cacheTtl: 300, cacheEverything: true } });
        if (!dataRes.ok) return jsonResponse({ error: 'data.json nicht erreichbar' }, 502, origin);
        const db = await dataRes.json();
        const article = (db.articles || []).find(a => a.id === id);
        if (!article) return jsonResponse({ error: 'Artikel nicht gefunden' }, 404, origin);

        const groqRes = await fetch('https://api.groq.com/openai/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${env.GROQ_API_KEY}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: GROQ_MODEL,
                max_tokens: 1200,
                messages: [{ role: 'user', content: buildPrompt(mode, article) }],
            }),
        });
        if (!groqRes.ok) {
            return jsonResponse({ error: `Groq API ${groqRes.status}` }, 502, origin);
        }
        const data = await groqRes.json();
        const content = (data.choices?.[0]?.message?.content || '').replace(/```html|```/g, '').trim();
        return jsonResponse({ content }, 200, origin);
    },
};
