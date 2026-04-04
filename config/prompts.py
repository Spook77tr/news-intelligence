SYSTEM_PROMPT = """
Sen üst düzey bir haber analisti ve sinyal tespit sistemisin.
Amacın:
- Gürültüyü elemek
- Erken sinyal yakalamak
- Karar destek içgörü üretmek

Her haber kümesini analiz ederken:

1. Olay Özeti
   - Tek paragraf, tamamen tarafsız, doğrulanabilir bilgilerle

2. Ana Temalar & Anlatı Ayrışması
   - Kaynakları grupla (örn: Batı medyası, yerel medya, resmi kaynaklar vs.)
   - Her grubun neyi vurguladığını belirt
   - Bias / framing farklarını açıkça yaz

3. Bilgi Boşlukları & Şüpheli Noktalar
   - Hangi kritik bilgiler eksik?
   - Çelişkili veriler var mı?
   - Henüz doğrulanmamış ama önemli iddialar

4. Güvenilirlik Skoru
   - Her kaynak için: base (statik) + instance (bu haber için) ayrımı
   - Kısa gerekçe: birincil kaynak / anonim / çelişkili veri

5. Etki Analizi
   - Türkiye etkisi (ekonomi, politika, sektör)
   - Küresel etkiler
   - Etkilenen varlıklar: sadece metinden çıkarılabilecekler
     Tahmin etme — çıkarım yapıyorsan inferred: true yaz
   - Kısa/orta vade ayrımı

6. Sinyal Sınıflandırması
   - noise / monitor / actionable
   - Gerekçeni yaz

7. Zaman Boyutu
   - Yeni gelişme mi, devam eden hikâye mi?
   - Momentum: increasing / stable / decreasing / unknown

8. Önem Skoru (0-1)
   - Finansal + jeopolitik etki × belirsizlik kombinasyonu

9. Senaryolar (max 2)
   - "Eğer X olursa Y olur" formatı
   - Olasılık: low / medium / high (sayı değil)

KURALLAR:
- Yanıtı SADECE geçerli JSON olarak ver, başka metin ekleme
- Etkilenen varlıkları uydurma, metinden çıkar
- Güvenilirlik skorlarını abartma
"""

NEWS_ANALYSIS_SCHEMA = {
    "type": "object",
    "required": [
        "cluster_id", "topic", "event_summary", "narrative_groups",
        "information_gaps", "source_credibility", "impact_analysis",
        "signal_classification", "temporal_context", "significance_score", "scenarios"
    ],
    "properties": {
        "cluster_id": {"type": "string"},
        "topic": {"type": "string"},
        "event_summary": {"type": "string"},
        "narrative_groups": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["group_label", "sources", "emphasis", "framing", "omissions"],
                "properties": {
                    "group_label": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "emphasis": {"type": "string"},
                    "framing": {"type": "string"},
                    "omissions": {"type": "string"}
                }
            }
        },
        "information_gaps": {
            "type": "object",
            "required": ["missing_critical", "contradictions", "unverified_claims"],
            "properties": {
                "missing_critical": {"type": "array", "items": {"type": "string"}},
                "contradictions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim_a": {"type": "string"},
                            "source_a": {"type": "string"},
                            "claim_b": {"type": "string"},
                            "source_b": {"type": "string"}
                        }
                    }
                },
                "unverified_claims": {"type": "array", "items": {"type": "string"}}
            }
        },
        "source_credibility": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source", "base_credibility", "instance_credibility", "factors"],
                "properties": {
                    "source": {"type": "string"},
                    "base_credibility": {"type": "number", "minimum": 0, "maximum": 1},
                    "instance_credibility": {"type": "number", "minimum": 0, "maximum": 1},
                    "factors": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "impact_analysis": {
            "type": "object",
            "required": ["turkey", "global", "affected_assets"],
            "properties": {
                "turkey": {
                    "type": "object",
                    "properties": {
                        "economy": {"type": "string"},
                        "politics": {"type": "string"},
                        "sectors": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "global": {"type": "string"},
                "affected_assets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["asset", "type", "direction", "timeframe", "inferred"],
                        "properties": {
                            "asset": {"type": "string"},
                            "type": {
                                "type": "string",
                                "enum": ["equity", "commodity", "crypto", "fx", "bond", "index"]
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["bullish", "bearish", "neutral", "volatile"]
                            },
                            "timeframe": {
                                "type": "string",
                                "enum": ["short", "medium", "long"]
                            },
                            "inferred": {"type": "boolean"}
                        }
                    }
                }
            }
        },
        "signal_classification": {
            "type": "object",
            "required": ["label", "rationale"],
            "properties": {
                "label": {
                    "type": "string",
                    "enum": ["noise", "monitor", "actionable"]
                },
                "rationale": {"type": "string"}
            }
        },
        "temporal_context": {
            "type": "object",
            "required": ["is_new", "ongoing_story", "momentum"],
            "properties": {
                "is_new": {"type": "boolean"},
                "ongoing_story": {"type": "boolean"},
                "momentum": {
                    "type": "string",
                    "enum": ["increasing", "stable", "decreasing", "unknown"]
                }
            }
        },
        "significance_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
        },
        "scenarios": {
            "type": "array",
            "maxItems": 2,
            "items": {
                "type": "object",
                "required": ["condition", "outcome", "probability"],
                "properties": {
                    "condition": {"type": "string"},
                    "outcome": {"type": "string"},
                    "probability": {
                        "type": "string",
                        "enum": ["low", "medium", "high"]
                    }
                }
            }
        }
    }
}

# Kept for reference — Gemini uses NEWS_ANALYSIS_SCHEMA directly
# via GenerationConfig(response_schema=NEWS_ANALYSIS_SCHEMA)
