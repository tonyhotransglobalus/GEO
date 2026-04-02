from __future__ import annotations

from .reporting import normalize_report_sections, report_sections_to_markdown


def _sequence(value):
    if isinstance(value, (list, tuple)):
        return list(value)
    return []


def _render_combined_client_report(client_sections: dict) -> list[str]:
    lines: list[str] = []

    cover = client_sections.get("cover_verdict", {})
    lines.extend(["---", "", "## Cover + Verdict", ""])
    if cover:
        lines.extend(
            [
                cover.get("one_sentence_verdict", ""),
                "",
                f"- Verdict: {cover.get('verdict_status', '')}",
                f"- How much to trust this read (confidence): {cover.get('overall_confidence', '')}",
                f"- How much evidence this run captured (sample completeness): {cover.get('sample_completeness', '')}",
                f"- Primary domain: {cover.get('primary_domain', '')}",
                "",
            ]
        )
        if cover.get("confidence_reason"):
            lines.append(f"- Why this trust level was assigned: {cover.get('confidence_reason', '')}")
            lines.append("")

    decision = client_sections.get("decision_summary", {})
    lines.extend(["---", "", "## Decision Summary", ""])
    if decision.get("leadership_takeaway"):
        lines.extend([decision["leadership_takeaway"], ""])
    for title, items in (
        ("What Is Working", decision.get("what_is_working", [])),
        ("What Is Not Working", decision.get("what_is_not_working", [])),
    ):
        lines.extend([f"### {title}", ""])
        if items:
            for item in items:
                lines.append(f"- {item}")
        else:
            lines.append("- None identified.")
        lines.append("")
    for title, items, kind in (
        ("Top Blockers", decision.get("top_blockers", []), "blocker"),
        ("Top Opportunities", decision.get("top_opportunities", []), "opportunity"),
        ("Top 3 Actions", decision.get("top_3_actions", []), "action"),
    ):
        lines.extend([f"### {title}", ""])
        if items:
            for item in items:
                if not isinstance(item, dict):
                    lines.append(f"- {item}")
                    continue
                if kind == "blocker":
                    detail = item.get("business_impact", "")
                    confidence = item.get("confidence", "")
                    text = f"- {item.get('title', '')}"
                    if detail:
                        text += f": {detail}"
                    if confidence:
                        text += f" Trust level (confidence): {confidence}."
                    lines.append(text)
                elif kind == "opportunity":
                    detail = item.get("why_now", "")
                    outcome = item.get("expected_outcome", "")
                    text = f"- {item.get('title', '')}"
                    if detail:
                        text += f": {detail}"
                    if outcome:
                        text += f" Expected outcome: {outcome}"
                    lines.append(text)
                else:
                    text = f"- {item.get('action', '')}"
                    owner = item.get("owner", "")
                    outcome = item.get("expected_outcome", "")
                    if owner:
                        text += f" Owner: {owner}."
                    if outcome:
                        text += f" Expected outcome: {outcome}"
                    lines.append(text)
        else:
            lines.append("- None identified.")
        lines.append("")

    score_definitions = client_sections.get("score_definitions", {})
    lines.extend(["---", "", "## What The Scores Mean", ""])
    lines.extend(
        [
            "Plain-English first. Formal GEO terms stay in parentheses so the report still stands up under challenge.",
            "",
        ]
    )
    term_guide = _sequence(score_definitions.get("term_guide"))
    if term_guide:
        lines.extend(["### Term Guide", ""])
        for item in term_guide:
            if isinstance(item, dict):
                lines.append(f"- {item.get('term', '')}: {item.get('plain_english', '')}")
        lines.append("")
    weighting = score_definitions.get("weighting", {})
    if isinstance(weighting, dict) and (weighting.get("summary") or weighting.get("components")):
        lines.extend(["### Scoring And Weighting", ""])
        if weighting.get("summary"):
            lines.extend([weighting.get("summary", ""), ""])
        for component in _sequence(weighting.get("components")):
            if isinstance(component, dict):
                lines.append(
                    f"- {component.get('metric_name', '')}: {component.get('weight', '')}%."
                    f" Why this weight exists: {component.get('why_this_weight_exists', '')}"
                )
        lines.append("")
    for metric in _sequence(score_definitions.get("metrics")):
        if not isinstance(metric, dict):
            continue
        evidence = ", ".join(_sequence(metric.get("primary_evidence_used")))
        lines.extend(
            [
                f"### {metric.get('metric_name', '')}",
                "",
                f"- Score: {metric.get('score', '')}/100",
                f"- What it means: {metric.get('plain_english_definition', '')}",
                f"- Why this score landed here: {metric.get('why_this_score_landed_here', '')}",
                f"- What good looks like: {metric.get('what_good_looks_like', '')}",
                f"- Main evidence used: {evidence}",
                f"- How much to trust this score (confidence): {metric.get('confidence', '')}",
                "",
            ]
        )

    lines.extend(["---", "", "## Priority Findings", ""])
    findings = _sequence(client_sections.get("priority_findings", {}).get("items"))
    if findings:
        for item in findings:
            if not isinstance(item, dict):
                continue
            affected = item.get("affected_pages_or_queries", [])
            if isinstance(affected, list):
                affected_text = ", ".join(str(value) for value in affected if value)
            else:
                affected_text = str(affected or "")
            lines.extend(
                [
                    f"### {item.get('title', '')}",
                    "",
                    f"- Severity: {item.get('severity', '')}",
                    f"- What we found: {item.get('plain_english_summary', '')}",
                    f"- What we observed: {item.get('what_we_observed', '')}",
                    f"- Why it matters: {item.get('why_it_matters_to_business', '')}",
                    f"- What proves it: {item.get('proof', '')}",
                    f"- Marketing next step: {item.get('marketing_action', '')}",
                    f"- Engineering next step: {item.get('engineering_action', '')}",
                    f"- Success check: {item.get('success_metric', '')}",
                    f"- Affected pages or queries: {affected_text}",
                    f"- Evidence type (evidence class): {item.get('evidence_class', '')}",
                    f"- How much to trust this finding (confidence): {item.get('confidence', '')}",
                    f"- Counterpoint / limitation: {item.get('counterpoint_or_limitation', '')}",
                    "",
                ]
            )
    else:
        lines.extend(["No priority findings captured.", ""])

    lines.extend(["---", "", "## Competitive Benchmark", ""])
    benchmark = client_sections.get("competitive_benchmark", {})
    if benchmark.get("summary"):
        lines.extend([benchmark["summary"], ""])
    rows = _sequence(benchmark.get("benchmark_rows"))
    if rows:
        for row in rows:
            if isinstance(row, dict):
                lines.append(f"- {row.get('competitor_name', row.get('label', ''))}: {row.get('our_gap', row.get('summary', ''))}")
        lines.append("")

    lines.extend(["---", "", "## Platform Breakdown", ""])
    for platform in _sequence(client_sections.get("platform_breakdown", {}).get("platforms")):
        if not isinstance(platform, dict):
            continue
        actions = _sequence(platform.get("recommended_actions"))
        lines.extend(
            [
                f"### {platform.get('platform', '')}",
                "",
                f"- Documented behavior: {platform.get('documented_behavior', '')}",
                f"- Observed site status: {platform.get('observed_site_status', '')}",
                f"- Visibility read: {platform.get('observed_visibility_status', '')}",
                f"- How much to trust this platform read (confidence): {platform.get('confidence', '')}",
                f"- Cautious inference: {platform.get('cautious_inference', '')}",
            ]
        )
        if actions:
            lines.append(f"- What to do next: {' '.join(str(action) for action in actions if action)}")
        lines.append("")

    lines.extend(["---", "", "## Prompt And Query Proof", ""])
    sampling_note = client_sections.get("prompt_query_proof", {}).get("sampling_note", "")
    if sampling_note:
        lines.extend([sampling_note, ""])
    proof_rows = _sequence(client_sections.get("prompt_query_proof", {}).get("rows"))
    if proof_rows:
        for row in proof_rows:
            if isinstance(row, dict):
                lines.append(f"- {row.get('query_or_prompt', '')}: {row.get('why_we_lost_or_won', '')}")
        lines.append("")
    else:
        lines.extend(["No prompt-proof rows captured.", ""])

    lines.extend(["---", "", "## Page And Source Evidence", ""])
    page_rows = _sequence(client_sections.get("page_source_evidence", {}).get("priority_pages"))
    source_rows = _sequence(client_sections.get("page_source_evidence", {}).get("source_domains"))
    if page_rows:
        lines.extend(["### Priority Pages", ""])
        for row in page_rows:
            if isinstance(row, dict):
                lines.append(
                    f"- {row.get('page_url', '')}: {row.get('recommended_fix', '')}"
                )
        lines.append("")
    if source_rows:
        lines.extend(["### Source Domains", ""])
        for row in source_rows:
            if isinstance(row, dict):
                lines.append(f"- {row.get('domain', '')}: {row.get('gap_or_advantage', '')}")
        lines.append("")

    lines.extend(["---", "", "## 30/60/90 Action Plan", ""])
    actions = _sequence(client_sections.get("action_plan_30_60_90", {}).get("actions"))
    if actions:
        for action in actions:
            if isinstance(action, dict):
                expected_outcome = str(action.get("expected_outcome", "")).rstrip(".")
                success_metric = str(action.get("success_metric", "")).rstrip(".")
                success_fragment = (
                    f"Success check: {success_metric}. "
                    if success_metric and success_metric != expected_outcome
                    else ""
                )
                lines.append(
                    f"- {action.get('time_horizon', '')}: {action.get('action', '')} "
                    f"Owner: {action.get('owner', '')}. Effort: {action.get('effort', '')}. "
                    f"Expected outcome: {expected_outcome}. "
                    + success_fragment
                    + f"Trust level (confidence): {action.get('confidence', '')}."
                )
        lines.append("")
    else:
        lines.extend(["No structured actions captured.", ""])

    lines.extend(["---", "", "## Technical Proof Appendix", ""])
    appendix = client_sections.get("technical_proof_appendix", {})
    methodology = appendix.get("methodology", {}) if isinstance(appendix, dict) else {}
    if methodology.get("summary"):
        lines.extend([methodology["summary"], ""])
    if methodology.get("confidence_note"):
        lines.append(f"- Trust note (confidence): {methodology.get('confidence_note')}")
    if methodology.get("provenance_note"):
        lines.append(f"- Provenance: {methodology.get('provenance_note')}")
    if methodology.get("official_sources"):
        official_sources = ", ".join(_sequence(methodology.get("official_sources")))
        lines.append(f"- Official sources used: {official_sources}")
    if methodology:
        lines.append("")
    for title, items in (
        ("Crawl And Fetch Evidence", appendix.get("crawl_and_fetch_evidence") or []),
        ("Robots And Bot Access", appendix.get("robots_and_bot_access") or []),
        ("DOM And Heading Proof", appendix.get("dom_and_heading_proof") or []),
        ("Schema Proof", appendix.get("schema_proof") or []),
        ("Source Inventory", appendix.get("source_inventory") or []),
    ):
        lines.extend([f"### {title}", ""])
        if items:
            for item in items:
                if isinstance(item, dict):
                    crawler = item.get("crawler", "")
                    platform = item.get("platform", "")
                    status = item.get("status", "")
                    recommendation = item.get("recommendation", "")
                    label = crawler or item.get("title", "") or item.get("term", "")
                    if label and platform:
                        label = f"{label} ({platform})"
                    text = f"- {label}: {status}." if label else f"- {status}."
                    if recommendation:
                        text += f" Recommendation: {recommendation}"
                    lines.append(text)
                else:
                    lines.append(f"- {item}")
        else:
            lines.append("- None identified.")
        lines.append("")
    limitations = appendix.get("limitations", {}) if isinstance(appendix, dict) else {}
    if isinstance(limitations, dict) and limitations.get("limitations_note"):
        lines.append(f"- Limitations: {limitations.get('limitations_note')}")
        lines.append("")

    return lines


