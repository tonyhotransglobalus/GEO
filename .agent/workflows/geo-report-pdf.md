---
description: Legacy alias for the stable strategist workflow
---

# GEO Report PDF Workflow

Legacy alias for `geo-strategy-report`.

Use this only when someone still asks for the old `report-pdf` name. It runs
the same stable report path as `geo-strategy-report`.

## Command

```powershell
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

- Prefer `.agent/workflows/geo-strategy-report.md` in new usage.
- This alias remains for backwards compatibility only.
