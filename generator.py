import requests, json, os, re, time, random, html as html_mod
from datetime import datetime
# feedparser/BeautifulSoup werden lazy importiert, damit Hilfsmodi
# (z.B. --outputs-only) ohne diese Dependencies laufen

# --- SETUP ---
def load_dotenv(path=".env"):
    """Minimaler .env-Loader ohne Zusatz-Dependency."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_dotenv()

GROQ_API_KEY    = os.environ.get("GROQ_API_KEY", "")
VOYAGE_API_KEY  = os.environ.get("VOYAGE_API_KEY", "")
UNSPLASH_KEY    = os.environ.get("UNSPLASH_ACCESS_KEY", "")
MODEL           = "llama-3.3-70b-versatile"
EMBED_MODEL     = "voyage-3-lite"
DATA_FILE       = "data.json"
EMBED_FILE      = "embeddings.json"   # nicht deployt, in .gitignore
SITE_URL        = "https://bytepost.de"
ARTICLE_DIR     = "artikel"

# --- COST PROTECTION ---
MAX_PER_RUN      = 10   # max. neue Artikel pro Generator-Lauf
MAX_PER_DAY      = 15   # max. neue Artikel pro Tag
MAX_PER_CATEGORY = 2    # max. Artikel pro Feed-Kategorie pro Lauf
MAX_ERRORS       = 3    # Circuit Breaker
FEED_TIMEOUT     = 10   # Sekunden pro Feed-Request

# --- RSS FEEDS (kategorisiert für balancierte Auswahl) ---
RSS_FEEDS = {
    "gaming": [
        ("Rock Paper Shotgun","https://feeds.feedburner.com/RockPaperShotgun"),
        ("GameSpot",          "https://www.gamespot.com/feeds/news/"),
        ("Heise Games",       "https://www.heise.de/games/rss/news-atom.xml"),
        ("Golem Games",       "https://www.golem.de/rss.php?tp=games"),
    ],
    "ai_ml": [
        ("TechCrunch KI",     "https://techcrunch.com/category/artificial-intelligence/feed/"),
        ("OpenAI Blog",       "https://openai.com/blog/rss/"),
        ("Microsoft AI",      "https://blogs.microsoft.com/ai/feed/"),
        ("Hugging Face",      "https://huggingface.co/blog/feed.xml"),
        ("Import AI",         "https://importai.substack.com/feed"),
        ("The Gradient",      "https://thegradient.pub/rss/"),
        ("MarkTechPost",      "https://www.marktechpost.com/feed/"),
        ("BAIR Blog",         "https://bair.berkeley.edu/blog/feed.xml"),
    ],
    "dev": [
        ("TechCrunch",        "https://techcrunch.com/feed/"),
        ("The Verge",         "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica",      "https://feeds.arstechnica.com/arstechnica/technology-lab"),
        ("Stack Overflow",    "https://stackoverflow.blog/feed/"),
        ("GitHub Blog",       "https://github.blog/feed/"),
        ("Smashing Magazine", "https://www.smashingmagazine.com/feed/"),
        ("Dev.to",            "https://dev.to/feed"),
        ("InfoQ",             "https://feed.infoq.com/"),
        ("freeCodeCamp",      "https://www.freecodecamp.org/news/rss/"),
        ("Martin Fowler",     "https://martinfowler.com/feed.atom"),
    ],
    "data": [
        ("Towards Data Science",   "https://towardsdatascience.com/feed"),
        ("KDnuggets",              "https://www.kdnuggets.com/feed"),
        ("Databricks Blog",        "https://www.databricks.com/blog/feed"),
        ("dbt Blog",               "https://www.getdbt.com/blog/rss.xml"),
        ("Confluent Blog",         "https://www.confluent.io/blog/feed/"),
        ("Analytics Vidhya",       "https://www.analyticsvidhya.com/feed/"),
        ("FlowingData",            "https://flowingdata.com/feed/"),
        ("Data Engineering Weekly","https://www.dataengineeringweekly.com/feed"),
    ],
    "cloud_devops": [
        ("AWS Blog",          "https://aws.amazon.com/blogs/aws/feed/"),
        ("Google Cloud",      "https://cloud.google.com/blog/rss"),
        ("Azure Blog",        "https://azure.microsoft.com/en-us/blog/feed/"),
        ("Kubernetes Blog",   "https://kubernetes.io/feed.xml"),
        ("Docker Blog",       "https://www.docker.com/blog/feed/"),
        ("The New Stack",     "https://thenewstack.io/feed/"),
        ("DevOps.com",        "https://devops.com/feed/"),
        ("HashiCorp Blog",    "https://www.hashicorp.com/blog/feed.xml"),
    ],
    "security": [
        ("Heise Security",    "https://www.heise.de/security/rss/alert-news-atom.xml"),
        ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
        ("The Hacker News",   "https://feeds.feedburner.com/TheHackersNews"),
        ("Schneier Blog",     "https://www.schneier.com/feed/atom/"),
        ("Dark Reading",      "https://www.darkreading.com/rss.xml"),
        ("BleepingComputer",  "https://www.bleepingcomputer.com/feed/"),
    ],
    "engineering_blogs": [
        ("Spotify Engineering",  "https://engineering.atspotify.com/feed/"),
        ("Netflix Tech Blog",    "https://netflixtechblog.com/feed"),
        ("Cloudflare Blog",      "https://blog.cloudflare.com/rss/"),
        ("Meta Engineering",     "https://engineering.fb.com/feed/"),
        ("Stripe Engineering",   "https://stripe.com/blog/engineering.rss"),
        ("LinkedIn Engineering", "https://engineering.linkedin.com/blog.rss.html"),
    ],
    "languages": [
        ("Python Insider",    "https://blog.python.org/feeds/posts/default"),
        ("Real Python",       "https://realpython.com/atom.xml"),
        ("Rust Blog",         "https://blog.rust-lang.org/feed.xml"),
        ("Go Blog",           "https://go.dev/blog/feed.atom"),
        ("TypeScript Blog",   "https://devblogs.microsoft.com/typescript/feed/"),
    ],
    "tech_de": [
        ("Heise Online",      "https://www.heise.de/rss/heise-top-atom.xml"),
        ("Heise Developer",   "https://www.heise.de/developer/rss/news-atom.xml"),
        ("Golem Dev",         "https://www.golem.de/rss.php?tp=dev"),
        ("Golem",             "https://rss.golem.de/rss.php?feed=RSS2.0"),
        ("t3n",               "https://t3n.de/rss.xml"),
        ("Netzpolitik",       "https://netzpolitik.org/feed/"),
    ],
    "business": [
        ("TechCrunch Startups","https://techcrunch.com/category/startups/feed/"),
        ("Y Combinator",      "https://www.ycombinator.com/blog/rss"),
        ("a16z",              "https://a16z.com/feed/"),
        ("First Round",       "https://review.firstround.com/feed.xml"),
    ],
    "hardware": [
        ("Engadget",          "https://www.engadget.com/rss.xml"),
        ("Tom's Hardware",    "https://www.tomshardware.com/feeds/all"),
        ("Golem Mobil",       "https://www.golem.de/rss.php?tp=mobile"),
    ],
}

# Mapping Feed-Kategorie → BytePost Kategorie-Hint für Groq
CATEGORY_HINT = {
    "gaming":           "gaming",
    "ai_ml":            "ki",
    "dev":              "dev",
    "data":             "data",
    "cloud_devops":     "dev",
    "security":         "security",
    "engineering_blogs":"dev",
    "languages":        "dev",
    "tech_de":          "tech",
    "business":         "business",
    "hardware":         "hardware",
}

def fetch_feed(feed_url):
    """Lädt einen RSS-Feed mit Timeout via requests."""
    import feedparser
    try:
        r = requests.get(feed_url, timeout=FEED_TIMEOUT,
                         headers={"User-Agent": "BytePost/1.0 (RSS Reader)"})
        r.raise_for_status()
        return feedparser.parse(r.content)
    except Exception:
        return None

def collect_candidates(existing_urls, effective_limit):
    """Sammelt neue Artikel aus allen Feeds, balanciert über Kategorien."""
    total_sources = sum(len(v) for v in RSS_FEEDS.values())
    print(f"\n📡 Lade Feeds aus {len(RSS_FEEDS)} Kategorien ({total_sources} Quellen)…")

    by_category = {cat: [] for cat in RSS_FEEDS}

    for cat_key, feeds in RSS_FEEDS.items():
        for source_name, feed_url in feeds:
            feed = fetch_feed(feed_url)
            if feed is None or not feed.entries:
                print(f"  ⚠️ Feed-Fehler: {source_name}")
                continue
            new = [e for e in feed.entries[:3]
                   if getattr(e, "link", None) and e.link not in existing_urls]
            if new:
                by_category[cat_key].extend([(cat_key, source_name, e) for e in new])

    # Balancierte Auswahl: max. MAX_PER_CATEGORY pro Kategorie, Rest zufällig auffüllen
    selected, per_cat = [], {cat: 0 for cat in RSS_FEEDS}
    for cat in RSS_FEEDS:
        random.shuffle(by_category[cat])

    changed = True
    while changed and len(selected) < effective_limit:
        changed = False
        for cat in RSS_FEEDS:
            if len(selected) >= effective_limit:
                break
            if per_cat[cat] < MAX_PER_CATEGORY and by_category[cat]:
                selected.append(by_category[cat].pop(0))
                per_cat[cat] += 1
                changed = True

    # Auffüllen falls noch Platz — zufällig aus verbleibenden
    remaining = [item for cat in RSS_FEEDS for item in by_category[cat]]
    random.shuffle(remaining)
    for item in remaining:
        if len(selected) >= effective_limit:
            break
        selected.append(item)

    return selected

def get_embedding(text):
    """Erzeugt einen semantischen Vektor via Voyage AI (mit Retry)."""
    if not VOYAGE_API_KEY:
        return None
    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {VOYAGE_API_KEY}", "Content-Type": "application/json"},
                json={"input": [text[:4000]], "model": EMBED_MODEL},
                timeout=20,
            )
            if r.status_code == 200:
                vec = r.json()["data"][0]["embedding"]
                return [round(x, 6) for x in vec]
            if r.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"  -> Rate-Limit, warte {wait}s...")
                time.sleep(wait)
                continue
            print(f"  -> Embedding-Fehler {r.status_code}: {r.text[:120]}")
            break
        except Exception as e:
            wait = 3 * (attempt + 1)
            print(f"  -> Embedding-Fehler (Versuch {attempt+1}): {e} — warte {wait}s")
            time.sleep(wait)
    return None


def strip_html(html):
    """HTML → Plaintext (ohne bs4-Dependency)."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    return html_mod.unescape(re.sub(r"\s+", " ", text).strip())


