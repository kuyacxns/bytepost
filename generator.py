import requests, json, os, re, feedparser, time, base64
from datetime import datetime

# --- KONFIGURATION ---
API_KEY = "AIzaSyBUVyNIeVmjE7MgVCOF6WbPJpR5uiJjU1A"
TEXT_MODEL = "gemini-3-flash-preview"
IMAGE_MODEL = "imagen-3.1-generate-preview" 

def ask_gemini(article_url, source_name):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_MODEL}:generateContent?key={API_KEY}"
    heute = datetime.now().strftime("%d.%m.%Y")
    
    prompt = f"""
    Analysiere diesen Artikel: {article_url}
    Erstelle ein JSON auf Deutsch für einen TLDR-Newsletter.
    
    FELDER:
    - teaser: Ein extrem kurzer Satz (max 10 Wörter), der neugierig macht.
    - content: Die 5-Minuten Zusammenfassung (ausführlich!) mit <h3>, <p>, <ul>.
    
    JSON Struktur: {{
        "date": "{heute}",
        "title": "Titel",
        "teaser": "Kurzer Teaser Satz",
        "source": "{source_name}",
        "read": "5 Min Deep Read",
        "content": "Ausführliches HTML"
    }}
    Antworte NUR mit purem JSON.
    """
    try:
        r = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]})
        return json.loads(re.sub(r'```json|```', '', r.json()['candidates'][0]['content']['parts'][0]['text']).strip())
    except: return None

def generate_image(title, article_id):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{IMAGE_MODEL}:generateImages?key={API_KEY}"
    prompt = f"Technology news visual for {title}. Minimalist, high quality, 16:9 ratio."
    try:
        r = requests.post(url, json={"instances": [{"prompt": prompt}]})
        img_data = base64.b64decode(r.json()['predictions'][0]['mimeTypeAndData']['data'])
        if not os.path.exists("images"): os.makedirs("images")
        path = f"images/{article_id}.jpg"
        with open(path, "wb") as f: f.write(img_data)
        return path
    except: return None

def run():
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f: db = json.load(f)
    else: db = {"articles": []}

    feed = feedparser.parse("https://techcrunch.com/feed/")
    for post in feed.entries[:3]:
        if any(a['title'] == post.title for a in db['articles']): continue
        
        item = ask_gemini(post.link, "TechCrunch")
        if item:
            item["id"] = os.urandom(4).hex()
            item["image_local"] = generate_image(item['title'], item['id'])
            db['articles'].insert(0, item)
            print(f"✅ Erstellt: {item['title']}")
            time.sleep(2)

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    run()