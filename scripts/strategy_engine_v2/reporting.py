from __future__ import annotations

from typing import Any, Mapping


REPORT_SECTION_ORDER = (
    "leadership_summary",
    "score_explanations",
    "priority_findings",
    "competitive_benchmark",
    "platform_breakdown",
    "page_source_evidence",
    "action_plan",
    "proof_appendix",
)

SECTION_EVIDENCE_TYPES = {
    "benchmark": ("run_manifest", "plugin_results"),
    "prompt_proof": ("plugin_results",),
    "platform_breakdown": ("run_manifest", "plugin_results"),
    "change_since_last_run": ("run_manifest",),
}


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


def _status_rank(status: str) -> int:
    ranks = {
        "decision-grade": 0,
        "directional": 1,
        "omitted": 2,
    }
    return ranks.get(status, 3)


def _worst_status(statuses: list[str]) -> str:
    cleaned = [status for status in statuses if status]
    if not cleaned:
        return "omitted"
    return sorted(cleaned, key=_status_rank)[-1]


def _visible_reason(section: Mapping[str, Any]) -> str:
    warning = _string(section.get("warning"))
    if warning:
        return warning
    reason = _string(section.get("reason"))
    if reason:
        return reason
    return "No evidence was captured for this section yet."


def _section_status(section: Mapping[str, Any]) -> str:
    return _string(section.get("status")) or "omitted"


def _most_severe_visible_reason(adjudication: Mapping[str, Any], section_names: tuple[str, ...]) -> str:
    best_section: Mapping[str, Any] | None = None
    best_rank = -1
    for section_name in section_names:
        section = _mapping(adjudication.get(section_name))
        rank = _status_rank(_section_status(section))
        if rank > best_rank:
            best_rank = rank
            best_section = section
    if best_section is None:
        return "No evidence has been captured yet."
    return _visible_reason(best_section)