def embed_text(article):
    """Erstellt den Text der für das Embedding verwendet wird."""
    content_plain = strip_html(article.get("content", ""))
    return f"{article['title']}. {content_plain[:600]}"


def load_embeddings():
    """Lädt den lokalen Embedding-Store (id → Vektor)."""
    if os.path.exists(EMBED_FILE):
        with open(EMBED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_embeddings(store):
    with open(EMBED_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f)


def backfill_embeddings(articles, emb_store):
    """Generiert Embeddings für alle Artikel die noch keinen Vektor im Store haben."""
    missing = [a for a in articles if a.get("id") and a["id"] not in emb_store]
    if not missing:
        return
    print(f"\nEmbedding-Backfill: {len(missing)} Artikel ohne Vektor...")
    for i, a in enumerate(missing):
        vec = get_embedding(embed_text(a))
        if vec:
            emb_store[a["id"]] = vec
            print(f"  [{i+1}/{len(missing)}] {a['title'][:50]}")
        else:
            print(f"  [{i+1}/{len(missing)}] FEHLER: {a['title'][:50]}")
        time.sleep(1.0)   # DNS-Cache schonen
    save_embeddings(emb_store)
    print("Backfill abgeschlossen.")


UNSPLASH_UTM = "?utm_source=bytepost&utm_medium=referral"

def save_image_variants(img_data, article_id):
    """Speichert das Bild als WebP (voll) + kleine Card-Variante (~400px).
    Fallback auf JPG wenn Pillow fehlt."""
    if not os.path.exists("images"): os.makedirs("images")
    try:
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(img_data)).convert("RGB")
        full_path = f"images/{article_id}.webp"
        img.save(full_path, "WEBP", quality=82)
        small = img.copy()
        small.thumbnail((400, 10000))
        small_path = f"images/{article_id}-sm.webp"
        small.save(small_path, "WEBP", quality=80)
        return full_path, small_path
    except ImportError:
        print("  -> Pillow fehlt — speichere JPG ohne Varianten (pip install Pillow)")
        path = f"images/{article_id}.jpg"
        with open(path, "wb") as f: f.write(img_data)
        return path, None


