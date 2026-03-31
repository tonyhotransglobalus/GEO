from __future__ import annotations

from typing import Any, Mapping

MARKDOWN_FILENAME = "GEO-STRATEGY-REPORT-V2.md"


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)
    return []


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _append_heading(lines: list[str], heading: str) -> None:
    lines.extend(["", f"## {heading}", ""])


def _render_summary_lines(section: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    trust_label = _string(section.get("trust_label"))
    trust_value = _string(section.get("trust_value"))
    if trust_label:
        if trust_value:
            lines.append(f"- {trust_label}: {trust_value}")
        else:
            lines.append(f"- Trust label: {trust_label}")
    for item in _sequence(section.get("summary")):
        lines.append(f"- {item}")
    visible_reason = _string(section.get("visible_reason"))
    if visible_reason:
        lines.append(f"- Visible reason: {visible_reason}")
    return lines


def _render_score_explanations(section: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    note = _string(section.get("plain_english_note"))
    if note:
        lines.append(note)
        lines.append("")
    terms = _sequence(section.get("terms"))
    if terms:
        lines.append("### Term Guide")
        lines.append("")
        for term in terms:
            if isinstance(term, Mapping):
                lines.append(
                    f"- {_string(term.get('label'))}: {_string(term.get('plain_english'))}"
                )
        lines.append("")
    weighting = _sequence(section.get("weighting"))
    if weighting:
        lines.append("### Scoring And Weighting")
        lines.append("")
        for item in weighting:
            if isinstance(item, Mapping):
                lines.append(
                    f"- {_string(item.get('label'))}: {_string(item.get('why_it_matters'))}"
                )
        lines.append("")
    scorecard = _sequence(section.get("scorecard"))
    if scorecard:
        lines.append("### Scorecard")
        lines.append("")
        for item in scorecard:
            if isinstance(item, Mapping):
                label = _string(item.get("label"))
                score = _string(item.get("score"))
                plain_english = _string(item.get("plain_english"))
                lines.append(f"- {label}: {score}. {plain_english}".strip())
        lines.append("")
    score_provenance = _string(section.get("score_provenance"))
    if score_provenance:
        lines.append(f"- Score provenance: {score_provenance}")
        lines.append("")
    run_context = _mapping(section.get("run_context"))
    if run_context:
        lines.append("### Run Context")
        lines.append("")
        for key, value in run_context.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    return lines


def _render_priority_findings(section: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    for finding in _sequence(section.get("findings")):
        if not isinstance(finding, Mapping):
            continue
        lines.extend([f"### {_string(finding.get('section')).replace('_', ' ').title()}", ""])
        lines.append(f"- Status: {_string(finding.get('status'))}")
        lines.append(f"- Summary: {_string(finding.get('summary'))}")
        visible_reason = _string(finding.get("visible_reason"))
        if visible_reason:
            lines.append(f"- Visible reason: {visible_reason}")
        leadership_impact = _string(finding.get("leadership_impact"))
        if leadership_impact:
            lines.append(f"- Why it matters: {leadership_impact}")
        marketing_action = _string(finding.get("marketing_action"))
        if marketing_action:
            lines.append(f"- Marketing action: {marketing_action}")
        engineering_action = _string(finding.get("engineering_action"))
        if engineering_action:
            lines.append(f"- Engineering action: {engineering_action}")
        evidence_items = _sequence(finding.get("evidence_items"))
        if evidence_items:
            lines.append("- Evidence items:")
            for item in evidence_items:
                if isinstance(item, Mapping):
                    lines.append(
                        "  - "
                        + ", ".join(
                            part
                            for part in (
                                _string(item.get("evidence_type")),
                                _string(item.get("source_class")),
                                _string(item.get("normalized_summary")),
                            )
                            if part
                        )
                    )
        lines.append("")
    if not lines:
        lines.append("- No priority findings captured.")
    return lines


def _render_benchmark(section: Mapping[str, Any]) -> list[str]:
    lines = [
        f"- Status: {_string(section.get('status'))}",
        f"- Summary: {_string(section.get('reason'))}",
    ]
    visible_reason = _string(section.get("visible_reason"))
    if visible_reason:
        lines.append(f"- Visible reason: {visible_reason}")
    competitors = _sequence(section.get("competitors"))
    if competitors:
        lines.append(f"- Competitors: {', '.join(_string(item) for item in competitors if _string(item))}")
    sample_scope = _mapping(section.get("sample_scope"))
    if sample_scope:
        lines.append("- Sample scope:")
        for key, value in sample_scope.items():
            lines.append(f"  - {key}: {value}")
    benchmark_rows = _sequence(section.get("benchmark_rows"))
    if benchmark_rows:
        lines.append("- Benchmark rows:")
        for row in benchmark_rows:
            if isinstance(row, Mapping):
                lines.append(
                    "  - "
                    + "; ".join(
                        part
                        for part in (
                            _string(row.get("competitor_name")),
                            _string(row.get("platform")),
                            _string(row.get("our_gap")),
                            _string(row.get("confidence")),
                        )
                        if part
                    )
                )
    sample_note = _string(section.get("sample_note"))
    if sample_note:
        lines.append(f"- Sample note: {sample_note}")
    return lines


def _render_platforms(section: Mapping[str, Any]) -> list[str]:
    lines = [
        f"- Status: {_string(section.get('status'))}",
        f"- Summary: {_string(section.get('reason'))}",
    ]
    visible_reason = _string(section.get("visible_reason"))
    if visible_reason:
        lines.append(f"- Visible reason: {visible_reason}")
    platforms = _sequence(section.get("platforms"))
    if platforms:
        if all(isinstance(item, Mapping) for item in platforms):
            lines.append("- Platforms:")
            for item in platforms:
                lines.append(
                    "  - "
                    + "; ".join(
                        part
                        for part in (
                            _string(item.get("platform")),
                            _string(item.get("observed_visibility_status")),
                            _string(item.get("confidence")),
                        )
                        if part
                    )
                )
        else:
            lines.append(f"- Platforms: {', '.join(_string(item) for item in platforms if _string(item))}")
    sample_note = _string(section.get("sample_note"))
    if sample_note:
        lines.append(f"- Sample note: {sample_note}")
    return lines


def _render_page_source_evidence(section: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    visible_reason = _string(section.get("visible_reason"))
    if visible_reason:
        lines.append(visible_reason)
        lines.append("")
    priority_pages = _sequence(section.get("priority_pages"))
    if priority_pages:
        lines.append("### Priority Pages")
        lines.append("")
        for item in priority_pages:
            if isinstance(item, Mapping):
                lines.append(
                    f"- {_string(item.get('page_url'))} "
                    f"({_string(item.get('page_type'))}, citability {_string(item.get('citability_score'))}, confidence {_string(item.get('confidence'))})"
                )
        lines.append("")
    source_domains = _sequence(section.get("source_domains"))
    if source_domains:
        lines.append("### Source Domains")
        lines.append("")
        for item in source_domains:
            if isinstance(item, Mapping):
                lines.append(
                    f"- {_string(item.get('domain'))}: {_string(item.get('why_it_matters'))}"
                )
        lines.append("")
    for item in _sequence(section.get("evidence_items")):
        if isinstance(item, Mapping):
            lines.append(
                f"- {_string(item.get('evidence_type'))}: {_string(item.get('summary'))}"
            )
    if not lines:
        lines.append("- No evidence ledger items were captured.")
    return lines


def _render_actions(section: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    for action in _sequence(section.get("actions")):
        if not isinstance(action, Mapping):
            continue
        time_horizon = _string(action.get("time_horizon"))
        action_text = _string(action.get("action"))
        owner = _string(action.get("owner"))
        expected_outcome = _string(action.get("expected_outcome")).rstrip(".")
        visible_reason = _string(action.get("visible_reason")).rstrip(".")
        lines.append(
            f"- {time_horizon}: {action_text} "
            f"Owner: {owner}. "
            f"Expected outcome: {expected_outcome}. "
            f"Visible reason: {visible_reason}"
        )
    if not lines:
        lines.append("- No structured actions captured.")
    return lines


def _render_proof_appendix(section: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    manifest = _mapping(section.get("manifest"))
    if manifest:
        lines.append(f"- Target URL: {_string(manifest.get('target_url'))}")
        lines.append(f"- Mode: {_string(manifest.get('mode'))}")
        lines.append(f"- Shadow run: {_string(manifest.get('shadow_run'))}")
    lines.append(f"- Evidence count: {_string(section.get('evidence_count'))}")
    visible_reason = _string(section.get("visible_reason"))
    if visible_reason:
        lines.append(f"- Visible reason: {visible_reason}")
    adjudication = _mapping(section.get("adjudication"))
    if adjudication:
        lines.append("- Section adjudication:")
        for name, item in adjudication.items():
            if isinstance(item, Mapping):
                lines.append(
                    f"  - {name}: {_string(item.get('status'))} | {_string(item.get('reason'))}"
                )
    methodology = _mapping(section.get("methodology"))
    if methodology:
        lines.append(f"- Methodology: {_string(methodology.get('summary'))}")
    bridge_warnings = _sequence(section.get("bridge_warnings"))
    if bridge_warnings:
        lines.append("- Bridge warnings:")
        for item in bridge_warnings:
            lines.append(f"  - {_string(item)}")
    limitations = _mapping(section.get("limitations"))
    if limitations:
        lines.append(f"- Limitation: {_string(limitations.get('limitations_note'))}")
    return lines


def render_v2_markdown_report(payload: Mapping[str, Any] | None) -> str:
    data = _mapping(payload)
    manifest = _mapping(data.get("manifest"))
    sections = _mapping(data.get("report_sections"))

    lines: list[str] = [
        "# GEO Strategy Report V2",
        "",
        f"**Primary URL:** {_string(manifest.get('target_url'))}",
        f"**Run Mode:** {_string(manifest.get('mode')) or 'script-only'}",
        f"**Artifact Filename:** {MARKDOWN_FILENAME}",
    ]

    leadership = _mapping(sections.get("leadership_summary"))
    _append_heading(lines, "Leadership Summary")
    lines.extend(_render_summary_lines(leadership))

    score_explanations = _mapping(sections.get("score_explanations"))
    _append_heading(lines, "Score Explanations")
    lines.extend(_render_score_explanations(score_explanations))

    priority_findings = _mapping(sections.get("priority_findings"))
    _append_heading(lines, "Priority Findings")
    lines.extend(_render_priority_findings(priority_findings))

    benchmark = _mapping(sections.get("competitive_benchmark"))
    _append_heading(lines, "Competitive Benchmark")
    lines.extend(_render_benchmark(benchmark))

    platform_breakdown = _mapping(sections.get("platform_breakdown"))
    _append_heading(lines, "Platform Breakdown")
    lines.extend(_render_platforms(platform_breakdown))

    page_source_evidence = _mapping(sections.get("page_source_evidence"))
    _append_heading(lines, "Page And Source Evidence")
    lines.extend(_render_page_source_evidence(page_source_evidence))

    action_plan = _mapping(sections.get("action_plan"))
    _append_heading(lines, "Action Plan")
    lines.extend(_render_actions(action_plan))

    proof_appendix = _mapping(sections.get("proof_appendix"))
    _append_heading(lines, "Proof Appendix")
    lines.extend(_render_proof_appendix(proof_appendix))

    return "\n".join(lines).strip() + "\n"
