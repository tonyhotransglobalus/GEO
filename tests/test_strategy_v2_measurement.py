from scripts.strategy_engine_v2.measurement import (
    build_measurement_summary,
    normalize_measurement_payload,
)


def test_normalize_measurement_payload_keeps_platform_and_page_metrics():
    payload = normalize_measurement_payload(
        {
            "platforms": [
                {
                    "platform": "Bing",
                    "source": "bing_ai_performance",
                    "date_range": {"start": "2026-03-01", "end": "2026-03-31"},
                    "page_metrics": [
                        {
                            "page_url": "https://www.transglobalus.com/retirement-income/",
                            "cited_count": 7,
                            "grounding_queries": ["best retirement income strategy", "retirement income planning"],
                        }
                    ],
                },
                {
                    "platform": "ChatGPT",
                    "source": "chatgpt_referrals",
                    "date_range": {"start": "2026-03-01", "end": "2026-03-31"},
                    "referrals": {
                        "visits": 42,
                        "change_pct": 18.5,
                        "utm_source": "chatgpt.com",
                    },
                },
            ]
        }
    )

    assert len(payload["platforms"]) == 2
    bing = next(item for item in payload["platforms"] if item["platform"] == "Bing")
    chatgpt = next(item for item in payload["platforms"] if item["platform"] == "ChatGPT")

    assert bing["page_metrics"][0]["page_url"] == "https://www.transglobalus.com/retirement-income/"
    assert bing["page_metrics"][0]["cited_count"] == 7
    assert bing["page_metrics"][0]["grounding_query_count"] == 2
    assert chatgpt["referrals"]["visits"] == 42
    assert chatgpt["referrals"]["change_pct"] == 18.5


def test_build_measurement_summary_rolls_up_platform_totals():
    normalized = normalize_measurement_payload(
        {
            "platforms": [
                {
                    "platform": "Bing",
                    "source": "bing_ai_performance",
                    "date_range": {"start": "2026-03-01", "end": "2026-03-31"},
                    "page_metrics": [
                        {
                            "page_url": "https://www.transglobalus.com/retirement-income/",
                            "cited_count": 7,
                            "grounding_queries": ["best retirement income strategy", "retirement income planning"],
                        },
                        {
                            "page_url": "https://www.transglobalus.com/life-insurance/",
                            "cited_count": 3,
                            "grounding_queries": ["life insurance cost"],
                        },
                    ],
                }
            ]
        }
    )

    summary = build_measurement_summary(normalized)
    bing = summary["platforms"][0]

    assert bing["citation_count"] == 10
    assert bing["grounding_query_count"] == 3
    assert bing["captured_date_range"] == "2026-03-01 to 2026-03-31"