def get_unsplash_image(query, article_id):
    """Lädt ein Unsplash-Bild. Gibt dict mit Pfaden + Fotografen-Attribution zurück."""
    try:
        url = f"https://api.unsplash.com/photos/random?query={query}&orientation=landscape&client_id={UNSPLASH_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        img_url = data["urls"]["regular"]
        img_data = requests.get(img_url, timeout=30).content
        path, small_path = save_image_variants(img_data, article_id)
        # Unsplash-Guidelines: Download-Endpoint triggern + Fotograf nennen
        dl = data.get("links", {}).get("download_location")
        if dl:
            try: requests.get(f"{dl}&client_id={UNSPLASH_KEY}", timeout=10)
            except Exception: pass
        credit_name = data.get("user", {}).get("name", "")
        credit_url  = data.get("user", {}).get("links", {}).get("html", "")
        if credit_url:
            credit_url += UNSPLASH_UTM
        print(f"  -> Bild gespeichert: {path} (Foto: {credit_name})")
        return {"path": path, "small": small_path,
                "credit_name": credit_name, "credit_url": credit_url}
    except Exception as e:
        print(f"  -> Bildfehler: {e}")
        return None

def fetch_article_text(url, max_chars=8000):
    """Lädt den Artikel und extrahiert den Haupttext."""
    from bs4 import BeautifulSoup
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        # Boilerplate entfernen
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        # Haupttext aus <article> oder <main> oder <body>
        main = soup.find("article") or soup.find("main") or soup.find("body")
        text = " ".join((main or soup).get_text(separator=" ").split())
        return text[:max_chars]
    except Exception as e:
        print(f"  -> Artikel-Fetch Fehler: {e}")
        return ""

