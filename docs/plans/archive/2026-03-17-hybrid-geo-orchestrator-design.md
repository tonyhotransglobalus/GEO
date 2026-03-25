# Hybrid GEO Orchestrator Design

**Date:** 2026-03-17
**Status:** Approved

## Goal

Provide one single entrypoint that works consistently across Codex, Antigravity, and Gemini CLI and produces one final PDF deliverable. The PDF should use `geo-seo-claude` as the numeric audit/scoring source and add a separate ReScience `seo-geo` optimization pass as an advisory section, not as a second competing score.

## Problem

The current repository mixes three different orchestration ideas:

- `geo-seo-claude` expects a high-level skill command such as `/geo audit <url>` or `/geo report-pdf <url>` to orchestrate the audit.
- The local Antigravity layer rewrites behavior into strict single-flow execution and local `.agent` workflows.
- The current local workflow still tells the agent to invoke multiple scripts directly rather than exposing one stable orchestration entrypoint.

This creates runtime-dependent behavior and makes the repo feel more manual than intended.

## Design

### Public entrypoint

The preferred single entrypoint will be:

`/geo report-pdf <url>`

That workflow will invoke one real Python orchestrator script instead of listing a sequence of individual scripts.

### Execution model

The orchestrator will:

1. Fetch the target website and supporting crawl signals using the existing `geo-seo-claude` utilities.
2. Compute the base `geo-seo-claude` audit data and numeric score.
3. Generate a ReScience `seo-geo` optimization pass from the same collected evidence.
4. Assemble one combined JSON payload.
5. Write one combined markdown report.
6. Render one final PDF.

### Scoring model

- `geo-seo-claude` remains the only numeric score in the final output.
- ReScience recommendations are presented in a separate section with:
  - Priority buckets (`P0`, `P1`, `P2`)
  - Princeton GEO methods
  - platform-specific guidance

This avoids pretending the two repositories share the same scoring system when they do not.

### Output artifacts

The orchestrator should write:

- `GEO-CLIENT-REPORT.md`
- `output/data/<slug>-geo-audit-<date>.json`
- `output/pdf/GEO-REPORT-<Brand>-<date>.pdf`

### PDF structure

The PDF should contain:

1. Executive summary
2. `geo-seo-claude` scorecard
3. Key findings
4. Prioritized action plan
5. ReScience optimization pass
6. Appendix / methodology

## Files to change

- Add `scripts/full_audit.py`
- Add ReScience mapping helpers in Python
- Extend `scripts/generate_pdf_report.py` for the extra advisory section
- Add or update `.agent` workflow entrypoints so `/geo report-pdf <url>` uses the orchestrator
- Update docs to make the single-entry flow clear

## Testing strategy

- Unit test helper functions that build the ReScience advisory section and combined audit payload.
- Unit test markdown generation for the extra section.
- Run one live end-to-end audit that produces the final PDF.
- Rasterize the PDF and visually verify the new section does not break layout.

## Non-goals

- Do not invent a merged weighted score across both repos.
- Do not remove the existing lower-level scripts.
- Do not make behavior depend on a specific agent profile being active.
