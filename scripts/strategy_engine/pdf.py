#!/usr/bin/env python3
"""
GEO-SEO PDF Report Generator
Generates professional, client-ready PDF reports from GEO audit data.

Usage:
    python generate_pdf_report.py <json_data_file> [output_file.pdf]

The JSON data file should contain the audit results structured as:
{
    "url": "https://example.com",
    "brand_name": "Example Co",
    "date": "2026-02-18",
    "geo_score": 62,
    "scores": { ... },
    "findings": { ... },
    ...
}

Or pipe JSON data from stdin:
    cat audit_data.json | python generate_pdf_report.py - output.pdf
"""

import sys
import json
import os
from datetime import datetime
from urllib.parse import urlparse
from xml.sax.saxutils import escape
from typing import Any, Mapping

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch, mm
    from reportlab.lib.colors import (
        HexColor, black, white, grey, lightgrey, darkgrey,
        Color
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, KeepTogether, Image as RLImage
    )
    from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line, Wedge
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics import renderPDF
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    from .reporting import (
        EVIDENCE_APPENDIX_TITLE,
        REPORT_SECTION_ORDER,
        format_evidence_item_text,
        normalize_report_sections,
    )
except ImportError:
    from scripts.strategy_engine.reporting import (
        EVIDENCE_APPENDIX_TITLE,
        REPORT_SECTION_ORDER,
        format_evidence_item_text,
        normalize_report_sections,
    )


# ============================================================
# COLOR PALETTE
# ============================================================
PRIMARY = HexColor("#1a1a2e")       # Dark navy
SECONDARY = HexColor("#16213e")     # Slightly lighter navy
ACCENT = HexColor("#0f3460")        # Blue accent
HIGHLIGHT = HexColor("#e94560")     # Red/coral highlight
SUCCESS = HexColor("#00b894")       # Green
WARNING = HexColor("#fdcb6e")       # Yellow/amber
DANGER = HexColor("#d63031")        # Red
INFO = HexColor("#0984e3")          # Blue
LIGHT_BG = HexColor("#f8f9fa")      # Light background
MEDIUM_BG = HexColor("#e9ecef")     # Medium background
TEXT_PRIMARY = HexColor("#2d3436")   # Dark text
TEXT_SECONDARY = HexColor("#636e72") # Grey text
WHITE = white
BLACK = black


def get_score_color(score):
    """Return color based on score value."""
    if score >= 80:
        return SUCCESS
    elif score >= 60:
        return INFO
    elif score >= 40:
        return WARNING
    else:
        return DANGER


def get_score_label(score):
    """Return label based on score value."""
    if score >= 85:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 55:
        return "Moderate"
    elif score >= 40:
        return "Below Average"
    else:
        return "Needs Attention"


def create_score_gauge(score, width=120, height=120):
    """Create a visual score gauge."""
    d = Drawing(width, height)

    # Background circle
    d.add(Circle(width/2, height/2, 50, fillColor=LIGHT_BG, strokeColor=lightgrey, strokeWidth=2))

    # Score arc (simplified as colored circle)
    color = get_score_color(score)
    d.add(Circle(width/2, height/2, 45, fillColor=color, strokeColor=None))

    # Inner white circle
    d.add(Circle(width/2, height/2, 35, fillColor=WHITE, strokeColor=None))

    # Score text
    d.add(String(width/2, height/2 + 5, str(score),
                 fontSize=24, fontName='Helvetica-Bold',
                 fillColor=TEXT_PRIMARY, textAnchor='middle'))

    # Label
    d.add(String(width/2, height/2 - 12, "/100",
                 fontSize=10, fontName='Helvetica',
                 fillColor=TEXT_SECONDARY, textAnchor='middle'))

    return d


def create_bar_chart(data, labels, width=400, height=200):
    """Create a horizontal bar chart for scores."""
    d = Drawing(width, height)

    chart = VerticalBarChart()
    chart.x = 60
    chart.y = 30
    chart.height = height - 60
    chart.width = width - 80
    chart.data = [data]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.angle = 0
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fontName = 'Helvetica'
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 100
    chart.valueAxis.valueStep = 20
    chart.valueAxis.labels.fontSize = 8

    # Color each bar based on score
    for i, score in enumerate(data):
        chart.bars[0].fillColor = get_score_color(score)

    chart.bars[0].strokeColor = None
    chart.bars[0].strokeWidth = 0

    d.add(chart)
    return d


def create_platform_chart(platforms, width=450, height=180):
    """Create a chart showing platform readiness scores."""
    d = Drawing(width, height)

    bar_height = 22
    bar_max_width = 280
    start_y = height - 30
    label_x = 10

    for i, (name, score) in enumerate(platforms.items()):
        y = start_y - (i * (bar_height + 10))

        # Platform name
        d.add(String(label_x, y + 5, name,
                     fontSize=9, fontName='Helvetica',
                     fillColor=TEXT_PRIMARY, textAnchor='start'))

        # Background bar
        bar_x = 130
        d.add(Rect(bar_x, y, bar_max_width, bar_height,
                    fillColor=LIGHT_BG, strokeColor=None))

        # Score bar
        bar_width = (score / 100) * bar_max_width
        color = get_score_color(score)
        d.add(Rect(bar_x, y, bar_width, bar_height,
                    fillColor=color, strokeColor=None))

        # Score text
        d.add(String(bar_x + bar_max_width + 10, y + 6, f"{score}/100",
                     fontSize=9, fontName='Helvetica-Bold',
                     fillColor=TEXT_PRIMARY, textAnchor='start'))

    return d


