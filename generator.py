import requests
import json
import os
import re
import feedparser
import time

# ==========================================
# 1. KONFIGURATION
# ==========================================
API_KEY = "AIzaSyBUVyNIeVmjE7MgVCOF6WbPJpR5uiJjU1A"
MODEL_NAME = "gemini-3-flash-preview" # Dein funktionierendes 2026er Modell
DATA_FILE = "data.json"

# Deine Quellen
FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Wired": "https://www.wired.com/feed/rss"
}

# ==========================================
# 2. KI-FUNKTION
# ==========================================
def ask_gemini(article_url, source_name):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    
    prompt = f"""
    Analysiere diesen Artikel: {article_url}
    Erstelle einen JSON-Eintrag auf Deutsch für den BytePost-Newsletter.
    Struktur: {{
        "cat": "tech",
        "tag": "Breaking",
        "title": "Knackiger Titel",
        "source": "{source_name}",
        "read": "4 Min",
        "icon": "⚡",
        "content": "HTML-Zusammenfassung mit <h3> und <p> Tags. Max 3 Absätze."
    }}
    Antworte NUR mit purem JSON.
    """

    try:
        response = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]})
        if response.status_code != 200: return None
        
        raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        clean_json = re.sub(r'```json|```', '', raw_text).strip()
        entry = json.loads(clean_json)
        entry["id"] = os.urandom(4).hex()
        return entry
    except:
        return None

# ==========================================
# 3. HAUPT-LOGIK
# ==========================================
def run_generator():
    print(f"🚀 BytePost Generator startet (Modell: {MODEL_NAME})...")
    
    # Bestehende Daten laden
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try: db = json.load(f)
            except: db = {"articles": []}
    else:
        db = {"articles": []}

    # Nur die Top 2 Artikel pro Feed verarbeiten (um API-Limits zu sparen)
    for name, url in FEEDS.items():
        print(f"--- Lese Feed: {name} ---")
        feed = feedparser.parse(url)
        
        for post in feed.entries[:2]:
            # Prüfen ob Titel schon existiert
            if any(a['title'] == post.title for a in db['articles']):
                print(f"  ⏭️ Überspringe (schon vorhanden): {post.title[:30]}...")
                continue
            
            print(f"  🧠 KI analysiert: {post.title[:50]}...")
            new_entry = ask_gemini(post.link, name)
            
            if new_entry:
                db['articles'].insert(0, new_entry)
                print(f"  ✅ Hinzugefügt!")
                # Kurze Pause für die API-Quote
                time.sleep(2) 

    # Speichern
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
    
    print("\n✨ Fertig! Deine data.json ist aktuell.")

if __name__ == "__main__":
    run_generator()