---
description: Run a full GEO+SEO audit on a website to analyze AI search visibility
---

# GEO Full Audit Workflow

Run the combined GEO audit without generating the final PDF.

This workflow now uses the single orchestrator entrypoint instead of listing
the individual scripts manually.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\strategy_report.py <URL>
```

## Outputs

- `GEO-CLIENT-REPORT.md`
- `output/data/<site>-geo-audit-<date>.json`

## Notes

- Use `.agent/workflows/geo-strategy-report.md` when the final deliverable should be a PDF.
- `.agent/workflows/geo-report-pdf.md` remains as a legacy alias to the same strategist entrypoint.
- The numeric score comes from `geo-seo-claude`.
- The ReScience pass is advisory and appears as a separate optimization section.
