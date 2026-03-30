from __future__ import annotations

from typing import Any

ADJUDICATION_THRESHOLDS = {
    "benchmark": {
        "decision_grade_competitors": 2,
        "directional_competitors": 1,
        "decision_grade_queries": 8,
        "directional_queries": 4,
        "decision_grade_winners": 2,
        "directional_winners": 1,
    },
    "prompt_proof": {
        "decision_grade_prompts": 3,
        "directional_prompts": 1,
        "decision_grade_winners": 1,
        "directional_winners": 1,
    },
    "platform_breakdown": {
        "decision_grade_platforms": 2,
        "directional_platforms": 1,
        "decision_grade_direct_captures": 2,
        "directional_direct_captures": 1,
    },
    "change_since_last_run": {
        "decision_grade_changes": 2,
        "directional_changes": 1,
    },
}


def _clean_rows(rows: list[Any] | None) -> list[Any]:
    return [row for row in (rows or []) if row is not None]


def _count_named_items(items: list[Any] | None) -> int:
    count = 0
    for item in _clean_rows(items):
        if isinstance(item, str) and item.strip():
            count += 1
        elif isinstance(item, dict) and any(str(value).strip() for value in item.values() if value is not None):
            count += 1
    return count


def _build_result(status: str, reason: str, warning: str) -> dict:
    return {
        "status": status,
        "reason": reason,
        "warning": warning,
    }


def build_adjudication_inputs(*, manifest: dict[str, Any], evidence: dict[str, Any]) -> dict:
    items = list(evidence.get("items") or [])
    manifest_platforms = list(manifest.get("platforms") or [])
    compare_to_v1 = bool(manifest.get("comparison_eligibility", {}).get("requested"))
    eligible_to_compare = bool(manifest.get("comparison_eligibility", {}).get("eligible"))

    return {
        "benchmark": {
            "competitor_rows": list(manifest.get("competitors") or []),
            "sampled_queries": 0,
            "winner_domains": [],
        },
        "prompt_proof": {
            "prompt_rows": [],
            "captured_prompts": 0,
            "winner_urls": [],
        },
        "platform_breakdown": {
            "platform_rows": manifest_platforms,
            "sampled_platforms": len(manifest_platforms),
            "direct_captures": sum(1 for item in items if item.get("platform")),
        },
        "change_since_last_run": {
            "compare_to_v1": compare_to_v1,
            "comparable_runs": eligible_to_compare,
            "change_points": 0,
        },
    }


def classify_benchmark_section(
    *,
    competitor_rows: list[Any],
    sampled_queries: int,
    winner_domains: list[str],
) -> dict:
    competitor_count = _count_named_items(competitor_rows)
    winner_count = _count_named_items(winner_domains)
    if (
        competitor_count >= ADJUDICATION_THRESHOLDS["benchmark"]["decision_grade_competitors"]
        and sampled_queries >= ADJUDICATION_THRESHOLDS["benchmark"]["decision_grade_queries"]
        and winner_count >= ADJUDICATION_THRESHOLDS["benchmark"]["decision_grade_winners"]
    ):
        return _build_result(
            "decision-grade",
            "Named competitors, sample size, and winner domains are strong enough for a benchmark read.",
            "",
        )
    if (
        competitor_count >= ADJUDICATION_THRESHOLDS["benchmark"]["directional_competitors"]
        and sampled_queries >= ADJUDICATION_THRESHOLDS["benchmark"]["directional_queries"]
        and winner_count >= ADJUDICATION_THRESHOLDS["benchmark"]["directional_winners"]
    ):
        return _build_result(
            "directional",
            "Some competitor and winner evidence exists, but the benchmark sample is still thin.",
            "Benchmark is directional because the sample is incomplete.",
        )
    return _build_result(
        "omitted",
        "Competitor benchmark evidence is too thin for a trustworthy read.",
        "Benchmark is omitted because named competitors or winner domains were not captured.",
    )


