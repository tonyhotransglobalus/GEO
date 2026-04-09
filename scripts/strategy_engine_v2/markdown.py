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


def _label_text(value: Any) -> str:
    text = _string(value).replace("_", " ")
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _strip_known_prefix(value: Any, prefixes: tuple[str, ...]) -> str:
    text = _string(value)
    lowered = text.lower()
    for prefix in prefixes:
        marker = prefix.lower()
        if lowered.startswith(marker):
            return text[len(prefix):].strip()
    return text


def _render_summary_lines(section: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    readiness_label = _string(section.get("readiness_label"))
    readiness_value = _string(section.get("readiness_value"))
    if readiness_label:
        if readiness_value:
            lines.append(f"- {readiness_label}: {readiness_value}")
        else:
            lines.append(f"- {readiness_label}")
    completeness_label = _string(section.get("completeness_label"))
    completeness_value = _string(section.get("completeness_value"))
    if completeness_label:
        if completeness_value:
            lines.append(f"- {completeness_label}: {completeness_value}")
        else:
            lines.append(f"- {completeness_label}")
    trust_label = _string(section.get("trust_label"))
    trust_value = _string(section.get("trust_value"))
    if trust_label and trust_label != completeness_label:
        if trust_value:
            lines.append(f"- {trust_label}: {trust_value}")
        else:
            lines.append(f"- Trust label: {trust_label}")
    for item in _sequence(section.get("summary")):
        lines.append(f"- {item}")
    visible_reason = _string(section.get("visible_reason"))
    if visible_reason:
        lines.append(f"- Visible reason: {visible_reason}")
    trust_note = _string(section.get("trust_note"))
    if trust_note:
        lines.append(f"- Trust note: {trust_note}")
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
        title = _string(finding.get("title")) or _string(finding.get("section")).replace("_", " ").title()
        lines.extend([f"### {title}", ""])
        lines.append(f"- Status: {_string(finding.get('status'))}")
        lines.append(f"- What's wrong: {_string(finding.get('summary'))}")
        visible_reason = _string(finding.get("visible_reason"))
        if visible_reason and _string(finding.get("summary")).lower() != visible_reason.lower():
            lines.append(f"- What we saw: {visible_reason}")
        leadership_impact = _string(finding.get("leadership_impact"))
        if leadership_impact:
            lines.append(f"- Why it matters: {leadership_impact}")
        claim_source = _label_text(finding.get("claim_source_class"))
        if claim_source:
            lines.append(f"- Claim source: {claim_source}")
        evidence_grade = _label_text(finding.get("evidence_grade"))
        if evidence_grade:
            lines.append(f"- Evidence grade: {evidence_grade}")
        related_action_title = _string(finding.get("related_action_title"))
        if related_action_title:
            lines.append(f"- Related website fix: {related_action_title}")
        else:
            marketing_action = _string(finding.get("marketing_action"))
            if marketing_action:
                lines.append(f"- Marketing action: {marketing_action}")
            engineering_action = _string(finding.get("engineering_action"))
            if engineering_action:
                lines.append(f"- Engineering action: {engineering_action}")
        what_upgrades_this = _string(finding.get("what_upgrades_this"))
        if what_upgrades_this:
            lines.append(f"- What upgrades this: {what_upgrades_this}")
        confidence = _string(finding.get("confidence"))
        confidence_reason = _string(finding.get("confidence_reason"))
        if confidence:
            if confidence_reason:
                lines.append(f"- Confidence: {confidence}. {confidence_reason}")
            else:
                lines.append(f"- Confidence: {confidence}")
        success_metric = _string(finding.get("success_metric"))
        if success_metric:
            lines.append(f"- How we will know this improved: {success_metric}")
        limitations = _string(finding.get("limitations"))
        if limitations:
            lines.append(f"- Limitations: {limitations}")
        supporting_evidence = [
            _string(item) for item in _sequence(finding.get("supporting_evidence")) if _string(item)
        ]
        evidence_items = _sequence(finding.get("evidence_items"))
        if supporting_evidence or evidence_items:
            lines.append("- Evidence from this run:")
        for item in supporting_evidence[:3]:
            lines.append(f"  - {item}")
        if evidence_items and not supporting_evidence:
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
    claim_source = _label_text(section.get("claim_source_class"))
    if claim_source:
        lines.append(f"- Claim source: {claim_source}")
    evidence_grade = _label_text(section.get("evidence_grade"))
    if evidence_grade:
        lines.append(f"- Evidence grade: {evidence_grade}")
    what_upgrades_this = _string(section.get("what_upgrades_this"))
    if what_upgrades_this:
        lines.append(f"- What upgrades this: {what_upgrades_this}")
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
                official_sources = _sequence(item.get("official_sources"))
                if official_sources:
                    lines.append(
                        "    Sources: "
                        + ", ".join(
                            f"{_string(source.get('title'))} ({_string(source.get('url'))})"
                            for source in official_sources
                            if isinstance(source, Mapping)
                        )
                    )
                control_rows = _sequence(item.get("control_rows"))
                if control_rows:
                    lines.append("    Control matrix:")
                    for control in control_rows:
                        if not isinstance(control, Mapping):
                            continue
                        surface_label = _string(control.get("surface_label")) or _string(control.get("surface")).replace("_", " ").title()
                        status = _string(control.get("status"))
                        recommendation = _string(control.get("recommendation"))
                        line = f"{_string(control.get('bot_name'))} ({surface_label}): {status}."
                        if recommendation:
                            line += f" {recommendation}"
                        lines.append(f"      - {line}")
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
    if _string(section.get("mode")) == "singleton":
        primary = _mapping(section.get("primary_action"))
        if primary:
            lines.extend(["## Primary Website Fix This Run", ""])
            lines.append(f"- {_string(primary.get('title'))}")
            for label, value in (
                ("Priority", _string(primary.get("priority"))),
                ("Owner", _string(primary.get("owner"))),
                ("Roles", ", ".join(_sequence(primary.get("role_tags")))),
                ("Exact location", _string(primary.get("exact_location"))),
                ("Observed evidence", _string(primary.get("observed_evidence"))),
                ("Why this is the lead fix", _string(primary.get("why_this_is_the_lead_fix"))),
                ("Expected GEO effect", _string(primary.get("expected_geo_effect"))),
                ("Confidence", _string(primary.get("confidence"))),
                ("Confidence reason", _string(primary.get("confidence_reason"))),
                ("Success metric", _string(primary.get("success_metric"))),
            ):
                if value:
                    lines.append(f"  - {label}: {value}")
            if _sequence(primary.get("exact_change")):
                lines.append("  - Exact change:")
                for step in _sequence(primary.get("exact_change"))[:3]:
                    if _string(step):
                        lines.append(f"    - {_string(step)}")
            for label, value in (
                ("Example implementation", _string(primary.get("example_implementation"))),
                ("Acceptance criteria", _string(primary.get("acceptance_criteria"))),
                ("QA", _strip_known_prefix(_string(primary.get("verification_qa")), ("QA:",))),
                ("Next run", _strip_known_prefix(_string(primary.get("verification_geo")), ("Next run:",))),
                ("Outcome tracking", _strip_known_prefix(_string(primary.get("verification_outcome")), ("Watch", "Outcome tracking:"))),
            ):
                if value:
                    lines.append(f"  - {label}: {value}")
            proof_packet = [_string(item) for item in _sequence(primary.get("proof_packet")) if _string(item)]
            if proof_packet:
                lines.append("  - Proof packet:")
                for item in proof_packet[:3]:
                    lines.append(f"    - {item}")
            lines.append("")
        rollout_sequence = [_string(item) for item in _sequence(primary.get("rollout_sequence")) if _string(item)]
        if rollout_sequence:
            lines.extend(["## Rollout Map", ""])
            for step in rollout_sequence:
                lines.append(f"- {step}")
            lines.append("")
        watchlist = [item for item in _sequence(section.get("watchlist")) if isinstance(item, Mapping)]
        if watchlist:
            lines.extend(["## Not Recommending Yet", ""])
            for item in watchlist:
                lines.append(f"- {_string(item.get('title'))}")
                for label, value in (
                    ("Evidence grade", _string(item.get("evidence_grade"))),
                    ("Why not recommended yet", _string(item.get("why_not_recommended_yet"))),
                    ("What upgrades this", _string(item.get("what_upgrades_this"))),
                    ("Strongest evidence", _string(item.get("strongest_evidence"))),
                ):
                    if value:
                        lines.append(f"  - {label}: {value}")
                lines.append("")
        return lines
    top_actions = [action for action in _sequence(section.get("top_actions")) if isinstance(action, Mapping)]
    if len(top_actions) > 1:
        lines.extend(["### Top Website Fixes", ""])
        for action in top_actions:
            lines.append(f"- {_string(action.get('title'))}")
            for label, value in (
                ("Priority", _string(action.get("priority"))),
                ("Owner", _string(action.get("owner"))),
                ("Roles", ", ".join(_sequence(action.get("role_tags")))),
                ("Exact location", _string(action.get("exact_location"))),
                ("Observed evidence", _string(action.get("observed_evidence"))),
                ("Expected GEO effect", _string(action.get("expected_geo_effect"))),
                ("Confidence", _string(action.get("confidence"))),
            ):
                if value:
                    lines.append(f"  - {label}: {value}")
            for step in _sequence(action.get("exact_change"))[:2]:
                if _string(step):
                    lines.append(f"  - Change: {_string(step)}")
            acceptance_criteria = _string(action.get("acceptance_criteria"))
            if acceptance_criteria:
                lines.append(f"  - Acceptance criteria: {acceptance_criteria}")
            lines.append("")
    groups = [group for group in _sequence(section.get("groups")) if isinstance(group, Mapping)]
    if groups:
        lines.extend(["### Full Website Improvement Plan", ""])
        for group in groups:
            lines.extend([f"#### {_string(group.get('label'))}", ""])
            for action in _sequence(group.get("actions")):
                if not isinstance(action, Mapping):
                    continue
                lines.append(f"- {_string(action.get('title'))}")
                for label, value in (
                    ("Priority", _string(action.get("priority"))),
                    ("Owner", _string(action.get("owner"))),
                    ("Exact location", _string(action.get("exact_location"))),
                    ("Observed evidence", _string(action.get("observed_evidence"))),
                ):
                    if value:
                        lines.append(f"  - {label}: {value}")
                if _sequence(action.get("exact_change")):
                    lines.append("  - Exact change:")
                    for step in _sequence(action.get("exact_change"))[:3]:
                        if _string(step):
                            lines.append(f"    - {_string(step)}")
                qa_text = _strip_known_prefix(_string(action.get("verification_qa")), ("QA:",))
                next_run_text = _strip_known_prefix(_string(action.get("verification_geo")), ("Next run:",))
                outcome_text = _strip_known_prefix(_string(action.get("verification_outcome")), ("Watch", "Outcome tracking:"))
                for label, value in (
                    ("Example implementation", _string(action.get("example_implementation"))),
                    ("Acceptance criteria", _string(action.get("acceptance_criteria"))),
                    ("QA", qa_text),
                    ("Next run", next_run_text),
                    ("Outcome tracking", outcome_text),
                    ("Expected GEO effect", _string(action.get("expected_geo_effect"))),
                    ("Confidence", _string(action.get("confidence"))),
                ):
                    if value:
                        lines.append(f"  - {label}: {value}")
                lines.append("")
        return lines
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
    evidence_completeness = _mapping(section.get("evidence_completeness"))
    if evidence_completeness:
        score = _string(evidence_completeness.get("score"))
        label = _string(evidence_completeness.get("label"))
        if label and score:
            lines.append(f"- Evidence completeness: {label} ({score}/100)")
        elif label:
            lines.append(f"- Evidence completeness: {label}")
        reason = _string(evidence_completeness.get("reason"))
        if reason:
            lines.append(f"- Evidence completeness note: {reason}")
    change_since_last_run = _mapping(section.get("delta_summary")) or _mapping(section.get("change_since_last_run"))
    if change_since_last_run:
        lines.append("### Change Since Last Run")
        lines.append("")
        comparable = change_since_last_run.get("comparable")
        if comparable is not None:
            lines.append(f"- Comparable: {'Yes' if comparable else 'No'}")
        summary = _string(change_since_last_run.get("summary"))
        if summary:
            lines.append(f"- Summary: {summary}")
        delta_items = _sequence(change_since_last_run.get("what_changed")) or _sequence(change_since_last_run.get("delta_items"))
        if delta_items:
            lines.append("- What changed:")
            for item in delta_items:
                if not isinstance(item, Mapping):
                    continue
                label = _string(item.get("label")) or _label_text(item.get("metric"))
                current = _string(item.get("current"))
                previous = _string(item.get("previous"))
                delta = _string(item.get("delta"))
                if label and current and previous and delta:
                    prefix = "+" if not delta.startswith("-") else ""
                    lines.append(f"  - {label}: {previous} -> {current} ({prefix}{delta})")
                    continue
                direction = _string(item.get("direction"))
                if label and direction and delta:
                    lines.append(f"  - {label}: {direction} {delta.lstrip('+')}")
        lines.append("")
        upgrade_note = _string(change_since_last_run.get("what_upgrades_this"))
        if upgrade_note:
            lines.append(f"- What upgrades this: {upgrade_note}")
    official_sources = _sequence(section.get("official_sources"))
    if official_sources:
        lines.append("- Official sources:")
        for item in official_sources:
            if isinstance(item, Mapping):
                lines.append(
                    f"  - {_string(item.get('title'))}: {_string(item.get('url'))}"
                )
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

    action_plan = _mapping(sections.get("action_plan"))
    if _string(action_plan.get("mode")) == "singleton":
        lines.extend(["", f"## {_string(action_plan.get('title')) or 'Website Improvement Plan'}", ""])
        lines.extend(_render_actions(action_plan))
    else:
        _append_heading(lines, _string(action_plan.get("title")) or "Website Improvement Plan")
        lines.extend(_render_actions(action_plan))

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

    proof_appendix = _mapping(sections.get("proof_appendix"))
    _append_heading(lines, "Proof Appendix")
    lines.extend(_render_proof_appendix(proof_appendix))

    return "\n".join(lines).strip() + "\n"
