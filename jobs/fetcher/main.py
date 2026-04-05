import sys, os
sys.path.insert(0, "/app/shared")

import hashlib
import feedparser
import yaml
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import bq_client

TR_TZ = ZoneInfo("Europe/Istanbul")

# Spor haberleri filtresi — bu kelimeleri içeren başlıklar atlanır
SPORTS_KEYWORDS = {
    # TR
    "futbol", "maç", "gol", "lig", "şampiyonluk", "transfer", "teknik direktör",
    "süper lig", "milli takım", "basketbol", "voleybol", "tenis", "formula",
    "olimpiyat", "dünya kupası", "şampiyonlar ligi", "fenerbahçe", "galatasaray",
    "beşiktaş", "trabzonspor", "taraftar",
    # EN
    "football", "soccer", "nfl", "nba", "nhl", "mlb", "fifa", "uefa",
    "premier league", "la liga", "bundesliga", "serie a", "champions league",
    "world cup", "olympic", "olympics", "tournament", "championship",
    "transfer window", "match", "goal", "striker", "midfielder", "goalkeeper",
    "tennis", "wimbledon", "formula 1", "f1", "grand prix", "nascar",
    "basketball", "baseball", "cricket", "rugby", "golf",
}


def is_sports(title: str) -> bool:
    title_lower = title.lower()
    return any(kw in title_lower for kw in SPORTS_KEYWORDS)


def load_sources(path: str = "/app/config/sources.yaml") -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f)["sources"]


def fetch_source(src: dict, max_articles: int = 20, snippet_len: int = 600) -> list[dict]:
    try:
        feed = feedparser.parse(src["url"], request_headers={"User-Agent": "Mozilla/5.0"})
    except Exception as e:
        print(f"[WARN] {src['name']} fetch failed: {e}")
        return []

    rows = []
    now = datetime.now(timezone.utc)

    for entry in feed.entries[:max_articles]:
        url = entry.get("link", "")
        title = entry.get("title", "").strip()
        if not url or not title:
            continue

        if is_sports(title):
            continue

        row_id = hashlib.md5(f"{src['name']}{url}".encode()).hexdigest()
        snippet = (
            entry.get("summary", "") or
            entry.get("description", "") or ""
        )[:snippet_len]

        # published_at parse
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        if pub:
            published_at = datetime(*pub[:6], tzinfo=timezone.utc).isoformat()
        else:
            published_at = now.isoformat()

        rows.append({
            "id": row_id,
            "source": src["name"],
            "bias_label": src["bias"],
            "title": title,
            "url": url,
            "content_snippet": snippet,
            "published_at": published_at,
            "fetched_at": now.isoformat(),
            "topic_tags": [],
        })

    return rows


def run():
    sources = load_sources()
    existing_ids = bq_client.get_today_ids()
    print(f"[INFO] Already fetched today: {len(existing_ids)} articles")

    all_rows = []
    for src in sources:
        rows = fetch_source(src)
        new_rows = [r for r in rows if r["id"] not in existing_ids]
        all_rows.extend(new_rows)
        print(f"[INFO] {src['name']}: {len(rows)} fetched, {len(new_rows)} new")

    if not all_rows:
        print("[INFO] No new articles. Exiting.")
        return

    errors = bq_client.insert_rows("raw_news", all_rows)
    if errors:
        print(f"[ERROR] BQ insert errors: {errors}")
        sys.exit(1)

    print(f"[INFO] Inserted {len(all_rows)} new articles to BQ.")


if __name__ == "__main__":
    run()
