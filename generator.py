import requests, json, os, re, feedparser, time, base64
from datetime import datetime

# --- SETUP ---
API_KEY = "AIzaSyBUVyNIeVmjE7MgVCOF6WbPJpR5uiJjU1A"
TEXT_MODEL = "gemini-3-flash-preview"
IMAGE_MODEL = "imagen-3.1-generate-preview" 
DATA_FILE = "data.json"

def ask_gemini(article_url, source_name):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_MODEL}:generateContent?key={API_KEY}"
    heute = datetime.now().strftime("%d.%m.%Y")
    
    prompt = f"""
    Analysiere diesen Artikel tiefgreifend: {article_url}
    Erstelle ein JSON auf Deutsch.
    STRUKTUR: Einleitung (h3), Key-Points (ul), Analyse, Fazit.
    JSON: {{
        "date": "{heute}",
        "title": "Titel",
        "source": "{source_name}",
        "read": "5 Min Deep Read",
        "icon": "🚀",
        "content": "HTML Inhalt"
    }}
    Antworte NUR mit purem JSON.
    """
    try:
        r = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]})
        return json.loads(re.sub(r'```json|```', '', r.json()['candidates'][0]['content']['parts'][0]['text']).strip())
    except: return None

def generate_image(title, article_id):
    # Imagen API Call
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{IMAGE_MODEL}:generateImages?key={API_KEY}"
    prompt = f"Professional high-tech minimalist header for an article about {title}. Dark aesthetic, cinematic lighting, 16:9."
    try:
        r = requests.post(url, json={"instances": [{"prompt": prompt}]})
        img_data = base64.b64decode(r.json()['predictions'][0]['mimeTypeAndData']['data'])
        path = f"images/{article_id}.jpg"
        with open(path, "wb") as f: f.write(img_data)
        return path
    except: return None

def run():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f: db = json.load(f)
    else: db = {"articles": []}

    feed = feedparser.parse("https://techcrunch.com/feed/")
    for post in feed.entries[:3]:
        if any(a['title'] == post.title for a in db['articles']): continue
        
        item = ask_gemini(post.link, "TechCrunch")
        if item:
            item["id"] = os.urandom(4).hex()
            item["image_local"] = generate_image(item['title'], item['id'])
            db['articles'].insert(0, item)
            print(f"✅ Geladen: {item['title']}")
            time.sleep(2)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    run()