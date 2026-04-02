---
description: Run the next-generation V2 strategist workflow and generate the V2 report artifacts
---

# GEO Strategy Report V2 Workflow

Run the next-generation V2 GEO strategist workflow.

Use this when you want the stricter evidence-gated report path, the separate
V2 output root, and the V2 markdown/PDF artifacts.

## Command

```powershell
.\.venv\Scripts\python.exe scripts\strategy_report_v2.py https://www.transglobalus.com/ --non-interactive --compare-to-v1
```

## What It Does

1. Runs the V2 workflow with manifest, evidence ledger, adjudication, and report assembly
2. Bridges safe V1 audit data where needed
3. Generates V2 markdown, PDF, manifest, and evidence artifacts
4. Publishes stable `latest` V2 artifacts into the V2 output root

## Outputs

- `output/reports-v2/<run>/GEO-STRATEGY-REPORT-V2.md`
- `output/reports-v2/<run>/GEO-STRATEGY-REPORT-V2.pdf`
- `output/reports-v2/<run>/GEO-STRATEGY-REPORT-V2.manifest.json`
- `output/reports-v2/<run>/GEO-STRATEGY-REPORT-V2.evidence.json`
- `output/reports-v2/<site>-latest/GEO-STRATEGY-REPORT-V2.md`
- `output/reports-v2/<site>-latest/GEO-STRATEGY-REPORT-V2.pdf`

## Notes

- This is the V2 preview path, not the default stable report path.
- Use `--shadow-run` when you want the shadow latest channel instead of published latest.
