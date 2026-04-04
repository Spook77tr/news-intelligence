import sys
sys.path.insert(0, "/app/shared")
sys.path.insert(0, "/app/config")

import os
import anthropic
from prompts import SYSTEM_PROMPT, ANALYSIS_TOOL

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")


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
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            tools=[ANALYSIS_TOOL],
            tool_choice={"type": "tool", "name": "news_analysis"},
            messages=[{"role": "user", "content": prompt}]
        )

        # tool_use garantili
        tool_block = next(
            (b for b in response.content if b.type == "tool_use"),
            None
        )
        if not tool_block:
            print(f"[WARN] No tool_use block for cluster {cluster_record['cluster_id']}")
            return None

        return tool_block.input

    except anthropic.APIError as e:
        print(f"[ERROR] Claude API error for cluster {cluster_record['cluster_id']}: {e}")
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
