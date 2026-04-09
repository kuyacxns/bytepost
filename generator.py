import requests, json, os, re, feedparser, time
from datetime import datetime
from bs4 import BeautifulSoup

# --- SETUP ---
# API-Key als Umgebungsvariable setzen:
#   export GROQ_API_KEY="gsk_..."
# Kostenloser Account: https://console.groq.com
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
UNSPLASH_KEY = "QQzUWbAsN6W9yoMZctADAd7ovx1CurH6-HxfaXzuwPE"
MODEL = "llama-3.3-70b-versatile"  # Kostenlos, sehr gute Qualität
DATA_FILE = "data.json"

# --- COST PROTECTION ---
MAX_PER_RUN = 10    # max. neue Artikel pro Generator-Lauf
MAX_PER_DAY = 15    # max. neue Artikel pro Tag (Tagessperre)
MAX_ERRORS  = 3     # Circuit Breaker: Abbruch nach N aufeinanderfolgenden Fehlern

# --- RSS FEEDS ---
RSS_FEEDS = [
    # Internationale Top-Quellen
    ("https://techcrunch.com/category/artificial-intelligence/feed/", "KI"),
    ("https://techcrunch.com/category/software/feed/", "Dev"),
    ("https://www.theverge.com/rss/index.xml", "Tech"),
    ("https://feeds.arstechnica.com/arstechnica/technology-lab", "Dev"),
    # Developer fokussiert
    ("https://stackoverflow.blog/feed/", "Dev"),
    ("https://github.blog/feed/", "Dev"),
    ("https://engineering.atspotify.com/feed/", "Dev"),
    # Data / AI / ML
    ("https://towardsdatascience.com/feed", "Data"),
    ("https://blogs.microsoft.com/ai/feed/", "KI"),
    ("https://openai.com/blog/rss/", "KI"),
    # Deutsche Quellen
    ("https://www.heise.de/developer/rss/news-atom.xml", "Dev"),
    ("https://www.golem.de/rss.php?tp=dev", "Dev"),
]

def get_unsplash_image(query, article_id):
    try:
        url = f"https://api.unsplash.com/photos/random?query={query}&orientation=landscape&client_id={UNSPLASH_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        img_url = data["urls"]["regular"]
        img_data = requests.get(img_url, timeout=30).content
        if not os.path.exists("images"): os.makedirs("images")
        path = f"images/{article_id}.jpg"
        with open(path, "wb") as f: f.write(img_data)
        print(f"  -> Bild gespeichert: {path}")
        return path
    except Exception as e:
        print(f"  -> Bildfehler: {e}")
        return None

def fetch_article_text(url, max_chars=8000):
    """Lädt den Artikel und extrahiert den Haupttext."""
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        # Boilerplate entfernen
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        # Haupttext aus <article> oder <main> oder <body>
        main = soup.find("article") or soup.find("main") or soup.find("body")
        text = " ".join((main or soup).get_text(separator=" ").split())
        return text[:max_chars]
    except Exception as e:
        print(f"  -> Artikel-Fetch Fehler: {e}")
        return ""

