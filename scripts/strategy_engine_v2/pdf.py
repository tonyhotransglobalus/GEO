from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _paragraph(value: Any) -> str:
    return escape(_text(value)).replace("\n", "<br/>")


def _title_case_status(value: Any) -> str:
    return _text(value).replace("-", " ").title()


def _normalized_text(value: Any) -> str:
    return _text(value).strip().lower()


def _label_text(value: Any) -> str:
    text = _text(value).replace("_", " ")
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _strip_known_prefix(value: Any, prefixes: tuple[str, ...]) -> str:
    text = _text(value)
    lowered = text.lower()
    for prefix in prefixes:
        marker = prefix.lower()
        if lowered.startswith(marker):
            return text[len(prefix):].strip()
    return text


def _unique_nonempty(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        text = _text(item)
        if not text:
            continue
        marker = text.lower()
        if marker in seen:
            continue
        seen.add(marker)
        ordered.append(text)
    return ordered


def _short_horizon_label(value: Any) -> str:
    text = _normalized_text(value)
    if text.startswith("30"):
        return "30 Days"
    if text.startswith("60"):
        return "60 Days"
    if text.startswith("90"):
        return "90 Days"
    return _title_case_status(value)


def _compact_action_groups(actions: list[Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = {"30 Days": [], "60 Days": [], "90 Days": []}
    for item in actions:
        if not isinstance(item, Mapping):
            continue
        label = _short_horizon_label(item.get("time_horizon"))
        grouped.setdefault(label, []).append(dict(item))
    ordered_groups: list[tuple[str, list[dict[str, Any]]]] = []
    for label in ("30 Days", "60 Days", "90 Days"):
        rows = grouped.get(label) or []
        if rows:
            ordered_groups.append((label, rows[:3]))
    for label, rows in grouped.items():
        if label in {"30 Days", "60 Days", "90 Days"} or not rows:
            continue
        ordered_groups.append((label, rows[:3]))
    return ordered_groups


def _compact_bot_access(lines: list[str]) -> list[str]:
    keep_accessible: list[str] = []
    review_logs: list[str] = []
    other_notes: list[str] = []
    for line in lines:
        text = _text(line)
        if not text:
            continue
        bot_name = text.split(":", 1)[0].strip()
        normalized = text.lower()
        if "recommendation: keep accessible" in normalized:
            keep_accessible.append(bot_name)
        elif "review app fetch behavior and logs" in normalized:
            review_logs.append(bot_name)
        else:
            other_notes.append(text)
    summary: list[str] = []
    if keep_accessible:
        summary.append(f"Allowed by default and worth keeping accessible: {', '.join(keep_accessible)}.")
    if review_logs:
        summary.append(f"Review app-style fetch behavior and logs separately for: {', '.join(review_logs)}.")
    summary.extend(other_notes[:2])
    return summary


def _evidence_highlight(item: Mapping[str, Any]) -> str:
    evidence_type = _label_text(item.get("evidence_type"))
    summary = _text(item.get("summary")) or _text(item.get("normalized_summary"))
    if evidence_type and summary:
        return f"{evidence_type}: {summary}"
    return summary or evidence_type


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="V2Title",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324d"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V2Subtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#486581"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V2Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f2940"),
            spaceBefore=12,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V2Subsection",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#17324d"),
            spaceBefore=7,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V2Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.8,
            leading=13.4,
            textColor=colors.HexColor("#243b53"),
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V2Small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#486581"),
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V2Detail",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.3,
            leading=10.8,
            leftIndent=12,
            textColor=colors.HexColor("#486581"),
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V2Bullet",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            leftIndent=12,
            firstLineIndent=-8,
            textColor=colors.HexColor("#243b53"),
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V2TableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.3,
            leading=10,
            textColor=colors.HexColor("#102a43"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="V2TableCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.3,
            leading=10,
            textColor=colors.HexColor("#243b53"),
        )
    )
    return styles


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#486581"))
    canvas.drawString(doc.leftMargin, 20, "GEO Strategy Report V2")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 20, f"Page {doc.page}")
    canvas.restoreState()


def _append_bullets(elements: list[Any], items: list[str], styles) -> None:
    for item in items:
        text = _text(item)
        if text:
            elements.append(Paragraph(f"• {_paragraph(text)}", styles["V2Bullet"]))


