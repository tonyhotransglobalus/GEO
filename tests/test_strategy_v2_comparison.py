from scripts.strategy_engine_v2.comparison import compare_runs, normalize_comparison_run


def test_normalize_comparison_run_keeps_fixed_scope_and_metrics():
    normalized = normalize_comparison_run(
        {
            "manifest": {
                "target_url": "https://www.transglobalus.com/",
                "locale": "en-us",
                "platforms": ["Bing", "ChatGPT"],
                "competitors": ["competitor.com"],
            },
            "audit_data": {
                "geo_score": 74,
                "query_clusters": [{"queries": ["retirement income planning"]}],
            },
            "evidence": {
                "items": [
                    {
                        "evidence_type": "citation_share_signal",
                        "query_theme": "retirement income planning",
                        "raw_observation": {"cited_count": 7},
                    },
                    {
                        "evidence_type": "referral_signal",
                        "raw_observation": {"visits": 42},
                    },
                    {
                        "evidence_type": "offsite_authority_gap",
                        "raw_observation": {"platform": "Wikipedia"},
                    },
                ]
            },
        }
    )

    assert normalized["target_url"] == "https://www.transglobalus.com/"
    assert normalized["locale"] == "en-us"
    assert normalized["platforms"] == ["Bing", "ChatGPT"]
    assert normalized["competitors"] == ["competitor.com"]
    assert normalized["query_set"] == ["retirement income planning"]
    assert normalized["geo_score"] == 74
    assert normalized["citation_count"] == 7
    assert normalized["referral_visits"] == 42
    assert normalized["authority_gap_count"] == 1


def test_compare_runs_returns_summary_and_deltas_when_scope_matches():
    previous = normalize_comparison_run(
        {
            "manifest": {
                "target_url": "https://www.transglobalus.com/",
                "locale": "en-us",
                "platforms": ["Bing"],
                "competitors": ["competitor.com"],
            },
            "audit_data": {"geo_score": 68},
            "evidence": {
                "items": [
                    {"evidence_type": "citation_share_signal", "raw_observation": {"cited_count": 5}},
                    {"evidence_type": "referral_signal", "raw_observation": {"visits": 30}},
                    {"evidence_type": "offsite_authority_gap", "raw_observation": {"platform": "Wikipedia"}},
                    {"evidence_type": "offsite_authority_gap", "raw_observation": {"platform": "LinkedIn"}},
                ]
            },
        }
    )
    current = normalize_comparison_run(
        {
            "manifest": {
                "target_url": "https://www.transglobalus.com/",
                "locale": "en-us",
                "platforms": ["Bing"],
                "competitors": ["competitor.com"],
            },
            "audit_data": {"geo_score": 74},
            "evidence": {
                "items": [
                    {"evidence_type": "citation_share_signal", "raw_observation": {"cited_count": 7}},
                    {"evidence_type": "referral_signal", "raw_observation": {"visits": 42}},
                    {"evidence_type": "offsite_authority_gap", "raw_observation": {"platform": "Wikipedia"}},
                ]
            },
        }
    )

    summary = compare_runs(current, previous)

    assert summary["comparable"] is True
    assert any(item["metric"] == "geo_score" and item["delta"] == 6 for item in summary["delta_items"])
    assert any(item["metric"] == "citation_count" and item["delta"] == 2 for item in summary["delta_items"])
    assert any(item["metric"] == "authority_gap_count" and item["delta"] == -1 for item in summary["delta_items"])
    assert "GEO score" in summary["summary"]
