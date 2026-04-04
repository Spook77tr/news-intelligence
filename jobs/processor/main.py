import sys, json
sys.path.insert(0, "/app/shared")

import bq_client
from clusterer import cluster_articles, build_cluster_record
from analyzer import analyze_cluster, build_analyzed_record


def run():
    # 1. Bugün çekilmiş, henüz işlenmemiş haberleri al
    articles = bq_client.get_unprocessed_articles()
    print(f"[INFO] Unprocessed articles: {len(articles)}")

    if len(articles) < 2:
        print("[INFO] Not enough articles to cluster. Exiting.")
        return

    # 2. Cluster
    clusters = cluster_articles(articles)
    if not clusters:
        print("[INFO] No valid clusters found.")
        return

    # 3. Her cluster için: BQ'ya yaz + analiz et
    for cluster_articles_list in clusters:
        cluster_record = build_cluster_record(cluster_articles_list)

        # Cluster'ı BQ'ya yaz
        errors = bq_client.insert_rows("news_clusters", [cluster_record])
        if errors:
            print(f"[ERROR] Cluster insert failed: {errors}")
            continue

        print(f"[INFO] Cluster {cluster_record['cluster_id'][:8]}... "
              f"({len(cluster_articles_list)} articles, {len(cluster_record['bias_spread'])} biases)")

        # Claude ile analiz et
        analysis = analyze_cluster(cluster_record, cluster_articles_list)
        if not analysis:
            continue

        analyzed_record = build_analyzed_record(cluster_record, analysis)

        # JSON alanlarını serialize et (BQ JSON type için)
        for field in ["narrative_groups", "information_gaps", "impact_analysis",
                      "source_credibility", "temporal_context", "scenarios"]:
            if field in analyzed_record and not isinstance(analyzed_record[field], str):
                analyzed_record[field] = json.dumps(analyzed_record[field], ensure_ascii=False)

        errors = bq_client.insert_rows("analyzed_news", [analyzed_record])
        if errors:
            print(f"[ERROR] Analysis insert failed: {errors}")
            continue

        signal = analyzed_record["signal_label"]
        score = analyzed_record["significance_score"]
        print(f"[INFO] Analyzed → signal={signal}, score={score:.2f}")

    print("[INFO] Processor complete.")


if __name__ == "__main__":
    run()