def _append_section_header(elements: list[Any], title: str, styles) -> None:
    elements.append(Paragraph(_paragraph(title), styles["V2Section"]))
    elements.append(HRFlowable(width="100%", thickness=1.4, color=colors.HexColor("#d9e2ec"), spaceAfter=7))


def _action_chip_line(action: Mapping[str, Any]) -> str:
    parts = [
        f"Priority: {_text(action.get('priority'))}" if _text(action.get("priority")) else "",
        f"Owner: {_text(action.get('owner'))}" if _text(action.get("owner")) else "",
    ]
    role_tags = [_text(item) for item in _sequence(action.get("role_tags")) if _text(item)]
    if role_tags:
        parts.append("Roles: " + ", ".join(role_tags))
    if _text(action.get("confidence")):
        parts.append(f"Confidence: {_text(action.get('confidence'))}")
    return " | ".join(part for part in parts if part)


def _render_action_cards(elements: list[Any], actions: list[dict[str, Any]], styles, detail: str = "summary") -> None:
    for action in actions:
        is_full = detail == "full"
        card: list[Any] = [Paragraph(_paragraph(_text(action.get("title"))), styles["V2Subsection"])]
        chip_line = _action_chip_line(action)
        if chip_line:
            card.append(Paragraph(_paragraph(chip_line), styles["V2Small"]))
        summary_fields = (
            ("Exact location", action.get("exact_location")),
            ("Observed evidence", action.get("observed_evidence")),
            ("Expected GEO effect", action.get("expected_geo_effect")),
        )
        full_fields = summary_fields + (
            ("Acceptance criteria", action.get("acceptance_criteria")),
            ("Example implementation", action.get("example_implementation")),
        )
        for label, value in (full_fields if is_full else summary_fields):
            text = _text(value)
            if text:
                card.append(Paragraph(f"<b>{label}:</b> {_paragraph(text)}", styles["V2Body"]))
        change_steps = [_text(step) for step in _sequence(action.get("exact_change")) if _text(step)]
        if change_steps:
            card.append(Paragraph("<b>Exact change:</b>", styles["V2Body"]))
            for step in change_steps[: (3 if is_full else 2)]:
                card.append(Paragraph(f"• {_paragraph(step)}", styles["V2Bullet"]))
        if is_full:
            qa_text = _strip_known_prefix(_text(action.get("verification_qa")), ("QA:",))
            if qa_text:
                card.append(Paragraph(f"<b>QA:</b> {_paragraph(qa_text)}", styles["V2Detail"]))
            next_run_text = _strip_known_prefix(_text(action.get("verification_geo")), ("Next run:",))
            if next_run_text:
                card.append(Paragraph(f"<b>Next run:</b> {_paragraph(next_run_text)}", styles["V2Detail"]))
            outcome_text = _strip_known_prefix(
                _text(action.get("verification_outcome")),
                ("Watch", "Outcome tracking:",),
            )
            if outcome_text:
                card.append(Paragraph(f"<b>Outcome tracking:</b> {_paragraph(outcome_text)}", styles["V2Detail"]))
        card.append(Spacer(1, 4))
        card.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#d9e2ec"), spaceBefore=0, spaceAfter=6))
        elements.extend(card)


def _render_singleton_action(elements: list[Any], action: Mapping[str, Any], styles) -> None:
    _render_action_cards(elements, [dict(action)], styles, detail="full")
    why_lead = _text(action.get("why_this_is_the_lead_fix"))
    if why_lead:
        elements.append(Paragraph(f"<b>Why this is the lead fix:</b> {_paragraph(why_lead)}", styles["V2Body"]))
    confidence_reason = _text(action.get("confidence_reason"))
    if confidence_reason:
        elements.append(Paragraph(f"<b>Confidence reason:</b> {_paragraph(confidence_reason)}", styles["V2Body"]))
    success_metric = _text(action.get("success_metric"))
    if success_metric:
        elements.append(Paragraph(f"<b>Success metric:</b> {_paragraph(success_metric)}", styles["V2Body"]))
    proof_packet = [_text(item) for item in _sequence(action.get("proof_packet")) if _text(item)]
    if proof_packet:
        elements.append(Paragraph("Supporting Proof", styles["V2Subsection"]))
        for item in proof_packet[:3]:
            elements.append(Paragraph(f"• {_paragraph(item)}", styles["V2Bullet"]))


