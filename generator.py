import requests, json, os, re, feedparser, time, base64
from datetime import datetime

# --- SETUP ---
API_KEY = "AIzaSyBUVyNIeVmjE7MgVCOF6WbPJpR5uiJjU1A"
TEXT_MODEL = "gemini-3-flash-preview"
IMAGE_MODEL = "imagen-3.1-generate-preview"
DATA_FILE = "data.json"

def generate_image(title, article_id):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{IMAGE_MODEL}:generateImages?key={API_KEY}"
    # Prompt für ein hochwertiges Tech-Header-Bild
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
    prompt = f"Analysiere {url}. Erstelle JSON: cat:{category}, tag: Schlagwort, icon: Emoji, title: Titel, content: ausführliches HTML (Zusammenfassungs-Box, h3, p, ul). Sprache: Deutsch."
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
            print(f"✅ Erstellt: {entry['title']}")
            time.sleep(2)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    run()