def build_styles():
    """Create custom paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='ReportTitle',
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=30,
        textColor=PRIMARY,
        spaceAfter=6,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='ReportSubtitle',
        fontName='Helvetica',
        fontSize=12,
        leading=14,
        textColor=TEXT_SECONDARY,
        spaceAfter=18,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='SectionHeader',
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=PRIMARY,
        spaceBefore=20,
        spaceAfter=10,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='SubHeader',
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=ACCENT,
        spaceBefore=14,
        spaceAfter=6,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='BodyText_Custom',
        fontName='Helvetica',
        fontSize=10,
        textColor=TEXT_PRIMARY,
        spaceBefore=4,
        spaceAfter=4,
        leading=14,
        alignment=TA_JUSTIFY,
    ))

    styles.add(ParagraphStyle(
        name='SmallText',
        fontName='Helvetica',
        fontSize=8,
        textColor=TEXT_SECONDARY,
        spaceBefore=2,
        spaceAfter=2,
    ))

    styles.add(ParagraphStyle(
        name='ScoreLabel',
        fontName='Helvetica-Bold',
        fontSize=36,
        textColor=PRIMARY,
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name='HighlightBox',
        fontName='Helvetica',
        fontSize=10,
        textColor=TEXT_PRIMARY,
        backColor=LIGHT_BG,
        borderPadding=10,
        spaceBefore=8,
        spaceAfter=8,
        leading=14,
    ))

    styles.add(ParagraphStyle(
        name='CriticalFinding',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=DANGER,
        spaceBefore=4,
        spaceAfter=2,
    ))

    styles.add(ParagraphStyle(
        name='Recommendation',
        fontName='Helvetica',
        fontSize=10,
        textColor=TEXT_PRIMARY,
        leftIndent=15,
        spaceBefore=3,
        spaceAfter=3,
        bulletIndent=5,
        leading=14,
    ))

    styles.add(ParagraphStyle(
        name='Footer',
        fontName='Helvetica',
        fontSize=8,
        textColor=TEXT_SECONDARY,
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name='TableHeaderCell',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10,
        textColor=WHITE,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=0,
    ))

    styles.add(ParagraphStyle(
        name='TableCell',
        fontName='Helvetica',
        fontSize=8.75,
        leading=11,
        textColor=TEXT_PRIMARY,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=0,
    ))

    styles.add(ParagraphStyle(
        name='TableLabelCell',
        parent=styles['TableCell'],
        fontName='Helvetica-Bold',
        textColor=ACCENT,
    ))

    styles.add(ParagraphStyle(
        name='FindingTitle',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=13,
        textColor=TEXT_PRIMARY,
        spaceBefore=0,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        name='FindingSummary',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=TEXT_PRIMARY,
        spaceBefore=0,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name='FindingDetail',
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=TEXT_PRIMARY,
        spaceBefore=0,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        name='PlaybookPageHeader',
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=PRIMARY,
        spaceBefore=0,
        spaceAfter=15,
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name='CalloutBox',
        fontName='Helvetica',
        fontSize=10,
        textColor=WHITE,
        backColor=ACCENT,
        borderPadding=12,
        spaceBefore=10,
        spaceAfter=10,
        leading=15,
        alignment=TA_LEFT,
        borderRadius=4,
    ))

    styles.add(ParagraphStyle(
        name='RescienceBefore',
        fontName='Helvetica',
        fontSize=9,
        textColor=DANGER,
        backColor=HexColor("#fff5f5"),
        borderPadding=8,
        spaceBefore=4,
        spaceAfter=4,
        leading=12,
    ))

    styles.add(ParagraphStyle(
        name='RescienceAfter',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=SUCCESS,
        backColor=HexColor("#f0fff4"),
        borderPadding=8,
        spaceBefore=4,
        spaceAfter=4,
        leading=12,
    ))

    return styles


def header_footer(canvas, doc):
    """Add header and footer to each page."""
    canvas.saveState()

    # Header line
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(2)
    canvas.line(50, letter[1] - 40, letter[0] - 50, letter[1] - 40)

    # Header text
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(TEXT_SECONDARY)
    canvas.drawString(50, letter[1] - 35, "GEO-SEO Analysis Report")

    # Footer
    canvas.setStrokeColor(lightgrey)
    canvas.setLineWidth(0.5)
    canvas.line(50, 40, letter[0] - 50, 40)

    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(TEXT_SECONDARY)
    canvas.drawString(50, 28, f"Generated {datetime.now().strftime('%B %d, %Y')}")
    canvas.drawRightString(letter[0] - 50, 28, f"Page {doc.page}")
    canvas.drawCentredString(letter[0] / 2, 28, "Confidential")

    canvas.restoreState()


def make_table_style(header_color=PRIMARY):
    """Create a consistent table style."""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_PRIMARY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, lightgrey),
        ('BACKGROUND', (0, 1), (-1, -1), WHITE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ('WORDWRAP', (0, 0), (-1, -1), 'LTR'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
    ])


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def paragraph_text(value):
    return escape(normalize_text(value)).replace("\n", "<br/>")


def display_text(value):
    text = normalize_text(value)
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if "-" in text and " " not in text and text.count("-") >= 2:
        text = text.replace("-", " ").strip().title()
    if len(text) > 96:
        text = text[:93].rstrip(" -_,.;:") + "..."
    return text


def make_label_value_paragraph(label, value, style):
    return Paragraph(f"<b>{escape(label)}:</b> {paragraph_text(display_text(value))}", style)


def wrap_table_rows(rows, styles=None, header_rows=1):
    if styles is None:
        styles = build_styles()

    wrapped_rows = []
    for row_index, row in enumerate(rows):
        wrapped_row = []
        for cell in row:
            if isinstance(cell, Paragraph):
                wrapped_row.append(cell)
                continue
            style_name = 'TableHeaderCell' if row_index < header_rows else 'TableCell'
            wrapped_row.append(Paragraph(paragraph_text(cell), styles[style_name]))
        wrapped_rows.append(wrapped_row)
    return wrapped_rows


def _report_item_text(item: Any) -> str:
    if isinstance(item, Mapping):
        if any(key in item for key in ("source_type", "source_tag", "metadata", "url")):
            return format_evidence_item_text(item)
        for key in ("name", "action", "label", "query", "issue", "competitor", "title", "service_line", "gap_theme"):
            value = item.get(key)
            if value:
                text = display_text(value)
                if text:
                    details = []
                    for detail_key in (
                        "owner",
                        "impact",
                        "severity",
                        "failure_mode",
                        "why_it_matters",
                        "priority",
                        "opportunity_score",
                        "visibility",
                        "citation_readiness",
                        "citation_strength",
                        "earned_media_strength",
                        "technical_readiness",
                    ):
                        detail_value = item.get(detail_key)
                        if detail_value:
                            if isinstance(detail_value, list):
                                detail_value = ", ".join(str(value).strip() for value in detail_value if value)
                            details.append(f"{detail_key.replace('_', ' ').title()}: {detail_value}")
                    if details:
                        return f"{text} ({'; '.join(details)})"
                    return text
        return str(item)
    if isinstance(item, list):
        return ", ".join(_report_item_text(value) for value in item if value)
    return display_text(item)


def _append_bullets(elements, items, styles, style_name="Recommendation"):
    for index, item in enumerate(items, 1):
        text = _report_item_text(item)
        if text:
            elements.append(Paragraph(f"<b>{index}.</b> {paragraph_text(text)}", styles[style_name]))


def _fit_widths(widths, available_width):
    total_width = sum(widths)
    if total_width <= available_width:
        return list(widths)

    scale = available_width / float(total_width)
    fitted = [max(1, int(width * scale)) for width in widths]
    fitted[-1] += available_width - sum(fitted)
    return fitted


def render_report_sections(elements, report_sections, styles, content_width):
    if not isinstance(report_sections, Mapping):
        return

    def add_heading(text, level="section"):
        style = styles["SectionHeader"] if level == "section" else styles["SubHeader"]
        elements.append(Paragraph(text, style))
        elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    for key in REPORT_SECTION_ORDER:
        section = report_sections.get(key)
        if not isinstance(section, Mapping):
            continue

        if key == "decision_summary":
            add_heading("Decision Summary")
            overview = section.get("overview")
            if overview:
                elements.append(Paragraph(paragraph_text(overview), styles["BodyText_Custom"]))
                elements.append(Spacer(1, 8))
            for title, items in (
                ("Top Blockers", section.get("blockers") or []),
                ("Top Opportunities", section.get("opportunities") or []),
                ("Service Lines In Scope", section.get("service_lines") or []),
                ("Next 30 Days", section.get("next_actions") or []),
            ):
                if items:
                    elements.append(Paragraph(title, styles["SubHeader"]))
                    _append_bullets(elements, items, styles)
                    elements.append(Spacer(1, 6))
            continue

        if key == "service_line_scorecard":
            add_heading("Service-Line Scorecard")
            rows = section.get("rows") or []
            if rows:
                table_rows = [[
                    "Service Line",
                    "Visibility",
                    "Citation Readiness",
                    "Citation Strength",
                    "Earned-Media",
                    "Technical",
                    "Priority",
                ]]
                for row in rows:
                    if not isinstance(row, Mapping):
                        continue
                    table_rows.append([
                        row.get("service_line", ""),
                        row.get("visibility", ""),
                        row.get("citation_readiness", ""),
                        row.get("citation_strength", ""),
                        row.get("earned_media_strength", ""),
                        row.get("technical_readiness", ""),
                        row.get("priority", ""),
                    ])
                table = build_wrapped_table(
                    table_rows,
                    _fit_widths([120, 62, 72, 70, 68, 60, 48], content_width),
                    styles,
                )
                elements.append(table)
                elements.append(Spacer(1, 8))
                elements.append(Paragraph("Observed Queries", styles["SubHeader"]))
                observed_lines = []
                for row in rows:
                    if isinstance(row, Mapping) and row.get("observed_queries"):
                        observed_lines.append(
                            f"{row.get('service_line', '')}: {', '.join(row.get('observed_queries') or [])}"
                        )
                _append_bullets(elements, observed_lines, styles)
                elements.append(Spacer(1, 6))
            continue

        if key == "query_universe":
            add_heading("Query Universe")
            service_lines = section.get("service_lines") or []
            if service_lines:
                elements.append(Paragraph("Service-Line Query Themes", styles["SubHeader"]))
                _append_bullets(elements, service_lines, styles)
                elements.append(Spacer(1, 6))
            clusters = section.get("clusters") or []
            if clusters:
                elements.append(Paragraph("Cluster Inventory", styles["SubHeader"]))
                _append_bullets(elements, clusters, styles)
                elements.append(Spacer(1, 6))
            continue

        if key == "competitor_visibility":
            add_heading("Competitor Visibility")
            summary = section.get("summary") or {}
            discovery_note = summary.get("discovery_note")
            if discovery_note:
                elements.append(Paragraph(paragraph_text(discovery_note), styles["BodyText_Custom"]))
                elements.append(Spacer(1, 6))
            competitors = section.get("competitors") or []
            if competitors:
                elements.append(Paragraph("Observed Competitors", styles["SubHeader"]))
                _append_bullets(elements, competitors, styles)
                elements.append(Spacer(1, 6))
            source_inventory = section.get("source_inventory") or {}
            if isinstance(source_inventory, Mapping):
                inventory_rows = [["Source Bucket", "Domains"]]
                inventory_rows.append(["Site-owned", ", ".join(source_inventory.get("site_owned") or []) or "none discovered"])
                inventory_rows.append(["Competitor-owned", ", ".join(source_inventory.get("competitor_owned") or []) or "none discovered"])
                inventory_rows.append(["Earned-media", ", ".join(source_inventory.get("earned_media") or []) or "none discovered"])
                table = build_wrapped_table(
                    inventory_rows,
                    _fit_widths([120, 380], content_width),
                    styles,
                )
                elements.append(table)
                elements.append(Spacer(1, 8))
            authority_gaps = section.get("authority_gaps") or []
            if authority_gaps:
                elements.append(Paragraph("Visibility Gaps", styles["SubHeader"]))
                _append_bullets(elements, authority_gaps, styles)
                elements.append(Spacer(1, 6))
            continue

        if key == "earned_media_gap":
            add_heading("Earned-Media Gap")
            summary_note = section.get("summary_note")
            if summary_note:
                elements.append(Paragraph(paragraph_text(summary_note), styles["BodyText_Custom"]))
                elements.append(Spacer(1, 6))
            sources = section.get("sources") or []
            if sources:
                elements.append(Paragraph("Observed Sources", styles["SubHeader"]))
                _append_bullets(elements, sources, styles)
                elements.append(Spacer(1, 6))
            gap_priorities = section.get("gap_priorities") or []
            if gap_priorities:
                elements.append(Paragraph("Gap Priorities", styles["SubHeader"]))
                _append_bullets(elements, gap_priorities, styles)
                elements.append(Spacer(1, 6))
            continue

        if key == "citation_diagnosis":
            add_heading("Citation Diagnosis")
            failures = section.get("failures") or []
            if failures:
                elements.append(Paragraph("Failure Items", styles["SubHeader"]))
                _append_bullets(elements, failures, styles)
                elements.append(Spacer(1, 6))
            failure_modes = section.get("failure_modes") or []
            if failure_modes:
                elements.append(Paragraph("Failure Modes", styles["SubHeader"]))
                _append_bullets(elements, [str(mode).replace("_", " ").title() for mode in failure_modes], styles)
                elements.append(Spacer(1, 6))
            citation_strength = section.get("citation_strength") or {}
            if isinstance(citation_strength, Mapping):
                elements.append(Paragraph("Citation Strength", styles["SubHeader"]))
                for bucket_key, bucket_label in (("owned_sources", "Owned Sources"), ("earned_sources", "Earned Sources")):
                    bucket = citation_strength.get(bucket_key) or {}
                    if not isinstance(bucket, Mapping):
                        continue
                    lines = [
                        f"Score: {bucket.get('score', 0)}/100",
                        f"Label: {bucket.get('label', '')}",
                    ]
                    elements.append(Paragraph(bucket_label, styles["FindingTitle"]))
                    elements.append(Paragraph(paragraph_text(" | ".join(lines)), styles["BodyText_Custom"]))
                    dimensions = bucket.get("dimensions") or {}
                    if isinstance(dimensions, Mapping):
                        dimension_lines = []
                        for dimension_key, dimension_value in dimensions.items():
                            if isinstance(dimension_value, Mapping):
                                dimension_lines.append(
                                    f"{str(dimension_key).replace('_', ' ').title()}: "
                                    f"{dimension_value.get('label', '')} ({dimension_value.get('score', 0)}/100)"
                                )
                        _append_bullets(elements, dimension_lines, styles)
                    notes = bucket.get("notes") or []
                    if notes:
                        _append_bullets(elements, notes, styles)
                    elements.append(Spacer(1, 6))
            summary = (section.get("summary") or {}).get("diagnosis")
            if summary:
                elements.append(Paragraph(paragraph_text(summary), styles["BodyText_Custom"]))
                elements.append(Spacer(1, 6))
            continue

        if key == "entity_trust_graph":
            add_heading("Entity and Trust Graph")
            entity_graph = section.get("entity_graph") or {}
            if isinstance(entity_graph, Mapping):
                lines = [
                    f"Entity: {entity_graph.get('entity_name', '')}",
                    f"Confidence: {entity_graph.get('confidence', '')}",
                ]
                elements.append(Paragraph(paragraph_text(" | ".join(lines)), styles["BodyText_Custom"]))
                elements.append(Spacer(1, 6))
            trust_signals = section.get("trust_signals") or []
            if trust_signals:
                elements.append(Paragraph("Trust Signals", styles["SubHeader"]))
                _append_bullets(elements, trust_signals, styles)
                elements.append(Spacer(1, 6))
            profile_links = section.get("profile_links") or []
            if profile_links:
                elements.append(Paragraph("Profile Links", styles["SubHeader"]))
                rows = [["Source", "URL"]]
                for link in profile_links:
                    url = normalize_text(link)
                    if not url:
                        continue
                    parsed = urlparse(url)
                    source_label = parsed.netloc.replace("www.", "") or "Profile"
                    rows.append([source_label, url])
                if len(rows) > 1:
                    table = build_wrapped_table(
                        rows,
                        _fit_widths([150, 350], content_width),
                        styles,
                    )
                    elements.append(table)
                    elements.append(Spacer(1, 6))
            continue

        if key == "technical_geo_gates":
            add_heading("Technical GEO Gates")
            summary = section.get("summary") or {}
            if isinstance(summary, Mapping):
                elements.append(Paragraph(
                    paragraph_text(f"GEO Score: {summary.get('geo_score', 0)}/100"),
                    styles["BodyText_Custom"],
                ))
                elements.append(Spacer(1, 6))
            gates = section.get("priority_gates") or []
            if gates:
                elements.append(Paragraph("Priority Gates", styles["SubHeader"]))
                _append_bullets(elements, gates, styles)
                elements.append(Spacer(1, 6))
            crawler_access = section.get("crawler_access") or {}
            if isinstance(crawler_access, Mapping) and crawler_access:
                rows = [["Crawler", "Platform", "Status", "Recommendation"]]
                for crawler_name, info in crawler_access.items():
                    if isinstance(info, Mapping):
                        rows.append([
                            crawler_name,
                            info.get("platform", ""),
                            info.get("status", ""),
                            info.get("recommendation", ""),
                        ])
                if len(rows) > 1:
                    table = build_wrapped_table(
                        rows,
                        _fit_widths([82, 96, 88, 214], content_width),
                        styles,
                    )
                    elements.append(table)
                    elements.append(Spacer(1, 6))
            continue

        if key == "execution_ledger":
            add_heading("30/60/90 Execution Ledger")
            for label, items in (
                ("30 Days", section.get("thirty_day") or []),
                ("60 Days", section.get("sixty_day") or []),
                ("90 Days", section.get("ninety_day") or []),
            ):
                elements.append(Paragraph(label, styles["SubHeader"]))
                deduped_items = []
                seen_items = set()
                for item in items:
                    text = _report_item_text(item)
                    if not text:
                        continue
                    if text in seen_items:
                        continue
                    seen_items.add(text)
                    deduped_items.append(item)
                _append_bullets(elements, deduped_items, styles)
                elements.append(Spacer(1, 4))
            continue

        if key == "developer_appendix":
            add_heading("Developer Appendix")
            technical_actions = section.get("technical_actions") or []
            if technical_actions:
                _append_bullets(elements, technical_actions, styles)
                elements.append(Spacer(1, 6))
            notes = section.get("implementation_notes") or []
            if notes:
                elements.append(Paragraph("Implementation Notes", styles["SubHeader"]))
                _append_bullets(elements, notes, styles)
                elements.append(Spacer(1, 6))
            continue

        if key == "evidence_appendix":
            add_heading(EVIDENCE_APPENDIX_TITLE)
            methodology = section.get("methodology") or []
            if methodology:
                elements.append(Paragraph("Methodology", styles["SubHeader"]))
                _append_bullets(elements, methodology, styles)
                elements.append(Spacer(1, 6))
            evidence_items = section.get("evidence_items") or []
            if evidence_items:
                elements.append(Paragraph("Evidence Items", styles["SubHeader"]))
                _append_bullets(elements, evidence_items, styles)
                elements.append(Spacer(1, 6))


def build_wrapped_table(rows, col_widths, styles, header_rows=1, header_color=PRIMARY):
    table = Table(
        wrap_table_rows(rows, styles=styles, header_rows=header_rows),
        colWidths=col_widths,
        repeatRows=header_rows,
        splitByRow=1,
        hAlign='LEFT',
    )
    table.setStyle(make_table_style(header_color))
    return table


def build_finding_card(finding, styles, width):
    severity = finding.get("severity", "info").upper()
    title = paragraph_text(finding.get("title", ""))
    summary = finding.get("summary") or finding.get("description", "")

    if severity == "CRITICAL":
        severity_color = DANGER
    elif severity == "HIGH":
        severity_color = WARNING
    elif severity == "MEDIUM":
        severity_color = INFO
    else:
        severity_color = TEXT_SECONDARY

    content = [
        Paragraph(
            f'<font color="{severity_color.hexval()}">[{severity}]</font> <b>{title}</b>',
            styles['FindingTitle'],
        ),
        Paragraph(paragraph_text(summary), styles['FindingSummary']),
        make_label_value_paragraph(
            "Why this matters to leadership",
            finding.get("leadership_impact", "Not provided."),
            styles['FindingDetail'],
        ),
        make_label_value_paragraph(
            "What marketing should do",
            finding.get("marketing_action", "Not provided."),
            styles['FindingDetail'],
        ),
        make_label_value_paragraph(
            "What dev should change",
            finding.get("developer_action", "Not provided."),
            styles['FindingDetail'],
        ),
        make_label_value_paragraph(
            "Observed evidence",
            finding.get("observed_evidence", "Not provided."),
            styles['FindingDetail'],
        ),
    ]

    card = Table([[content]], colWidths=[width], splitByRow=1, hAlign='LEFT')
    card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.75, lightgrey),
        ('LINEBEFORE', (0, 0), (0, 0), 4, severity_color),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    return card


def _client_sections_from_data(data):
    sections = data.get("client_report_sections")
    if isinstance(sections, Mapping) and sections:
        return sections

    scores = data.get("scores", {}) if isinstance(data.get("scores"), Mapping) else {}
    findings = [item for item in data.get("findings", []) if isinstance(item, Mapping)]
    return {
        "cover": {
            "title": "GEO Client Brief",
            "subtitle": f"Business roadmap for {normalize_text(data.get('brand_name'))}",
            "website": normalize_text(data.get("url")),
            "analysis_date": normalize_text(data.get("date")),
            "readiness_snapshot": [
                {"label": "GEO", "value": f"{int(data.get('geo_score', 0))}/100"},
                {"label": "AI Citability", "value": f"{int(scores.get('ai_citability', 0))}/100"},
                {"label": "Technical", "value": f"{int(scores.get('technical', 0))}/100"},
                {"label": "Schema", "value": f"{int(scores.get('schema', 0))}/100"},
            ],
        },
        "decision_summary": {
            "overview": normalize_text(data.get("executive_summary")),
        },
        "priority_risks": {
            "items": [
                {
                    "title": normalize_text(item.get("title")),
                    "severity": normalize_text(item.get("severity")),
                    "business_impact": normalize_text(item.get("leadership_impact") or item.get("summary")),
                    "evidence": normalize_text(item.get("observed_evidence")),
                }
                for item in findings[:3]
            ],
        },
        "top_opportunities": {
            "items": [
                {
                    "title": normalize_text(item),
                    "priority": "high",
                    "why_it_matters": "Recommended next action from the current audit.",
                }
                for item in data.get("quick_wins", [])[:3]
            ],
        },
        "market_snapshot": {
            "title": "Market Visibility Snapshot",
            "summary": "The competitive picture is still incomplete in this sample, so this page highlights the known gap rather than forcing a weak benchmark.",
            "confidence": "limited",
            "benchmark_rows": [],
        },
        "roadmap": {
            "thirty_day": [normalize_text(item) for item in data.get("quick_wins", []) if normalize_text(item)],
            "sixty_day": [normalize_text(item) for item in data.get("medium_term", []) if normalize_text(item)],
            "ninety_day": [normalize_text(item) for item in data.get("strategic", []) if normalize_text(item)],
        },
        "methodology": {
            "summary": "Point-in-time GEO audit based on live crawl, content scoring, and visibility sampling.",
            "confidence_note": "Market data is directional rather than exhaustive in this run.",
        },
    }


def _append_client_list(elements, items, styles):
    for index, item in enumerate(items, 1):
        if isinstance(item, Mapping):
            title = normalize_text(
                item.get("title")
                or item.get("label")
                or item.get("action")
                or item.get("query")
            )
            details = []
            for key in (
                "severity",
                "priority",
                "opportunity_score",
                "business_impact",
                "why_it_matters",
                "evidence",
                "summary",
            ):
                value = normalize_text(item.get(key))
                if not value:
                    continue
                if key == "opportunity_score":
                    details.append(f"Opportunity Score: {value}")
                else:
                    details.append(value)
            text = f"<b>{index}. {escape(title)}</b>"
            if details:
                text += "<br/>" + "<br/>".join(paragraph_text(value) for value in details)
        else:
            text = f"<b>{index}.</b> {paragraph_text(item)}"
        elements.append(Paragraph(text, styles["Recommendation"]))


def _build_snapshot_table(snapshot_items, styles, content_width):
    rows = [["Metric", "Value"]]
    for item in snapshot_items:
        if not isinstance(item, Mapping):
            continue
        rows.append([item.get("label", ""), item.get("value", "")])
    return build_wrapped_table(
        rows,
        _fit_widths([160, max(120, content_width - 160)], content_width),
        styles,
    )


def generate_report(data, output_path="GEO-REPORT.pdf"):
    """Generate the client-facing brief PDF."""

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=55,
        bottomMargin=55,
        leftMargin=50,
        rightMargin=50,
    )

    styles = build_styles()
    # Tighten the executive brief so sparse runs stay compact without affecting workbook density.
    styles["ReportSubtitle"].spaceAfter = 14
    styles["SectionHeader"].spaceBefore = 16
    styles["SectionHeader"].spaceAfter = 8
    styles["SubHeader"].spaceBefore = 10
    styles["BodyText_Custom"].leading = 13
    styles["Recommendation"].leading = 13
    styles["Recommendation"].spaceBefore = 2
    styles["Recommendation"].spaceAfter = 2
    styles["HighlightBox"].spaceBefore = 4
    styles["HighlightBox"].spaceAfter = 4
    elements = []
    content_width = doc.width
    client_sections = _client_sections_from_data(data)

    cover = client_sections.get("cover", {}) if isinstance(client_sections, Mapping) else {}
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(cover.get("title", "GEO Client Brief"), styles["ReportTitle"]))
    elements.append(Spacer(1, 4))
    if cover.get("subtitle"):
        elements.append(Paragraph(paragraph_text(cover.get("subtitle")), styles["ReportSubtitle"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=16))

    details_rows = [
        [
            Paragraph(paragraph_text("Website"), styles["TableLabelCell"]),
            Paragraph(paragraph_text(cover.get("website") or data.get("url")), styles["TableCell"]),
        ],
        [
            Paragraph(paragraph_text("Analysis Date"), styles["TableLabelCell"]),
            Paragraph(paragraph_text(cover.get("analysis_date") or data.get("date")), styles["TableCell"]),
        ],
    ]
    details_table = Table(details_rows, colWidths=[112, 368], hAlign="LEFT")
    details_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, lightgrey),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 12))

    snapshot_items = cover.get("readiness_snapshot") or []
    if snapshot_items:
        elements.append(Paragraph("Readiness Snapshot", styles["SubHeader"]))
        elements.append(_build_snapshot_table(snapshot_items, styles, content_width))
        elements.append(Spacer(1, 10))

    decision_summary = client_sections.get("decision_summary", {}) if isinstance(client_sections, Mapping) else {}
    elements.append(Paragraph("Decision Summary", styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10))
    elements.append(
        Paragraph(
            paragraph_text(decision_summary.get("overview") or data.get("executive_summary") or "No summary available."),
            styles["BodyText_Custom"],
        )
    )
    elements.append(Spacer(1, 12))

    risk_section = client_sections.get("priority_risks", {}) if isinstance(client_sections, Mapping) else {}
    elements.append(Paragraph("Top Risks", styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10))
    risk_items = risk_section.get("items") or []
    if risk_items:
        _append_client_list(elements, risk_items, styles)
    else:
        elements.append(Paragraph("No major risks were surfaced in this run.", styles["BodyText_Custom"]))
    elements.append(Spacer(1, 12))

    opportunity_section = client_sections.get("top_opportunities", {}) if isinstance(client_sections, Mapping) else {}
    elements.append(Paragraph("Top Opportunities", styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10))
    opportunity_items = opportunity_section.get("items") or []
    if opportunity_items:
        _append_client_list(elements, opportunity_items, styles)
    else:
        elements.append(Paragraph("No priority opportunities were surfaced in this run.", styles["BodyText_Custom"]))
    elements.append(Spacer(1, 12))

    market_snapshot = client_sections.get("market_snapshot", {}) if isinstance(client_sections, Mapping) else {}
    elements.append(Paragraph(market_snapshot.get("title", "Market Visibility Snapshot"), styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10))
    elements.append(Paragraph(paragraph_text(market_snapshot.get("summary")), styles["BodyText_Custom"]))
    benchmark_rows = market_snapshot.get("benchmark_rows") or []
    if benchmark_rows:
        rows = [["Source", "Bucket", "Why It Matters"]]
        for row in benchmark_rows:
            if not isinstance(row, Mapping):
                continue
            rows.append([
                row.get("label", ""),
                row.get("bucket", ""),
                row.get("summary", ""),
            ])
        elements.append(Spacer(1, 8))
        elements.append(
            build_wrapped_table(
                rows,
                _fit_widths([140, 110, 262], content_width),
                styles,
            )
        )
    elements.append(Spacer(1, 12))

    roadmap = client_sections.get("roadmap", {}) if isinstance(client_sections, Mapping) else {}
    elements.append(Paragraph("30/60/90 Roadmap", styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10))
    for label, items in (
        ("30 Days", roadmap.get("thirty_day") or []),
        ("60 Days", roadmap.get("sixty_day") or []),
        ("90 Days", roadmap.get("ninety_day") or []),
    ):
        elements.append(Paragraph(label, styles["SubHeader"]))
        if items:
            _append_client_list(elements, items, styles)
        else:
            elements.append(Paragraph("No actions captured.", styles["BodyText_Custom"]))
        elements.append(Spacer(1, 6))

    methodology = client_sections.get("methodology", {}) if isinstance(client_sections, Mapping) else {}
    elements.append(Paragraph("Methodology and Confidence", styles["SectionHeader"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10))
    elements.append(Paragraph(paragraph_text(methodology.get("summary")), styles["BodyText_Custom"]))
    confidence_note = normalize_text(methodology.get("confidence_note"))
    if confidence_note:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(paragraph_text(confidence_note), styles["HighlightBox"]))

    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    return output_path


def generate_playbook_report(data, output_path="GEO-STRATEGIST-PLAYBOOK.pdf"):
    """Generate the 10-page GEO Playbook style report."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=55,
        bottomMargin=55,
        leftMargin=50,
        rightMargin=50,
    )

    styles = build_styles()
    elements = []
    content_width = doc.width

    # Extract playbook sections
    playbook_sections = data.get("playbook_report_sections", {})
    if not playbook_sections:
        # Fallback to workbook generator if playbook data is missing
        return generate_workbook_report(data, output_path)

    brand_name = data.get("brand_name", "Brand")
    url = data.get("url", "https://example.com")

    # ============================================================
    # PAGE 1: EXECUTIVE SUMMARY & THE "WHY"
    # ============================================================
    p1 = playbook_sections.get("page1_executive_summary", {})
    elements.append(Paragraph("Page 1: Executive Summary & The 'Why' of GEO", styles['PlaybookPageHeader']))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=20))

    elements.append(Paragraph(
        "<b>The Shift: From Searching for Links to Generating Answers</b>",
        styles['SubHeader']
    ))
    elements.append(Paragraph(
        "Traditional SEO is about ranking #1. GEO (Generative Engine Optimization) is about becoming the "
        "<i>source of truth</i> cited by AI models like ChatGPT, Claude, and Gemini.",
        styles['BodyText_Custom']
    ))

    elements.append(Spacer(1, 15))

    # Score Gauge and Brief
    gauge = create_score_gauge(p1.get("geo_score", 0), 180, 180)
    elements.append(gauge)

    elements.append(Paragraph(
        f"<b>AI Visibility Score: {p1.get('geo_score', 0)}/100</b>",
        ParagraphStyle('ScoreTitle', parent=styles['SubHeader'], alignment=TA_CENTER)
    ))

    elements.append(Spacer(1, 15))

    elements.append(Paragraph("Strategic Overview", styles['SubHeader']))
    elements.append(Paragraph(paragraph_text(p1.get("overview")), styles['BodyText_Custom']))

    elements.append(Paragraph("Business Impact & ROI", styles['SubHeader']))
    _append_bullets(elements, p1.get("key_takeaways", []), styles)

    elements.append(PageBreak())

    # ============================================================
    # PAGE 2: GEO PARADIGM & ARCHITECTURE
    # ============================================================
    p2 = playbook_sections.get("page2_geo_paradigm", {})
    elements.append(Paragraph("Page 2: The GEO Paradigm & Architecture", styles['PlaybookPageHeader']))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=20))

    elements.append(Paragraph("The AI Search Funnel Status", styles['SubHeader']))
    funnel = p2.get("funnel_status", {})
    funnel_rows = [
        ["Phase", "Agent", "Status", "Optimization Needed"],
        ["1. Crawl", "GPTBot, ClaudeBot", funnel.get("crawl", "unknown"), "SSR, robots.txt, llms.txt"],
        ["2. Index", "Librarian (Vectorize)", funnel.get("index", "unknown"), "Answer Blocks, Headings"],
        ["3. Retrieval", "RAG (Vector Search)", funnel.get("retrieval", "unknown"), "Claim-Based Architecture"],
        ["4. Generation", "The LLM Writer", "pending", "Entity Verification"],
    ]
    elements.append(build_wrapped_table(funnel_rows, _fit_widths([100, 120, 100, 180], content_width), styles))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("The 4 Pillars of GEO Readiness", styles['SubHeader']))
    _append_bullets(elements, p2.get("pillars", []), styles)

    elements.append(PageBreak())

    # ============================================================
    # PAGE 3: STRATEGIC IMPLEMENTATION (MARKETING VIEW)
    # ============================================================
    p3 = playbook_sections.get("page3_strategic_implementation", {})
    elements.append(Paragraph("Page 3: Strategic Implementation (Marketing View)", styles['PlaybookPageHeader']))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=20))

    elements.append(Paragraph("From Keywords to 'Answer Blocks'", styles['SubHeader']))
    elements.append(Paragraph(
        "In traditional SEO, we targeted keywords. In GEO, we target <b>Questions</b> and <b>Entities</b>. "
        "The goal is to provide specific <i>Answer Blocks</i> (40-60 words) that directly answer user queries.",
        styles['BodyText_Custom']
    ))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("High-Priority Service Line Query Themes", styles['SubHeader']))
    themes = p3.get("service_line_themes", [])
    if themes:
        theme_rows = [["Service Line", "Visibility", "Opportunity Score"]]
        for t in themes:
            theme_rows.append([t.get("service_line"), t.get("visibility"), f"{t.get('opportunity_score')}/100"])
        elements.append(build_wrapped_table(theme_rows, _fit_widths([200, 150, 150], content_width), styles))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("Recommended GEO Methods", styles['SubHeader']))
    _append_bullets(elements, p3.get("recommended_methods", []), styles)

    elements.append(PageBreak())

    # ============================================================
    # PAGE 4: CONTENT TACTICS & 'CITABILITY'
    # ============================================================
    p4 = playbook_sections.get("page4_content_citability", {})
    elements.append(Paragraph("Page 4: Content Tactics & 'Citability'", styles['PlaybookPageHeader']))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=20))

    elements.append(Paragraph(
        "AI models prioritize content with high information-per-word ratios. Use specific entities and remove transition fluff.",
        styles['BodyText_Custom']
    ))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("The Citability Checklist Status", styles['SubHeader']))
    checklist = p4.get("checklist_status", {})
    for label, score in checklist.items():
        elements.append(Paragraph(f"<b>{label.replace('_', ' ').title()}:</b> {score}/100", styles['BodyText_Custom']))
        # Add a small progress bar
        bar_w = content_width * (score / 100)
        d = Drawing(content_width, 10)
        d.add(Rect(0, 0, content_width, 10, fillColor=LIGHT_BG, strokeWidth=0))
        d.add(Rect(0, 0, bar_w, 10, fillColor=get_score_color(score), strokeWidth=0))
        elements.append(d)
        elements.append(Spacer(1, 5))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("Observed Citation Failures", styles['SubHeader']))
    _append_bullets(elements, p4.get("failures", []), styles)

    elements.append(PageBreak())

    # ============================================================
    # PAGE 5: BRAND & ENTITY VERIFICATION
    # ============================================================
    p5 = playbook_sections.get("page5_brand_entity_verification", {})
    elements.append(Paragraph("Page 5: Brand & Entity Verification", styles['PlaybookPageHeader']))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=20))

    elements.append(Paragraph(
        "AI doesn't just read text; it builds a map of 'Entities'. If you are not a defined Entity, the AI might hallucinate facts about you.",
        styles['BodyText_Custom']
    ))

    elements.append(Paragraph("Entity: " + p5.get("entity_name", brand_name), styles['SubHeader']))
    elements.append(Paragraph(f"<b>Knowledge Graph Confidence:</b> {p5.get('knowledge_graph_confidence', '0%')}", styles['BodyText_Custom']))

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("Digital Footprint (Profile Links)", styles['SubHeader']))
    _append_bullets(elements, p5.get("profile_links", []), styles)

    elements.append(Spacer(1, 15))
    elements.append(Paragraph("Authority Signals", styles['SubHeader']))
    _append_bullets(elements, p5.get("trust_signals", []), styles)

    elements.append(PageBreak())

    # ============================================================
    # PAGE 6: TECHNICAL IMPLEMENTATION
    # ============================================================
    p6 = playbook_sections.get("page6_technical_implementation", {})
    elements.append(Paragraph("Page 6: Technical Implementation (Developer View)", styles['PlaybookPageHeader']))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=20))

    elements.append(Paragraph("The New Standards", styles['SubHeader']))
    tech_data = [
        ["Standard", "Status", "Action"],
        ["llms.txt (AI Sitemap)", "Found" if p6.get("llms_txt_exists") else "Missing", "Create machine-readable crawl map"],
        ["SSR (Server Rendering)", "Enabled" if p6.get("ssr_status") else "Disabled", "Ensure bots see static HTML"],
        ["Schema.org (LD+JSON)", f"{p6.get('schema_score')}/100", "Add Organization, Article, FAQ schema"],
    ]
    elements.append(build_wrapped_table(tech_data, _fit_widths([150, 100, 250], content_width), styles))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("AI Crawler Access Status", styles['SubHeader']))
    crawler_rows = [["Crawler", "Platform", "Status"]]
    for c, info in p6.get("crawler_access", {}).items():
        if isinstance(info, Mapping):
            crawler_rows.append([c, info.get("platform"), info.get("status")])
    elements.append(build_wrapped_table(crawler_rows, _fit_widths([150, 150, 200], content_width), styles))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 7: THE AUDIT PROCESS
    # ============================================================
    p7 = playbook_sections.get("page7_audit_process", {})
    elements.append(Paragraph("Page 7: The Audit Process & Scores", styles['PlaybookPageHeader']))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=20))

    elements.append(Paragraph("AI Visibility Score Breakdown", styles['SubHeader']))
    comp_rows = [["Component", "Score", "Weight"]]
    for c in p7.get("components", []):
        comp_rows.append([c.get("label"), f"{c.get('score')}/100", f"{c.get('weight')}%"])
    elements.append(build_wrapped_table(comp_rows, _fit_widths([250, 150, 100], content_width), styles))

    elements.append(Spacer(20, 20))
    elements.append(Paragraph("AI Platform Readiness", styles['SubHeader']))
    platform_rows = [["AI Platform", "Score", "Status"]]
    for plat in p7.get("platforms", []):
        platform_rows.append([plat.get("platform"), f"{plat.get('score')}/100", plat.get("status")])
    elements.append(build_wrapped_table(platform_rows, _fit_widths([200, 100, 200], content_width), styles))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 8: DIAGNOSIS & TROUBLESHOOTING
    # ============================================================
    p8 = playbook_sections.get("page8_diagnosis_troubleshooting", {})
    elements.append(Paragraph("Page 8: Diagnosis & Troubleshooting", styles['PlaybookPageHeader']))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=20))

    elements.append(Paragraph("Common Scenarios & Visibility Issues", styles['SubHeader']))
    _append_bullets(elements, p8.get("visibility_issues", []), styles)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Diagnosis Checklist", styles['SubHeader']))
    _append_bullets(elements, p8.get("troubleshooting_notes", []), styles)

    elements.append(PageBreak())

    # ============================================================
    # PAGE 9: FAQ BY ROLE
    # ============================================================
    p9 = playbook_sections.get("page9_faq_by_role", {})
    elements.append(Paragraph("Page 9: FAQ by Role", styles['PlaybookPageHeader']))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=20))

    for role, summary in p9.get("role_summaries", {}).items():
        elements.append(Paragraph(role.replace("_", " ").title(), styles['SubHeader']))
        elements.append(Paragraph(paragraph_text(summary), styles['BodyText_Custom']))
        elements.append(Spacer(1, 15))

    elements.append(PageBreak())

    # ============================================================
    # PAGE 10: ROADMAP & FUTURE
    # ============================================================
    p10 = playbook_sections.get("page10_roadmap_future", {})
    elements.append(Paragraph("Page 10: Roadmap & The Future of Search", styles['PlaybookPageHeader']))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=20))

    elements.append(Paragraph("Implementation Roadmap", styles['SubHeader']))
    for label, items in (("30 Days", p10.get("thirty_day")), ("60 Days", p10.get("sixty_day")), ("90 Days", p10.get("ninety_day"))):
        elements.append(Paragraph(label, styles['SubHeader']))
        _append_bullets(elements, items, styles)
        elements.append(Spacer(1, 10))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "<b>The Future: Agentic Web & Multi-Modal Search</b>",
        styles['CalloutBox']
    ))

    # Footer disclaimer on last page
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=lightgrey, spaceAfter=8))
    elements.append(Paragraph(
        "This report was generated according to the 2026 GEO Playbook standards. "
        "Verified by GEO-SEO Strategist AI.",
        styles['SmallText']
    ))

    # ============================================================
    # BUILD PDF
    # ============================================================
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    return output_path