def render_markdown_report(data: dict) -> str:
    rescience = data.get("rescience_pass", {})
    report_sections = normalize_report_sections(data.get("report_sections"))
    client_sections = data.get("client_report_sections", {})
    has_combined_client_contract = isinstance(client_sections, dict) and "cover_verdict" in client_sections

    lines = [
        f"# GEO Strategy Report: {data['brand_name']}",
        "",
        f"**Audit Date:** {data['date']}",
        f"**Primary URL:** {data['url']}",
        "",
    ]

    if report_sections and not has_combined_client_contract:
        lines.extend(["---", "", report_sections_to_markdown(report_sections).strip(), ""])

    if has_combined_client_contract:
        lines.extend(_render_combined_client_report(client_sections))
        return "\n".join(lines).strip() + "\n"

    narrative = client_sections.get("strategic_narrative")
    if isinstance(narrative, dict):
        lines.extend(["---", "", f"## {narrative.get('title', 'Strategic Narrative')}", ""])
        lines.extend([narrative.get("content", ""), ""])

    if data["findings"]:
        lines.extend(["---", "", "## Key Findings", ""])
        for finding in data["findings"]:
            summary = finding.get("summary") or finding.get("description", "")
            lines.extend(
                [
                    f"### [{finding['severity'].upper()}] {finding['title']}",
                    "",
                    summary,
                    "",
                    f"**Why this matters to leadership:** {finding.get('leadership_impact', 'Not provided.')}",
                    "",
                    f"**What marketing should do:** {finding.get('marketing_action', 'Not provided.')}",
                    "",
                    f"**What dev should change:** {finding.get('developer_action', 'Not provided.')}",
                    "",
                    f"**Observed evidence:** {finding.get('observed_evidence', 'Not provided.')}",
                    "",
                ]
            )
    else:
        lines.extend(["---", "", "## Key Findings", ""])
        lines.extend(["No critical findings recorded.", ""])

    lines.extend(["---", "", "## Prioritized Action Plan", ""])
    for title, items in (
        ("Quick Wins (This Week)", data.get("quick_wins", [])),
        ("Medium-Term Improvements (This Month)", data.get("medium_term", [])),
        ("Strategic Initiatives (This Quarter)", data.get("strategic", [])),
    ):
        lines.extend([f"### {title}", ""])
        if items:
            for item in items:
                lines.append(f"- {item}")
        else:
            lines.append("- None identified.")
        lines.append("")

    if rescience:
        lines.extend(["---", "", "## ReScience Optimization Pass", ""])
        if rescience.get("summary"):
            lines.extend([rescience["summary"], ""])

        priority_actions = rescience.get("priority_actions", {})
        if priority_actions:
            for priority in ("P0", "P1", "P2"):
                lines.extend([f"### {priority} Priorities", ""])
                items = priority_actions.get(priority, [])
                if items:
                    for item in items:
                        lines.append(f"- {item}")
                else:
                    lines.append("- None identified.")
                lines.append("")

        if rescience.get("platform_guidance"):
            lines.extend(["### Platform Guidance", ""])
            for platform, items in rescience["platform_guidance"].items():
                lines.append(f"#### {platform}")
                lines.append("")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")

        if rescience.get("geo_methods"):
            lines.extend(["### Recommended GEO Methods", ""])
            for method in rescience["geo_methods"]:
                recommendation = method.get("recommendation", "")
                suffix = f": {recommendation}" if recommendation else ""
                lines.append(
                    f"- **{method['method']}** ({method['impact']}){suffix}"
                )
            lines.append("")

    guidance = client_sections.get("platform_guidance")
    if isinstance(guidance, dict):
        lines.extend(["---", "", f"## {guidance.get('title', 'Platform Guidance 2026')}", ""])
        rules = guidance.get("key_rules", [])
        if rules:
            lines.extend(["### Strategic Rules", ""])
            for rule in rules:
                lines.append(f"- {rule}")
            lines.append("")
        sources = guidance.get("official_sources", [])
        if sources:
            lines.extend(["### Verifiable Sources", ""])
            for source in sources:
                lines.append(f"- {source}")
            lines.append("")
        ref = guidance.get("reference_citation")
        if ref:
            lines.append(f"*{ref}*")
            lines.append("")

    return "\n".join(lines).strip() + "\n"
