"""
Einmalige Migration: Embeddings aus data.json nach embeddings.json auslagern
und 'related' für alle Alt-Artikel embedding-basiert berechnen.

Self-contained — benötigt keine API-Keys und keine Generator-Dependencies.
Aufruf:  python migrate_embeddings.py
"""
import json, os

DATA_FILE  = "data.json"
EMBED_FILE = "embeddings.json"


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
    """Embedding-basierte Ähnlichkeit — identische Logik wie in generator.py."""
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


def normalize_related(related, existing_ids):
    """Altes Format (Liste von ID-Strings) → neues Format [{id, reason}]."""
    if not isinstance(related, list):
        return []
    out = []
    for r in related:
        if isinstance(r, dict) and r.get("id") in existing_ids:
            out.append({"id": r["id"], "reason": r.get("reason", "Verwandter Artikel")})
        elif isinstance(r, str) and r in existing_ids:
            out.append({"id": r, "reason": "Verwandter Artikel"})
    return out[:3]


def migrate():
    if not os.path.exists(DATA_FILE):
        print(f"FEHLER: {DATA_FILE} nicht gefunden.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
    articles = db.get("articles", [])
    existing_ids = {a["id"] for a in articles if a.get("id")}

    # 1. Embeddings extrahieren → embeddings.json
    emb_store = {}
    if os.path.exists(EMBED_FILE):
        with open(EMBED_FILE, "r", encoding="utf-8") as f:
            emb_store = json.load(f)
    extracted = 0
    for a in articles:
        vec = a.pop("embedding", None)
        if vec and a.get("id"):
            emb_store[a["id"]] = vec
            extracted += 1
    with open(EMBED_FILE, "w", encoding="utf-8") as f:
        json.dump(emb_store, f)
    print(f"Embeddings extrahiert: {extracted} (Store gesamt: {len(emb_store)}) → {EMBED_FILE}")

    # 2. Related berechnen (embedding-basiert) bzw. Altformat normalisieren
    computed, kept = 0, 0
    for a in articles:
        if a.get("id") in emb_store:
            a["related"] = find_related(a, articles, emb_store)
            computed += 1
        else:
            a["related"] = normalize_related(a.get("related"), existing_ids)
            kept += 1
    print(f"Related berechnet: {computed} via Embedding, {kept} normalisiert (kein Vektor)")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    size_mb = os.path.getsize(DATA_FILE) / 1024 / 1024
    print(f"Fertig. {DATA_FILE}: {size_mb:.2f} MB")


if __name__ == "__main__":
    migrate()