def generate_workbook_report(data, output_path="GEO-STRATEGIST-WORKBOOK.pdf"):
    """Generate the full PDF report from audit data, using Playbook layout if available."""

    if data.get("playbook_report_sections"):
        return generate_playbook_report(data, output_path)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=55,
        bottomMargin=55,
        leftMargin=50,
        rightMargin=50,
    )

    styles = build_styles()
    elements = []
    content_width = doc.width

    # Extract data with defaults
    url = data.get("url", "https://example.com")
    brand_name = data.get("brand_name", url.replace("https://", "").replace("http://", "").split("/")[0])
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    geo_score = data.get("geo_score", 0)

    scores = data.get("scores", {})
    ai_citability = scores.get("ai_citability", 0)
    brand_authority = scores.get("brand_authority", 0)
    content_eeat = scores.get("content_eeat", 0)
    technical = scores.get("technical", 0)
    schema_score = scores.get("schema", 0)
    platform_optimization = scores.get("platform_optimization", 0)

    platforms = data.get("platforms", {
        "Google AI Overviews": 0,
        "ChatGPT": 0,
        "Perplexity": 0,
        "Gemini": 0,
        "Bing Copilot": 0,
    })

    findings = data.get("findings", [])
    quick_wins = data.get("quick_wins", [])
    medium_term = data.get("medium_term", [])
    strategic = data.get("strategic", [])
    executive_summary = data.get("executive_summary", "")
    rescience_pass = data.get("rescience_pass", {})
    crawler_access = data.get("crawler_access", {})
    report_sections = normalize_report_sections(data.get("report_sections"))
    if not report_sections and data.get("crawler_access"):
        report_sections = {
            "technical_geo_gates": {
                "summary": {"geo_score": geo_score, "platforms": platforms},
                "priority_gates": [],
                "crawler_access": data.get("crawler_access", {}),
            }
        }
    decision_summary = (
        report_sections.get("decision_summary")
        if isinstance(report_sections, Mapping)
        else {}
    )

    # ============================================================
    # COVER PAGE
    # ============================================================
    elements.append(Spacer(1, 48))

    # Title
    elements.append(Paragraph("GEO Strategist Workbook", styles['ReportTitle']))
    elements.append(Spacer(1, 12))

    # Subtitle
    elements.append(Paragraph(
        f"Internal GEO/SEO operating report for <b>{brand_name}</b>",
        styles['ReportSubtitle']
    ))

    elements.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=20))

    # Key details table
    details_data = [
        [
            Paragraph(paragraph_text("Website"), styles['TableLabelCell']),
            Paragraph(paragraph_text(url), styles['TableCell']),
        ],
        [
            Paragraph(paragraph_text("Analysis Date"), styles['TableLabelCell']),
            Paragraph(
                paragraph_text(datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y") if "-" in date else date),
                styles['TableCell'],
            ),
        ],
        [
            Paragraph(paragraph_text("Readiness Snapshot"), styles['TableLabelCell']),
            Paragraph(paragraph_text(
                f"GEO {geo_score}/100 | AI Citability {ai_citability}/100 | "
                f"Technical {technical}/100 | Schema {schema_score}/100"
            ), styles['TableCell']),
        ],
    ]

    details_table = Table(details_data, colWidths=[112, 368], hAlign='LEFT')
    details_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, lightgrey),
    ]))
    elements.append(details_table)

    overview = ""
    if isinstance(decision_summary, Mapping):
        overview = decision_summary.get("overview", "")
    if not overview:
        overview = executive_summary
    if overview:
        elements.append(Spacer(1, 18))
        elements.append(Paragraph("Decision Summary", styles["SectionHeader"]))
        elements.append(Paragraph(paragraph_text(overview), styles["BodyText_Custom"]))
        elements.append(Spacer(1, 8))

    # Score gauge
    gauge = create_score_gauge(geo_score, 200, 200)
    elements.append(gauge)

    elements.append(Spacer(1, 20))

    # Score label
    score_color = get_score_color(geo_score)
    elements.append(Paragraph(
        f'<font color="{score_color.hexval()}">{get_score_label(geo_score)}</font>',
        ParagraphStyle('ScoreLabelColored', parent=styles['SectionHeader'],
                       alignment=TA_CENTER, fontSize=20)
    ))

    elements.append(PageBreak())

    # ============================================================
    # EXECUTIVE SUMMARY
    # ============================================================
    elements.append(Paragraph("Executive Summary", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    if executive_summary:
        elements.append(Paragraph(executive_summary, styles['BodyText_Custom']))
    else:
        elements.append(Paragraph(
            f"This report presents the findings of a comprehensive Generative Engine Optimization (GEO) "
            f"audit conducted on <b>{brand_name}</b> ({url}). The analysis evaluated the website's readiness "
            f"for AI-powered search engines including Google AI Overviews, ChatGPT, Perplexity, Gemini, "
            f"and Bing Copilot. The overall GEO Readiness Score is <b>{geo_score}/100</b>, "
            f"placing the site in the <b>{get_score_label(geo_score)}</b> tier.",
            styles['BodyText_Custom']
        ))

    elements.append(Spacer(1, 16))

    # ============================================================
    # SCORE BREAKDOWN
    # ============================================================
    elements.append(Paragraph("GEO Score Breakdown", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    score_data = [
        ["Component", "Score", "Weight", "Weighted"],
        ["AI Citability & Visibility", f"{ai_citability}/100", "25%", f"{round(ai_citability * 0.25, 1)}"],
        ["Brand Authority Signals", f"{brand_authority}/100", "20%", f"{round(brand_authority * 0.20, 1)}"],
        ["Content Quality & E-E-A-T", f"{content_eeat}/100", "20%", f"{round(content_eeat * 0.20, 1)}"],
        ["Technical Foundations", f"{technical}/100", "15%", f"{round(technical * 0.15, 1)}"],
        ["Structured Data", f"{schema_score}/100", "10%", f"{round(schema_score * 0.10, 1)}"],
        ["Platform Optimization", f"{platform_optimization}/100", "10%", f"{round(platform_optimization * 0.10, 1)}"],
        ["OVERALL", f"{geo_score}/100", "100%", f"{geo_score}"],
    ]

    score_table = Table(score_data, colWidths=[200, 80, 60, 80])
    style = make_table_style()

    # Bold the last row
    style.add('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    style.add('BACKGROUND', (0, -1), (-1, -1), MEDIUM_BG)

    # Color-code score cells
    for i in range(1, len(score_data) - 1):
        score_val = int(score_data[i][1].split("/")[0])
        color = get_score_color(score_val)
        style.add('TEXTCOLOR', (1, i), (1, i), color)

    score_table.setStyle(style)
    elements.append(score_table)

    elements.append(Spacer(1, 16))

    # Score bar chart
    chart_scores = [ai_citability, brand_authority, content_eeat, technical, schema_score, platform_optimization]
    chart_labels = ["Citability", "Brand", "Content", "Technical", "Schema", "Platform"]
    elements.append(create_bar_chart(chart_scores, chart_labels))

    elements.append(PageBreak())

    # ============================================================
    # AI PLATFORM READINESS
    # ============================================================
    elements.append(Paragraph("AI Platform Readiness", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    elements.append(Paragraph(
        "These scores reflect how likely your content is to be cited by each AI search platform. "
        "A score below 50 indicates significant barriers to citation on that platform.",
        styles['BodyText_Custom']
    ))
    elements.append(Spacer(1, 10))

    # Platform chart
    if platforms:
        elements.append(create_platform_chart(platforms))

    elements.append(Spacer(1, 10))

    # Platform table
    platform_table_data = [["AI Platform", "Score", "Status"]]
    for name, score in platforms.items():
        status = get_score_label(score)
        platform_table_data.append([name, f"{score}/100", status])

    pt = Table(platform_table_data, colWidths=[180, 80, 150])
    pt_style = make_table_style()
    for i in range(1, len(platform_table_data)):
        score_val = int(platform_table_data[i][1].split("/")[0])
        color = get_score_color(score_val)
        pt_style.add('TEXTCOLOR', (1, i), (1, i), color)
    pt.setStyle(pt_style)
    elements.append(pt)

    elements.append(PageBreak())

    # ============================================================
    # AI CRAWLER ACCESS
    # ============================================================
    elements.append(Paragraph("AI Crawler Access Status", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    elements.append(Paragraph(
        "Blocking AI crawlers prevents AI platforms from citing your content. "
        "The table below shows which AI crawlers can currently access your site.",
        styles['BodyText_Custom']
    ))
    elements.append(Spacer(1, 8))

    if crawler_access:
        # Use Paragraph objects for text wrapping in cells
        cell_style = ParagraphStyle(
            'CrawlerCell', fontName='Helvetica', fontSize=9,
            textColor=TEXT_PRIMARY, leading=12,
        )
        header_cell_style = ParagraphStyle(
            'CrawlerHeaderCell', fontName='Helvetica-Bold', fontSize=9,
            textColor=WHITE, leading=12,
        )
        status_style_allowed = ParagraphStyle(
            'StatusAllowed', fontName='Helvetica-Bold', fontSize=9,
            textColor=SUCCESS, leading=12,
        )
        status_style_blocked = ParagraphStyle(
            'StatusBlocked', fontName='Helvetica-Bold', fontSize=9,
            textColor=DANGER, leading=12,
        )
        status_style_restricted = ParagraphStyle(
            'StatusRestricted', fontName='Helvetica-Bold', fontSize=9,
            textColor=WARNING, leading=12,
        )
        status_style_default = ParagraphStyle(
            'StatusDefault', fontName='Helvetica', fontSize=9,
            textColor=TEXT_PRIMARY, leading=12,
        )

        crawler_data = [[
            Paragraph("Crawler", header_cell_style),
            Paragraph("Platform", header_cell_style),
            Paragraph("Status", header_cell_style),
            Paragraph("Recommendation", header_cell_style),
        ]]
        for crawler_name, info in crawler_access.items():
            if isinstance(info, dict):
                status_text = info.get("status", "Unknown")
                status_upper = status_text.upper()
                if "ALLOW" in status_upper:
                    s_style = status_style_allowed
                elif "BLOCK" in status_upper:
                    s_style = status_style_blocked
                elif "RESTRICT" in status_upper:
                    s_style = status_style_restricted
                else:
                    s_style = status_style_default

                crawler_data.append([
                    Paragraph(crawler_name, cell_style),
                    Paragraph(info.get("platform", ""), cell_style),
                    Paragraph(status_text, s_style),
                    Paragraph(info.get("recommendation", ""), cell_style),
                ])
            else:
                crawler_data.append([
                    Paragraph(crawler_name, cell_style),
                    Paragraph("", cell_style),
                    Paragraph(str(info), cell_style),
                    Paragraph("", cell_style),
                ])

        # Full page width: letter (612pt) - 50pt margins each side = 512pt
        ct = Table(crawler_data, colWidths=[90, 110, 72, 240])
        ct_style = make_table_style()
        ct_style.add('VALIGN', (0, 0), (-1, -1), 'TOP')

        ct.setStyle(ct_style)
        elements.append(ct)
    else:
        elements.append(Paragraph(
            "<i>Run /geo crawlers to populate this section with AI crawler access data.</i>",
            styles['BodyText_Custom']
        ))

    elements.append(PageBreak())
    if isinstance(report_sections, Mapping):
        render_report_sections(elements, report_sections, styles, content_width)
        elements.append(PageBreak())

    # ============================================================
    # KEY FINDINGS
    # ============================================================
    elements.append(Paragraph("Key Findings", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    if findings:
        for finding in findings:
            elements.append(build_finding_card(finding, styles, content_width))
            elements.append(Spacer(1, 10))
    else:
        elements.append(Paragraph(
            "<i>Run a full /geo audit to populate findings.</i>",
            styles['BodyText_Custom']
        ))

    elements.append(PageBreak())

    # ============================================================
    # PRIORITIZED ACTION PLAN
    # ============================================================
    elements.append(Paragraph("Prioritized Action Plan", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    # Quick Wins
    elements.append(Paragraph("Quick Wins (This Week)", styles['SubHeader']))
    elements.append(Paragraph(
        "High impact, low effort — can be implemented immediately.",
        styles['SmallText']
    ))

    if quick_wins:
        for i, action in enumerate(quick_wins, 1):
            if isinstance(action, dict):
                text = f"<b>{i}.</b> {action.get('action', '')} — <i>{action.get('impact', '')}</i>"
            else:
                text = f"<b>{i}.</b> {action}"
            elements.append(Paragraph(text, styles['Recommendation']))
    else:
        default_wins = [
            "Allow all Tier 1 AI crawlers in robots.txt (GPTBot, ClaudeBot, PerplexityBot)",
            "Add publication and last-updated dates to all content pages",
            "Add author bylines with credentials to blog posts and articles",
            "Create an llms.txt file to guide AI systems to your key content",
            "Add sameAs properties to Organization schema linking to all platform profiles",
        ]
        for i, action in enumerate(default_wins, 1):
            elements.append(Paragraph(f"<b>{i}.</b> {action}", styles['Recommendation']))

    elements.append(Spacer(1, 12))

    # Medium-Term
    elements.append(Paragraph("Medium-Term Improvements (This Month)", styles['SubHeader']))
    elements.append(Paragraph(
        "Significant impact, moderate effort — requires content or technical changes.",
        styles['SmallText']
    ))

    if medium_term:
        for i, action in enumerate(medium_term, 1):
            if isinstance(action, dict):
                text = f"<b>{i}.</b> {action.get('action', '')} — <i>{action.get('impact', '')}</i>"
            else:
                text = f"<b>{i}.</b> {action}"
            elements.append(Paragraph(text, styles['Recommendation']))
    else:
        default_medium = [
            "Restructure top 10 pages with question-based headings and direct answer blocks",
            "Implement comprehensive Organization + Article + Person schema markup",
            "Optimize content blocks for AI citability (134-167 word self-contained passages)",
            "Ensure server-side rendering for all public content pages",
            "Implement IndexNow protocol for Bing/Copilot indexing speed",
        ]
        for i, action in enumerate(default_medium, 1):
            elements.append(Paragraph(f"<b>{i}.</b> {action}", styles['Recommendation']))

    elements.append(Spacer(1, 12))

    # Strategic
    elements.append(Paragraph("Strategic Initiatives (This Quarter)", styles['SubHeader']))
    elements.append(Paragraph(
        "Long-term competitive advantage — requires ongoing investment.",
        styles['SmallText']
    ))

    if strategic:
        for i, action in enumerate(strategic, 1):
            if isinstance(action, dict):
                text = f"<b>{i}.</b> {action.get('action', '')} — <i>{action.get('impact', '')}</i>"
            else:
                text = f"<b>{i}.</b> {action}"
            elements.append(Paragraph(text, styles['Recommendation']))
    else:
        default_strategic = [
            "Build Wikipedia/Wikidata entity presence through press coverage and notability",
            "Develop active Reddit community engagement strategy in relevant subreddits",
            "Create YouTube content strategy aligned with AI-searched queries",
            "Establish original research/data publication program for unique citability",
            "Build topical authority through comprehensive content clusters",
        ]
        for i, action in enumerate(default_strategic, 1):
            elements.append(Paragraph(f"<b>{i}.</b> {action}", styles['Recommendation']))

    if rescience_pass:
        elements.append(PageBreak())

        elements.append(Paragraph("ReScience Optimization Pass", styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

        summary = rescience_pass.get("summary", "")
        if summary:
            elements.append(Paragraph(summary, styles['BodyText_Custom']))
            elements.append(Spacer(1, 10))

        priority_actions = rescience_pass.get("priority_actions", {})
        for label in ("P0", "P1", "P2"):
            elements.append(Paragraph(f"{label} Priorities", styles['SubHeader']))
            items = priority_actions.get(label, [])
            if items:
                for item in items:
                    elements.append(Paragraph(f"- {item}", styles['Recommendation']))
            else:
                elements.append(Paragraph("- None identified.", styles['Recommendation']))
            elements.append(Spacer(1, 6))

        platform_guidance = rescience_pass.get("platform_guidance", {})
        if platform_guidance:
            elements.append(Paragraph("Platform Guidance", styles['SubHeader']))
            for platform_name, items in platform_guidance.items():
                elements.append(Paragraph(platform_name, styles['BodyText_Custom']))
                for item in items:
                    elements.append(Paragraph(f"- {item}", styles['Recommendation']))
                elements.append(Spacer(1, 4))

        geo_methods = rescience_pass.get("geo_methods", [])
        if geo_methods:
            elements.append(Paragraph("Recommended GEO Methods", styles['SubHeader']))
            for method in geo_methods:
                text = (
                    f"<b>{method.get('method', '')}</b> "
                    f"({method.get('impact', '')})"
                )
                recommendation = method.get("recommendation", "")
                if recommendation:
                    text += f": {recommendation}"
                elements.append(Paragraph(text, styles['Recommendation']))

    if rescience_pass:
        elements.append(Spacer(1, 12))
    else:
        elements.append(PageBreak())

    # ============================================================
    # METHODOLOGY & GLOSSARY
    # ============================================================
    elements.append(Paragraph("Appendix: Methodology", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    elements.append(Paragraph(
        f"This GEO audit was conducted on {date} analyzing {url}. "
        "The analysis evaluated the website across six dimensions: AI Citability & Visibility (25%), "
        "Brand Authority Signals (20%), Content Quality & E-E-A-T (20%), Technical Foundations (15%), "
        "Structured Data (10%), and Platform Optimization (10%).",
        styles['BodyText_Custom']
    ))

    elements.append(Spacer(1, 8))

    elements.append(Paragraph(
        "<b>Platforms assessed:</b> Google AI Overviews, ChatGPT Web Search, Perplexity AI, "
        "Google Gemini, Bing Copilot",
        styles['BodyText_Custom']
    ))

    elements.append(Paragraph(
        "<b>Standards referenced:</b> Google Search Quality Rater Guidelines (Dec 2025), "
        "Schema.org specification, Core Web Vitals (2026 thresholds), "
        "llms.txt emerging standard, RSL 1.0 licensing framework",
        styles['BodyText_Custom']
    ))

    elements.append(Spacer(1, 16))

    # Glossary
    elements.append(Paragraph("Glossary", styles['SubHeader']))

    glossary = [
        ["Term", "Definition"],
        ["GEO", "Generative Engine Optimization — optimizing content for AI search citation"],
        ["AIO", "AI Overviews — Google's AI-generated answer boxes in search results"],
        ["E-E-A-T", "Experience, Expertise, Authoritativeness, Trustworthiness"],
        ["SSR", "Server-Side Rendering — generating HTML on the server for crawler access"],
        ["CWV", "Core Web Vitals — Google's page experience metrics (LCP, INP, CLS)"],
        ["INP", "Interaction to Next Paint — responsiveness metric (replaced FID March 2024)"],
        ["JSON-LD", "JavaScript Object Notation for Linked Data — preferred structured data format"],
        ["sameAs", "Schema.org property linking an entity to its profiles on other platforms"],
        ["llms.txt", "Proposed standard file for guiding AI systems about site content"],
        ["IndexNow", "Protocol for instantly notifying search engines of content changes"],
    ]

    gt = build_wrapped_table(
        glossary,
        col_widths=[90, 390],
        styles=styles,
    )
    gt.setStyle(make_table_style())
    elements.append(gt)

    elements.append(Spacer(1, 30))

    # Footer disclaimer
    elements.append(HRFlowable(width="100%", thickness=0.5, color=lightgrey, spaceAfter=8))
    elements.append(Paragraph(
        "This report was generated by the GEO-SEO Claude Code Analysis Tool. "
        "Scores and recommendations are based on automated analysis and industry benchmarks. "
        "Results should be validated with platform-specific testing.",
        styles['SmallText']
    ))

    # ============================================================
    # BUILD PDF
    # ============================================================
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    return output_path
    elements = []
    content_width = doc.width

    # Extract data with defaults
    url = data.get("url", "https://example.com")
    brand_name = data.get("brand_name", url.replace("https://", "").replace("http://", "").split("/")[0])
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    geo_score = data.get("geo_score", 0)

    scores = data.get("scores", {})
    ai_citability = scores.get("ai_citability", 0)
    brand_authority = scores.get("brand_authority", 0)
    content_eeat = scores.get("content_eeat", 0)
    technical = scores.get("technical", 0)
    schema_score = scores.get("schema", 0)
    platform_optimization = scores.get("platform_optimization", 0)

    platforms = data.get("platforms", {
        "Google AI Overviews": 0,
        "ChatGPT": 0,
        "Perplexity": 0,
        "Gemini": 0,
        "Bing Copilot": 0,
    })

    findings = data.get("findings", [])
    quick_wins = data.get("quick_wins", [])
    medium_term = data.get("medium_term", [])
    strategic = data.get("strategic", [])
    executive_summary = data.get("executive_summary", "")
    rescience_pass = data.get("rescience_pass", {})
    crawler_access = data.get("crawler_access", {})
    report_sections = normalize_report_sections(data.get("report_sections"))
    if not report_sections and data.get("crawler_access"):
        report_sections = {
            "technical_geo_gates": {
                "summary": {"geo_score": geo_score, "platforms": platforms},
                "priority_gates": [],
                "crawler_access": data.get("crawler_access", {}),
            }
        }
    decision_summary = (
        report_sections.get("decision_summary")
        if isinstance(report_sections, Mapping)
        else {}
    )

    # ============================================================
    # COVER PAGE
    # ============================================================
    elements.append(Spacer(1, 48))

    # Title
    elements.append(Paragraph("GEO Strategist Workbook", styles['ReportTitle']))
    elements.append(Spacer(1, 12))

    # Subtitle
    elements.append(Paragraph(
        f"Internal GEO/SEO operating report for <b>{brand_name}</b>",
        styles['ReportSubtitle']
    ))

    elements.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=20))

    # Key details table
    details_data = [
        [
            Paragraph(paragraph_text("Website"), styles['TableLabelCell']),
            Paragraph(paragraph_text(url), styles['TableCell']),
        ],
        [
            Paragraph(paragraph_text("Analysis Date"), styles['TableLabelCell']),
            Paragraph(
                paragraph_text(datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y") if "-" in date else date),
                styles['TableCell'],
            ),
        ],
        [
            Paragraph(paragraph_text("Readiness Snapshot"), styles['TableLabelCell']),
            Paragraph(paragraph_text(
                f"GEO {geo_score}/100 | AI Citability {ai_citability}/100 | "
                f"Technical {technical}/100 | Schema {schema_score}/100"
            ), styles['TableCell']),
        ],
    ]

    details_table = Table(details_data, colWidths=[112, 368], hAlign='LEFT')
    details_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, lightgrey),
    ]))
    elements.append(details_table)

    overview = ""
    if isinstance(decision_summary, Mapping):
        overview = decision_summary.get("overview", "")
    if not overview:
        overview = executive_summary
    if overview:
        elements.append(Spacer(1, 18))
        elements.append(Paragraph("Decision Summary", styles["SectionHeader"]))
        elements.append(Paragraph(paragraph_text(overview), styles["BodyText_Custom"]))
        elements.append(Spacer(1, 8))

    # Score gauge
    gauge = create_score_gauge(geo_score, 200, 200)
    elements.append(gauge)

    elements.append(Spacer(1, 20))

    # Score label
    score_color = get_score_color(geo_score)
    elements.append(Paragraph(
        f'<font color="{score_color.hexval()}">{get_score_label(geo_score)}</font>',
        ParagraphStyle('ScoreLabelColored', parent=styles['SectionHeader'],
                       alignment=TA_CENTER, fontSize=20)
    ))

    elements.append(PageBreak())

    # ============================================================
    # EXECUTIVE SUMMARY
    # ============================================================
    elements.append(Paragraph("Executive Summary", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    if executive_summary:
        elements.append(Paragraph(executive_summary, styles['BodyText_Custom']))
    else:
        elements.append(Paragraph(
            f"This report presents the findings of a comprehensive Generative Engine Optimization (GEO) "
            f"audit conducted on <b>{brand_name}</b> ({url}). The analysis evaluated the website's readiness "
            f"for AI-powered search engines including Google AI Overviews, ChatGPT, Perplexity, Gemini, "
            f"and Bing Copilot. The overall GEO Readiness Score is <b>{geo_score}/100</b>, "
            f"placing the site in the <b>{get_score_label(geo_score)}</b> tier.",
            styles['BodyText_Custom']
        ))

    elements.append(Spacer(1, 16))

    # ============================================================
    # SCORE BREAKDOWN
    # ============================================================
    elements.append(Paragraph("GEO Score Breakdown", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    score_data = [
        ["Component", "Score", "Weight", "Weighted"],
        ["AI Citability & Visibility", f"{ai_citability}/100", "25%", f"{round(ai_citability * 0.25, 1)}"],
        ["Brand Authority Signals", f"{brand_authority}/100", "20%", f"{round(brand_authority * 0.20, 1)}"],
        ["Content Quality & E-E-A-T", f"{content_eeat}/100", "20%", f"{round(content_eeat * 0.20, 1)}"],
        ["Technical Foundations", f"{technical}/100", "15%", f"{round(technical * 0.15, 1)}"],
        ["Structured Data", f"{schema_score}/100", "10%", f"{round(schema_score * 0.10, 1)}"],
        ["Platform Optimization", f"{platform_optimization}/100", "10%", f"{round(platform_optimization * 0.10, 1)}"],
        ["OVERALL", f"{geo_score}/100", "100%", f"{geo_score}"],
    ]

    score_table = Table(score_data, colWidths=[200, 80, 60, 80])
    style = make_table_style()

    # Bold the last row
    style.add('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    style.add('BACKGROUND', (0, -1), (-1, -1), MEDIUM_BG)

    # Color-code score cells
    for i in range(1, len(score_data) - 1):
        score_val = int(score_data[i][1].split("/")[0])
        color = get_score_color(score_val)
        style.add('TEXTCOLOR', (1, i), (1, i), color)

    score_table.setStyle(style)
    elements.append(score_table)

    elements.append(Spacer(1, 16))

    # Score bar chart
    chart_scores = [ai_citability, brand_authority, content_eeat, technical, schema_score, platform_optimization]
    chart_labels = ["Citability", "Brand", "Content", "Technical", "Schema", "Platform"]
    elements.append(create_bar_chart(chart_scores, chart_labels))

    elements.append(PageBreak())

    # ============================================================
    # AI PLATFORM READINESS
    # ============================================================
    elements.append(Paragraph("AI Platform Readiness", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    elements.append(Paragraph(
        "These scores reflect how likely your content is to be cited by each AI search platform. "
        "A score below 50 indicates significant barriers to citation on that platform.",
        styles['BodyText_Custom']
    ))
    elements.append(Spacer(1, 10))

    # Platform chart
    if platforms:
        elements.append(create_platform_chart(platforms))

    elements.append(Spacer(1, 10))

    # Platform table
    platform_table_data = [["AI Platform", "Score", "Status"]]
    for name, score in platforms.items():
        status = get_score_label(score)
        platform_table_data.append([name, f"{score}/100", status])

    pt = Table(platform_table_data, colWidths=[180, 80, 150])
    pt_style = make_table_style()
    for i in range(1, len(platform_table_data)):
        score_val = int(platform_table_data[i][1].split("/")[0])
        color = get_score_color(score_val)
        pt_style.add('TEXTCOLOR', (1, i), (1, i), color)
    pt.setStyle(pt_style)
    elements.append(pt)

    elements.append(PageBreak())

    # ============================================================
    # AI CRAWLER ACCESS
    # ============================================================
    elements.append(Paragraph("AI Crawler Access Status", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    elements.append(Paragraph(
        "Blocking AI crawlers prevents AI platforms from citing your content. "
        "The table below shows which AI crawlers can currently access your site.",
        styles['BodyText_Custom']
    ))
    elements.append(Spacer(1, 8))

    if crawler_access:
        # Use Paragraph objects for text wrapping in cells
        cell_style = ParagraphStyle(
            'CrawlerCell', fontName='Helvetica', fontSize=9,
            textColor=TEXT_PRIMARY, leading=12,
        )
        header_cell_style = ParagraphStyle(
            'CrawlerHeaderCell', fontName='Helvetica-Bold', fontSize=9,
            textColor=WHITE, leading=12,
        )
        status_style_allowed = ParagraphStyle(
            'StatusAllowed', fontName='Helvetica-Bold', fontSize=9,
            textColor=SUCCESS, leading=12,
        )
        status_style_blocked = ParagraphStyle(
            'StatusBlocked', fontName='Helvetica-Bold', fontSize=9,
            textColor=DANGER, leading=12,
        )
        status_style_restricted = ParagraphStyle(
            'StatusRestricted', fontName='Helvetica-Bold', fontSize=9,
            textColor=WARNING, leading=12,
        )
        status_style_default = ParagraphStyle(
            'StatusDefault', fontName='Helvetica', fontSize=9,
            textColor=TEXT_PRIMARY, leading=12,
        )

        crawler_data = [[
            Paragraph("Crawler", header_cell_style),
            Paragraph("Platform", header_cell_style),
            Paragraph("Status", header_cell_style),
            Paragraph("Recommendation", header_cell_style),
        ]]
        for crawler_name, info in crawler_access.items():
            if isinstance(info, dict):
                status_text = info.get("status", "Unknown")
                status_upper = status_text.upper()
                if "ALLOW" in status_upper:
                    s_style = status_style_allowed
                elif "BLOCK" in status_upper:
                    s_style = status_style_blocked
                elif "RESTRICT" in status_upper:
                    s_style = status_style_restricted
                else:
                    s_style = status_style_default

                crawler_data.append([
                    Paragraph(crawler_name, cell_style),
                    Paragraph(info.get("platform", ""), cell_style),
                    Paragraph(status_text, s_style),
                    Paragraph(info.get("recommendation", ""), cell_style),
                ])
            else:
                crawler_data.append([
                    Paragraph(crawler_name, cell_style),
                    Paragraph("", cell_style),
                    Paragraph(str(info), cell_style),
                    Paragraph("", cell_style),
                ])

        # Full page width: letter (612pt) - 50pt margins each side = 512pt
        ct = Table(crawler_data, colWidths=[90, 110, 72, 240])
        ct_style = make_table_style()
        ct_style.add('VALIGN', (0, 0), (-1, -1), 'TOP')

        ct.setStyle(ct_style)
        elements.append(ct)
    else:
        elements.append(Paragraph(
            "<i>Run /geo crawlers to populate this section with AI crawler access data.</i>",
            styles['BodyText_Custom']
        ))

    elements.append(PageBreak())
    if isinstance(report_sections, Mapping):
        render_report_sections(elements, report_sections, styles, content_width)
        elements.append(PageBreak())

    # ============================================================
    # KEY FINDINGS
    # ============================================================
    elements.append(Paragraph("Key Findings", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    if findings:
        for finding in findings:
            elements.append(build_finding_card(finding, styles, content_width))
            elements.append(Spacer(1, 10))
    else:
        elements.append(Paragraph(
            "<i>Run a full /geo audit to populate findings.</i>",
            styles['BodyText_Custom']
        ))

    elements.append(PageBreak())

    # ============================================================
    # PRIORITIZED ACTION PLAN
    # ============================================================
    elements.append(Paragraph("Prioritized Action Plan", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    # Quick Wins
    elements.append(Paragraph("Quick Wins (This Week)", styles['SubHeader']))
    elements.append(Paragraph(
        "High impact, low effort — can be implemented immediately.",
        styles['SmallText']
    ))

    if quick_wins:
        for i, action in enumerate(quick_wins, 1):
            if isinstance(action, dict):
                text = f"<b>{i}.</b> {action.get('action', '')} — <i>{action.get('impact', '')}</i>"
            else:
                text = f"<b>{i}.</b> {action}"
            elements.append(Paragraph(text, styles['Recommendation']))
    else:
        default_wins = [
            "Allow all Tier 1 AI crawlers in robots.txt (GPTBot, ClaudeBot, PerplexityBot)",
            "Add publication and last-updated dates to all content pages",
            "Add author bylines with credentials to blog posts and articles",
            "Create an llms.txt file to guide AI systems to your key content",
            "Add sameAs properties to Organization schema linking to all platform profiles",
        ]
        for i, action in enumerate(default_wins, 1):
            elements.append(Paragraph(f"<b>{i}.</b> {action}", styles['Recommendation']))

    elements.append(Spacer(1, 12))

    # Medium-Term
    elements.append(Paragraph("Medium-Term Improvements (This Month)", styles['SubHeader']))
    elements.append(Paragraph(
        "Significant impact, moderate effort — requires content or technical changes.",
        styles['SmallText']
    ))

    if medium_term:
        for i, action in enumerate(medium_term, 1):
            if isinstance(action, dict):
                text = f"<b>{i}.</b> {action.get('action', '')} — <i>{action.get('impact', '')}</i>"
            else:
                text = f"<b>{i}.</b> {action}"
            elements.append(Paragraph(text, styles['Recommendation']))
    else:
        default_medium = [
            "Restructure top 10 pages with question-based headings and direct answer blocks",
            "Implement comprehensive Organization + Article + Person schema markup",
            "Optimize content blocks for AI citability (134-167 word self-contained passages)",
            "Ensure server-side rendering for all public content pages",
            "Implement IndexNow protocol for Bing/Copilot indexing speed",
        ]
        for i, action in enumerate(default_medium, 1):
            elements.append(Paragraph(f"<b>{i}.</b> {action}", styles['Recommendation']))

    elements.append(Spacer(1, 12))

    # Strategic
    elements.append(Paragraph("Strategic Initiatives (This Quarter)", styles['SubHeader']))
    elements.append(Paragraph(
        "Long-term competitive advantage — requires ongoing investment.",
        styles['SmallText']
    ))

    if strategic:
        for i, action in enumerate(strategic, 1):
            if isinstance(action, dict):
                text = f"<b>{i}.</b> {action.get('action', '')} — <i>{action.get('impact', '')}</i>"
            else:
                text = f"<b>{i}.</b> {action}"
            elements.append(Paragraph(text, styles['Recommendation']))
    else:
        default_strategic = [
            "Build Wikipedia/Wikidata entity presence through press coverage and notability",
            "Develop active Reddit community engagement strategy in relevant subreddits",
            "Create YouTube content strategy aligned with AI-searched queries",
            "Establish original research/data publication program for unique citability",
            "Build topical authority through comprehensive content clusters",
        ]
        for i, action in enumerate(default_strategic, 1):
            elements.append(Paragraph(f"<b>{i}.</b> {action}", styles['Recommendation']))

    if rescience_pass:
        elements.append(PageBreak())

        elements.append(Paragraph("ReScience Optimization Pass", styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

        summary = rescience_pass.get("summary", "")
        if summary:
            elements.append(Paragraph(summary, styles['BodyText_Custom']))
            elements.append(Spacer(1, 10))

        priority_actions = rescience_pass.get("priority_actions", {})
        for label in ("P0", "P1", "P2"):
            elements.append(Paragraph(f"{label} Priorities", styles['SubHeader']))
            items = priority_actions.get(label, [])
            if items:
                for item in items:
                    elements.append(Paragraph(f"- {item}", styles['Recommendation']))
            else:
                elements.append(Paragraph("- None identified.", styles['Recommendation']))
            elements.append(Spacer(1, 6))

        platform_guidance = rescience_pass.get("platform_guidance", {})
        if platform_guidance:
            elements.append(Paragraph("Platform Guidance", styles['SubHeader']))
            for platform_name, items in platform_guidance.items():
                elements.append(Paragraph(platform_name, styles['BodyText_Custom']))
                for item in items:
                    elements.append(Paragraph(f"- {item}", styles['Recommendation']))
                elements.append(Spacer(1, 4))

        geo_methods = rescience_pass.get("geo_methods", [])
        if geo_methods:
            elements.append(Paragraph("Recommended GEO Methods", styles['SubHeader']))
            for method in geo_methods:
                text = (
                    f"<b>{method.get('method', '')}</b> "
                    f"({method.get('impact', '')})"
                )
                recommendation = method.get("recommendation", "")
                if recommendation:
                    text += f": {recommendation}"
                elements.append(Paragraph(text, styles['Recommendation']))

    if rescience_pass:
        elements.append(Spacer(1, 12))
    else:
        elements.append(PageBreak())

    # ============================================================
    # METHODOLOGY & GLOSSARY
    # ============================================================
    elements.append(Paragraph("Appendix: Methodology", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=12))

    elements.append(Paragraph(
        f"This GEO audit was conducted on {date} analyzing {url}. "
        "The analysis evaluated the website across six dimensions: AI Citability & Visibility (25%), "
        "Brand Authority Signals (20%), Content Quality & E-E-A-T (20%), Technical Foundations (15%), "
        "Structured Data (10%), and Platform Optimization (10%).",
        styles['BodyText_Custom']
    ))

    elements.append(Spacer(1, 8))

    elements.append(Paragraph(
        "<b>Platforms assessed:</b> Google AI Overviews, ChatGPT Web Search, Perplexity AI, "
        "Google Gemini, Bing Copilot",
        styles['BodyText_Custom']
    ))

    elements.append(Paragraph(
        "<b>Standards referenced:</b> Google Search Quality Rater Guidelines (Dec 2025), "
        "Schema.org specification, Core Web Vitals (2026 thresholds), "
        "llms.txt emerging standard, RSL 1.0 licensing framework",
        styles['BodyText_Custom']
    ))

    elements.append(Spacer(1, 16))

    # Glossary
    elements.append(Paragraph("Glossary", styles['SubHeader']))

    glossary = [
        ["Term", "Definition"],
        ["GEO", "Generative Engine Optimization — optimizing content for AI search citation"],
        ["AIO", "AI Overviews — Google's AI-generated answer boxes in search results"],
        ["E-E-A-T", "Experience, Expertise, Authoritativeness, Trustworthiness"],
        ["SSR", "Server-Side Rendering — generating HTML on the server for crawler access"],
        ["CWV", "Core Web Vitals — Google's page experience metrics (LCP, INP, CLS)"],
        ["INP", "Interaction to Next Paint — responsiveness metric (replaced FID March 2024)"],
        ["JSON-LD", "JavaScript Object Notation for Linked Data — preferred structured data format"],
        ["sameAs", "Schema.org property linking an entity to its profiles on other platforms"],
        ["llms.txt", "Proposed standard file for guiding AI systems about site content"],
        ["IndexNow", "Protocol for instantly notifying search engines of content changes"],
    ]

    gt = build_wrapped_table(
        glossary,
        col_widths=[90, 390],
        styles=styles,
    )
    gt.setStyle(make_table_style())
    elements.append(gt)

    elements.append(Spacer(1, 30))

    # Footer disclaimer
    elements.append(HRFlowable(width="100%", thickness=0.5, color=lightgrey, spaceAfter=8))
    elements.append(Paragraph(
        "This report was generated by the GEO-SEO Claude Code Analysis Tool. "
        "Scores and recommendations are based on automated analysis and industry benchmarks. "
        "Results should be validated with platform-specific testing.",
        styles['SmallText']
    ))

    # ============================================================
    # BUILD PDF
    # ============================================================
    doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Generate a sample report for demonstration
        sample_data = {
            "url": "https://example.com",
            "brand_name": "Example Company",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "geo_score": 58,
            "scores": {
                "ai_citability": 45,
                "brand_authority": 62,
                "content_eeat": 70,
                "technical": 55,
                "schema": 30,
                "platform_optimization": 48,
            },
            "platforms": {
                "Google AI Overviews": 65,
                "ChatGPT": 52,
                "Perplexity": 48,
                "Gemini": 60,
                "Bing Copilot": 45,
            },
            "executive_summary": (
                "This report presents the findings of a comprehensive GEO audit "
                "conducted on Example Company (https://example.com). The site achieved "
                "an overall GEO Readiness Score of 58/100, placing it in the Moderate tier. "
                "The strongest area is Content Quality (70/100), while Structured Data (30/100) "
                "represents the biggest opportunity for improvement. Implementing schema markup, "
                "allowing AI crawlers, and optimizing content structure could increase the score "
                "to approximately 78/100 within 90 days."
            ),
            "findings": [
                {"severity": "critical", "title": "No Schema Markup Detected",
                 "description": "The site has no JSON-LD structured data, making it difficult for AI models to understand entity relationships."},
                {"severity": "high", "title": "JavaScript-Only Rendering",
                 "description": "Key content pages use client-side rendering, making them invisible to AI crawlers that don't execute JavaScript."},
                {"severity": "high", "title": "Missing llms.txt",
                 "description": "No llms.txt file exists to guide AI systems to the most important content."},
                {"severity": "medium", "title": "Weak Brand Entity Presence",
                 "description": "Brand is not present on Wikipedia or Wikidata, limiting entity recognition by AI models."},
                {"severity": "medium", "title": "Content Not Optimized for Citability",
                 "description": "Most content blocks are either too short or too long for optimal AI citation (target: 134-167 words)."},
            ],
            "quick_wins": [
                "Allow all Tier 1 AI crawlers in robots.txt",
                "Add publication dates to all content pages",
                "Create llms.txt file with key page references",
                "Add author bylines with credentials",
                "Fix meta descriptions on top 10 pages",
            ],
            "medium_term": [
                "Implement Organization schema with sameAs linking",
                "Add Article + Person schema to all blog posts",
                "Restructure content with question-based H2 headings",
                "Optimize content blocks for 134-167 word citability",
                "Implement server-side rendering for content pages",
            ],
            "strategic": [
                "Build Wikipedia/Wikidata entity presence",
                "Develop Reddit community engagement strategy",
                "Create YouTube content aligned with AI search queries",
                "Establish original research publication program",
                "Build comprehensive topical authority content clusters",
            ],
            "crawler_access": {
                "GPTBot": {"platform": "ChatGPT", "status": "Allowed", "recommendation": "Keep allowed"},
                "ClaudeBot": {"platform": "Claude", "status": "Allowed", "recommendation": "Keep allowed"},
                "PerplexityBot": {"platform": "Perplexity", "status": "Blocked", "recommendation": "Unblock for visibility"},
                "Google-Extended": {"platform": "Gemini", "status": "Allowed", "recommendation": "Keep allowed"},
                "Bingbot": {"platform": "Bing Copilot", "status": "Allowed", "recommendation": "Keep allowed"},
            },
        }

        output_file = "GEO-REPORT-sample.pdf"
        result = generate_report(sample_data, output_file)
        print(f"Report generated: {result}")

    else:
        # Load data from file or stdin
        input_path = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "GEO-REPORT.pdf"

        if input_path == "-":
            data = json.loads(sys.stdin.read())
        else:
            with open(input_path) as f:
                data = json.load(f)

        result = generate_report(data, output_file)
        print(f"Report generated: {result}")
