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
