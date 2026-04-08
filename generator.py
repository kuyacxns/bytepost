import requests, json, os, re, feedparser, time
from datetime import datetime

# --- SETUP ---
API_KEY = "AIzaSyCDjSDM3y_DtRGCkveILJma8dH-paEq284"
UNSPLASH_KEY = "QQzUWbAsN6W9yoMZctADAd7ovx1CurH6-HxfaXzuwPE"
TEXT_MODEL = "gemini-2.5-flash"
DATA_FILE = "data.json"

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
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_MODEL}:generateContent?key={API_KEY}"
    heute = datetime.now().strftime("%d.%m.%Y")

    prompt = f"""Du bist nicht nur ein KI-Bot, sondern der Host von 'BytePost', dem frechsten Tech-Newsletter für Deutschlands Entwickler-Elite. Deine Leser sind Profis in Python, SQL, Kubernetes und Cloud-Architektur.

Analysiere diesen Artikel: {url}

DEINE MISSION:
Schreibe eine fesselnde, extrem kompakte Zusammenfassung auf Deutsch, die den Leser direkt packt.

STIL-GUIDE FÜR 'BYTEPOST':
1. **Direkte Ansprache:** Nutze die "Du"-Form ("Du solltest wissen...", "Stell dir vor...").
2. **Persönlichkeit:** Sei journalistisch, aber mit einer Prise Ironie, Begeisterung oder gesundem Skeptizismus. Kein trockenes Bla-Bla!
3. **Länge:** Der gesamte 'content' darf ABSOLUT MAXIMAL 800 ZEICHEN (inklusive Leerzeichen) haben.
4. **Tech-Sprech:** Nutze Fachbegriffe (LLM, Sharding, Latenz, CI/CD) ohne sie zu erklären.
5. **Keine Verweise:** Sätze wie "Lies mehr im Original" sind streng verboten. Sei die alleinige Wissensquelle.

FORMATIERUNG IM CONTENT:
- Nutze `<strong>...</strong>` für die 2-3 wichtigsten Kernbegriffe.
- Nutze eine kurze Liste `<ul><li>...</li></ul>` für maximal 3 technische Highlights.
- Keine H3-Überschriften, keine summary-box. Nur flüssiger Text und die Liste.

ZUSÄTZLICH erzeuge zwei Varianten:
- content_simple: Selbes Thema, ohne Fachbegriffe, mit Alltagsanalogien. Für Tech-Einsteiger. Reines HTML wie content, max. 600 Zeichen.
- content_pro: Selbes Thema, mit mehr technischen Details und Architektur-Implikationen. Reines HTML wie content, max. 1000 Zeichen.

SENTIMENT: Bewerte den Artikel als genau einen dieser Werte:
- "positiv" → Innovation, Fortschritt, Verbesserung
- "neutral" → Ankündigung, Update, Information
- "kritisch" → Problem, Risiko, Datenschutz, Sicherheitslücke, Kontroverse

Erstelle exakt dieses JSON-Objekt (kein Text davor/danach, keine Markdown-Backticks):
{{
    "cat": "ki|dev|data|security|cloud|hardware|business",
    "tag": "Exakt ein Wert aus: KI, Dev, Data, Security, Cloud, Hardware, Business",
    "icon": "Passendes Emoji",
    "title": "Klickstarke, freche Headline (max. 10 Wörter)",
    "source": "Quellenname",
    "read": "X Min",
    "image_query": "2 englische Suchbegriffe für ein cooles Unsplash-Foto",
    "sentiment": "positiv|neutral|kritisch",
    "content": "HTML-String Standard-Version (max. 800 Zeichen, Du-Form, fette Begriffe, 1 Liste)",
    "content_simple": "HTML-String Einfach-Version ohne Fachbegriffe (max. 600 Zeichen)",
    "content_pro": "HTML-String Profi-Version mit technischen Details (max. 1000 Zeichen)"
}}
"""

    try:
        r = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]})
        print(f"  -> Gemini Status: {r.status_code}")
        raw = r.json()['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(re.sub(r'```json|```', '', raw).strip())
        data["date"] = heute
        word_count = len(data.get("content", "").split())
        print(f"  -> Inhalt: ~{word_count} Woerter, Sentiment: {data.get('sentiment', 'unbekannt')}")
        return data
    except Exception as e:
        print(f"  -> Gemini Fehler: {e}")
        print(f"  -> Rohantwort: {r.text[:300]}")
        return None

def compute_bytepulse(articles, today_str):
    """Berechne das Stimmungsbarometer für alle Artikel des heutigen Tages."""
    today_articles = [a for a in articles if a.get("date") == today_str]
    if not today_articles:
        return None
    counts = {"positiv": 0, "neutral": 0, "kritisch": 0}
    for a in today_articles:
        s = a.get("sentiment", "neutral")
        if s in counts:
            counts[s] += 1
        else:
            counts["neutral"] += 1
    total = sum(counts.values())
    if total == 0:
        return None
    return {
        "date": today_str,
        "positiv": round(counts["positiv"] / total * 100),
        "neutral": round(counts["neutral"] / total * 100),
        "kritisch": round(counts["kritisch"] / total * 100),
        "total": total
    }

def find_related(article, all_articles, limit=3):
    """Finde verwandte Artikel basierend auf Tag und Kategorie."""
    related = []
    for a in all_articles:
        if a.get("id") == article.get("id"):
            continue
        if a.get("tag") == article.get("tag") or a.get("cat") == article.get("cat"):
            related.append(a["id"])
        if len(related) >= limit:
            break
    return related

def run():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: db = json.load(f)
    else: db = {"articles": []}

    existing_titles = {a.get('title', '') for a in db['articles']}
    new_count = 0
    heute = datetime.now().strftime("%d.%m.%Y")
    new_articles = []

    for feed_url, category in RSS_FEEDS:
        if new_count >= 10:
            break
        try:
            feed = feedparser.parse(feed_url)
            print(f"\nFeed: {feed_url} ({len(feed.entries)} Eintraege)")
        except Exception as e:
            print(f"Feed-Fehler: {e}")
            continue

        for post in feed.entries[:2]:
            if new_count >= 10:
                break
            if post.title in existing_titles:
                print(f"  -> Duplikat: {post.title[:50]}")
                continue

            print(f"Verarbeite: {post.title[:60]}")
            entry = ask_gemini(post.link, category)
            if entry:
                entry["id"] = os.urandom(4).hex()
                entry["url"] = post.link
                entry["reactions"] = {"fire": 0, "think": 0, "bulb": 0, "sleep": 0}
                image_query = entry.pop("image_query", "technology")
                entry["image_local"] = get_unsplash_image(image_query, entry["id"])
                db['articles'].insert(0, entry)
                new_articles.append(entry)
                existing_titles.add(post.title)
                new_count += 1
                print(f"  -> Erstellt: {entry['title']} ({new_count}/10)")
                time.sleep(30)

    # Pick of the Day: erster (neuester) Artikel des heutigen Tages
    for a in db['articles']:
        a.setdefault("pick", False)
        a["pick"] = False
    today_articles = [a for a in db['articles'] if a.get("date") == heute]
    if today_articles:
        today_articles[0]["pick"] = True
        print(f"\nPick of the Day: {today_articles[0]['title']}")

    # Related articles für neue Artikel berechnen
    for article in new_articles:
        article["related"] = find_related(article, db['articles'])

    # BytePulse Stimmungsbarometer
    pulse = compute_bytepulse(db['articles'], heute)
    if pulse:
        db["bytepulse"] = pulse
        print(f"BytePulse: {pulse['positiv']}% positiv, {pulse['neutral']}% neutral, {pulse['kritisch']}% kritisch")

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
    print(f"\nFertig. {new_count} neue Artikel erstellt.")

if __name__ == "__main__":
    run()
