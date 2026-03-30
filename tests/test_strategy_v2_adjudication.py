from scripts.strategy_engine_v2.adjudication import (
    classify_benchmark_section,
    classify_change_since_last_run_section,
    classify_platform_breakdown_section,
    classify_prompt_proof_section,
)
from scripts.strategy_engine_v2.workflow import run_strategy_report_v2


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


def test_v2_workflow_includes_adjudication():
    result = run_strategy_report_v2("https://www.transglobalus.com/")

    assert "adjudication" in result
