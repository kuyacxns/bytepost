import requests, json, os, re, feedparser, time, base64
from datetime import datetime

# --- SETUP ---
API_KEY = "AIzaSyCDjSDM3y_DtRGCkveILJma8dH-paEq284"
UNSPLASH_KEY = "QQzUWbAsN6W9yoMZctADAd7ovx1CurH6-HxfaXzuwPE"
TEXT_MODEL = "gemini-2.5-flash"
DATA_FILE = "data.json"

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

    prompt = f"""Du bist ein professioneller Tech-Journalist. Analysiere diesen Artikel: {url}

WICHTIG: Der content-Wert im JSON MUSS mindestens 800 Woerter lang sein. Kuerzere Antworten sind UNGUELTIG.

Erstelle ein JSON-Objekt fuer den BytePost Newsletter auf DEUTSCH:
{{
    "cat": "ki/dev/hardware/security/business/tech",
    "tag": "KI/Dev/Hardware/Security/Business/Tech",
    "icon": "Emoji",
    "title": "Headline max 10 Woerter",
    "source": "Quellenname",
    "read": "5 Min",
    "image_query": "2-3 englische Suchbegriffe fuer ein passendes Foto (z.B. 'electric car highway')",
    "content": "MINDESTENS 800 WOERTER HTML"
}}

Der content MUSS exakt diese Struktur haben:

<div class='summary-box'><h4>Highlights</h4><ul><li>Fakt 1</li><li>Fakt 2</li><li>Fakt 3</li><li>Fakt 4</li></ul></div>

<h3>Hintergrund und Kontext</h3>
<p>MINDESTENS 4 Saetze: Vorgeschichte und groesserer Zusammenhang.</p>
<p>MINDESTENS 4 Saetze: Beteiligte Akteure und ihre Interessen.</p>

<h3>Was genau ist passiert?</h3>
<p>MINDESTENS 4 Saetze: Detaillierte Beschreibung des Ereignisses.</p>
<p>MINDESTENS 4 Saetze: Technische Details, Zahlen, Fakten.</p>

<h3>Warum ist das wichtig?</h3>
<p>MINDESTENS 4 Saetze: Relevanz fuer die Tech-Branche.</p>
<p>MINDESTENS 4 Saetze: Auswirkungen auf Nutzer oder Entwickler.</p>

<h3>Kritische Einordnung</h3>
<p>MINDESTENS 4 Saetze: Moegliche Risiken oder Schwachstellen.</p>
<p>MINDESTENS 4 Saetze: Vergleich mit Konkurrenten.</p>

<h3>Was kommt als naechstes?</h3>
<p>MINDESTENS 4 Saetze: Erwartete Entwicklungen und naechste Schritte.</p>

<h3>Fazit</h3>
<p>MINDESTENS 4 Saetze: Persoenliche Einordnung und Ausblick.</p>

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

    feed = feedparser.parse("https://techcrunch.com/feed/")
    print(f"Feed geladen: {len(feed.entries)} Eintraege")

    for post in feed.entries[:3]:
        print(f"Verarbeite: {post.title}")
        if any(a['title'] == post.title for a in db['articles']):
            print("  -> Duplikat, uebersprungen")
            continue

        entry = ask_gemini(post.link, "Tech")
        if entry:
            entry["id"] = os.urandom(4).hex()
            image_query = entry.pop("image_query", entry.get("title", "technology"))
            entry["image_local"] = get_unsplash_image(image_query, entry["id"])
            db['articles'].insert(0, entry)
            print(f"  -> Erstellt: {entry['title']}")
            time.sleep(30)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
    print("Fertig.")

if __name__ == "__main__":
    run()