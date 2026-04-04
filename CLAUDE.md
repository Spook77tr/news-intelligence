# News Intelligence Pipeline — Claude Code Session

## Project Purpose
Sabah haber brifing sistemi. Farklı kaynaklardan (bias spread ile) haber çekip, clustering, analiz ve kişisel brifing üretiyor. Tamamen GCP-native.

## Stack
- **Cloud Run Jobs** — fetcher, processor, notifier (3 ayrı job)
- **Cloud Scheduler** — 05:30 TR saati trigger
- **BigQuery** — raw_news, news_clusters, analyzed_news
- **Vertex AI** — text-embedding-004 (clustering)
- **Claude API (Anthropic)** — haber analizi (tool_use ile structured JSON)
- **Telegram Bot** — sabah brifing delivery

## GCP Project
- Project ID: `[SET: GCP_PROJECT_ID]`
- Region: `europe-west1`
- BQ Dataset: `news_intelligence`
- Service Account: `news-sa@[PROJECT].iam.gserviceaccount.com`

## Repo Structure
```
news-intelligence/
├── CLAUDE.md                  ← bu dosya
├── jobs/
│   ├── fetcher/               ← RSS çek → BQ raw_news
│   │   ├── main.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── processor/             ← cluster + Claude analiz → BQ analyzed_news
│   │   ├── main.py
│   │   ├── clusterer.py
│   │   ├── analyzer.py
│   │   └── Dockerfile
│   └── notifier/              ← BQ → Telegram brifing formatla
│       ├── main.py
│       └── Dockerfile
├── shared/
│   ├── bq_client.py           ← BQ insert/query helpers
│   ├── schemas.py             ← BQ tablo şemaları
│   └── models.py              ← Pydantic modeller
├── config/
│   ├── sources.yaml           ← RSS kaynakları + bias label
│   └── prompts.py             ← System prompt + JSON schema
├── infra/
│   ├── setup.sh               ← GCP kaynak oluşturma (tek seferlik)
│   ├── deploy.sh              ← tüm jobları build + deploy
│   └── bq_init.sql            ← tablo DDL
└── .env.example
```

## Build & Deploy
```bash
# İlk kurulum (tek seferlik)
bash infra/setup.sh

# Deploy all jobs
bash infra/deploy.sh

# Tek job deploy
bash infra/deploy.sh fetcher
```

## Environment Variables
```
GCP_PROJECT_ID=
BQ_DATASET=news_intelligence
ANTHROPIC_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
GOOGLE_APPLICATION_CREDENTIALS=  # local dev için, Cloud Run'da SA ile otomatik
```

## Data Flow
```
05:30 → Scheduler → fetcher job (RSS çek, BQ'ya yaz)
05:45 → Scheduler → processor job (cluster + analiz, BQ'ya yaz)
06:15 → Scheduler → notifier job (brifing formatla, Telegram'a gönder)
```

## BigQuery Tables

### raw_news
- Partition: DATE(fetched_at)
- Cluster: source, bias_label
- Dedup key: id = MD5(source + url)

### news_clusters
- Partition: DATE(created_at)
- Cluster: significance_score DESC

### analyzed_news
- Partition: analysis_date
- Cluster: signal_label, significance_score

## Clustering Logic
- Vertex AI text-embedding-004 ile başlık embedding
- Cosine similarity threshold: 0.82
- Minimum 2 farklı kaynak = geçerli cluster
- Tek kaynaktan gelen haberler → skip (gürültü)

## Analysis — Claude API
- Model: claude-sonnet-4-5 (kalite/maliyet dengesi)
- Structured output: tool_use zorunlu (JSON garantisi)
- Tool name: `news_analysis`
- Schema: config/prompts.py içinde NEWS_ANALYSIS_SCHEMA

## Signal Labels
- `noise` → Telegram'a gönderilmez
- `monitor` → Brifinge eklenir, düşük öncelik
- `actionable` → Brifing başına, highlight ile

## Haber Kaynakları (config/sources.yaml)
Bias spread: TR Sol / TR Sağ / TR Ekonomi / Batı Nötr / Batı Liberal / Orta Doğu / Rus perspektifi

## Known Issues / TODOs
- [ ] Embedding'ler BQ'da saklanmıyor (cost), her seferinde yeniden hesaplanıyor — kabul edilebilir şimdilik
- [ ] FT (Financial Times) paywall — snippet yeterli, tam içerik yok
- [ ] Haber duplicate'ları aynı gün içinde — MD5 dedup yeterli
- [ ] Telegram mesaj 4096 char limiti — notifier'da chunking gerekli

## Session Continuation Notes
Bu dosyayı her Claude Code session başında oku.
Değişiklik yaparsan bu dosyayı güncelle.
