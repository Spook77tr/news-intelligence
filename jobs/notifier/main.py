import sys, os, json, requests
sys.path.insert(0, "/app/shared")

import bq_client
from datetime import datetime
from zoneinfo import ZoneInfo

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

SIGNAL_EMOJI = {
    "actionable": "🔴",
    "monitor": "🟡",
    "noise": "⚪",
}

BIAS_EMOJI = {
    "TR_LEFT": "🇹🇷↙",
    "TR_RIGHT": "🇹🇷↗",
    "TR_CENTER": "🇹🇷",
    "TR_ECONOMY": "🇹🇷💹",
    "INTL_NEUTRAL": "🌐",
    "WEST_LIBERAL": "🇪🇺",
    "WEST_LEFT": "🌿",
    "WEST_FINANCE": "💰",
    "MIDEAST": "🌙",
    "RU_STATE": "🇷🇺",
    "CRYPTO": "₿",
    "CRYPTO_BTC": "🟠",
}


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Telegram 4096 char limitini handle et — chunk gönder."""
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        resp = requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        })
        if not resp.ok:
            print(f"[ERROR] Telegram send failed: {resp.text}")
            return False
    return True


def safe_json(val) -> dict | list:
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {}
    return val or {}


def format_cluster(cluster: dict, rank: int) -> str:
    signal = cluster.get("signal_label", "noise")
    score = cluster.get("significance_score", 0)
    emoji = SIGNAL_EMOJI.get(signal, "⚪")

    impact = safe_json(cluster.get("impact_analysis", {}))
    temporal = safe_json(cluster.get("temporal_context", {}))
    gaps = safe_json(cluster.get("information_gaps", {}))
    scenarios = safe_json(cluster.get("scenarios", []))
    narratives = safe_json(cluster.get("narrative_groups", []))

    sources_str = ", ".join(cluster.get("sources", []))
    bias_spread = cluster.get("bias_spread", [])
    bias_str = " ".join(BIAS_EMOJI.get(b, b) for b in bias_spread)

    # Momentum
    momentum = temporal.get("momentum", "unknown")
    momentum_str = {"increasing": "📈", "decreasing": "📉", "stable": "➡️", "unknown": "❓"}.get(momentum, "")

    # TR etkisi
    tr_impact = impact.get("turkey", {})
    tr_economy = tr_impact.get("economy", "")
    tr_politics = tr_impact.get("politics", "")

    # Anlatı farkı (ilk 2 grup)
    narrative_lines = []
    for ng in narratives[:2]:
        label = ng.get("group_label", "")
        emphasis = ng.get("emphasis", "")
        narrative_lines.append(f"  • <b>{label}:</b> {emphasis[:120]}")

    # Bilgi boşlukları
    missing = gaps.get("missing_critical", [])[:2]
    missing_str = " | ".join(missing) if missing else ""

    # Senaryolar
    scenario_lines = []
    for s in scenarios[:2]:
        prob = s.get("probability", "")
        cond = s.get("condition", "")[:100]
        out = s.get("outcome", "")[:100]
        scenario_lines.append(f"  ↪ [{prob.upper()}] {cond} → {out}")

    lines = [
        f"{emoji} <b>#{rank} {cluster.get('topic', '')[:80]}</b>",
        f"Skor: {score:.2f} | {momentum_str} {momentum} | {bias_str}",
        f"Kaynaklar: {sources_str}",
        "",
        f"<b>Özet:</b> {cluster.get('event_summary', '')[:300]}",
    ]

    if narrative_lines:
        lines += ["", "<b>Anlatı Farkı:</b>"] + narrative_lines

    tr_parts = []
    if tr_economy:
        tr_parts.append(f"Ekonomi: {tr_economy[:150]}")
    if tr_politics:
        tr_parts.append(f"Politika: {tr_politics[:150]}")
    if tr_parts:
        lines += ["", "<b>🇹🇷 TR Etkisi:</b>"] + [f"  {p}" for p in tr_parts]

    if missing_str:
        lines += ["", f"<b>⚠️ Eksik Bilgi:</b> {missing_str}"]

    if scenario_lines:
        lines += ["", "<b>📐 Senaryolar:</b>"] + scenario_lines

    return "\n".join(lines)


def run():
    now_tr = datetime.now(ZoneInfo("Europe/Istanbul"))
    date_str = now_tr.strftime("%d %B %Y, %A")

    clusters = bq_client.get_todays_actionable_clusters()
    print(f"[INFO] Clusters to report: {len(clusters)}")

    if not clusters:
        send_message(f"📰 <b>SABAH BRİFİNG — {date_str}</b>\n\nBugün raporlanacak kayda değer haber bulunamadı.")
        return

    actionable = [c for c in clusters if c["signal_label"] == "actionable"]
    monitor = [c for c in clusters if c["signal_label"] == "monitor"]

    header = (
        f"📰 <b>SABAH BRİFİNG</b>\n"
        f"{date_str}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🔴 Actionable: {len(actionable)} | 🟡 Monitor: {len(monitor)}"
    )
    send_message(header)

    rank = 1
    for cluster in actionable + monitor:
        body = format_cluster(cluster, rank)
        send_message(body)
        rank += 1

    send_message("━━━━━━━━━━━━━━━━━━━\n✅ Brifing tamamlandı.")
    print("[INFO] Notifier complete.")


if __name__ == "__main__":
    run()