def _render_watchlist(elements: list[Any], watchlist: list[dict[str, Any]], styles) -> None:
    for item in watchlist:
        elements.append(Paragraph(_paragraph(_text(item.get("title"))), styles["V2Subsection"]))
        for label, value in (
            ("Evidence grade", item.get("evidence_grade")),
            ("Why not recommended yet", item.get("why_not_recommended_yet")),
            ("What upgrades this", item.get("what_upgrades_this")),
            ("Strongest evidence", item.get("strongest_evidence")),
        ):
            text = _text(value)
            if text:
                elements.append(Paragraph(f"<b>{label}:</b> {_paragraph(text)}", styles["V2Body"]))
        elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#d9e2ec"), spaceBefore=0, spaceAfter=6))


def _table(rows: list[list[Any]], widths: list[int]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4f8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102a43")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bcccdc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
            ]
        )
    )
    return table


def _table_rows(rows: list[list[str]], styles) -> list[list[Any]]:
    converted: list[list[Any]] = []
    for row_index, row in enumerate(rows):
        style_name = "V2TableHeader" if row_index == 0 else "V2TableCell"
        converted.append(
            [Paragraph(_paragraph(cell), styles[style_name]) for cell in row]
        )
    return converted


def generate_v2_pdf_report(payload: Mapping[str, Any], output_path: str | Path = "GEO-STRATEGY-REPORT-V2.pdf") -> str:
    payload_map = _mapping(payload)
    manifest = _mapping(payload_map.get("manifest"))
    evidence = _mapping(payload_map.get("evidence"))
    adjudication = _mapping(payload_map.get("adjudication"))
    report_sections = _mapping(payload_map.get("report_sections"))
    audit_data = _mapping(payload_map.get("audit_data"))

    styles = _build_styles()
    output = str(output_path)
    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        topMargin=48,
        bottomMargin=40,
        leftMargin=42,
        rightMargin=42,
        title="GEO Strategy Report V2",
    )
    elements: list[Any] = []

    leadership = _mapping(report_sections.get("leadership_summary"))
    score_explanations = _mapping(report_sections.get("score_explanations"))
    priority_findings = _mapping(report_sections.get("priority_findings"))
    benchmark = _mapping(report_sections.get("competitive_benchmark"))
    platforms = _mapping(report_sections.get("platform_breakdown"))
    page_source = _mapping(report_sections.get("page_source_evidence"))
    action_plan = _mapping(report_sections.get("action_plan"))
    proof = _mapping(report_sections.get("proof_appendix"))

    generated_label = datetime.now().strftime("%B %d, %Y")
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("GEO Strategy Report V2", styles["V2Title"]))
    elements.append(Paragraph(_paragraph(_text(audit_data.get("brand_name")) or _text(manifest.get("target_domain"))), styles["V2Subtitle"]))
    elements.append(
        Paragraph(
            _paragraph(
                " | ".join(
                    part
                    for part in (
                        _text(manifest.get("target_url")),
                        f"Generated {generated_label}",
                        f"Mode: {_text(manifest.get('mode')) or 'script-only'}",
                    )
                    if part
                )
            ),
            styles["V2Subtitle"],
        )
    )
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#17324d"), spaceBefore=6, spaceAfter=10))

    _append_section_header(elements, "Leadership Summary", styles)
    readiness_label = _text(leadership.get("readiness_label")) or ""
    readiness_value = _text(leadership.get("readiness_value")) or ""
    completeness_label = _text(leadership.get("completeness_label")) or _text(leadership.get("trust_label")) or ""
    completeness_value = _text(leadership.get("completeness_value")) or _text(leadership.get("trust_value")) or "Low"
    leadership_lines = []
    if readiness_label:
        leadership_lines.append(f"{readiness_label}: {readiness_value}")
    if completeness_label:
        leadership_lines.append(f"{completeness_label}: {completeness_value}")
    elif completeness_value:
        leadership_lines.append(f"How much to trust this: {completeness_value}")
    leadership_lines.extend(_sequence(leadership.get("summary")))
    _append_bullets(elements, [item for item in leadership_lines if _text(item)], styles)
    visible_reason = _text(leadership.get("visible_reason"))
    if visible_reason:
        elements.append(Paragraph(f"<b>Current constraint:</b> {_paragraph(visible_reason)}", styles["V2Body"]))
    trust_note = _text(leadership.get("trust_note"))
    if trust_note:
        elements.append(Paragraph(_paragraph(trust_note), styles["V2Body"]))
    top_actions = [
        dict(item)
        for item in _sequence(action_plan.get("top_actions"))
        if isinstance(item, Mapping)
    ]
    action_mode = _text(action_plan.get("mode"))
    if action_mode in {"", "multi_action"} and len(top_actions) > 1:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("Top Website Fixes", styles["V2Subsection"]))
        _render_action_cards(elements, top_actions[:3], styles)
    elements.append(Spacer(1, 10))

    _append_section_header(elements, _text(action_plan.get("title")) or "Website Improvement Plan", styles)
    if action_mode == "singleton":
        primary_action = _mapping(action_plan.get("primary_action"))
        if primary_action:
            _append_section_header(elements, "Primary Website Fix This Run", styles)
            _render_singleton_action(elements, primary_action, styles)
            rollout_sequence = [_text(item) for item in _sequence(primary_action.get("rollout_sequence")) if _text(item)]
            if rollout_sequence:
                _append_section_header(elements, "Rollout Map", styles)
                _append_bullets(elements, rollout_sequence, styles)
        watchlist = [dict(item) for item in _sequence(action_plan.get("watchlist")) if isinstance(item, Mapping)]
        if watchlist:
            _append_section_header(elements, "Not Recommending Yet", styles)
            _render_watchlist(elements, watchlist, styles)
    else:
        grouped_actions = [
            dict(group)
            for group in _sequence(action_plan.get("groups"))
            if isinstance(group, Mapping)
        ]
        if grouped_actions:
            for group in grouped_actions:
                elements.append(Paragraph(_paragraph(_text(group.get("label"))), styles["V2Subsection"]))
                _render_action_cards(
                    elements,
                    [dict(item) for item in _sequence(group.get("actions")) if isinstance(item, Mapping)],
                    styles,
                    detail="full",
                )
        else:
            grouped_actions = _compact_action_groups(_sequence(action_plan.get("actions")))
            if grouped_actions:
                for horizon_label, rows in grouped_actions:
                    elements.append(Paragraph(horizon_label, styles["V2Subsection"]))
                    for item in rows:
                        action_text = _text(item.get("action"))
                        owner = _text(item.get("owner"))
                        outcome = _text(item.get("expected_outcome"))
                        visible_reason = _text(item.get("visible_reason"))
                        action_block: list[Any] = []
                        if action_text:
                            action_block.append(Paragraph(f"• {_paragraph(action_text)}", styles["V2Bullet"]))
                        if owner:
                            action_block.append(Paragraph(f"<b>Owner:</b> {_paragraph(owner)}", styles["V2Detail"]))
                        if visible_reason:
                            action_block.append(Paragraph(f"<b>Why now:</b> {_paragraph(visible_reason)}", styles["V2Detail"]))
                        if outcome:
                            action_block.append(Paragraph(f"<b>Expected outcome:</b> {_paragraph(outcome)}", styles["V2Detail"]))
                        if action_block:
                            action_block.append(Spacer(1, 2))
                            elements.extend(action_block)
            else:
                elements.append(Paragraph("No actions were captured in this run.", styles["V2Body"]))

    _append_section_header(elements, "Priority Findings", styles)
    for finding in _sequence(priority_findings.get("findings")):
        if not isinstance(finding, Mapping):
            continue
        title = _text(finding.get("title")) or _text(finding.get("section")).replace("_", " ").title()
        summary = _text(finding.get("summary"))
        visible_reason = _text(finding.get("visible_reason"))
        problem_statement = summary or visible_reason
        observation = visible_reason if _normalized_text(visible_reason) != _normalized_text(summary) else ""
        supporting_lines = _unique_nonempty(
            [line for line in _sequence(finding.get("supporting_evidence")) if _text(line)]
        )
        if not supporting_lines:
            for item in _sequence(finding.get("evidence_items"))[:2]:
                if not isinstance(item, Mapping):
                    continue
                parts = [
                    _text(item.get("source_class")).replace("_", " "),
                    _text(item.get("observed_vs_inferred")),
                    _text(item.get("url_or_domain")),
                    _text(item.get("normalized_summary")),
                ]
                rendered = " - ".join(part for part in parts if part)
                if rendered:
                    supporting_lines.append(rendered)
        confidence = _text(finding.get("confidence"))
        confidence_reason = _text(finding.get("confidence_reason"))
        success_metric = _text(finding.get("success_metric"))
        limitations = _text(finding.get("limitations"))
        finding_block: list[Any] = [
            Paragraph(
                f"{_paragraph(title)} <font color='#486581'>({_paragraph(_title_case_status(finding.get('status')) or 'Omitted')})</font>",
                styles["V2Subsection"],
            )
        ]
        for label, value in (
            ("What's wrong", problem_statement),
            ("Why it matters", finding.get("leadership_impact")),
        ):
            text = _text(value)
            if text:
                finding_block.append(Paragraph(f"<b>{label}:</b> {_paragraph(text)}", styles["V2Body"]))
        if observation:
            finding_block.append(Paragraph(f"<b>What we saw:</b> {_paragraph(observation)}", styles["V2Body"]))
        claim_source = _label_text(finding.get("claim_source_class"))
        if claim_source:
            finding_block.append(Paragraph(f"<b>Claim source:</b> {_paragraph(claim_source)}", styles["V2Body"]))
        evidence_grade = _label_text(finding.get("evidence_grade"))
        if evidence_grade:
            finding_block.append(Paragraph(f"<b>Evidence grade:</b> {_paragraph(evidence_grade)}", styles["V2Body"]))
        related_action_title = _text(finding.get("related_action_title"))
        if related_action_title:
            finding_block.append(Paragraph(f"<b>Related website fix:</b> {_paragraph(related_action_title)}", styles["V2Body"]))
        if supporting_lines:
            finding_block.append(Paragraph("<b>Evidence from this run:</b>", styles["V2Small"]))
            for line in supporting_lines[:3]:
                finding_block.append(Paragraph(f"• {_paragraph(line)}", styles["V2Small"]))
        if not related_action_title:
            next_steps = _unique_nonempty(
                [
                    f"Marketing: {_text(finding.get('marketing_action'))}",
                    f"Engineering: {_text(finding.get('engineering_action'))}",
                ]
            )
            if next_steps:
                finding_block.append(Paragraph("<b>What to do next:</b>", styles["V2Body"]))
                for line in next_steps[:2]:
                    if line.endswith(":"):
                        continue
                    finding_block.append(Paragraph(f"• {_paragraph(line)}", styles["V2Bullet"]))
        what_upgrades_this = _text(finding.get("what_upgrades_this"))
        if what_upgrades_this:
            finding_block.append(Paragraph(f"<b>What upgrades this:</b> {_paragraph(what_upgrades_this)}", styles["V2Body"]))
        if confidence:
            confidence_line = confidence
            if confidence_reason:
                confidence_line = f"{confidence}. {confidence_reason}"
            finding_block.append(Paragraph(f"<b>Confidence:</b> {_paragraph(confidence_line)}", styles["V2Body"]))
        if success_metric:
            finding_block.append(Paragraph(f"<b>How we will know this improved:</b> {_paragraph(success_metric)}", styles["V2Body"]))
        if limitations:
            finding_block.append(Paragraph(f"<b>Limitations:</b> {_paragraph(limitations)}", styles["V2Body"]))
        finding_block.append(Spacer(1, 6))
        finding_block.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#d9e2ec"), spaceBefore=0, spaceAfter=6))
        elements.extend(finding_block)

    _append_section_header(elements, "Score Snapshot", styles)
    note = _text(score_explanations.get("plain_english_note"))
    if note:
        elements.append(
            Paragraph(
                _paragraph("This quick snapshot shows where the current run is stronger or weaker. Full term definitions appear in the glossary."),
                styles["V2Body"],
            )
        )
    scorecard_rows = [["Metric", "Score"]]
    for item in _sequence(score_explanations.get("scorecard")):
        if not isinstance(item, Mapping):
            continue
        scorecard_rows.append(
            [
                _text(item.get("label")),
                _text(item.get("score")),
            ]
        )
    if len(scorecard_rows) > 1:
        elements.append(_table(_table_rows(scorecard_rows, styles), [340, 120]))

    _append_section_header(elements, "Competitive Benchmark", styles)
    benchmark_status = _text(benchmark.get("status"))
    if benchmark_status:
        elements.append(Paragraph(f"<b>Status:</b> {_paragraph(_title_case_status(benchmark_status))}", styles["V2Body"]))
    for line in _unique_nonempty(
        [
            _text(benchmark.get("reason")),
            _text(benchmark.get("visible_reason")),
            _text(benchmark.get("sample_note")),
        ]
    ):
        text = _text(line)
        if text:
            elements.append(Paragraph(_paragraph(text), styles["V2Body"]))
    competitor_rows = [["Competitor", "Platform", "Gap", "Confidence"]]
    for item in _sequence(benchmark.get("benchmark_rows")):
        if not isinstance(item, Mapping):
            continue
        competitor_rows.append(
            [
                _text(item.get("competitor_name")),
                _text(item.get("platform")),
                _text(item.get("our_gap")),
                _text(item.get("confidence")),
            ]
        )
    if len(competitor_rows) > 1:
        elements.append(_table(_table_rows(competitor_rows, styles), [105, 75, 210, 85]))
    elif _sequence(benchmark.get("competitors")):
        _append_bullets(elements, [f"Competitors captured: {', '.join(_text(item) for item in _sequence(benchmark.get('competitors')) if _text(item))}"], styles)

    _append_section_header(elements, "Platform Breakdown", styles)
    platform_rows = [["Platform", "Current read", "Row proof"]]
    platform_actions = _unique_nonempty(
        [
            "; ".join(_text(action) for action in _sequence(item.get("recommended_actions")) if _text(action))
            for item in _sequence(platforms.get("platforms"))
            if isinstance(item, Mapping)
        ]
    )
    for item in _sequence(platforms.get("platforms")):
        if isinstance(item, Mapping):
            platform_rows.append(
                [
                    _text(item.get("platform")),
                    _text(item.get("observed_visibility_status")) or _text(item.get("status")),
                    _text(item.get("confidence")),
                ]
            )
        elif _text(item):
            platform_rows.append([_text(item), "", ""])
    if platform_actions:
        elements.append(Paragraph(f"<b>What to do next:</b> {_paragraph(platform_actions[0])}", styles["V2Body"]))
    claim_source = _label_text(platforms.get("claim_source_class"))
    if claim_source:
        elements.append(Paragraph(f"<b>Claim source:</b> {_paragraph(claim_source)}", styles["V2Body"]))
    evidence_grade = _label_text(platforms.get("evidence_grade"))
    if evidence_grade:
        elements.append(Paragraph(f"<b>Evidence grade:</b> {_paragraph(evidence_grade)}", styles["V2Body"]))
    platform_confidences = _unique_nonempty(
        [
            _text(item.get("confidence"))
            for item in _sequence(platforms.get("platforms"))
            if isinstance(item, Mapping) and _text(item.get("confidence"))
        ]
    )
    if evidence_grade and platform_confidences:
        elements.append(
            Paragraph(
                "Row confidence describes the proof quality for each platform line. "
                "Evidence grade describes how complete the overall platform section is.",
                styles["V2Small"],
            )
        )
    what_upgrades_this = _text(platforms.get("what_upgrades_this"))
    if what_upgrades_this:
        elements.append(Paragraph(f"<b>What upgrades this:</b> {_paragraph(what_upgrades_this)}", styles["V2Body"]))
    if len(platform_rows) > 1:
        elements.append(_table(_table_rows(platform_rows, styles), [95, 240, 85]))
    control_matrix = [
        dict(row)
        for row in _sequence(platforms.get("control_matrix"))
        if isinstance(row, Mapping)
    ]
    if not control_matrix:
        control_matrix = [
            dict(control)
            for item in _sequence(platforms.get("platforms"))
            if isinstance(item, Mapping)
            for control in _sequence(item.get("control_rows"))
            if isinstance(control, Mapping)
        ]
    if control_matrix:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Platform Control Matrix", styles["V2Subsection"]))
        control_rows = [["Platform", "Agent", "Use", "State", "Control Via"]]
        for row in control_matrix[:12]:
            control_rows.append(
                [
                    _text(row.get("platform")),
                    _text(row.get("bot_name")),
                    _text(row.get("surface_label")) or _title_case_status(row.get("surface")),
                    _text(row.get("status")),
                    _text(row.get("control_mechanism")),
                ]
            )
        elements.append(_table(_table_rows(control_rows, styles), [78, 105, 80, 52, 115]))
    sample_note = _text(platforms.get("sample_note"))
    if sample_note:
        elements.append(Paragraph(_paragraph(sample_note), styles["V2Body"]))

    _append_section_header(elements, "Page And Source Evidence", styles)
    visible_reason = _text(page_source.get("visible_reason"))
    if visible_reason:
        elements.append(Paragraph(_paragraph(visible_reason), styles["V2Body"]))
    page_rows = [["Page", "Type", "Citability", "Recommended fix"]]
    for item in _sequence(page_source.get("priority_pages")):
        if not isinstance(item, Mapping):
            continue
        page_rows.append(
            [
                _text(item.get("page_url")),
                _text(item.get("page_type")),
                _text(item.get("citability_score")),
                _text(item.get("recommended_fix")),
            ]
        )
    if len(page_rows) > 1:
        elements.append(_table(_table_rows(page_rows, styles), [190, 62, 55, 173]))
    source_rows = [["Source domain", "Type", "Why it matters"]]
    for item in _sequence(page_source.get("source_domains")):
        if not isinstance(item, Mapping):
            continue
        source_rows.append(
            [
                _text(item.get("domain")),
                _text(item.get("source_type")),
                _text(item.get("why_it_matters")),
            ]
        )
    if len(source_rows) > 1:
        elements.append(Spacer(1, 6))
        elements.append(_table(_table_rows(source_rows, styles), [135, 85, 260]))
    evidence_lines = _unique_nonempty(
        [
            _evidence_highlight(item)
            for item in _sequence(page_source.get("evidence_items"))
            if isinstance(item, Mapping)
        ]
    )
    if evidence_lines:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Evidence Ledger Highlights", styles["V2Subsection"]))
        for line in evidence_lines[:4]:
            elements.append(Paragraph(f"• {_paragraph(line)}", styles["V2Small"]))
    elif len(page_rows) == 1 and len(source_rows) == 1 and not visible_reason:
        elements.append(Paragraph("No structured page or source evidence was captured in this run.", styles["V2Small"]))

    _append_section_header(elements, "Proof Appendix", styles)
    proof_manifest = _mapping(proof.get("manifest"))
    run_context_rows = [
        ["Target URL", _text(proof_manifest.get("target_url")) or _text(manifest.get("target_url"))],
        ["Mode", _text(proof_manifest.get("mode")) or _text(manifest.get("mode")) or "script-only"],
        ["Shadow run", _text(proof_manifest.get("shadow_run") if proof_manifest else manifest.get("shadow_run"))],
    ]
    elements.append(Paragraph("Run Context", styles["V2Subsection"]))
    elements.append(_table(_table_rows([["Field", "Value"], *run_context_rows], styles), [110, 350]))
    methodology = _text(_mapping(proof.get("methodology")).get("summary"))
    if methodology:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"<b>Methodology:</b> {_paragraph(methodology)}", styles["V2Body"]))
    evidence_completeness = _mapping(proof.get("evidence_completeness"))
    if evidence_completeness:
        label = _text(evidence_completeness.get("label"))
        score = _text(evidence_completeness.get("score"))
        reason = _text(evidence_completeness.get("reason"))
        summary = label
        if label and score:
            summary = f"{label} ({score}/100)"
        elif score:
            summary = f"{score}/100"
        if summary or reason:
            elements.append(Spacer(1, 6))
            elements.append(Paragraph("Evidence Completeness", styles["V2Subsection"]))
            if summary:
                elements.append(Paragraph(_paragraph(summary), styles["V2Body"]))
            if reason:
                elements.append(Paragraph(_paragraph(reason), styles["V2Body"]))
    change_since_last_run = _mapping(proof.get("delta_summary")) or _mapping(proof.get("change_since_last_run"))
    if change_since_last_run:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Change Since Last Run", styles["V2Subsection"]))
        comparable = change_since_last_run.get("comparable")
        if comparable is not None:
            elements.append(
                Paragraph(
                    f"<b>Comparable:</b> {_paragraph('Yes' if comparable else 'No')}",
                    styles["V2Body"],
                )
            )
        summary = _text(change_since_last_run.get("summary"))
        if summary:
            elements.append(Paragraph(_paragraph(summary), styles["V2Body"]))
        delta_lines = []
        for item in _sequence(change_since_last_run.get("what_changed")) or _sequence(change_since_last_run.get("delta_items")):
            if not isinstance(item, Mapping):
                continue
            label = _text(item.get("label")) or _label_text(item.get("metric"))
            current = _text(item.get("current"))
            previous = _text(item.get("previous"))
            delta = _text(item.get("delta"))
            if label and current and previous and delta:
                prefix = "+" if not delta.startswith("-") else ""
                delta_lines.append(f"{label}: {previous} -> {current} ({prefix}{delta})")
                continue
            direction = _text(item.get("direction"))
            if label and direction and delta:
                delta_lines.append(f"{label}: {direction} {delta.lstrip('+')}")
        if delta_lines:
            for line in delta_lines[:4]:
                elements.append(Paragraph(_paragraph(line), styles["V2Body"]))
        upgrade_note = _text(change_since_last_run.get("what_upgrades_this"))
        if upgrade_note:
            elements.append(Paragraph(f"<b>What upgrades this:</b> {_paragraph(upgrade_note)}", styles["V2Body"]))
    crawl_notes = [_text(item) for item in _sequence(proof.get("crawl_and_fetch_evidence")) if _text(item)]
    if crawl_notes:
        elements.append(Paragraph("Crawl And Fetch Notes", styles["V2Subsection"]))
        _append_bullets(elements, crawl_notes[:2], styles)
    bot_access = [_text(item) for item in _sequence(proof.get("robots_and_bot_access")) if _text(item)]
    if bot_access:
        elements.append(Paragraph("Bot Access", styles["V2Subsection"]))
        _append_bullets(elements, _compact_bot_access(bot_access), styles)
    official_sources = _sequence(proof.get("official_sources"))
    if official_sources:
        elements.append(Paragraph("Official Sources", styles["V2Subsection"]))
        _append_bullets(
            elements,
            [
                " - ".join(
                    part
                    for part in (_text(item.get("title")), _text(item.get("url")))
                    if part
                )
                for item in official_sources
                if isinstance(item, Mapping)
            ][:6],
            styles,
        )
    limitations = _text(_mapping(proof.get("limitations")).get("limitations_note"))
    if limitations:
        elements.append(Paragraph(f"<b>Limitation:</b> {_paragraph(limitations)}", styles["V2Body"]))
    bridge_warnings = _sequence(proof.get("bridge_warnings"))
    if bridge_warnings:
        elements.append(Paragraph("Bridge Warnings", styles["V2Subsection"]))
        _append_bullets(elements, [_text(item) for item in bridge_warnings], styles)

    adjudication_rows = [["Section", "Status", "Reason"]]
    for name, section in adjudication.items():
        section_map = _mapping(section)
        status = _title_case_status(section_map.get("status"))
        reason = _text(section_map.get("warning")) or _text(section_map.get("reason"))
        if not status and not reason:
            continue
        adjudication_rows.append(
            [
                _text(name).replace("_", " ").title(),
                status,
                reason,
            ]
        )
    if len(adjudication_rows) > 1:
        elements.append(Paragraph("Section Evidence Status", styles["V2Subsection"]))
        elements.append(Spacer(1, 6))
        elements.append(_table(_table_rows(adjudication_rows, styles), [120, 70, 270]))
    term_rows = [["Term", "Plain-English Meaning"]]
    for item in _sequence(score_explanations.get("terms")):
        if not isinstance(item, Mapping):
            continue
        term_rows.append([_text(item.get("label")), _text(item.get("plain_english"))])
    if len(term_rows) > 1:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Glossary", styles["V2Subsection"]))
        elements.append(_table(_table_rows(term_rows, styles), [135, 325]))

    doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return output
