import requests
import json
import os
import re
import feedparser
import time
import base64
from io import BytesIO
from datetime import datetime
from PIL import Image

# --- KONFIGURATION ---
API_KEY = "AIzaSyBUVyNIeVmjE7MgVCOF6WbPJpR5uiJjU1A"
TEXT_MODEL = "gemini-3-flash-preview" 
IMAGE_MODEL = "imagen-3.1-generate-preview" # Dein KI-Bild Modell von 2026
DATA_FILE = "data.json"
IMAGE_FOLDER = "images"

# Stelle sicher, dass der Ordner existiert
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

FEEDS = {
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml"
}

# --- BILD-GENERIERUNG (Imagen-3.1) ---
def generate_image(article_title, article_content, article_id):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{IMAGE_MODEL}:generateImages?key={API_KEY}"
    
    # Einen Prompt für das Bild erstellen, basierend auf Titel und Inhalt
    short_content = article_content[:300]
    prompt = f"A fotorealistic, high-resolution, professional technology blog header image for the article titled: '{article_title}'. The image should visualize the themes: {short_content}. Cinematic lighting, depth of field, minimalist tech aesthetic, no text or watermarks inside the image."

    payload = {
        "instances": [{"prompt": prompt}]
    }

    try:
        print(f"  🎨 KI generiert Bild für: {article_title[:40]}...")
        response = requests.post(api_url, json=payload, timeout=60) # Bilder brauchen länger
        
        if response.status_code != 200: 
            print(f"    Fehler bei Imagen (Code {response.status_code}): {response.text}")
            return None
            
        result = response.json()
        
        # Das generierte Bild kommt als Base64 String zurück
        base64_image = result['predictions'][0]['mimeTypeAndData']['data']
        image_data = base64.b64decode(base64_image)
        
        # Bild lokal speichern
        image_filename = f"{article_id}.jpg"
        image_path = os.path.join(IMAGE_FOLDER, image_filename)
        
        # PIL nutzen, um es als JPG zu speichern (und ggf. die Größe anzupassen)
        with Image.open(BytesIO(image_data)) as img:
            img.convert("RGB").save(image_path, "JPEG", quality=85)
            
        print(f"    ✅ Bild gespeichert: {image_path}")
        return f"{IMAGE_FOLDER}/{image_filename}" # Pfad für data.json zurückgeben

    except Exception as e:
        print(f"    ❌ Fehler bei Bild-Generierung: {e}")
        return None

# --- TEXT-GENERIERUNG (Gemini 3) ---
def ask_gemini(article_url, source_name):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_MODEL}:generateContent?key={API_KEY}"
    heute = datetime.now().strftime("%d.%m.%Y")
    
    prompt = f"""
    Analysiere diesen Artikel tiefgreifend: {article_url}
    Erstelle ein JSON auf Deutsch für den BytePost-Newsletter.
    
    ZIEL: Der Leser soll alles Wichtige wissen (5 Min Deep Read), ohne die Quelle zu öffnen.
    STRUKTUR: Einleitung (### h3), Key-Points (<ul> Liste), Analyse, Fazit.
    
    JSON Struktur (OHNE 'id' und 'image_local'): {{
        "date": "{heute}",
        "cat": "tech",
        "title": "Titel",
        "source": "{source_name}",
        "read": "5 Min Deep Read",
        "content": "HTML mit h3, p und ul"
    }}
    Antworte NUR mit purem JSON.
    """

    try:
        response = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
        if response.status_code != 200: return None
        raw_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        clean_json = re.sub(r'```json|```', '', raw_text).strip()
        return json.loads(clean_json)
    except:
        return None

# --- HAUPT-LOGIK ---
def run_generator():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try: db = json.load(f)
            except: db = {"articles": []}
    else:
        db = {"articles": []}

    print("🚀 BytePost Generator (Text & Bild) startet...")

    for name, url in FEEDS.items():
        print(f"\n--- Verarbeite {name} ---")
        feed = feedparser.parse(url)
        for post in feed.entries[:2]:
            if any(a['title'] == post.title for a in db['articles']): 
                print(f"  ⏩ Überspringe (schon da): {post.title[:30]}...")
                continue
            
            # 1. Text generieren
            print(f"  🧠 KI analysiert Text: {post.title[:40]}...")
            new_entry = ask_gemini(post.link, name)
            
            if new_entry:
                article_id = os.urandom(4).hex()
                new_entry["id"] = article_id
                
                # 2. Bild passend zum Artikel generieren
                local_image_path = generate_image(new_entry['title'], new_entry['content'], article_id)
                new_entry["image_local"] = local_image_path or ""
                
                db['articles'].insert(0, new_entry)
                print(f"  ✅ Artikel komplett hinzugefügt!")
                time.sleep(1)

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
    print("\n✨ data.json wurde aktualisiert.")

if __name__ == "__main__":
    run_generator()