def ask_gemini(url, category, rss_title="", rss_summary=""):
    heute = datetime.now().strftime("%d.%m.%Y")

    print(f"  -> Lade Artikel...")
    article_text = fetch_article_text(url)

    # Kombiniere RSS-Summary + gescrapten Text für maximalen Kontext
    combined = " ".join(filter(None, [rss_title, rss_summary, article_text]))
    source_block = f"ARTIKELINHALT:\n{combined[:4500]}" if combined.strip() else f"URL: {url}"

    prompt = f"""Du bist Redakteur bei 'BytePost', einem deutschen Tech-Newsletter für Entwickler.

{source_block}

DEINE AUFGABE:
Schreibe eine EIGENSTÄNDIGE, KURZE Zusammenfassung dieses Artikels auf Deutsch — in deinen EIGENEN Worten. Die Zusammenfassung gibt die Kernfakten wieder und macht neugierig auf den Originalartikel, ersetzt ihn aber NICHT.

WICHTIGE REGELN (Urheberrecht):
- Komplett eigene Formulierungen — KEINE Übersetzung des Originaltexts Absatz für Absatz
- Keine wörtlichen Zitate über 15 Wörter; kurze Zitate immer als solche kennzeichnen
- Nur die wichtigsten Fakten und Zahlen — Details bleiben dem Original vorbehalten
- Der Text soll motivieren, den verlinkten Originalartikel zu lesen

STIL:
- Fließender, gut lesbarer Journalismus auf Deutsch
- Direkte "Du"-Ansprache wo es passt
- Am Ende: kurze eigene Einordnung für Entwickler

FORMAT für "content" (Zusammenfassung auf Deutsch):
- <h3>kurze Zwischenüberschriften</h3> zur Strukturierung (max. 2)
- <p>-Absätze, <ul> für Aufzählungen
- Abschluss: <p><em>BytePost-Einordnung: ...</em></p>
- Länge: MAXIMAL 250 Wörter

FORMAT für "content_simple" (Einfach erklärt — für Einsteiger & Nicht-Techniker):
- Keine Fachbegriffe, stattdessen Alltagsvergleiche und Analogien
- 100-130 Wörter, <p>-Absätze, kein h3

FORMAT für "content_pro" (Für Profis — für Entwickler & Engineers):
- Technische Einordnung: Architektur, Technologien, Protokolle, Trade-offs — in eigenen Worten
- Code-Beispiele in <pre><code> NUR wenn ein echtes, sinnvolles Beispiel möglich ist (z.B. Patch-Check, Erkennungslogik, Konfiguration, API-Aufruf). KEIN Placeholder-Code, KEINE Kommentare wie "Beispielcode hier". Lieber kein Code-Block als ein leerer.
- Hinweise auf verwandte Konzepte, Standards oder Papers
- 150-220 Wörter, <h3> zur Strukturierung

SENTIMENT: "positiv" (Fortschritt/Innovation), "neutral" (Update/Info), "kritisch" (Risiko/Sicherheitsproblem/Kontroverse)

Antworte NUR mit diesem JSON (keine Backticks, kein Text davor/danach):
{{
    "cat": ["ki"],
    "icon": "Passendes Emoji",
    "title": "Aussagekräftige Headline auf Deutsch: Wer/Was + Aktion + Kontext. Max. 10 Wörter. Kein Clickbait, keine Auslassungspunkte. Beispiele: 'Meta ersetzt WebRTC-Fork nach 10 Jahren Eigenentwicklung', 'Kritische Lücke in OpenSSH erlaubt Root-Zugriff ohne Passwort'",
    "source": "Echter Name der Originalquelle (z.B. TechCrunch, The Verge, GitHub Blog) — NICHT 'BytePost'",
    "read": "X Min",
    "image_query": "2 englische Suchbegriffe für Unsplash",
    "sentiment": "positiv|neutral|kritisch",
    "content": "Vollständiger Artikel auf Deutsch (HTML mit h3, p, ul)",
    "content_simple": "Einfach erklärt ohne Fachbegriffe (HTML, nur p)",
    "content_pro": "Technische Tiefenversion für Entwickler (HTML mit h3, p, pre>code)"
}}

"cat" ist ein JSON-Array mit 1-3 passenden Kategorien aus: ki, dev, data, security, cloud, hardware, business, gaming
Beispiele: ["ki"] oder ["ki","dev"] oder ["security","ki"]"""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        print(f"  -> Groq Status: {r.status_code}")
        if r.status_code != 200:
            print(f"  -> Fehler: {r.text[:200]}")
            return None

        raw = r.json()["choices"][0]["message"]["content"].strip()
        clean = re.sub(r"```json|```", "", raw).strip()
        # Literal-Newlines in JSON-Strings sind ungültig — durch Leerzeichen ersetzen
        clean = re.sub(r'\n', ' ', clean)
        data = json.loads(clean)
        # Normalize cat to always be a list of clean lowercase strings
        cat = data.get("cat", ["ki"])
        if isinstance(cat, str):
            cat = [c.strip().lower() for c in re.split(r'[|/,]+', cat) if c.strip()]
        else:
            cat = [c.strip().lower() for c in cat if c.strip()]
        valid = {"ki", "dev", "data", "security", "cloud", "hardware", "business", "gaming"}
        cat = [c for c in cat if c in valid] or ["ki"]
        if category.lower() == "gaming" and "gaming" not in cat:
            cat.insert(0, "gaming")
        data["cat"] = cat
        data.pop("tag", None)      # tag field no longer needed
        data.pop("related", None)  # related wird serverseitig via Embeddings berechnet
        # Never let source be "BytePost" — derive from URL if needed
        SOURCE_MAP = {
            'techcrunch.com': 'TechCrunch', 'theverge.com': 'The Verge',
            'arstechnica.com': 'Ars Technica', 'stackoverflow.blog': 'Stack Overflow Blog',
            'github.blog': 'GitHub Blog', 'towardsdatascience.com': 'Towards Data Science',
            'engineering.atspotify.com': 'Spotify Engineering', 'openai.com': 'OpenAI',
            'heise.de': 'Heise', 'golem.de': 'Golem', 't3n.de': 't3n',
            'blogs.microsoft.com': 'Microsoft AI Blog',
            'ign.com': 'IGN', 'rockpapershotgun.com': 'Rock Paper Shotgun',
            'gamespot.com': 'GameSpot',
        }
        if not data.get('source') or data.get('source') in ('BytePost', 'Quellenname', 'Unknown', 'unknown', ''):
            for domain, name in SOURCE_MAP.items():
                if domain in url:
                    data['source'] = name
                    break
            else:
                # Fallback: Domain aus URL ableiten
                m = re.search(r'https?://(?:www\.)?([^/]+)', url)
                if m:
                    parts = m.group(1).split('.')
                    data['source'] = parts[-2].capitalize() if len(parts) >= 2 else m.group(1)
        data["date"] = heute
        # Lesezeit aus tatsächlichem Content berechnen (200 Wörter/Min)
        content_text = re.sub(r'<[^>]+>', '', data.get('content', ''))
        word_count = len(content_text.split())
        read_min = max(1, round(word_count / 200))
        data['read'] = f'{read_min} Min'
        tokens = r.json().get("usage", {})
        print(f"  -> OK | Cats: {cat} | Sentiment: {data.get('sentiment','?')} | Tokens: {tokens.get('total_tokens','?')}")
        return data
    except json.JSONDecodeError as e:
        print(f"  -> JSON-Fehler: {e} | Antwort: {raw[:200]}")
        return None
    except Exception as e:
        print(f"  -> Fehler: {e}")
        return None

