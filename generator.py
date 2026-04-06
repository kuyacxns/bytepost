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

    prompt = f"""Analysiere diesen Artikel vollstaendig: {url}

Erstelle einen ausfuehrlichen Eintrag fuer den BytePost Tech-Newsletter auf DEUTSCH.
Der Inhalt soll ca. 5 Minuten Lesezeit haben (~800-1000 Woerter), sodass der Leser den Originalartikel nicht mehr lesen muss.

Antworte NUR im JSON-Format mit exakt dieser Struktur:
{{
    "cat": "passendes Kuerzel",
    "tag": "Schlagwort",
    "icon": "Emoji",
    "title": "Praegnante deutsche Headline (max. 10 Woerter)",
    "source": "Name der Quelle",
    "read": "5 Min",
    "content": "VOLLSTAENDIGER HTML-INHALT"
}}

Passe cat und tag dem Thema an:
- KI/Machine Learning: cat=ki, tag=KI
- Software/Tools: cat=dev, tag=Dev
- Hardware/Gadgets: cat=hardware, tag=Hardware
- Security: cat=security, tag=Security
- Business: cat=business, tag=Business
- Sonstiges: cat=tech, tag=Tech

Der content muss folgende HTML-Struktur haben:

<div class='summary-box'><h4>Highlights</h4><ul><li>Punkt 1</li><li>Punkt 2</li><li>Punkt 3</li><li>Punkt 4</li></ul></div>

Dann 4-6 Abschnitte mit je einem <h3>Titel</h3> und 2-3 <p>Absaetze</p> (je 3-5 Saetze). Beantworte dabei:
- Was ist passiert und worum geht es genau?
- Warum ist das relevant?
- Was sind die Hintergruende?
- Was bedeutet das fuer Nutzer, Entwickler oder die Branche?
- Was sind moegliche Konsequenzen oder naechste Schritte?

Am Ende: <h3>Fazit</h3><p>Persoenliche Einordnung und Ausblick.</p>

Schreibe journalistisch und informativ fuer tech-affine Leser. Keine Fuellsaetze.
Antworte NUR mit dem JSON-Code, kein weiterer Text, keine Markdown-Codeblöcke."""

    try:
        r = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]})
        data = json.loads(re.sub(r'```json|```', '', r.json()['candidates'][0]['content']['parts'][0]['text']).strip())
        data["date"] = heute
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