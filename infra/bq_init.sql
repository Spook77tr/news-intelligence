-- Run once: bq query --use_legacy_sql=false < infra/bq_init.sql

CREATE SCHEMA IF NOT EXISTS `${PROJECT}.news_intelligence`
OPTIONS(location="EU");

CREATE TABLE IF NOT EXISTS `${PROJECT}.news_intelligence.raw_news` (
  id STRING NOT NULL,
  source STRING,
  bias_label STRING,
  title STRING,
  url STRING,
  content_snippet STRING,
  published_at TIMESTAMP,
  fetched_at TIMESTAMP,
  topic_tags ARRAY<STRING>
)
PARTITION BY DATE(fetched_at)
CLUSTER BY source, bias_label
OPTIONS(partition_expiration_days=90);

CREATE TABLE IF NOT EXISTS `${PROJECT}.news_intelligence.news_clusters` (
  cluster_id STRING NOT NULL,
  topic STRING,
  article_ids ARRAY<STRING>,
  sources ARRAY<STRING>,
  bias_spread ARRAY<STRING>,
  created_at TIMESTAMP
)
PARTITION BY DATE(created_at)
OPTIONS(partition_expiration_days=90);

CREATE TABLE IF NOT EXISTS `${PROJECT}.news_intelligence.analyzed_news` (
  cluster_id STRING NOT NULL,
  analysis_date DATE,
  significance_score FLOAT64,
  signal_label STRING,
  event_summary STRING,
  narrative_groups JSON,
  information_gaps JSON,
  impact_analysis JSON,
  source_credibility JSON,
  temporal_context JSON,
  scenarios JSON,
  analyzed_at TIMESTAMP
)
PARTITION BY analysis_date
CLUSTER BY signal_label, significance_score
OPTIONS(partition_expiration_days=180);