def compute_bytepulse(articles, today_str):
    today_articles = [a for a in articles if a.get("date") == today_str]
    if not today_articles: return None
    counts = {"positiv": 0, "neutral": 0, "kritisch": 0}
    for a in today_articles:
        s = a.get("sentiment", "neutral")
        counts[s if s in counts else "neutral"] += 1
    total = sum(counts.values())
    return {
        "date": today_str,
        "positiv": round(counts["positiv"] / total * 100),
        "neutral": round(counts["neutral"] / total * 100),
        "kritisch": round(counts["kritisch"] / total * 100),
        "total": total,
    }

def cosine_sim(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(y * y for y in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def find_related(article, all_articles, emb_store, limit=3, threshold=0.87):
    """Embedding-basierte Ähnlichkeit (Cosine Similarity), max. 3 Treffer."""
    vec = emb_store.get(article.get("id"))
    if not vec:
        return []
    scored = []
    for a in all_articles:
        if a.get("id") == article.get("id") or a.get("title") == article.get("title"):
            continue
        other = emb_store.get(a.get("id"))
        if not other:
            continue
        sim = cosine_sim(vec, other)
        if sim >= threshold:
            reason = "Sehr ähnliches Thema" if sim > 0.93 else "Verwandtes Thema"
            scored.append((sim, {"id": a["id"], "reason": reason}))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:limit]]