def ask_gemini(url, category, rss_title="", rss_summary=""):
    heute = datetime.now().strftime("%d.%m.%Y")

    print(f"  -> Lade Artikel...")
    article_text = fetch_article_text(url)

    # Kombiniere RSS-Summary + gescrapten Text für maximalen Kontext
    combined = " ".join(filter(None, [rss_title, rss_summary, article_text]))
    source_block = f"ARTIKELINHALT:\n{combined[:4500]}" if combined.strip() else f"URL: {url}"

    prompt = f"""Du bist Redakteur bei 'BytePost', einem deutschen Tech-Newsletter für Entwickler.

{source_block}

DEINE AUFGABE:
Übersetze und übertrage diesen Artikel vollständig ins Deutsche. Der Leser soll nach dem Lesen deines Textes den Originalartikel nicht mehr aufrufen müssen — er hat alle Informationen. Nutze ALLE Fakten, Zitate, Zahlen und Details aus dem Originaltext.

STIL:
- Fließender, gut lesbarer Journalismus auf Deutsch
- Direkte "Du"-Ansprache wo es passt
- Konkrete Fakten und Zitate aus dem Original behalten
- Am Ende: kurze eigene Einordnung für Entwickler

FORMAT für "content" (vollständiger Artikel auf Deutsch):
- <h3>kurze Zwischenüberschriften</h3> zur Strukturierung
- Mehrere <p>-Absätze mit dem vollständigen Inhalt des Originals
- <ul> für Aufzählungen aus dem Original
- Abschluss: <p><em>BytePost-Einordnung: ...</em></p>
- Länge: 400-600 Wörter — so lang wie nötig um den vollen Artikel abzudecken

FORMAT für "content_simple" (kompakte Version für Einsteiger):
- Kernaussagen ohne Fachbegriffe, mit Alltagsvergleichen
- 150-200 Wörter, gleiche HTML-Struktur ohne h3

SENTIMENT: "positiv" (Fortschritt/Innovation), "neutral" (Update/Info), "kritisch" (Risiko/Sicherheitsproblem/Kontroverse)

Antworte NUR mit diesem JSON (keine Backticks, kein Text davor/danach):
{{
    "cat": ["ki"],
    "icon": "Passendes Emoji",
    "title": "Prägnante Headline, max. 8 Wörter",
    "source": "Echter Name der Originalquelle (z.B. TechCrunch, The Verge, GitHub Blog) — NICHT 'BytePost'",
    "read": "X Min",
    "image_query": "2 englische Suchbegriffe für Unsplash",
    "sentiment": "positiv|neutral|kritisch",
    "content": "Vollständiger Artikel auf Deutsch (HTML mit h3, p, ul)",
    "content_simple": "Kompakte Version für Einsteiger (HTML)"
}}

"cat" ist ein JSON-Array mit 1-3 passenden Kategorien aus: ki, dev, data, security, cloud, hardware, business
Beispiele: ["ki"] oder ["ki","dev"] oder ["security","ki"]"""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 3000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        print(f"  -> Groq Status: {r.status_code}")
        if r.status_code != 200:
            print(f"  -> Fehler: {r.text[:200]}")
            return None

        raw = r.json()["choices"][0]["message"]["content"].strip()
        clean = re.sub(r"```json|```", "", raw).strip()
        # Literal-Newlines in JSON-Strings sind ungültig — durch Leerzeichen ersetzen
        clean = re.sub(r'\n', ' ', clean)
        data = json.loads(clean)
        # Normalize cat to always be a list of clean lowercase strings
        cat = data.get("cat", ["ki"])
        if isinstance(cat, str):
            cat = [c.strip().lower() for c in re.split(r'[|/,]+', cat) if c.strip()]
        else:
            cat = [c.strip().lower() for c in cat if c.strip()]
        valid = {"ki", "dev", "data", "security", "cloud", "hardware", "business"}
        cat = [c for c in cat if c in valid] or ["ki"]
        data["cat"] = cat
        data.pop("tag", None)  # tag field no longer needed
        # Never let source be "BytePost" — derive from URL if needed
        SOURCE_MAP = {
            'techcrunch.com': 'TechCrunch', 'theverge.com': 'The Verge',
            'arstechnica.com': 'Ars Technica', 'stackoverflow.blog': 'Stack Overflow Blog',
            'github.blog': 'GitHub Blog', 'towardsdatascience.com': 'Towards Data Science',
            'engineering.atspotify.com': 'Spotify Engineering', 'openai.com': 'OpenAI',
            'heise.de': 'Heise Developer', 'golem.de': 'Golem',
            'blogs.microsoft.com': 'Microsoft AI Blog',
        }
        if not data.get('source') or data.get('source') in ('BytePost', 'Quellenname'):
            for domain, name in SOURCE_MAP.items():
                if domain in url:
                    data['source'] = name
                    break
        data["date"] = heute
        tokens = r.json().get("usage", {})
        print(f"  -> OK | Cats: {cat} | Sentiment: {data.get('sentiment','?')} | Tokens: {tokens.get('total_tokens','?')}")
        return data
    except json.JSONDecodeError as e:
        print(f"  -> JSON-Fehler: {e} | Antwort: {raw[:200]}")
        return None
    except Exception as e:
        print(f"  -> Fehler: {e}")
        return None

def compute_bytepulse(articles, today_str):
    today_articles = [a for a in articles if a.get("date") == today_str]
    if not today_articles: return None
    counts = {"positiv": 0, "neutral": 0, "kritisch": 0}
    for a in today_articles:
        s = a.get("sentiment", "neutral")
        counts[s if s in counts else "neutral"] += 1
    total = sum(counts.values())
    return {
        "date": today_str,
        "positiv": round(counts["positiv"] / total * 100),
        "neutral": round(counts["neutral"] / total * 100),
        "kritisch": round(counts["kritisch"] / total * 100),
        "total": total,
    }

def find_related(article, all_articles, limit=3):
    related = []
    for a in all_articles:
        if a.get("id") == article.get("id"): continue
        if a.get("tag") == article.get("tag") or a.get("cat") == article.get("cat"):
            related.append(a["id"])
        if len(related) >= limit: break
    return related

