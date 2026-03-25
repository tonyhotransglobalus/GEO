# Report Audience and Layout Design

**Date:** 2026-03-17

## Goal

Improve the final GEO report so it works for executive and technical readers in the same document, while also fixing PDF layout defects such as clipped table text and occasional overlap in dense sections.

## Approved Direction

Use one shared report with:

- richer multi-audience findings
- stronger PDF table wrapping and pagination
- no change to the core single-entry audit flow

## Audience Design

Each key finding should move from a short audit note to a compact stakeholder block that explains the same issue from four angles:

- **Leadership impact** for CEO and CMO readers
- **Marketing action** for marketing managers
- **Developer action** for implementation teams
- **Observed evidence** so the recommendation is anchored to the audit

This keeps one report useful for multiple audiences without creating separate reports or duplicate sections.

## Content Design

The `geo-seo-claude` audit remains the numeric source of truth. ReScience remains a separate optimization pass.

The key findings section should:

- keep severity and title
- preserve a short summary sentence
- add audience-specific action and impact fields
- stay concise enough for PDF rendering

Markdown and PDF output should use the same enriched finding model.

## Layout Design

The current PDF generator uses several fixed-width ReportLab tables with raw string cells. Long values can be clipped because the cells are not consistently rendered as wrapped paragraph flowables.

The layout update should:

- convert table cells to wrapped `Paragraph` objects
- introduce reusable table cell styles
- rebalance widths for dense tables, especially crawler access and glossary sections
- increase padding and leading where needed
- keep headers repeated and pages split cleanly

## Verification

Verification should include:

- unit tests for enriched findings and markdown rendering
- unit tests proving wrapped table helpers are used
- PDF generation and text extraction checks
- visual inspection of rendered PNG pages for overlap or clipping