def classify_prompt_proof_section(
    *,
    prompt_rows: list[Any],
    captured_prompts: int,
    winner_urls: list[str],
) -> dict:
    prompt_count = _count_named_items(prompt_rows)
    winner_count = _count_named_items(winner_urls)
    if (
        captured_prompts >= ADJUDICATION_THRESHOLDS["prompt_proof"]["decision_grade_prompts"]
        and winner_count >= ADJUDICATION_THRESHOLDS["prompt_proof"]["decision_grade_winners"]
        and prompt_count >= ADJUDICATION_THRESHOLDS["prompt_proof"]["decision_grade_prompts"]
    ):
        return _build_result(
            "decision-grade",
            "Prompt capture and winner URLs are sufficient for proof-grade reporting.",
            "",
        )
    if (
        captured_prompts >= ADJUDICATION_THRESHOLDS["prompt_proof"]["directional_prompts"]
        and (prompt_count > 0 or winner_count > 0)
    ):
        return _build_result(
            "directional",
            "Some prompt or winner evidence exists, but the proof set is partial.",
            "Prompt proof is directional because exact prompts or winner URLs are limited.",
        )
    return _build_result(
        "omitted",
        "No useful prompt proof was captured.",
        "Prompt proof is omitted because exact prompts or winner URLs were not captured.",
    )


def classify_platform_breakdown_section(
    *,
    platform_rows: list[Any],
    sampled_platforms: int,
    direct_captures: int,
) -> dict:
    platform_count = _count_named_items(platform_rows)
    if (
        sampled_platforms >= ADJUDICATION_THRESHOLDS["platform_breakdown"]["decision_grade_platforms"]
        and direct_captures >= ADJUDICATION_THRESHOLDS["platform_breakdown"]["decision_grade_direct_captures"]
        and platform_count >= ADJUDICATION_THRESHOLDS["platform_breakdown"]["decision_grade_platforms"]
    ):
        return _build_result(
            "decision-grade",
            "Multiple platforms were sampled with direct captures.",
            "",
        )
    if (
        sampled_platforms >= ADJUDICATION_THRESHOLDS["platform_breakdown"]["directional_platforms"]
        and direct_captures >= ADJUDICATION_THRESHOLDS["platform_breakdown"]["directional_direct_captures"]
    ):
        return _build_result(
            "directional",
            "At least one platform was sampled, but the coverage is still partial.",
            "Platform breakdown is directional because platform coverage is limited.",
        )
    return _build_result(
        "omitted",
        "No platform-level evidence was captured.",
        "Platform breakdown is omitted because sampled platforms were not captured.",
    )


def classify_change_since_last_run_section(
    *,
    compare_to_v1: bool,
    comparable_runs: bool,
    change_points: int,
) -> dict:
    if not compare_to_v1:
        return _build_result(
            "omitted",
            "No comparison was requested.",
            "Change-since-last-run is omitted because comparison was not requested.",
        )
    if not comparable_runs:
        return _build_result(
            "omitted",
            "Comparison is not valid for this run.",
            "Change-since-last-run is omitted because the runs are not comparable.",
        )
    if change_points == 0:
        return _build_result(
            "omitted",
            "Comparison is eligible, but no comparable change points were captured.",
            "Change-since-last-run is omitted because no comparable change points were captured.",
        )
    if change_points >= ADJUDICATION_THRESHOLDS["change_since_last_run"]["decision_grade_changes"]:
        return _build_result(
            "decision-grade",
            "The run has enough comparable change points to support a strong delta read.",
            "",
        )
    if change_points >= ADJUDICATION_THRESHOLDS["change_since_last_run"]["directional_changes"]:
        return _build_result(
            "directional",
            "The run has some comparable changes, but the delta is still limited.",
            "Change-since-last-run is directional because the change set is small.",
        )
    return _build_result(
        "omitted",
        "No meaningful changes were captured.",
        "Change-since-last-run is omitted because no comparable change points were captured.",
    )


def adjudicate_v2_sections(*, manifest: dict[str, Any], evidence: dict[str, Any]) -> dict:
    inputs = build_adjudication_inputs(manifest=manifest, evidence=evidence)

    benchmark = classify_benchmark_section(
        **inputs["benchmark"],
    )
    prompt_proof = classify_prompt_proof_section(
        **inputs["prompt_proof"],
    )
    platform_breakdown = classify_platform_breakdown_section(
        **inputs["platform_breakdown"],
    )
    change_since_last_run = classify_change_since_last_run_section(
        **inputs["change_since_last_run"],
    )

    return {
        "benchmark": benchmark,
        "prompt_proof": prompt_proof,
        "platform_breakdown": platform_breakdown,
        "change_since_last_run": change_since_last_run,
    }
