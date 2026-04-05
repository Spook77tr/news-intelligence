import uuid
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from vertexai.language_models import TextEmbeddingModel
import vertexai
import os

vertexai.init(project=os.environ["GCP_PROJECT_ID"], location="europe-west1")

SIMILARITY_THRESHOLD = float(os.environ.get("CLUSTER_THRESHOLD", "0.70"))
MIN_SOURCES_PER_CLUSTER = int(os.environ.get("MIN_CLUSTER_SOURCES", "2"))


def embed_titles(titles: list[str]) -> np.ndarray:
    model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    # Batch max 250
    all_embeddings = []
    for i in range(0, len(titles), 250):
        batch = titles[i:i+250]
        embeddings = model.get_embeddings(batch)
        all_embeddings.extend([e.values for e in embeddings])
    return np.array(all_embeddings)


def cluster_articles(articles: list[dict]) -> list[list[dict]]:
    if len(articles) < 2:
        return []

    titles = [a["title"] for a in articles]
    print(f"[INFO] Embedding {len(titles)} titles...")
    embeddings = embed_titles(titles)
    sim_matrix = cosine_similarity(embeddings)
    np.fill_diagonal(sim_matrix, 0)  # exclude self-similarity
    print(f"[INFO] Similarity — max: {sim_matrix.max():.3f}, mean: {sim_matrix.mean():.3f}, threshold: {SIMILARITY_THRESHOLD}")

    n = len(articles)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    # Only link articles from DIFFERENT sources
    for i in range(n):
        for j in range(i + 1, n):
            if (sim_matrix[i][j] >= SIMILARITY_THRESHOLD and
                    articles[i]["source"] != articles[j]["source"]):
                union(i, j)

    from collections import defaultdict
    components = defaultdict(list)
    for i in range(n):
        components[find(i)].append(articles[i])

    clusters = []
    for component in components.values():
        unique_sources = {a["source"] for a in component}
        if len(unique_sources) >= MIN_SOURCES_PER_CLUSTER:
            clusters.append(component)

    print(f"[INFO] Found {len(clusters)} valid clusters from {len(articles)} articles")
    return clusters


def build_cluster_record(articles: list[dict]) -> dict:
    from datetime import datetime, timezone

    sources = list({a["source"] for a in articles})
    bias_spread = list({a["bias_label"] for a in articles})
    article_ids = [a["id"] for a in articles]

    # Topic: en çok tekrar eden kelimeleri kullan (basit yaklaşım)
    all_titles = " ".join(a["title"] for a in articles)
    topic = all_titles[:100]  # processor/analyzer.py'de Claude ile refine edilecek

    return {
        "cluster_id": str(uuid.uuid4()),
        "topic": topic,
        "article_ids": article_ids,
        "sources": sources,
        "bias_spread": bias_spread,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