def pick_of_the_day(today_articles):
    """Lässt die KI den relevantesten Artikel wählen und begründen."""
    if len(today_articles) == 1:
        return today_articles[0]

    overview = "\n".join(
        f"{i+1}. [{a.get('tag','')}] {a.get('title','')} — {a.get('source','')} ({a.get('sentiment','')})"
        for i, a in enumerate(today_articles)
    )

    prompt = f"""Du bist Chefredakteur von 'BytePost', einem deutschen Tech-Newsletter für Entwickler.

Hier sind die heutigen Artikel:
{overview}

Wähle den "Pick of the Day" — den Artikel mit dem größten Impact für Entwickler heute.

Schreibe dann einen packenden Teaser-Text für die Hero-Sektion der Website: 2-3 Sätze, die den Leser sofort fesseln. Erkläre konkret, warum dieser Artikel heute wichtig ist, was auf dem Spiel steht, was sich verändert oder was Entwickler daraus mitnehmen sollten. Schreibe direkt, meinungsstark und journalistisch — kein "Dieser Artikel zeigt...", sondern direkt in die Relevanz einsteigen.

Antworte NUR mit diesem JSON (keine Backticks, kein Text davor/danach):
{{"id": <Nummer>, "reason": "<2-3 Sätze packender Teaser auf Deutsch — direkt, konkret, journalistisch>"}}"""

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        if r.status_code == 200:
            raw = r.json()["choices"][0]["message"]["content"].strip()
            result = json.loads(re.sub(r"```json|```", "", raw).strip())
            idx = int(result["id"]) - 1
            if 0 <= idx < len(today_articles):
                reason = result.get("reason", "")
                print(f"  -> KI wählt Artikel #{idx+1}: {reason}")
                today_articles[idx]["pick_reason"] = reason
                return today_articles[idx]
    except Exception as e:
        print(f"  -> Pick-Fehler: {e}")

    # Fallback: erster Artikel
    return today_articles[0]


