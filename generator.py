import requests, json, os, re, feedparser, time, base64
from datetime import datetime

# --- SETUP ---
API_KEY = "AIzaSyBUVyNIeVmjE7MgVCOF6WbPJpR5uiJjU1A"
TEXT_MODEL = "gemini-3-flash-preview"
IMAGE_MODEL = "imagen-3.1-generate-preview"
DATA_FILE = "data.json"

def generate_image(title, article_id):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{IMAGE_MODEL}:generateImages?key={API_KEY}"
    prompt = f"A professional, minimalist technology header image about {title}. High-end cinematic lighting, apple-style aesthetics, clean background, 16:9 aspect ratio."
    try:
        r = requests.post(url, json={"instances": [{"prompt": prompt}]}, timeout=60)
        img_data = base64.b64decode(r.json()['predictions'][0]['mimeTypeAndData']['data'])
        if not os.path.exists("images"): os.makedirs("images")
        path = f"images/{article_id}.jpg"
        with open(path, "wb") as f: f.write(img_data)
        return path
    except Exception as e:
        print(f"Bildfehler: {e}")
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
    "content": "MINDESTENS 800 WOERTER HTML"
}}

Der content MUSS exakt diese Struktur haben und MINDESTENS 800 Woerter enthalten:

<div class='summary-box'><h4>Highlights</h4><ul><li>Wichtigster Fakt 1</li><li>Wichtigster Fakt 2</li><li>Wichtigster Fakt 3</li><li>Wichtigster Fakt 4</li></ul></div>

<h3>Hintergrund und Kontext</h3>
<p>MINDESTENS 4 Saetze: Was ist die Vorgeschichte? Wie kam es dazu? Was ist der groessere Zusammenhang?</p>
<p>MINDESTENS 4 Saetze: Welche Akteure sind beteiligt? Was sind ihre Interessen und Motivationen?</p>

<h3>Was genau ist passiert?</h3>
<p>MINDESTENS 4 Saetze: Beschreibe das Ereignis detailliert. Was wurde angekuendigt, veroeffentlicht oder entschieden?</p>
<p>MINDESTENS 4 Saetze: Technische Details, Zahlen, Fakten, Spezifikationen soweit vorhanden.</p>

<h3>Warum ist das wichtig?</h3>
<p>MINDESTENS 4 Saetze: Relevanz fuer die Tech-Branche. Marktbedeutung. Competitive Landscape.</p>
<p>MINDESTENS 4 Saetze: Auswirkungen auf Nutzer, Entwickler oder Unternehmen.</p>

<h3>Kritische Einordnung</h3>
<p>MINDESTENS 4 Saetze: Was sind moegliche Risiken oder Schwachstellen? Was bleibt unklar oder offen?</p>
<p>MINDESTENS 4 Saetze: Vergleich mit Konkurrenten oder aehnlichen Entwicklungen in der Vergangenheit.</p>

<h3>Was kommt als naechstes?</h3>
<p>MINDESTENS 4 Saetze: Welche Entwicklungen sind zu erwarten? Was sind die naechsten Schritte?</p>

<h3>Fazit</h3>
<p>MINDESTENS 4 Saetze: Persoenliche Einordnung und Ausblick. Was bedeutet das langfristig fuer die Branche?</p>

Antworte NUR mit dem JSON. Kein Text davor oder danach. Keine Markdown-Codeblöcke."""

    try:
        r = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]})
        data = json.loads(re.sub(r'```json|```', '', r.json()['candidates'][0]['content']['parts'][0]['text']).strip())
        data["date"] = heute
        # Laenge pruefen
        word_count = len(data.get("content", "").split())
        print(f"   Inhalt: ~{word_count} Woerter")
        return data
    except: return None

def run():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: db = json.load(f)
    else: db = {"articles": []}

    feed = feedparser.parse("https://techcrunch.com/feed/")
    for post in feed.entries[:3]:
        if any(a['title'] == post.title for a in db['articles']): continue

        entry = ask_gemini(post.link, "Tech")
        if entry:
            entry["id"] = os.urandom(4).hex()
            entry["image_local"] = generate_image(entry['title'], entry['id'])
            db['articles'].insert(0, entry)
            print(f"Erstellt: {entry['title']}")
            time.sleep(2)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    run()