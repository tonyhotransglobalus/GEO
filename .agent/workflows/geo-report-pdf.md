---
description: Run the single-entry GEO orchestration flow and generate the final PDF deliverable
---

# GEO Report PDF Workflow

Legacy alias for the preferred `geo-strategy-report` workflow.

Run the end-to-end GEO workflow through the shared strategist entrypoint.

This is the single public entrypoint for Codex, Antigravity, and Gemini CLI when
the desired output is one final PDF.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\strategy_report.py <URL>
```

## What It Does

1. Runs the `geo-seo-claude` scoring and audit flow
2. Runs a ReScience `seo-geo` optimization pass
3. Writes the combined markdown report and JSON payload
4. Generates the final PDF deliverable

## Outputs

- `GEO-CLIENT-REPORT.md`
- `output/data/<site>-geo-audit-<date>.json`
- `output/pdf/GEO-REPORT-<Brand>-<date>.pdf`