def parse_date_de(s):
    """DD.MM.YYYY → datetime (oder None)."""
    try:
        return datetime.strptime(s or "", "%d.%m.%Y")
    except ValueError:
        return None


ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="de" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — BytePost</title>
    <meta name="description" content="{description}">
    <link rel="canonical" href="{canonical}">
    <link rel="icon" type="image/svg+xml" href="../favicon.svg">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{canonical}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    {og_image}
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <style>
        :root {{ --bg:#0a0a0a; --bg-card:#141414; --text:#f5f5f7; --text-2:#aeaeb2; --text-3:#636366; --accent:#0071e3; --border:rgba(255,255,255,0.08); }}
        * {{ box-sizing:border-box; margin:0; padding:0; }}
        body {{ background:var(--bg); color:var(--text); font-family:-apple-system,'DM Sans',sans-serif; line-height:1.7; }}
        .wrap {{ max-width:680px; margin:0 auto; padding:32px 20px 60px; }}
        .top-link {{ font-size:13px; color:var(--accent); text-decoration:none; }}
        h1 {{ font-size:28px; line-height:1.2; margin:18px 0 8px; }}
        .meta {{ font-size:12px; color:var(--text-3); margin-bottom:24px; font-family:monospace; }}
        img.hero {{ width:100%; border-radius:12px; margin-bottom:20px; }}
        .content {{ font-size:15px; color:var(--text-2); }}
        .content h3 {{ color:var(--text); margin:22px 0 8px; }}
        .content p {{ margin:12px 0; }}
        .content ul {{ padding-left:20px; margin:12px 0; }}
        .cta {{ display:block; margin:32px 0 0; padding:14px 18px; background:var(--bg-card); border:1px solid var(--border); border-radius:12px; color:var(--accent); text-decoration:none; font-weight:600; }}
        .src {{ margin-top:14px; font-size:12px; color:var(--text-3); }}
        .src a {{ color:var(--accent); }}
    </style>
</head>
<body>
<div class="wrap">
    <a class="top-link" href="../index.html">← BytePost</a>
    <h1>{title}</h1>
    <div class="meta">{source} · {date} · {read} Lesezeit</div>
    {hero_img}
    <div class="content">{content}</div>
    <a class="cta" href="../index.html#a={id}">↗ Auf BytePost öffnen — mit „Einfach erklärt" &amp; Profi-Version</a>
    <div class="src">Originalquelle: <a href="{url}" target="_blank" rel="noopener">{source}</a> · KI-generierte Zusammenfassung, alle Rechte am Original beim Verlag/Autor.</div>
</div>
</body>
</html>
"""


def write_article_pages(db):
    """Schreibt pro Artikel eine statische SEO-Seite nach artikel/<id>.html."""
    os.makedirs(ARTICLE_DIR, exist_ok=True)
    count = 0
    for a in db["articles"]:
        if not a.get("id"):
            continue
        esc = html_mod.escape
        title = esc(a.get("title", ""))
        description = esc(strip_html(a.get("content", ""))[:160])
        canonical = f"{SITE_URL}/{ARTICLE_DIR}/{a['id']}.html"
        og_image = (f'<meta property="og:image" content="{SITE_URL}/{a["image_local"]}">'
                    if a.get("image_local") else "")
        hero_img = (f'<img class="hero" src="../{esc(a["image_local"])}" alt="{title}">'
                    if a.get("image_local") else "")
        page = ARTICLE_TEMPLATE.format(
            title=title, description=description, canonical=canonical,
            og_image=og_image, hero_img=hero_img,
            content=a.get("content", ""), id=a["id"],
            url=esc(a.get("url", "")), source=esc(a.get("source", "")),
            date=esc(a.get("date", "")), read=esc(a.get("read", "")),
        )
        with open(f"{ARTICLE_DIR}/{a['id']}.html", "w", encoding="utf-8") as f:
            f.write(page)
        count += 1
    print(f"Artikel-Seiten geschrieben: {count} → {ARTICLE_DIR}/")


def write_sitemap(db):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
             f'  <url><loc>{SITE_URL}/</loc></url>']
    for a in db["articles"]:
        if not a.get("id"):
            continue
        d = parse_date_de(a.get("date"))
        lastmod = f"<lastmod>{d.strftime('%Y-%m-%d')}</lastmod>" if d else ""
        lines.append(f"  <url><loc>{SITE_URL}/{ARTICLE_DIR}/{a['id']}.html</loc>{lastmod}</url>")
    lines.append("</urlset>")
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("sitemap.xml geschrieben.")


def write_rss(db):
    """RSS 2.0 Feed mit den letzten 30 Artikeln."""
    esc = html_mod.escape
    articles = sorted(db["articles"],
                      key=lambda a: parse_date_de(a.get("date")) or datetime(1970, 1, 1),
                      reverse=True)[:30]
    items = []
    for a in articles:
        if not a.get("id"):
            continue
        d = parse_date_de(a.get("date"))
        pub = f"<pubDate>{d.strftime('%a, %d %b %Y 06:00:00 +0000')}</pubDate>" if d else ""
        teaser = esc(strip_html(a.get("content", ""))[:300])
        cats_xml = "".join(f"<category>{esc(c)}</category>" for c in (a.get("cat") or []))
        link = f"{SITE_URL}/{ARTICLE_DIR}/{a['id']}.html"
        items.append(f"""    <item>
      <title>{esc(a.get('title', ''))}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <description>{teaser}</description>
      {pub}{cats_xml}
    </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>BytePost — Deutsche Tech News</title>
    <link>{SITE_URL}/</link>
    <description>Deutsche Tech News täglich in 5 Minuten — KI-kuratierte Zusammenfassungen.</description>
    <language>de-de</language>
{chr(10).join(items)}
  </channel>
</rss>
"""
    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(feed)
    print(f"feed.xml geschrieben ({len(items)} Einträge).")


def write_outputs(db):
    """Statische Artikel-Seiten, Sitemap und RSS-Feed erzeugen."""
    write_article_pages(db)
    write_sitemap(db)
    write_rss(db)


def check_api_keys():
    """Bricht mit klarer Fehlermeldung ab, wenn ein Key fehlt."""
    missing = []
    if not GROQ_API_KEY:   missing.append("GROQ_API_KEY        (https://console.groq.com)")
    if not VOYAGE_API_KEY: missing.append("VOYAGE_API_KEY      (https://www.voyageai.com)")
    if not UNSPLASH_KEY:   missing.append("UNSPLASH_ACCESS_KEY (https://unsplash.com/developers)")
    if missing:
        print("FEHLER: Folgende API-Keys fehlen (Umgebungsvariable oder .env):")
        for m in missing:
            print(f"  - {m}")
        print("Vorlage: siehe .env.example")
        raise SystemExit(1)


def run():
    check_api_keys()

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = {"articles": []}

    heute = datetime.now().strftime("%d.%m.%Y")

    # Embedding-Store laden, fehlende Vektoren nachholen (unabhängig vom Groq-Tageslimit)
    emb_store = load_embeddings()
    backfill_embeddings(db["articles"], emb_store)

    # Related für Alt-Artikel nachziehen, sobald deren Embedding vorliegt
    for a in db["articles"]:
        if not a.get("related") and a.get("id") in emb_store:
            a["related"] = find_related(a, db["articles"], emb_store)

    # Tagessperre prüfen
    today_count = sum(1 for a in db["articles"] if a.get("date") == heute)
    if today_count >= MAX_PER_DAY:
        print(f"Tageslimit erreicht ({today_count}/{MAX_PER_DAY}). Abbruch.")
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        write_outputs(db)
        return

    remaining_today = MAX_PER_DAY - today_count
    effective_limit = min(MAX_PER_RUN, remaining_today)
    print(f"Heute bereits: {today_count} | Noch erlaubt: {remaining_today} | Diesen Lauf max: {effective_limit}")

    existing_urls = {a.get("url", "") for a in db["articles"] if a.get("url")}
    new_count = 0
    error_streak = 0
    new_articles = []

    candidates = collect_candidates(existing_urls, effective_limit)
    print(f"✅ {len(candidates)} Kandidaten gefunden\n")

    for cat_key, source_name, post in candidates:
        if new_count >= effective_limit:
            break

        category_hint = CATEGORY_HINT.get(cat_key, "tech")
        print(f"Verarbeite [{cat_key}]: {post.title[:60]}")

        rss_title   = getattr(post, "title", "")
        rss_summary = getattr(post, "summary", "") or getattr(post, "description", "")
        rss_summary = strip_html(rss_summary)[:2000]

        # Dedupe: gleiche News aus zweiter Quelle (z.B. Heise + Golem) überspringen
        cand_vec = get_embedding(f"{rss_title}. {rss_summary[:600]}")
        if cand_vec and emb_store:
            best_sim = max(cosine_sim(cand_vec, v) for v in emb_store.values())
            if best_sim > 0.92:
                print(f"  -> ÜBERSPRUNGEN (Duplikat, Similarity {best_sim:.3f}): {rss_title[:60]}")
                continue

        entry = ask_gemini(post.link, category_hint, rss_title, rss_summary)

        if entry is None:
            error_streak += 1
            print(f"  -> Fehler-Serie: {error_streak}/{MAX_ERRORS}")
            if error_streak >= MAX_ERRORS:
                print("Circuit Breaker ausgelöst. Abbruch.")
                break
            continue

        error_streak = 0
        entry["id"]        = os.urandom(4).hex()
        entry["url"]       = post.link
        image_query        = entry.pop("image_query", "technology")
        img = get_unsplash_image(image_query, entry["id"])
        entry["image_local"]       = img["path"]  if img else None
        entry["image_small"]       = img["small"] if img else None
        entry["image_credit_name"] = img["credit_name"] if img else ""
        entry["image_credit_url"]  = img["credit_url"]  if img else ""
        vec = get_embedding(embed_text(entry))
        if vec:
            emb_store[entry["id"]] = vec
            save_embeddings(emb_store)
            print(f"  -> Embedding: {len(vec)} Dimensionen (→ {EMBED_FILE})")
        db["articles"].insert(0, entry)
        new_articles.append(entry)
        existing_urls.add(post.link)
        new_count += 1
        print(f"  -> Erstellt: {entry['title']} ({new_count}/{effective_limit})")
        time.sleep(20)

    # Pick of the Day — KI entscheidet
    for a in db["articles"]: a["pick"] = False
    today_articles = [a for a in db["articles"] if a.get("date") == heute]
    if today_articles:
        pick = pick_of_the_day(today_articles)
        pick["pick"] = True
        print(f"\nPick of the Day: {pick['title']}")

    # Related Articles — serverseitig via Embeddings (Cosine Similarity)
    for article in new_articles:
        article["related"] = find_related(article, db["articles"], emb_store)

    # BytePulse — aktueller Tag + Historie (max. 90 Tage)
    pulse = compute_bytepulse(db["articles"], heute)
    if pulse:
        db["bytepulse"] = pulse
        history = [h for h in db.get("bytepulse_history", []) if h.get("date") != heute]
        history.append(pulse)
        history.sort(key=lambda h: parse_date_de(h.get("date")) or datetime(1970, 1, 1))
        db["bytepulse_history"] = history[-90:]
        print(f"BytePulse: {pulse['positiv']}% positiv, {pulse['neutral']}% neutral, {pulse['kritisch']}% kritisch ({len(db['bytepulse_history'])} Tage Historie)")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    write_outputs(db)
    print(f"\nFertig. {new_count} neue Artikel erstellt.")

if __name__ == "__main__":
    import sys
    if "--outputs-only" in sys.argv:
        # Nur Artikel-Seiten/Sitemap/Feed neu erzeugen — keine Keys nötig
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            write_outputs(json.load(f))
    else:
        run()
