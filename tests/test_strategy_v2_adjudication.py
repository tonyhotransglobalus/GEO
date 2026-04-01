from scripts.strategy_engine_v2.adjudication import (
    build_adjudication_inputs,
    classify_benchmark_section,
    classify_change_since_last_run_section,
    classify_platform_breakdown_section,
    classify_prompt_proof_section,
)
from scripts.strategy_engine_v2.evidence import build_v2_evidence_ledger
from scripts.strategy_engine_v2.workflow import run_strategy_report_v2
from tests.strategy_v2_samples import sample_v1_audit_payload, sample_v2_workflow_deps


def test_benchmark_without_named_competitors_is_omitted():
    result = classify_benchmark_section(
        competitor_rows=[],
        sampled_queries=6,
        winner_domains=[],
    )

    assert result["status"] == "omitted"


def test_prompt_proof_with_partial_capture_is_directional():
    result = classify_prompt_proof_section(
        prompt_rows=[{"prompt": "life insurance"}],
        captured_prompts=1,
        winner_urls=[],
    )

    assert result["status"] == "directional"


def test_platform_breakdown_with_strong_capture_is_decision_grade():
    result = classify_platform_breakdown_section(
        platform_rows=[{"platform": "chatgpt"}, {"platform": "gemini"}],
        sampled_platforms=2,
        direct_captures=2,
    )

    assert result["status"] == "decision-grade"


def test_change_since_last_run_without_comparable_baseline_is_omitted():
    result = classify_change_since_last_run_section(
        compare_to_v1=True,
        comparable_runs=False,
        change_points=2,
    )

    assert result["status"] == "omitted"


def test_v2_workflow_includes_adjudication(tmp_path):
    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        reports_dir=tmp_path,
        deps=sample_v2_workflow_deps(),
    )

    assert "adjudication" in result


def test_build_adjudication_inputs_keeps_placeholder_signals_conservative():
    inputs = build_adjudication_inputs(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "platforms": ["chatgpt"],
            "competitors": ["example.com"],
            "comparison_eligibility": {"requested": True, "eligible": True},
        },
        evidence={
            "items": [
                {"evidence_type": "page_fetch", "query_theme": "life insurance", "platform": "chatgpt"},
                {"evidence_type": "plugin_results", "query_theme": "life insurance"},
            ]
        },
    )

    assert inputs["benchmark"]["sampled_queries"] == 0
    assert inputs["prompt_proof"]["prompt_rows"] == []
    assert inputs["prompt_proof"]["captured_prompts"] == 0
    assert inputs["change_since_last_run"]["compare_to_v1"] is True
    assert inputs["change_since_last_run"]["comparable_runs"] is True


def test_build_adjudication_inputs_uses_v1_audit_rows_when_available():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "platforms": ["ChatGPT", "Perplexity"],
        "competitors": ["competitor.com"],
        "comparison_eligibility": {"requested": True, "eligible": True},
    }
    ledger = build_v2_evidence_ledger(
        manifest=manifest,
        audit_data=sample_v1_audit_payload(),
    )

    inputs = build_adjudication_inputs(
        manifest=manifest,
        evidence=ledger,
        audit_data=sample_v1_audit_payload(),
    )

    assert inputs["benchmark"]["sampled_queries"] == 6
    assert inputs["benchmark"]["winner_domains"] == ["competitor.com"]
    assert inputs["prompt_proof"]["captured_prompts"] == 1
    assert inputs["platform_breakdown"]["sampled_platforms"] == 2
    assert inputs["platform_breakdown"]["direct_captures"] == 1


def test_build_adjudication_inputs_uses_sampled_query_proof_when_exact_prompt_rows_are_missing():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "platforms": ["ChatGPT", "Perplexity"],
        "competitors": ["competitor.com"],
        "comparison_eligibility": {"requested": True, "eligible": True},
    }
    audit_data = sample_v1_audit_payload()
    audit_data["client_report_sections"]["prompt_query_proof"] = {
        "sampling_note": "Exact platform captures were not retained in this sample.",
        "rows": [],
    }
    ledger = build_v2_evidence_ledger(
        manifest=manifest,
        audit_data=audit_data,
    )

    inputs = build_adjudication_inputs(
        manifest=manifest,
        evidence=ledger,
        audit_data=audit_data,
    )

    assert inputs["prompt_proof"]["captured_prompts"] >= 1
    assert inputs["prompt_proof"]["prompt_rows"][0]["capture_mode"] == "sampled_query_bridge"

    result = classify_prompt_proof_section(**inputs["prompt_proof"])
    assert result["status"] == "directional"
    assert "sampled query" in result["warning"].lower()


def test_build_adjudication_inputs_uses_loaded_comparison_context_when_available():
    inputs = build_adjudication_inputs(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "platforms": ["chatgpt"],
            "competitors": [],
            "comparison_eligibility": {"requested": True, "eligible": True},
        },
        evidence={"items": []},
        comparison_context={
            "previous_manifest": {"run_timestamp": "2026-03-30T10:00:00+00:00"},
            "change_points": 2,
            "current_snapshot": {"evidence_count": 5},
            "previous_snapshot": {"evidence_count": 3},
        },
    )

    assert inputs["change_since_last_run"]["compare_to_v1"] is True
    assert inputs["change_since_last_run"]["comparable_runs"] is True
    assert inputs["change_since_last_run"]["change_points"] == 2
