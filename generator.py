import requests, json, os, re, feedparser, time
from datetime import datetime

# --- KONFIGURATION ---
API_KEY = "AIzaSyBUVyNIeVmjE7MgVCOF6WbPJpR5uiJjU1A"
MODEL_NAME = "gemini-3-flash-preview" 
DATA_FILE = "data.json"

# Deine News-Quellen
FEEDS = {
    "tech": "https://techcrunch.com/feed/",
    "science": "https://arstechnica.com/feed/",
    "ai": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"
}

def ask_gemini(article_url, category):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    
    prompt = f"""
    Analysiere diesen Artikel: {article_url}
    Erstelle ein JSON für ein Apple-Style News-Portal.
    
    WICHTIG:
    - cat: Muss exakt '{category}' sein.
    - tag: Ein kurzes Schlagwort (z.B. BREAKING, KI, APPLE, ANALYSE).
    - icon: Ein passendes Emoji.
    - content: Ein tiefgreifender 5-Minuten-Read in HTML. 
      Nutze <div class="summary-box"><h4>Zusammenfassung</h4>...</div> für den Anfang, 
      gefolgt von <h3> details </h3> und <p> Texten.
    
    JSON Struktur: {{
        "cat": "{category}",
        "tag": "TAG",
        "title": "Knackiger Titel",
        "source": "Quelle",
        "read": "5 Min",
        "icon": "🚀",
        "content": "HTML_STRING"
    }}
    Antworte NUR mit purem JSON.
    """

    try:
        response = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]})
        raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        clean_json = re.sub(r'```json|```', '', raw_text).strip()
        data = json.loads(clean_json)
        data["id"] = os.urandom(4).hex() # Eindeutige ID für das Modal
        return data
    except:
        return None

def run():
    print(f"🚀 BytePost Generator für Apple-Style UI startet...")
    
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)
    else:
        db = {"articles": []}

    for cat, url in FEEDS.items():
        feed = feedparser.parse(url)
        for post in feed.entries[:2]: # Top 2 pro Kategorie
            if any(a['title'] == post.title for a in db['articles']): continue
            
            entry = ask_gemini(post.link, cat)
            if entry:
                db['articles'].insert(0, entry)
                print(f"✅ Artikel erstellt: {entry['title']}")
                time.sleep(1)

    # Speicher die Datei
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
    print("✨ Fertig! data.json ist bereit.")

if __name__ == "__main__":
    run()