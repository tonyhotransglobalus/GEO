---
description: Run the stable strategist workflow and generate the final combined report
---

# GEO Strategy Report Workflow

Run the stable end-to-end GEO strategist workflow.

Use this when the goal is one final client-ready report on the current stable
path.

## Command

```powershell
# When running within Antigravity or Codex, no extra flags are needed
.\.venv\Scripts\python.exe scripts\strategy_report.py https://www.transglobalus.com/ --non-interactive
```

## What It Does

1. Runs the shared audit orchestration flow
2. Builds the combined markdown report and audit payload
3. Generates the final PDF deliverable

## Outputs

- `output/reports/<site>-<date>/GEO-STRATEGY-REPORT.md`
- `output/reports/<site>-<date>/audit-data.json`
- `output/reports/<site>-<date>/GEO-STRATEGY-REPORT.pdf`

## Notes

- This is the stable V1-style report path.
- Use `.agent/workflows/geo-strategy-report-v2.md` when you want the newer V2 evidence-gated report flow instead.
