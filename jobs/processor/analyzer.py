import sys, json, os
sys.path.insert(0, "/app/shared")
sys.path.insert(0, "/app/config")

import google.generativeai as genai
from prompts import SYSTEM_PROMPT, NEWS_ANALYSIS_SCHEMA

genai.configure(api_key=os.environ["VERTEXAI_API_KEY"])

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def format_articles_for_prompt(articles: list[dict]) -> str:
    lines = []
    for a in articles:
        lines.append(
            f"[{a['source']} | {a['bias_label']}]\n"
            f"Başlık: {a['title']}\n"
            f"Snippet: {a.get('content_snippet', '')[:400]}\n"
        )
    return "\n---\n".join(lines)


def analyze_cluster(cluster_record: dict, articles: list[dict]) -> dict | None:
    articles_text = format_articles_for_prompt(articles)

    prompt = (
        f"Cluster ID: {cluster_record['cluster_id']}\n"
        f"Kaynak sayısı: {len(articles)}\n"
        f"Bias spread: {', '.join(cluster_record['bias_spread'])}\n\n"
        f"Haberler:\n{articles_text}"
    )

    try:
        model = genai.GenerativeModel(MODEL, system_instruction=SYSTEM_PROMPT)
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=NEWS_ANALYSIS_SCHEMA,
                temperature=0.3,
                max_output_tokens=8192,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"[ERROR] Gemini API error for cluster {cluster_record['cluster_id']}: {e}")
        return None


def build_analyzed_record(cluster_record: dict, analysis: dict) -> dict:
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo

    today = datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat()

    return {
        "cluster_id": cluster_record["cluster_id"],
        "analysis_date": today,
        "significance_score": analysis.get("significance_score", 0.0),
        "signal_label": analysis.get("signal_classification", {}).get("label", "noise"),
        "event_summary": analysis.get("event_summary", ""),
        "narrative_groups": analysis.get("narrative_groups", []),
        "information_gaps": analysis.get("information_gaps", {}),
        "impact_analysis": analysis.get("impact_analysis", {}),
        "source_credibility": analysis.get("source_credibility", []),
        "temporal_context": analysis.get("temporal_context", {}),
        "scenarios": analysis.get("scenarios", []),
        "analyzed_at": now,
    }
