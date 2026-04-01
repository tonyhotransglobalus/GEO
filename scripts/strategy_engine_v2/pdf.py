from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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


def _table(rows: list[list[str]], widths: list[int]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4f8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102a43")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bcccdc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


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
        elements.append(Paragraph(f"<b>Visible reason:</b> {_paragraph(visible_reason)}", styles["V2Body"]))

    scorecard_rows = [["Metric", "Score", "Explanation"]]
    for item in _sequence(score_explanations.get("scorecard")):
        if not isinstance(item, Mapping):
            continue
        scorecard_rows.append(
            [
                _text(item.get("label")),
                _text(item.get("score")),
                _text(item.get("plain_english")),
            ]
        )
    if len(scorecard_rows) > 1:
        elements.append(Spacer(1, 4))
        elements.append(_table(scorecard_rows, [136, 54, 290]))
    elements.append(Spacer(1, 10))

    _append_section_header(elements, "Score Explanations", styles)
    note = _text(score_explanations.get("plain_english_note"))
    if note:
        elements.append(Paragraph(_paragraph(note), styles["V2Body"]))
    term_rows = [["Term", "Plain-English Meaning"]]
    for item in _sequence(score_explanations.get("terms")):
        if not isinstance(item, Mapping):
            continue
        term_rows.append([_text(item.get("label")), _text(item.get("plain_english"))])
    if len(term_rows) > 1:
        elements.append(_table(term_rows, [140, 340]))

    elements.append(PageBreak())

    _append_section_header(elements, "Priority Findings", styles)
    for finding in _sequence(priority_findings.get("findings")):
        if not isinstance(finding, Mapping):
            continue
        title = _text(finding.get("title")) or _text(finding.get("section")).replace("_", " ").title()
        elements.append(
            Paragraph(
                f"{_paragraph(title)} <font color='#486581'>({_paragraph(_title_case_status(finding.get('status')) or 'Omitted')})</font>",
                styles["V2Subsection"],
            )
        )
        for label, value in (
            ("Summary", finding.get("summary")),
            ("Visible reason", finding.get("visible_reason")),
            ("Why it matters", finding.get("leadership_impact")),
            ("Marketing action", finding.get("marketing_action")),
            ("Engineering action", finding.get("engineering_action")),
        ):
            text = _text(value)
            if text:
                elements.append(Paragraph(f"<b>{label}:</b> {_paragraph(text)}", styles["V2Body"]))
        evidence_items = []
        for item in _sequence(finding.get("evidence_items")):
            if not isinstance(item, Mapping):
                continue
            pieces = [
                _text(item.get("evidence_type")),
                _text(item.get("source_class")),
                _text(item.get("normalized_summary")),
            ]
            evidence_items.append(", ".join(piece for piece in pieces if piece))
        if evidence_items:
            _append_bullets(elements, evidence_items[:4], styles)
        elements.append(Spacer(1, 6))

    _append_section_header(elements, "Competitive Benchmark", styles)
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
        elements.append(_table(competitor_rows, [140, 90, 210, 40]))
    elif _sequence(benchmark.get("competitors")):
        _append_bullets(elements, [f"Competitors captured: {', '.join(_text(item) for item in _sequence(benchmark.get('competitors')) if _text(item))}"], styles)

    _append_section_header(elements, "Platform Breakdown", styles)
    platform_rows = [["Platform", "Status", "Confidence", "Recommended action"]]
    for item in _sequence(platforms.get("platforms")):
        if isinstance(item, Mapping):
            platform_rows.append(
                [
                    _text(item.get("platform")),
                    _text(item.get("observed_visibility_status")) or _text(item.get("status")),
                    _text(item.get("confidence")),
                    "; ".join(_text(action) for action in _sequence(item.get("recommended_actions")) if _text(action)),
                ]
            )
        elif _text(item):
            platform_rows.append([_text(item), "", "", ""])
    if len(platform_rows) > 1:
        elements.append(_table(platform_rows, [110, 140, 60, 170]))
    sample_note = _text(platforms.get("sample_note"))
    if sample_note:
        elements.append(Paragraph(_paragraph(sample_note), styles["V2Body"]))

    elements.append(PageBreak())

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
        elements.append(_table(page_rows, [210, 62, 55, 153]))
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
        elements.append(_table(source_rows, [150, 90, 240]))

    _append_section_header(elements, "30/60/90 Action Plan", styles)
    action_rows = [["Horizon", "Action", "Owner", "Expected outcome"]]
    for item in _sequence(action_plan.get("actions")):
        if not isinstance(item, Mapping):
            continue
        action_rows.append(
            [
                _text(item.get("time_horizon")),
                _text(item.get("action")),
                _text(item.get("owner")),
                _text(item.get("expected_outcome")),
            ]
        )
    if len(action_rows) > 1:
        elements.append(_table(action_rows, [72, 210, 70, 128]))
    else:
        elements.append(Paragraph("No actions were captured in this run.", styles["V2Body"]))

    _append_section_header(elements, "Proof Appendix", styles)
    proof_lines = [
        f"Target URL: {_text(_mapping(proof.get('manifest')).get('target_url')) or _text(manifest.get('target_url'))}",
        f"Mode: {_text(_mapping(proof.get('manifest')).get('mode')) or _text(manifest.get('mode')) or 'script-only'}",
        f"Shadow run: {_text(_mapping(proof.get('manifest')).get('shadow_run') if _mapping(proof.get('manifest')) else manifest.get('shadow_run'))}",
        f"Evidence count: {_text(proof.get('evidence_count') or evidence.get('count'))}",
        f"Visible reason: {_text(proof.get('visible_reason'))}",
    ]
    _append_bullets(elements, proof_lines, styles)
    methodology = _text(_mapping(proof.get("methodology")).get("summary"))
    if methodology:
        elements.append(Paragraph(f"<b>Methodology:</b> {_paragraph(methodology)}", styles["V2Body"]))
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
        elements.append(Spacer(1, 6))
        elements.append(_table(adjudication_rows, [130, 70, 310]))

    doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return output
