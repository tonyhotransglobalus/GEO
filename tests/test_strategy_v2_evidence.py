from scripts.strategy_engine_v2.evidence import (
    build_citability_evidence,
    build_evidence_item,
    build_v2_evidence_ledger,
)


def test_build_evidence_item_marks_observed_vs_inferred():
    item = build_evidence_item(
        evidence_type="page_citability",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme="life insurance",
        url_or_domain="https://www.transglobalus.com/",
        raw_observation={"score": 28},
        normalized_summary="Citability is weak on the homepage.",
        confidence="medium",
    )

    assert item["source_class"] == "live_site"
    assert item["observed_vs_inferred"] == "observed"


def test_build_v2_evidence_ledger_ingests_multiple_sources():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": True,
            "comparison_eligibility": {"requested": True},
            "platforms": ["chatgpt"],
            "competitors": ["example.com"],
        },
        page_data={"title": "TransGlobal"},
        robots_data={"gptbot": "allowed"},
        llms_data={"found": False},
        citability_data={"score": 28},
        brand_data={"entity_score": 71},
        plugin_results={"readiness": "ok"},
    )

    assert ledger["count"] == 7
    assert [item["evidence_type"] for item in ledger["items"]] == [
        "run_manifest",
        "page_fetch",
        "robots",
        "llms",
        "page_citability",
        "brand_entity",
        "plugin_results",
    ]


def test_build_v2_evidence_ledger_keeps_empty_payloads():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": False,
            "comparison_eligibility": {"requested": False},
            "platforms": [],
            "competitors": [],
        },
        page_data={},
        robots_data={},
        llms_data={},
        citability_data={},
        brand_data={},
        plugin_results={},
    )

    assert ledger["count"] == 7
    assert [item["evidence_type"] for item in ledger["items"]] == [
        "run_manifest",
        "page_fetch",
        "robots",
        "llms",
        "page_citability",
        "brand_entity",
        "plugin_results",
    ]


def test_build_citability_evidence_is_computed():
    item = build_citability_evidence(
        {"score": 28},
        url="https://www.transglobalus.com/",
    )

    assert item["source_class"] == "internal_score"
    assert item["observed_vs_inferred"] == "inferred"
