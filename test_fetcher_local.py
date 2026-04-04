#!/usr/bin/env python3
"""
Local fetcher test. Tests RSS fetch and optionally BQ write.

Usage:
    python test_fetcher_local.py            # fetch only (no BQ)
    python test_fetcher_local.py --write-bq # fetch + insert to raw_news

Requirements:
    pip install feedparser google-cloud-bigquery pyyaml pydantic
    export GCP_PROJECT_ID=bi4ward
    # gcloud auth application-default login  (or set GOOGLE_APPLICATION_CREDENTIALS)
"""
import sys, os, hashlib, yaml
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "shared"))

# Single test source — Reuters is reliable and unauthenticated
TEST_SOURCE = {
    "name": "Reuters_TEST",
    "url": "https://feeds.reuters.com/reuters/topNews",
    "bias": "INTL_NEUTRAL",
}


def fetch_source(src: dict, max_articles: int = 3) -> list[dict]:
    import feedparser
    feed = feedparser.parse(src["url"], request_headers={"User-Agent": "Mozilla/5.0"})
    now = datetime.now(timezone.utc)
    rows = []
    for entry in feed.entries[:max_articles]:
        url = entry.get("link", "")
        title = entry.get("title", "").strip()
        if not url or not title:
            continue
        row_id = hashlib.md5(f"{src['name']}{url}".encode()).hexdigest()
        snippet = (entry.get("summary", "") or "")[:600]
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        published_at = datetime(*pub[:6], tzinfo=timezone.utc).isoformat() if pub else now.isoformat()
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


if __name__ == "__main__":
    print("=== Fetcher Local Test ===\n")

    rows = fetch_source(TEST_SOURCE)
    if not rows:
        print("[FAIL] No articles fetched — check RSS URL or network")
        sys.exit(1)

    print(f"[OK] Fetched {len(rows)} articles from {TEST_SOURCE['name']}:")
    for r in rows:
        print(f"  • {r['title'][:90]}")
        print(f"    id={r['id'][:12]}... url={r['url'][:60]}")

    if "--write-bq" not in sys.argv:
        print("\n[INFO] RSS fetch OK. Run with --write-bq to test BQ insert.")
        sys.exit(0)

    # BQ test
    project = os.environ.get("GCP_PROJECT_ID")
    if not project:
        print("\n[FAIL] GCP_PROJECT_ID not set")
        sys.exit(1)

    import bq_client
    print(f"\n[INFO] Writing {len(rows)} rows to {project}.news_intelligence.raw_news ...")
    errors = bq_client.insert_rows("raw_news", rows)
    if errors:
        print(f"[FAIL] BQ insert errors: {errors}")
        sys.exit(1)

    print(f"[OK] Inserted {len(rows)} rows successfully.")
    print(f"[INFO] Verify: bq query --use_legacy_sql=false "
          f"'SELECT id,source,title FROM `{project}.news_intelligence.raw_news` "
          f"WHERE source=\"Reuters_TEST\" LIMIT 5'")
