import requests, json, os, re, feedparser, time
from datetime import datetime

# --- SETUP ---
API_KEY = "AIzaSyCDjSDM3y_DtRGCkveILJma8dH-paEq284"
UNSPLASH_KEY = "QQzUWbAsN6W9yoMZctADAd7ovx1CurH6-HxfaXzuwPE"
TEXT_MODEL = "gemini-2.5-flash"
DATA_FILE = "data.json"

# --- RSS FEEDS ---
# Kuratierte Quellen für Entwickler & Data Engineers
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

    prompt = f"""Du bist ein professioneller Tech-Journalist der speziell fuer Softwareentwickler, Data Engineers und KI-Experten in Deutschland schreibt.

Analysiere diesen Artikel vollstaendig: {url}

WICHTIG: Der content-Wert MUSS mindestens 1000 Woerter lang sein. Kuerzere Antworten sind UNGUELTIG und werden verworfen.

Erstelle ein JSON-Objekt fuer den BytePost Newsletter:
{{
    "cat": "ki/dev/data/security/cloud/hardware/business",
    "tag": "Exakt ein Wert aus: KI, Dev, Data, Security, Cloud, Hardware, Business",
    "icon": "Emoji",
    "title": "Praegnante deutsche Headline (max. 10 Woerter)",
    "source": "Quellenname",
    "read": "5 Min",
    "image_query": "2-3 englische Suchbegriffe fuer passendes Foto (z.B. 'machine learning code')",
    "content": "MINDESTENS 1000 WOERTER HTML"
}}

Kategorien:
- KI/ML/LLMs: cat=ki, tag=KI
- Software/Tools/Frameworks: cat=dev, tag=Dev
- Data Engineering/Analytics: cat=data, tag=Data
- Cloud/DevOps/Infrastructure: cat=cloud, tag=Cloud
- Security/Privacy: cat=security, tag=Security
- Hardware/Chips: cat=hardware, tag=Hardware
- Business/Startups: cat=business, tag=Business

Schreibe fuer ein Publikum das: Python, SQL, Spark, Databricks, dbt, Kubernetes, Docker kennt.
Nutze Fachbegriffe ohne sie zu erklaeren. Gehe tief in technische Details.

ABSOLUT VERBOTEN im content:
- Saetze wie "Lesen Sie den Originalartikel fuer mehr Details"
- Saetze wie "Laut dem Originalbericht" oder "Gemaess dem Quelltext"
- Jegliche Aufforderung, eine externe Quelle zu besuchen
- Formulierungen wie "weitere Informationen finden Sie unter" oder "der vollstaendige Artikel beschreibt"
Ziel: Ein eigenstaendiger journalistischer Bericht — alle relevanten Informationen sind enthalten.
Schreibe direkte Aussagen: Nicht "Laut Bericht hat X..." sondern "X hat...".

Der content MUSS diese Struktur haben:

<div class='summary-box'><h4>Highlights</h4><ul><li>Technischer Fakt 1</li><li>Technischer Fakt 2</li><li>Technischer Fakt 3</li><li>Technischer Fakt 4</li></ul></div>

<h3>Hintergrund</h3>
<p>MINDESTENS 5 Saetze: Technischer Kontext und Vorgeschichte — erklaere den Stand der Technik vor dieser Neuigkeit.</p>
<p>MINDESTENS 5 Saetze: Beteiligte Technologien, Unternehmen, Standards, Protokolle, Versionen.</p>

<h3>Was ist neu?</h3>
<p>MINDESTENS 4 Saetze: Genaue technische Details der Neuerung.</p>
<p>MINDESTENS 4 Saetze: Benchmarks, Metriken, Spezifikationen.</p>

<h3>Praxisrelevanz fuer Entwickler</h3>
<p>MINDESTENS 4 Saetze: Konkrete Auswirkungen auf den Arbeitsalltag.</p>
<p>MINDESTENS 4 Saetze: Welche Workflows, Tools oder Architekturen aendern sich?</p>

<h3>Kritische Perspektive</h3>
<p>MINDESTENS 4 Saetze: Schwachstellen, Trade-offs, offene Fragen.</p>
<p>MINDESTENS 4 Saetze: Vergleich mit bestehenden Loesungen.</p>

<h3>Ausblick</h3>
<p>MINDESTENS 4 Saetze: Roadmap, naechste Versionen, Trends.</p>

<h3>Fazit</h3>
<p>MINDESTENS 4 Saetze: Einordnung und Empfehlung fuer die Zielgruppe.</p>

Antworte NUR mit dem JSON. Kein Text davor oder danach. Keine Markdown-Codeblöcke."""

    try:
        r = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]})
        print(f"  -> Gemini Status: {r.status_code}")
        raw = r.json()['candidates'][0]['content']['parts'][0]['text']
        data = json.loads(re.sub(r'```json|```', '', raw).strip())
        data["date"] = heute
        word_count = len(data.get("content", "").split())
        print(f"  -> Inhalt: ~{word_count} Woerter")
        return data
    except Exception as e:
        print(f"  -> Gemini Fehler: {e}")
        print(f"  -> Rohantwort: {r.text[:300]}")
        return None

def run():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: db = json.load(f)
    else: db = {"articles": []}

    existing_titles = {a.get('title', '') for a in db['articles']}
    new_count = 0

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
                image_query = entry.pop("image_query", "technology")
                entry["image_local"] = get_unsplash_image(image_query, entry["id"])
                db['articles'].insert(0, entry)
                existing_titles.add(post.title)
                new_count += 1
                print(f"  -> Erstellt: {entry['title']} ({new_count}/10)")
                time.sleep(30)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
    print(f"\nFertig. {new_count} neue Artikel erstellt.")

if __name__ == "__main__":
    run()