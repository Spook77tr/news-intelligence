import os
import json
from google.cloud import bigquery

PROJECT = os.environ["GCP_PROJECT_ID"]
DATASET = os.environ.get("BQ_DATASET", "news_intelligence")


def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT)


def table_ref(table: str) -> str:
    return f"{PROJECT}.{DATASET}.{table}"


def insert_rows(table: str, rows: list[dict]) -> list:
    client = get_client()
    errors = client.insert_rows_json(table_ref(table), rows)
    return errors


def query(sql: str) -> list[dict]:
    client = get_client()
    result = client.query(sql).result()
    return [dict(row) for row in result]


def get_today_ids(table: str = "raw_news") -> set[str]:
    rows = query(f"""
        SELECT id FROM `{table_ref(table)}`
        WHERE DATE(fetched_at) = CURRENT_DATE('Europe/Istanbul')
    """)
    return {r["id"] for r in rows}


def get_unprocessed_articles() -> list[dict]:
    """Bugün çekilmiş ama henüz cluster'a atanmamış haberler."""
    return query(f"""
        SELECT r.*
        FROM `{table_ref('raw_news')}` r
        LEFT JOIN (
            SELECT DISTINCT art_id
            FROM `{table_ref('news_clusters')}`,
            UNNEST(article_ids) AS art_id
            WHERE DATE(created_at) = CURRENT_DATE('Europe/Istanbul')
        ) c ON r.id = c.art_id
        WHERE DATE(r.fetched_at) = CURRENT_DATE('Europe/Istanbul')
          AND c.art_id IS NULL
    """)


def get_unanalyzed_clusters() -> list[dict]:
    """Bugün cluster'a atanmış ama analiz edilmemiş kayıtlar (Gemini hatası sonrası retry için)."""
    # Debug: toplam bugünkü cluster sayısını da logla
    total = query(f"""
        SELECT COUNT(*) AS cnt
        FROM `{table_ref('news_clusters')}`
        WHERE DATE(created_at) = CURRENT_DATE('Europe/Istanbul')
    """)
    print(f"[DEBUG] Total clusters today in BQ: {total[0]['cnt'] if total else 'query failed'}")

    return query(f"""
        SELECT c.*
        FROM `{table_ref('news_clusters')}` c
        LEFT JOIN `{table_ref('analyzed_news')}` a USING (cluster_id)
        WHERE DATE(c.created_at) = CURRENT_DATE('Europe/Istanbul')
          AND a.cluster_id IS NULL
    """)


def get_articles_by_ids(article_ids) -> list[dict]:
    """Verilen ID listesindeki haberleri getir. BQ REPEATED alanı list veya tuple olabilir."""
    if not article_ids:
        return []
    ids = list(article_ids)  # tuple/RepeatField → list
    if not ids:
        return []
    ids_str = ", ".join(f"'{aid}'" for aid in ids)
    return query(f"""
        SELECT * FROM `{table_ref('raw_news')}`
        WHERE id IN ({ids_str})
    """)


def get_todays_actionable_clusters() -> list[dict]:
    """Notifier için: bugünün monitor + actionable analizleri."""
    return query(f"""
        SELECT a.*, c.article_ids, c.sources, c.bias_spread
        FROM `{table_ref('analyzed_news')}` a
        JOIN `{table_ref('news_clusters')}` c USING (cluster_id)
        WHERE a.analysis_date = CURRENT_DATE('Europe/Istanbul')
          AND a.signal_label IN ('monitor', 'actionable')
        ORDER BY a.significance_score DESC
    """)
