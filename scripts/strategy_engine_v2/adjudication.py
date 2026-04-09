from __future__ import annotations

from typing import Any, Mapping

from .evidence import build_sampled_query_prompt_rows

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


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _dedupe_text(values: Any) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for value in _sequence(values):
        text = _string(value)
        if not text:
            continue
        normalized = text.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        items.append(text)
    return items


def _count_named_items(items: list[Any] | None) -> int:
    count = 0
    for item in _clean_rows(items):
        if isinstance(item, str) and item.strip():
            count += 1
        elif isinstance(item, dict) and any(str(value).strip() for value in item.values() if value is not None):
            count += 1
    return count


def _change_since_last_run_inputs(
    *,
    manifest: dict[str, Any],
    comparison_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    compare_to_v1 = bool(_mapping(manifest.get("comparison_eligibility")).get("requested"))
    eligible_to_compare = bool(_mapping(manifest.get("comparison_eligibility")).get("eligible"))
    if comparison_context is None:
        return {
            "compare_to_v1": compare_to_v1,
            "comparable_runs": eligible_to_compare,
            "change_points": 0,
        }

    comparison = _mapping(comparison_context)
    previous_manifest = _mapping(comparison.get("previous_manifest"))
    return {
        "compare_to_v1": compare_to_v1,
        "comparable_runs": eligible_to_compare and bool(previous_manifest),
        "change_points": _int(comparison.get("change_points")),
    }


def _build_result(status: str, reason: str, warning: str) -> dict:
    return {
        "status": status,
        "reason": reason,
        "warning": warning,
    }


def _status_points(status: Any) -> int:
    normalized = _string(status).lower()
    if normalized == "decision-grade":
        return 2
    if normalized == "directional":
        return 1
    return 0


def _completeness_label(score: int) -> str:
    if score >= 75:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def _audit_data_inputs(
    *,
    manifest: dict[str, Any],
    audit_data: dict[str, Any],
    comparison_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    client_sections = _mapping(audit_data.get("client_report_sections"))
    report_sections = _mapping(audit_data.get("report_sections"))
    benchmark = _mapping(client_sections.get("competitive_benchmark"))
    benchmark_rows = _clean_rows(_sequence(benchmark.get("benchmark_rows")))
    sample_scope = _mapping(benchmark.get("sample_scope"))
    legacy_competitor_visibility = _mapping(report_sections.get("competitor_visibility"))
    competitor_rows = (
        benchmark_rows
        or _clean_rows(_sequence(benchmark.get("competitor_set")))
        or _clean_rows(_sequence(legacy_competitor_visibility.get("competitors")))
        or list(manifest.get("competitors") or [])
    )
    winner_domains: list[str] = []
    for row in benchmark_rows:
        if isinstance(row, Mapping):
            winner_domains.extend(_dedupe_text(row.get("winning_domains")))
    sampled_queries = _int(sample_scope.get("query_count")) or len(_sequence(audit_data.get("query_clusters")))

    prompt_proof = _mapping(client_sections.get("prompt_query_proof"))
    prompt_rows = _clean_rows(_sequence(prompt_proof.get("rows")))
    if not prompt_rows:
        prompt_rows = build_sampled_query_prompt_rows(audit_data)
    winner_urls: list[str] = []
    direct_capture_platforms: set[str] = set()
    for row in prompt_rows:
        if isinstance(row, Mapping):
            winner_urls.extend(_dedupe_text(row.get("winning_urls")))
            platform = _string(row.get("platform")).lower()
            if platform:
                direct_capture_platforms.add(platform)

    platform_breakdown = _mapping(client_sections.get("platform_breakdown"))
    legacy_technical_geo_gates = _mapping(report_sections.get("technical_geo_gates"))
    legacy_platform_rows = _clean_rows(_sequence(_mapping(legacy_technical_geo_gates.get("summary")).get("platforms")))
    platform_rows = _clean_rows(_sequence(platform_breakdown.get("platforms"))) or legacy_platform_rows

    return {
        "benchmark": {
            "competitor_rows": competitor_rows,
            "sampled_queries": sampled_queries,
            "winner_domains": winner_domains,
        },
        "prompt_proof": {
            "prompt_rows": prompt_rows,
            "captured_prompts": len(prompt_rows),
            "winner_urls": winner_urls,
        },
        "platform_breakdown": {
            "platform_rows": platform_rows,
            "sampled_platforms": len(platform_rows) or len(list(manifest.get("platforms") or [])),
            "direct_captures": len(direct_capture_platforms),
        },
        "change_since_last_run": {
            **_change_since_last_run_inputs(
                manifest=manifest,
                comparison_context=comparison_context,
            ),
        },
    }


def _evidence_inputs(
    *,
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    comparison_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items = list(evidence.get("items") or [])
    manifest_platforms = list(manifest.get("platforms") or [])

    benchmark_rows = [
        _mapping(item.get("raw_observation"))
        for item in items
        if _string(item.get("evidence_type")) == "benchmark_row"
    ]
    prompt_rows = [
        _mapping(item.get("raw_observation"))
        for item in items
        if _string(item.get("evidence_type")) == "prompt_proof"
    ]
    platform_rows = [
        _mapping(item.get("raw_observation"))
        for item in items
        if _string(item.get("evidence_type")) == "platform_observation"
    ]
    winner_domains: list[str] = []
    for row in benchmark_rows:
        winner_domains.extend(_dedupe_text(row.get("winning_domains")))
    winner_urls: list[str] = []
    direct_capture_platforms: set[str] = set()
    for row in prompt_rows:
        winner_urls.extend(_dedupe_text(row.get("winning_urls")))
        platform = _string(row.get("platform")).lower()
        if platform:
            direct_capture_platforms.add(platform)

    return {
        "benchmark": {
            "competitor_rows": benchmark_rows or list(manifest.get("competitors") or []),
            "sampled_queries": len(
                {
                    _string(item.get("query_theme")).lower()
                    for item in items
                    if _string(item.get("evidence_type")) in {"query_cluster", "citation_failure", "prompt_proof"}
                    and _string(item.get("query_theme"))
                }
            ),
            "winner_domains": winner_domains,
        },
        "prompt_proof": {
            "prompt_rows": prompt_rows,
            "captured_prompts": len(prompt_rows),
            "winner_urls": winner_urls,
        },
        "platform_breakdown": {
            "platform_rows": platform_rows or manifest_platforms,
            "sampled_platforms": len(platform_rows) or len(manifest_platforms),
            "direct_captures": len(direct_capture_platforms),
        },
        "change_since_last_run": {
            **_change_since_last_run_inputs(
                manifest=manifest,
                comparison_context=comparison_context,
            ),
        },
    }


def build_adjudication_inputs(
    *,
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    audit_data: dict[str, Any] | None = None,
    comparison_context: dict[str, Any] | None = None,
) -> dict:
    bridged_audit = _mapping(audit_data)
    if bridged_audit:
        return _audit_data_inputs(
            manifest=manifest,
            audit_data=bridged_audit,
            comparison_context=comparison_context,
        )
    return _evidence_inputs(
        manifest=manifest,
        evidence=evidence,
        comparison_context=comparison_context,
    )


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
    sampled_query_bridge = any(
        _string(_mapping(row).get("capture_mode")) == "sampled_query_bridge"
        for row in _clean_rows(prompt_rows)
        if isinstance(row, Mapping)
    )
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
            (
                "Sampled query evidence exists, but exact prompt or winner capture is still partial."
                if sampled_query_bridge
                else "Some prompt or winner evidence exists, but the proof set is partial."
            ),
            (
                "Prompt proof is directional because it relies on sampled query evidence instead of exact prompt or winner capture."
                if sampled_query_bridge
                else "Prompt proof is directional because exact prompts or winner URLs are limited."
            ),
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
    if (
        sampled_platforms >= ADJUDICATION_THRESHOLDS["platform_breakdown"]["directional_platforms"]
        and platform_count >= ADJUDICATION_THRESHOLDS["platform_breakdown"]["directional_platforms"]
    ):
        return _build_result(
            "directional",
            "Platform-level readiness signals exist, but direct prompt or answer captures are still limited.",
            "Platform breakdown is directional because it relies on platform readiness signals without direct answer captures.",
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
            "decision-grade",
            "A comparable prior run exists and no material change points were detected.",
            "",
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


def classify_evidence_completeness_section(
    *,
    benchmark_status: str,
    prompt_proof_status: str,
    platform_breakdown_status: str,
    change_status: str,
    comparison_requested: bool,
) -> dict:
    component_statuses = [
        ("benchmark", benchmark_status),
        ("prompt proof", prompt_proof_status),
        ("platform breakdown", platform_breakdown_status),
    ]
    if comparison_requested:
        component_statuses.append(("change comparison", change_status))

    possible_points = max(len(component_statuses) * 2, 1)
    earned_points = sum(_status_points(status) for _, status in component_statuses)
    score = round((earned_points / possible_points) * 100)
    label = _completeness_label(score)

    partial_components = [
        name for name, status in component_statuses if _string(status).lower() == "directional"
    ]
    missing_components = [
        name for name, status in component_statuses if _string(status).lower() == "omitted"
    ]

    if label == "High":
        reason = "This run captured enough benchmark, prompt-proof, and platform evidence to support most topline claims."
    elif label == "Medium":
        reason = "This run captured some direct evidence, but important proof layers are still partial."
    else:
        reason = "This run is still missing key benchmark, prompt-proof, or platform captures, so leadership claims stay conservative."

    if comparison_requested and "change comparison" in partial_components + missing_components:
        reason += " Comparison evidence is still limited in this run."

    return {
        "score": score,
        "label": label,
        "reason": reason,
        "partial_components": partial_components,
        "missing_components": missing_components,
    }


def adjudicate_v2_sections(
    *,
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    audit_data: dict[str, Any] | None = None,
    comparison_context: dict[str, Any] | None = None,
) -> dict:
    inputs = build_adjudication_inputs(
        manifest=manifest,
        evidence=evidence,
        audit_data=audit_data,
        comparison_context=comparison_context,
    )

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
    evidence_completeness = classify_evidence_completeness_section(
        benchmark_status=benchmark.get("status", "omitted"),
        prompt_proof_status=prompt_proof.get("status", "omitted"),
        platform_breakdown_status=platform_breakdown.get("status", "omitted"),
        change_status=change_since_last_run.get("status", "omitted"),
        comparison_requested=bool(inputs["change_since_last_run"].get("compare_to_v1")),
    )

    return {
        "benchmark": benchmark,
        "prompt_proof": prompt_proof,
        "platform_breakdown": platform_breakdown,
        "change_since_last_run": change_since_last_run,
        "evidence_completeness": evidence_completeness,
    }
