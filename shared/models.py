from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RawArticle(BaseModel):
    id: str
    source: str
    bias_label: str
    title: str
    url: str
    content_snippet: str
    published_at: datetime
    fetched_at: datetime
    topic_tags: list[str] = []


class NewsCluster(BaseModel):
    cluster_id: str
    topic: str
    article_ids: list[str]
    sources: list[str]
    bias_spread: list[str]
    created_at: datetime


class AnalyzedCluster(BaseModel):
    cluster_id: str
    analysis_date: str  # DATE string for BQ
    significance_score: float
    signal_label: str
    event_summary: str
    narrative_groups: list[dict]
    information_gaps: dict
    impact_analysis: dict
    source_credibility: list[dict]
    temporal_context: dict
    scenarios: list[dict]
    analyzed_at: datetime