def pick_of_the_day(today_articles):
    """Lässt die KI den relevantesten Artikel wählen und begründen."""
    if len(today_articles) == 1:
        return today_articles[0]

    overview = "\n".join(
        f"{i+1}. [{a.get('tag','')}] {a.get('title','')} — {a.get('source','')} ({a.get('sentiment','')})"
        for i, a in enumerate(today_articles)
    )

    prompt = f"""Du kuratierst 'BytePost', einen deutschen Tech-Newsletter für Entwickler.

Hier sind die heutigen Artikel:
{overview}

Welcher Artikel verdient heute den "Pick of the Day"? Kriterien:
- Hohe Relevanz für Entwickler und Tech-Profis
- Nachhaltiger Impact oder besondere Brisanz
- Lieber überraschend oder kontrovers als generisch

Antworte NUR mit diesem JSON (keine Backticks, kein Text davor/danach):
{{"id": <Nummer>, "reason": "<1-2 Sätze warum dieser Artikel heute besonders wichtig ist — direkt, meinungsstark, auf Deutsch>"}}"""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 120,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        if r.status_code == 200:
            raw = r.json()["choices"][0]["message"]["content"].strip()
            result = json.loads(re.sub(r"```json|```", "", raw).strip())
            idx = int(result["id"]) - 1
            if 0 <= idx < len(today_articles):
                reason = result.get("reason", "")
                print(f"  -> KI wählt Artikel #{idx+1}: {reason}")
                today_articles[idx]["pick_reason"] = reason
                return today_articles[idx]
    except Exception as e:
        print(f"  -> Pick-Fehler: {e}")

    # Fallback: erster Artikel
    return today_articles[0]


def run():
    if not GROQ_API_KEY:
        print("FEHLER: GROQ_API_KEY nicht gesetzt.")
        print("  export GROQ_API_KEY='gsk_...'")
        print("  Kostenloser Account: https://console.groq.com")
        return

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = {"articles": []}

    heute = datetime.now().strftime("%d.%m.%Y")

    # Tagessperre prüfen
    today_count = sum(1 for a in db["articles"] if a.get("date") == heute)
    if today_count >= MAX_PER_DAY:
        print(f"Tageslimit erreicht ({today_count}/{MAX_PER_DAY}). Abbruch.")
        return

    remaining_today = MAX_PER_DAY - today_count
    effective_limit = min(MAX_PER_RUN, remaining_today)
    print(f"Heute bereits: {today_count} | Noch erlaubt: {remaining_today} | Diesen Lauf max: {effective_limit}")

    existing_urls = {a.get("url", "") for a in db["articles"] if a.get("url")}
    new_count = 0
    error_streak = 0
    new_articles = []

    for feed_url, category in RSS_FEEDS:
        if new_count >= effective_limit: break
        try:
            feed = feedparser.parse(feed_url)
            print(f"\nFeed: {feed_url} ({len(feed.entries)} Einträge)")
        except Exception as e:
            print(f"Feed-Fehler: {e}")
            continue

        for post in feed.entries[:2]:
            if new_count >= effective_limit: break
            if post.link in existing_urls:
                print(f"  -> Duplikat (URL): {post.title[:50]}")
                continue

            print(f"Verarbeite: {post.title[:60]}")
            rss_title = getattr(post, "title", "")
            rss_summary = getattr(post, "summary", "") or getattr(post, "description", "")
            # HTML aus RSS-Summary entfernen
            rss_summary = BeautifulSoup(rss_summary, "html.parser").get_text(separator=" ")[:2000]
            entry = ask_gemini(post.link, category, rss_title, rss_summary)

            if entry is None:
                error_streak += 1
                print(f"  -> Fehler-Serie: {error_streak}/{MAX_ERRORS}")
                if error_streak >= MAX_ERRORS:
                    print("Circuit Breaker ausgelöst. Abbruch.")
                    break
                continue

            error_streak = 0
            entry["id"] = os.urandom(4).hex()
            entry["url"] = post.link
            entry["reactions"] = {"fire": 0, "think": 0, "bulb": 0, "sleep": 0}
            image_query = entry.pop("image_query", "technology")
            entry["image_local"] = get_unsplash_image(image_query, entry["id"])
            db["articles"].insert(0, entry)
            new_articles.append(entry)
            existing_urls.add(post.link)
            new_count += 1
            print(f"  -> Erstellt: {entry['title']} ({new_count}/{effective_limit})")
            time.sleep(20)

        else:
            continue
        break  # Circuit Breaker hat inneren Loop verlassen

    # Pick of the Day — KI entscheidet
    for a in db["articles"]: a["pick"] = False
    today_articles = [a for a in db["articles"] if a.get("date") == heute]
    if today_articles:
        pick = pick_of_the_day(today_articles)
        pick["pick"] = True
        print(f"\nPick of the Day: {pick['title']}")

    # Related Articles
    for article in new_articles:
        article["related"] = find_related(article, db["articles"])

    # BytePulse
    pulse = compute_bytepulse(db["articles"], heute)
    if pulse:
        db["bytepulse"] = pulse
        print(f"BytePulse: {pulse['positiv']}% positiv, {pulse['neutral']}% neutral, {pulse['kritisch']}% kritisch")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
    print(f"\nFertig. {new_count} neue Artikel erstellt.")

if __name__ == "__main__":
    run()
