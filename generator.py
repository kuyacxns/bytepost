import google.generativeai as genai
import json
import os
import re

# ==========================================
# 1. SETUP
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY", "DEIN_API_KEY_HIER")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def generate_news(article_url):
    print(f"--- Starte Analyse für: {article_url} ---")
    
    prompt = f"""
    Analysiere diesen Artikel vollständig: {article_url}

    Erstelle einen ausführlichen Eintrag für den 'BytePost' Tech-Newsletter auf DEUTSCH.
    Der Inhalt soll ca. 5 Minuten Lesezeit haben (~800-1000 Wörter) und so detailliert sein,
    dass der Leser den Originalartikel nicht mehr lesen muss.

    Antworte NUR im JSON-Format mit exakt dieser Struktur:
    {{
        "id": "{os.urandom(4).hex()}",
        "cat": "ki",
        "tag": "KI",
        "title": "Prägnante, neugierig machende Headline (max. 10 Wörter)",
        "source": "Name der Website",
        "read": "5 Min",
        "icon": "passendes Emoji",
        "content": "HIER KOMMT DER VOLLSTÄNDIGE HTML-INHALT"
    }}

    Der "content" soll folgende Struktur haben (als ein langer HTML-String):

    1. Highlights-Box:
    <div class='summary-box'>
      <h4>✦ Highlights</h4>
      <ul>
        <li>Wichtigster Punkt 1</li>
        <li>Wichtigster Punkt 2</li>
        <li>Wichtigster Punkt 3</li>
        <li>Wichtigster Punkt 4</li>
      </ul>
    </div>

    2. Dann 4-6 inhaltliche Abschnitte mit je einem <h3>Titel</h3> und 2-3 <p>Absätzen</p>.
       Jeder Absatz soll 3-5 Sätze lang sein. Gehe wirklich in die Tiefe:
       - Was ist passiert / worum geht es genau?
       - Warum ist das relevant?
       - Was sind die Hintergründe?
       - Was bedeutet das für die Branche / Nutzer / Entwickler?
       - Was sind mögliche Konsequenzen oder nächste Schritte?

    3. Am Ende ein Fazit-Abschnitt:
    <h3>💡 Fazit</h3>
    <p>Ein abschließender Absatz mit persönlicher Einordnung und Ausblick.</p>

    Schreibe journalistisch, informativ und auf Augenhöhe mit tech-affinen Lesern.
    Keine Füllsätze, keine Wiederholungen. Jeder Satz soll einen Mehrwert haben.
    Antworte NUR mit dem JSON-Code, kein weiterer Text, keine Markdown-Codeblöcke.
    """

    try:
        response = model.generate_content(prompt)
        text_response = response.text
        
        # JSON bereinigen
        json_str = re.sub(r'```json|```', '', text_response).strip()
        new_entry = json.loads(json_str)

        # data.json laden oder neu erstellen
        file_path = 'data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {"articles": []}
        else:
            data = {"articles": []}

        # Neuen Artikel oben einfügen
        data['articles'].insert(0, new_entry)

        # Speichern als UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ Erfolg! '{new_entry['title']}' wurde hinzugefügt.")
        print(f"   Inhaltslänge: {len(new_entry['content'])} Zeichen")

    except json.JSONDecodeError as e:
        print(f"❌ JSON-Parsing-Fehler: {e}")
        print(f"   Rohantwort von Gemini:\n{text_response[:500]}")
    except Exception as e:
        print(f"❌ Fehler: {e}")

# ==========================================
# 2. AUSFÜHRUNG
# ==========================================
if __name__ == "__main__":
    # HIER DIE URL EINTRAGEN:
    ziel_url = "https://www.theverge.com/2024/3/13/24099434/apple-m3-macbook-air-review"
    
    generate_news(ziel_url)
