from scripts.strategy_engine_v2.evidence import (
    build_citability_evidence,
    build_evidence_item,
    build_v2_evidence_ledger,
)
from tests.strategy_v2_samples import sample_v1_audit_payload


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


def test_build_v2_evidence_ledger_reuses_v1_audit_sections():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": True,
            "comparison_eligibility": {"requested": True, "eligible": True},
            "platforms": ["ChatGPT", "Perplexity"],
            "competitors": ["competitor.com"],
        },
        audit_data=sample_v1_audit_payload(),
    )

    evidence_types = [item["evidence_type"] for item in ledger["items"]]
    assert "query_cluster" in evidence_types
    assert "citation_failure" in evidence_types
    assert "benchmark_row" in evidence_types
    assert "platform_observation" in evidence_types
    assert "prompt_proof" in evidence_types
    assert "priority_page" in evidence_types


def test_build_v2_evidence_ledger_synthesizes_sampled_prompt_proof_when_exact_rows_are_missing():
    audit_data = sample_v1_audit_payload()
    audit_data["client_report_sections"]["prompt_query_proof"] = {
        "sampling_note": "Exact platform captures were not retained in this sample.",
        "rows": [],
    }

    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": True,
            "comparison_eligibility": {"requested": True, "eligible": True},
            "platforms": ["ChatGPT", "Perplexity"],
            "competitors": ["competitor.com"],
        },
        audit_data=audit_data,
    )

    prompt_proof_items = [
        item for item in ledger["items"] if item["evidence_type"] == "prompt_proof"
    ]
    assert prompt_proof_items
    assert prompt_proof_items[0]["observed_vs_inferred"] == "inferred"
    assert (
        prompt_proof_items[0]["raw_observation"]["capture_mode"]
        == "sampled_query_bridge"
    )


def test_build_v2_evidence_ledger_captures_internal_page_breadth():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": True,
            "comparison_eligibility": {"requested": True, "eligible": True},
            "platforms": [],
            "competitors": [],
        },
        page_data={
            "title": "TransGlobal",
            "internal_links": [
                {"url": "https://www.transglobalus.com/"},
                {"url": "https://www.transglobalus.com/life-insurance-annuity/", "text": "Life & Annuities"},
                {"url": "https://www.transglobalus.com/wealth-management/", "text": "Advisory"},
            ],
        },
    )

    linked_pages = [
        item for item in ledger["items"] if item["evidence_type"] == "linked_page"
    ]
    assert len(linked_pages) == 2
    assert {
        item["url_or_domain"] for item in linked_pages
    } == {
        "https://www.transglobalus.com/life-insurance-annuity/",
        "https://www.transglobalus.com/wealth-management/",
    }


def test_build_v2_evidence_ledger_filters_low_signal_page_noise():
    ledger = build_v2_evidence_ledger(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": True,
            "comparison_eligibility": {"requested": True, "eligible": True},
            "platforms": [],
            "competitors": [],
        },
        audit_data={
            "plugin_results": {
                "readiness": {
                    "inputs": {
                        "sitemap_pages": [
                            "https://www.transglobalus.com/zh/example-page/",
                            "https://www.transglobalus.com/category/financial/",
                        ]
                    }
                }
            }
        },
        page_data={
            "title": "TransGlobal",
            "internal_links": [
                {"url": "https://www.transglobalus.com/life-insurance-annuity/", "text": "Life & Annuities"},
                {"url": "https://www.transglobalus.com/author/admin/", "text": "admin"},
                {"url": "https://www.transglobalus.com/category/financial/", "text": "Financial News"},
                {"url": "https://www.transglobalus.com/treasury-rally-offers-mortgage-market-brief-relief-amid-war-jitters/", "text": ""},
            ],
        },
    )

    linked_pages = [
        item["url_or_domain"]
        for item in ledger["items"]
        if item["evidence_type"] == "linked_page"
    ]
    assert linked_pages == ["https://www.transglobalus.com/life-insurance-annuity/"]