def _evidence_items(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    evidence = _mapping(report_input.get("evidence"))
    items: list[dict[str, Any]] = []
    for item in _sequence(evidence.get("items")):
        if isinstance(item, Mapping):
            items.append(dict(item))
    return items


def _score_explanations(report_input: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping(report_input.get("manifest"))
    adjudication = _mapping(report_input.get("adjudication"))
    evidence = _mapping(report_input.get("evidence"))
    return {
        "title": "Score Explanations",
        "plain_english_note": (
            "Scores are a guide, not proof. Sections are labeled decision-grade, directional, or omitted so weak samples stay visible."
        ),
        "terms": [
            {
                "label": "How much to trust this",
                "plain_english": "A short read on how confident we should be in the current run.",
            },
            {
                "label": "Decision-grade",
                "plain_english": "The evidence is strong enough to support a client-facing claim.",
            },
            {
                "label": "Directional",
                "plain_english": "The signal is useful, but the sample is still partial.",
            },
            {
                "label": "Omitted",
                "plain_english": "There was not enough proof to make the section look stronger than it is.",
            },
            {
                "label": "Evidence class",
                "plain_english": "The source type behind a claim, such as live site checks or internal scoring.",
            },
        ],
        "weighting": [
            {
                "label": "Evidence completeness",
                "why_it_matters": "Weak samples should stay directional or omitted instead of being overstated.",
            },
            {
                "label": "Visible reasons",
                "why_it_matters": "Every downgraded section should explain itself in plain English.",
            },
        ],
        "run_context": {
            "mode": _string(manifest.get("mode")) or "script-only",
            "evidence_items": len(_sequence(evidence.get("items"))),
            "adjudicated_sections": list(adjudication.keys()),
        },
    }


def _priority_findings(report_input: Mapping[str, Any]) -> dict[str, Any]:
    adjudication = _mapping(report_input.get("adjudication"))
    evidence_items = _evidence_items(report_input)
    evidence_by_type: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_items:
        evidence_type = _string(item.get("evidence_type")) or "unknown"
        evidence_by_type.setdefault(evidence_type, []).append(item)

    findings: list[dict[str, Any]] = []
    for section_name in ("benchmark", "prompt_proof", "platform_breakdown", "change_since_last_run"):
        section = _mapping(adjudication.get(section_name))
        status = _string(section.get("status")) or "omitted"
        reason = _string(section.get("reason")) or "No reason recorded."
        warning = _string(section.get("warning"))
        evidence_types = SECTION_EVIDENCE_TYPES.get(section_name, ())
        section_evidence: list[dict[str, Any]] = []
        for evidence_type in evidence_types:
            section_evidence.extend(evidence_by_type.get(evidence_type, []))
        findings.append(
            {
                "section": section_name,
                "status": status,
                "summary": reason,
                "visible_reason": warning or reason,
                "evidence_items": section_evidence,
            }
        )

    return {
        "title": "Priority Findings",
        "findings": findings,
    }


def _competitive_benchmark(report_input: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping(report_input.get("manifest"))
    adjudication = _mapping(report_input.get("adjudication")).get("benchmark", {})
    if not isinstance(adjudication, Mapping):
        adjudication = {}
    return {
        "title": "Competitive Benchmark",
        "status": _string(adjudication.get("status")) or "omitted",
        "reason": _string(adjudication.get("reason")) or "No benchmark reason was recorded.",
        "visible_reason": _visible_reason(adjudication),
        "competitors": _sequence(manifest.get("competitors")),
        "sample_note": (
            "This section stays conservative until named competitors, sampled queries, and winners are captured."
        ),
    }


def _platform_breakdown(report_input: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping(report_input.get("manifest"))
    adjudication = _mapping(report_input.get("adjudication")).get("platform_breakdown", {})
    if not isinstance(adjudication, Mapping):
        adjudication = {}
    return {
        "title": "Platform Breakdown",
        "status": _string(adjudication.get("status")) or "omitted",
        "reason": _string(adjudication.get("reason")) or "No platform reason was recorded.",
        "visible_reason": _visible_reason(adjudication),
        "platforms": _sequence(manifest.get("platforms")),
        "sample_note": "Platform-specific claims stay directional until direct captures are available.",
    }


def _page_source_evidence(report_input: Mapping[str, Any]) -> dict[str, Any]:
    evidence_items = []
    for item in _evidence_items(report_input):
        evidence_items.append(
            {
                "evidence_type": _string(item.get("evidence_type")),
                "source_class": _string(item.get("source_class")),
                "observed_vs_inferred": _string(item.get("observed_vs_inferred")),
                "summary": _string(item.get("normalized_summary")),
                "confidence": _string(item.get("confidence")),
            }
        )
    return {
        "title": "Page And Source Evidence",
        "evidence_items": evidence_items,
        "visible_reason": "The appendix lists the evidence ledger used to build the report.",
    }


def _action_plan(report_input: Mapping[str, Any]) -> dict[str, Any]:
    adjudication = _mapping(report_input.get("adjudication"))
    benchmark = _mapping(adjudication.get("benchmark"))
    prompt_proof = _mapping(adjudication.get("prompt_proof"))
    platform_breakdown = _mapping(adjudication.get("platform_breakdown"))
    change = _mapping(adjudication.get("change_since_last_run"))
    actions = [
        {
            "time_horizon": "30 days",
            "action": "Capture named competitor queries and exact answer snippets before upgrading benchmark claims.",
            "owner": "strategy",
            "expected_outcome": "Benchmark reporting becomes decision-grade instead of directional.",
            "visible_reason": _visible_reason(benchmark),
        },
        {
            "time_horizon": "60 days",
            "action": "Collect real prompt and platform captures so proof and platform sections can move beyond placeholders.",
            "owner": "marketing",
            "expected_outcome": "Prompt proof and platform breakdowns become more defensible.",
            "visible_reason": _visible_reason(prompt_proof) or _visible_reason(platform_breakdown),
        },
        {
            "time_horizon": "90 days",
            "action": "Define a repeatable comparison baseline so change-since-last-run can show real deltas.",
            "owner": "strategy",
            "expected_outcome": "Comparisons move from omitted to directional or decision-grade.",
            "visible_reason": _visible_reason(change),
        },
    ]
    return {
        "title": "Action Plan",
        "actions": actions,
    }


def _proof_appendix(report_input: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping(report_input.get("manifest"))
    evidence = _mapping(report_input.get("evidence"))
    adjudication = _mapping(report_input.get("adjudication"))
    return {
        "title": "Proof Appendix",
        "manifest": manifest,
        "evidence_count": len(_sequence(evidence.get("items"))),
        "adjudication": adjudication,
        "visible_reason": "This appendix preserves the run scope, evidence ledger, and section reasons.",
    }


def build_v2_report_sections(report_input: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(report_input)
    evidence = _mapping(payload.get("evidence"))
    adjudication = _mapping(payload.get("adjudication"))
    manifest = _mapping(payload.get("manifest"))
    evidence_count = len(_sequence(evidence.get("items")))
    section_statuses = [
        _section_status(_mapping(adjudication.get(section_name)))
        for section_name in ("benchmark", "prompt_proof", "platform_breakdown", "change_since_last_run")
    ]

    sections = {
        "leadership_summary": {
            "title": "Leadership Summary",
            "status": _worst_status(section_statuses),
            "trust_label": "How much to trust this",
            "summary": [
                "The V2 report keeps the top layer short and the proof visible.",
                f"Run mode: {_string(manifest.get('mode')) or 'script-only'}.",
                f"Evidence items captured: {evidence_count}.",
            ],
            "visible_reason": _most_severe_visible_reason(
                adjudication,
                ("benchmark", "prompt_proof", "platform_breakdown", "change_since_last_run"),
            ),
        },
        "score_explanations": _score_explanations(payload),
        "priority_findings": _priority_findings(payload),
        "competitive_benchmark": _competitive_benchmark(payload),
        "platform_breakdown": _platform_breakdown(payload),
        "page_source_evidence": _page_source_evidence(payload),
        "action_plan": _action_plan(payload),
        "proof_appendix": _proof_appendix(payload),
    }
    return {key: sections[key] for key in REPORT_SECTION_ORDER}
