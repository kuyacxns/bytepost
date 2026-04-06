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
    
    # Der neue "Deep Read" Prompt
    prompt = f"""
    Analysiere diesen Artikel tiefgreifend: {article_url}
    Erstelle einen ausführlichen JSON-Eintrag auf Deutsch für den BytePost-Newsletter.
    
    ZIEL: Der Leser soll nach dem Lesen alles Wichtige wissen, ohne die Originalquelle besuchen zu müssen.
    
    STRENGER AUFBAU DES 'content' Feldes (HTML):
    1. Einleitung: Was ist passiert? (1 Absatz)
    2. Die 3 wichtigsten Key-Points als <ul> Liste.
    3. Eine kurze Analyse: Warum ist das für die Tech-Welt relevant?
    4. Ein Fazit oder Ausblick.

    JSON Struktur: {{
        "cat": "tech",
        "tag": "Deep Read",
        "title": "Ein fesselnder, aussagekräftiger Titel",
        "source": "{source_name}",
        "read": "5 Min",
        "icon": "🧠",
        "content": "Hier der strukturierte HTML-Inhalt..."
    }}
    Antworte NUR mit purem JSON.
    """

    # Konfiguration für längere Antworten
    generation_config = {
        "temperature": 0.7,
        "maxOutputTokens": 2000, # Mehr Platz für die lange Zusammenfassung
    }

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config
        }
        response = requests.post(api_url, json=payload)
        
        if response.status_code != 200: 
            print(f"Fehler: {response.text}")
            return None
        
        raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        clean_json = re.sub(r'```json|```', '', raw_text).strip()
        entry = json.loads(clean_json)
        entry["id"] = os.urandom(4).hex()
        return entry
    except Exception as e:
        print(f"Fehler bei der KI-Anfrage: {e}")
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