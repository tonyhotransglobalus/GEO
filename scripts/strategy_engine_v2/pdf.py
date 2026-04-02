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
            ordered_groups.append((label, rows[:2]))
    for label, rows in grouped.items():
        if label in {"30 Days", "60 Days", "90 Days"} or not rows:
            continue
        ordered_groups.append((label, rows[:2]))
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
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#102a43"),
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V2Subsection",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#243b53"),
            spaceBefore=6,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="V2Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
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
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d9e2ec"), spaceAfter=6))


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
    trust_value = _text(leadership.get("trust_value")) or "Low"
    leadership_lines = [
        f"How much to trust this: {trust_value}",
        *_sequence(leadership.get("summary")),
    ]
    _append_bullets(elements, [item for item in leadership_lines if _text(item)], styles)
    visible_reason = _text(leadership.get("visible_reason"))
    if visible_reason:
        elements.append(Paragraph(f"<b>Current constraint:</b> {_paragraph(visible_reason)}", styles["V2Body"]))
    top_priorities: list[str] = []
    for finding in _sequence(priority_findings.get("findings"))[:3]:
        if not isinstance(finding, Mapping):
            continue
        title = _text(finding.get("title")) or _text(finding.get("section")).replace("_", " ").title()
        if title:
            top_priorities.append(title)
    if top_priorities:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("Top Priorities Now", styles["V2Subsection"]))
        _append_bullets(elements, _unique_nonempty(top_priorities)[:3], styles)
    elements.append(Spacer(1, 10))

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

    elements.append(PageBreak())

    _append_section_header(elements, "Priority Findings", styles)
    for finding in _sequence(priority_findings.get("findings")):
        if not isinstance(finding, Mapping):
            continue
        title = _text(finding.get("title")) or _text(finding.get("section")).replace("_", " ").title()
        summary = _text(finding.get("summary"))
        visible_reason = _text(finding.get("visible_reason"))
        problem_statement = summary or visible_reason
        observation = visible_reason if _normalized_text(visible_reason) != _normalized_text(summary) else ""
        finding_block: list[Any] = [
            Paragraph(
                f"{_paragraph(title)} <font color='#486581'>({_paragraph(_title_case_status(finding.get('status')) or 'Omitted')})</font>",
                styles["V2Subsection"],
            )
        ]
        for label, value in (
            ("What's wrong", problem_statement),
            ("What we saw", observation),
            ("Why it matters", finding.get("leadership_impact")),
        ):
            text = _text(value)
            if text:
                finding_block.append(Paragraph(f"<b>{label}:</b> {_paragraph(text)}", styles["V2Body"]))
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
        supporting_lines: list[str] = []
        for item in _sequence(finding.get("evidence_items"))[:1]:
            if not isinstance(item, Mapping):
                continue
            summary = _text(item.get("normalized_summary"))
            if summary:
                supporting_lines.append(summary)
        if supporting_lines:
            finding_block.append(Paragraph("<b>Supporting evidence:</b>", styles["V2Small"]))
            for line in supporting_lines:
                finding_block.append(Paragraph(f"• {_paragraph(line)}", styles["V2Small"]))
        finding_block.append(Spacer(1, 6))
        finding_block.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#d9e2ec"), spaceBefore=0, spaceAfter=6))
        elements.append(KeepTogether(finding_block))

    _append_section_header(elements, "Competitive Benchmark", styles)
    benchmark_status = _text(benchmark.get("status"))
    if benchmark_status:
        elements.append(Paragraph(f"<b>Status:</b> {_paragraph(_title_case_status(benchmark_status))}", styles["V2Body"]))
    for line in (
        benchmark.get("reason"),
        benchmark.get("visible_reason"),
        benchmark.get("sample_note"),
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
        elements.append(_table(_table_rows(competitor_rows, styles), [115, 85, 225, 50]))
    elif _sequence(benchmark.get("competitors")):
        _append_bullets(elements, [f"Competitors captured: {', '.join(_text(item) for item in _sequence(benchmark.get('competitors')) if _text(item))}"], styles)

    _append_section_header(elements, "Platform Breakdown", styles)
    platform_rows = [["Platform", "Current read", "Confidence"]]
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
    if len(platform_rows) > 1:
        elements.append(_table(_table_rows(platform_rows, styles), [110, 255, 55]))
    sample_note = _text(platforms.get("sample_note"))
    if sample_note:
        elements.append(Paragraph(_paragraph(sample_note), styles["V2Body"]))

    _append_section_header(elements, "Page And Source Evidence", styles)
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

    _append_section_header(elements, "30/60/90 Action Plan", styles)
    grouped_actions = _compact_action_groups(_sequence(action_plan.get("actions")))
    if grouped_actions:
        for horizon_label, rows in grouped_actions:
            elements.append(Paragraph(horizon_label, styles["V2Subsection"]))
            for item in rows:
                action_text = _text(item.get("action"))
                owner = _text(item.get("owner"))
                outcome = _text(item.get("expected_outcome"))
                detail_parts = [segment for segment in [f"Owner: {owner}." if owner else "", outcome] if segment]
                line = action_text
                if detail_parts:
                    line = f"{action_text} {' '.join(detail_parts)}"
                elements.append(Paragraph(f"• {_paragraph(line)}", styles["V2Bullet"]))
    else:
        elements.append(Paragraph("No actions were captured in this run.", styles["V2Body"]))

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
    crawl_notes = [_text(item) for item in _sequence(proof.get("crawl_and_fetch_evidence")) if _text(item)]
    if crawl_notes:
        elements.append(Paragraph("Crawl And Fetch Notes", styles["V2Subsection"]))
        _append_bullets(elements, crawl_notes[:2], styles)
    bot_access = [_text(item) for item in _sequence(proof.get("robots_and_bot_access")) if _text(item)]
    if bot_access:
        elements.append(Paragraph("Bot Access", styles["V2Subsection"]))
        _append_bullets(elements, _compact_bot_access(bot_access), styles)
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
        adjudication_rows.append(
            [
                _text(name).replace("_", " ").title(),
                _title_case_status(section_map.get("status")),
                _text(section_map.get("warning")) or _text(section_map.get("reason")),
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
