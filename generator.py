import requests, json, os, re, feedparser, time
from datetime import datetime
from PIL import Image # Neu: Für Bildoptimierung
from io import BytesIO

# --- SETUP ---
API_KEY = ""
UNSPLASH_KEY = ""
TEXT_MODEL = "gemini-2.5-flash"
DATA_FILE = "data.json"
MAX_ARTICLES = 50 # Neu: Damit die Datei nicht zu groß wird

# ... (RSS_FEEDS bleiben gleich)

def get_unsplash_image(query, article_id):
    try:
        url = f"https://api.unsplash.com/photos/random?query={query}&orientation=landscape&client_id={UNSPLASH_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        img_url = data["urls"]["regular"]
        
        # Bild downloaden
        img_data = requests.get(img_url, timeout=30).content
        img = Image.open(BytesIO(img_data))
        
        # NEU: Bild optimieren (max 1000px Breite, WebP Format für Speed)
        img.thumbnail((1000, 1000))
        if not os.path.exists("images"): os.makedirs("images")
        path = f"images/{article_id}.webp"
        img.save(path, "WEBP", quality=80)
        
        print(f"  -> Bild optimiert gespeichert: {path}")
        return path
    except Exception as e:
        print(f"  -> Bildfehler: {e}")
        return None

def ask_gemini(url, category):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_MODEL}:generateContent?key={API_KEY}"
    heute = datetime.now().strftime("%d.%m.%Y")

    # NEU: Prompt angepasst für Code-Beispiele und technischeren Fokus
    prompt = f"""Analysiere diesen Tech-Artikel: {url}
    Schreibe einen Deep-Read (ca. 800 Wörter) für Senior Devs/Data Engineers.
    Integriere mindestens ein relevantes Code-Beispiel (Python, SQL, Bash oder YAML) in Markdown-Syntax.
    
    Erstelle exakt dieses JSON:
    {{
        "cat": "ki/dev/data/security/cloud/hardware/business",
        "tag": "KI/Dev/Data/Security/Cloud/Hardware/Business",
        "icon": "Emoji",
        "title": "Headline",
        "source": "Quelle",
        "read": "X Min",
        "image_query": "English keywords",
        "content": "HTML Struktur mit <div class='summary-box'>, <h3>, <p> und <code>"
    }}
    Kein Smalltalk, nur das JSON."""

    try:
        r = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]})
        raw = r.json()['candidates'][0]['content']['parts'][0]['text']
        
        # NEU: Sicherer Regex-Parser für JSON
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not json_match: return None
        
        data = json.loads(json_match.group(0))
        data["date"] = heute
        return data
    except Exception as e:
        print(f"  -> Gemini Fehler: {e}")
        return None

def run():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: db = json.load(f)
    else: db = {"articles": []}

    # ... (Loop Logik bleibt gleich)
    
    # NEU: Cleanup Routine am Ende
    db['articles'] = db['articles'][:MAX_ARTICLES]

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
