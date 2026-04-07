import requests
import json
import os
import re
import feedparser
import time
from datetime import datetime
from PIL import Image
from io import BytesIO

# --- KONFIGURATION ---
API_KEY = "AIzaSyCDjSDM3y_DtRGCkveILJma8dH-paEq284"
UNSPLASH_KEY = "QQzUWbAsN6W9yoMZctADAd7ovx1CurH6-HxfaXzuwPE"
TEXT_MODEL = "gemini-1.5-flash" # Oder gemini-2.0-flash
DATA_FILE = "data.json"
MAX_ARTICLES = 50 

RSS_FEEDS = [
    "https://www.heise.de/rss/heise-top-it.xml",
    "https://nodes.com/feed/", # Beispiel
    "https://techcrunch.com/feed/"
]

def get_optimized_image(query, article_id):
    """Holt ein Bild von Unsplash, skaliert es und speichert es als WebP."""
    try:
        url = f"https://api.unsplash.com/photos/random?query={query}&orientation=landscape&client_id={UNSPLASH_KEY}"
        r = requests.get(url, timeout=10)
        img_url = r.json()["urls"]["regular"]
        
        img_data = requests.get(img_url, timeout=20).content
        img = Image.open(BytesIO(img_data))
        
        # Optimierung: Max 1000px Breite, WebP Format
        img.thumbnail((1000, 1000))
        if not os.path.exists("images"): os.makedirs("images")
        
        rel_path = f"images/{article_id}.webp"
        img.save(rel_path, "WEBP", quality=80)
        return rel_path
    except Exception as e:
        print(f"  ! Bild-Fehler: {e}")
        return "https://via.placeholder.com/1000x600?text=Tech+News"

def ask_gemini(url):
    """Analysiert den Artikel und generiert strukturierten Deep-Content."""
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_MODEL}:generateContent?key={API_KEY}"
    
    prompt = f"""Analysiere: {url}
    Schreibe einen technischer Deep-Read (ca. 800 Wörter) für Software-Entwickler.
    Anforderungen:
    1. Nutze <h3> für Zwischenüberschriften.
    2. Integriere ein Code-Beispiel (Python, Bash oder SQL) in <pre><code> Tags.
    3. Erstelle eine <div class='summary-box'> mit den 3 wichtigsten Takeaways am Anfang.

    Gib NUR exakt dieses JSON zurück:
    {{
        "cat": "ki oder dev oder data oder security",
        "tag": "KI / Dev / Data / Security",
        "icon": "Emoji",
        "title": "Headline",
        "source": "Quelle",
        "read": "10 Min",
        "image_query": "English technical term",
        "content": "HTML String"
    }}"""

    try:
        r = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]})
        response_text = r.json()['candidates'][0]['content']['parts'][0]['text']
        
        # Extrahiere JSON (falls Gemini Markdown-Backticks nutzt)
        clean_json = re.search(r'\{.*\}', response_text, re.DOTALL).group(0)
        return json.loads(clean_json)
    except Exception as e:
        print(f"  ! Gemini-Fehler: {e}")
        return None

def run():
    print(f"--- Start BytePost Generator: {datetime.now()} ---")
    
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)
    else:
        db = {"articles": []}

    existing_urls = [a['url'] for a in db['articles']]
    new_count = 0

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:3]: # Pro Feed max 3 neue
            if entry.link not in existing_urls:
                print(f"Verarbeite: {entry.title[:50]}...")
                
                data = ask_gemini(entry.link)
                if data:
                    article_id = int(time.time())
                    data["url"] = entry.link
                    data["id"] = article_id
                    data["date"] = datetime.now().strftime("%d.%m.%Y")
                    data["image"] = get_optimized_image(data["image_query"], article_id)
                    
                    db['articles'].insert(0, data)
                    new_count += 1
                    time.sleep(2) # Rate Limiting

    # Cleanup: Nur die neuesten X Artikel behalten
    db['articles'] = db['articles'][:MAX_ARTICLES]

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
    
    print(f"Fertig! {new_count} neue Artikel hinzugefügt.")

if __name__ == "__main__":
    run()
