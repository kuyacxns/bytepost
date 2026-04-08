import requests, json, os, re, feedparser, time
from datetime import datetime

# --- SETUP ---
# API-Key als Umgebungsvariable setzen:
#   export OPENROUTER_API_KEY="sk-or-..."
# Oder direkt hier eintragen (nicht empfohlen für öffentliche Repos):
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
UNSPLASH_KEY = "QQzUWbAsN6W9yoMZctADAd7ovx1CurH6-HxfaXzuwPE"
MODEL = "google/gemini-2.5-flash"   # Gemini via OpenRouter
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

def ask_gemini(url, category):
    heute = datetime.now().strftime("%d.%m.%Y")
    prompt = f"""Du bist der Host von 'BytePost', dem frechsten Tech-Newsletter für Deutschlands Entwickler-Elite. Deine Leser sind Profis in Python, SQL, Kubernetes und Cloud-Architektur.

Analysiere diesen Artikel: {url}

STIL-GUIDE:
1. "Du"-Form, journalistisch mit Ironie oder Skepsis. Kein Bla-Bla.
2. content: MAX 800 ZEICHEN. Nutze <strong> für 2-3 Kernbegriffe, eine <ul> mit max. 3 Highlights.
3. content_simple: Ohne Fachbegriffe, Alltagsanalogien, max. 500 Zeichen.
4. content_pro: Technische Details + Architektur-Implikationen, max. 900 Zeichen.
5. Keine Sätze wie "Lies mehr im Original".

SENTIMENT: "positiv" (Innovation), "neutral" (Update/Info), "kritisch" (Risiko/Sicherheit/Datenschutz)

Antworte NUR mit diesem JSON (keine Backticks, kein Text davor/danach):
{{
    "cat": "ki|dev|data|security|cloud|hardware|business",
    "tag": "KI|Dev|Data|Security|Cloud|Hardware|Business",
    "icon": "Passendes Emoji",
    "title": "Freche Headline max. 10 Wörter",
    "source": "Quellenname",
    "read": "X Min",
    "image_query": "2 englische Suchbegriffe für Unsplash",
    "sentiment": "positiv|neutral|kritisch",
    "content": "HTML Standard-Version",
    "content_simple": "HTML Einfach-Version",
    "content_pro": "HTML Profi-Version"
}}"""

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://bytepost.de",
                "X-Title": "BytePost Generator",
            },
            json={
                "model": MODEL,
                "max_tokens": 700,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        print(f"  -> OpenRouter Status: {r.status_code}")
        if r.status_code != 200:
            print(f"  -> Fehler: {r.text[:200]}")
            return None

        raw = r.json()["choices"][0]["message"]["content"].strip()
        data = json.loads(re.sub(r"```json|```", "", raw).strip())
        data["date"] = heute
        tokens = r.json().get("usage", {})
        print(f"  -> OK | Sentiment: {data.get('sentiment','?')} | Tokens: {tokens.get('total_tokens','?')}")
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

def run():
    if not OPENROUTER_API_KEY:
        print("FEHLER: OPENROUTER_API_KEY nicht gesetzt.")
        print("  export OPENROUTER_API_KEY='sk-or-...'")
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

    existing_titles = {a.get("title", "") for a in db["articles"]}
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
            if post.title in existing_titles:
                print(f"  -> Duplikat: {post.title[:50]}")
                continue

            print(f"Verarbeite: {post.title[:60]}")
            entry = ask_gemini(post.link, category)

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
            existing_titles.add(post.title)
            new_count += 1
            print(f"  -> Erstellt: {entry['title']} ({new_count}/{effective_limit})")
            time.sleep(5)

        else:
            continue
        break  # Circuit Breaker hat inneren Loop verlassen

    # Pick of the Day
    for a in db["articles"]: a["pick"] = False
    today_articles = [a for a in db["articles"] if a.get("date") == heute]
    if today_articles:
        today_articles[0]["pick"] = True
        print(f"\nPick of the Day: {today_articles[0]['title']}")

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
