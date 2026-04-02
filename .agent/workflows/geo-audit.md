---
description: Run the analysis-oriented GEO audit workflow
---

# GEO Full Audit Workflow

Run the analysis-oriented GEO audit workflow.

Use this when the goal is to inspect the audit behavior and intermediate
results, not just hand over the final PDF.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\strategy_report.py https://www.transglobalus.com/ --non-interactive
```

## Primary Outputs

- `output/reports/<site>-<date>/GEO-STRATEGY-REPORT.md`
- `output/reports/<site>-<date>/audit-data.json`

## Notes

- The current implementation may also generate the PDF as part of the same run.
- Use `.agent/workflows/geo-strategy-report.md` when the final deliverable itself is the main goal.
- Use `.agent/workflows/geo-strategy-report-v2.md` when testing the next-generation V2 report pipeline.
