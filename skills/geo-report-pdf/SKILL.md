---
name: geo-report-pdf
description: Generate a professional PDF report from GEO audit data using ReportLab. Creates a polished, client-ready PDF with score gauges, bar charts, platform readiness visualizations, color-coded tables, and prioritized action plans.
version: 1.0.0
author: geo-seo-claude
tags: [geo, pdf, report, client-deliverable, professional]
---

# GEO PDF Report Generator

## Purpose

This skill generates a professional, visually polished PDF report from GEO audit data. The PDF includes score gauges, bar charts, platform readiness visualizations, color-coded tables, and a prioritized action plan — ready to deliver directly to clients.

## Prerequisites

- **ReportLab** must be installed: `pip install reportlab`
- The PDF generation script is located at: `~/.claude/skills/geo/scripts/generate_pdf_report.py`
- Use `/geo strategy-report <url>` to generate the strategist report payload and PDF

## How to Generate a PDF Report

For this repository, the preferred implementation is now a single orchestrator entrypoint instead of a manual chain of separate script calls.

### Preferred Command

```bash
python scripts/strategy_report.py <url>
```

This command:
- runs the strategist workflow through the shared audit orchestrator
- writes the combined markdown and JSON artifacts
- prints the final JSON payload and generates the PDF automatically

### Underlying JSON Shape

The strategist wrapper generates a structured JSON payload that includes the audit data and report sections. Its shape is compatible with the PDF generator and follows this general schema:

```json
{
    "url": "https://example.com",
    "brand_name": "Example Company",
    "date": "2026-02-18",
    "geo_score": 65,
    "scores": {
        "ai_citability": 62,
        "brand_authority": 78,
        "content_eeat": 74,
        "technical": 72,
        "schema": 45,
        "platform_optimization": 59
    },
    "platforms": {
        "Google AI Overviews": 68,
        "ChatGPT": 62,
        "Perplexity": 55,
        "Gemini": 60,
        "Bing Copilot": 50
    },
    "executive_summary": "A 4-6 sentence summary of the audit findings...",
    "findings": [
        {
            "severity": "critical",
            "title": "Finding Title",
            "description": "Description of the finding and its impact."
        }
    ],
    "quick_wins": [
        "Action item 1",
        "Action item 2"
    ],
    "medium_term": [
        "Action item 1",
        "Action item 2"
    ],
    "strategic": [
        "Action item 1",
        "Action item 2"
    ],
    "crawler_access": {
        "GPTBot": {"platform": "ChatGPT", "status": "Allowed", "recommendation": "Keep allowed"},
        "ClaudeBot": {"platform": "Claude", "status": "Blocked", "recommendation": "Unblock for visibility"}
    }
}
```

### Manual Fallback

If the wrapper is unavailable and you need to render a PDF manually, write the collected audit data to a temporary JSON file:

```bash
# Write audit data to temp file
cat > /tmp/geo-audit-data.json << 'EOF'
{ ... audit JSON data ... }
EOF
```

### Manual PDF Rendering

Run the PDF generation script:

```bash
python3 ~/.claude/skills/geo/scripts/generate_pdf_report.py /tmp/geo-audit-data.json GEO-REPORT-[brand].pdf
```

The script will produce a professional PDF report with:
- **Cover Page** — Brand name, URL, date, overall GEO score with visual gauge
- **Executive Summary** — Key findings and top recommendations
- **Score Breakdown** — Table and bar chart of all 6 scoring categories
- **AI Platform Readiness** — Visual horizontal bar chart per platform with scores
- **AI Crawler Access** — Color-coded table (green=allowed, red=blocked)
- **Key Findings** — Severity-coded findings list (critical/high/medium/low)
- **Prioritized Action Plan** — Quick wins, medium-term, and strategic initiatives
- **Appendix** — Methodology, data sources, and glossary

### Return the PDF Path

After generation, tell the user where the PDF was saved and its file size.

## Complete Workflow Example

When the user runs `/geo strategy-report <url>` with a URL:

1. Run the shared strategist wrapper with `python scripts/strategy_report.py <url>`
2. The wrapper prints the JSON payload and generates the PDF automatically
3. Generate the PDF as described above

## If the User Provides a URL

If the user runs `/geo strategy-report https://example.com` or invokes this skill with a URL:
1. Run `python scripts/strategy_report.py <url>`
2. Return the generated PDF path and any JSON path written by the orchestrator

## Parsing Markdown Audit Data

When extracting data from existing GEO markdown reports, look for these patterns:

- **GEO Score**: Look for "GEO Score: XX/100" or "Overall: XX/100" or "GEO Readiness Score: XX"
- **Category Scores**: Look for score tables with columns like "Component | Score | Weight"
- **Platform Scores**: Look for tables with "Google AI Overviews", "ChatGPT", "Perplexity", etc.
- **Crawler Status**: Look for tables with "Allowed" or "Blocked" status for crawlers like GPTBot, ClaudeBot
- **Findings**: Look for sections titled "Key Findings", "Critical Issues", "Recommendations"
- **Action Items**: Look for sections titled "Quick Wins", "Action Plan", "Recommendations"

## Notes

- If ReportLab is not installed, run: `pip install reportlab`
- The PDF is designed for US Letter size (8.5" x 11")
- Color palette: Navy primary (#1a1a2e), Blue accent (#0f3460), Coral highlight (#e94560), Green success (#00b894)
- Each page has a header line, page numbers, "Confidential" watermark, and generation date
- Score gauges use traffic-light colors: green (80+), blue (60-79), yellow (40-59), red (below 40)
