---
description: Run the preferred strategist workflow and generate the final PDF deliverable
---

# GEO Strategy Report Workflow

Run the preferred end-to-end GEO strategist workflow.

This is the primary Antigravity and Gemini CLI workflow when the desired output
is one final strategist PDF backed by the shared JSON payload.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\strategy_report.py <URL>
```

## What It Does

1. Runs the shared audit orchestration flow
2. Runs the strategist opportunity, competitive, entity, and diagnosis layers
3. Writes the combined markdown report and JSON payload
4. Generates the final PDF deliverable

## Outputs

- `GEO-CLIENT-REPORT.md`
- `output/data/<site>-geo-audit-<date>.json`
- `output/pdf/GEO-REPORT-<Brand>-<date>.pdf`
