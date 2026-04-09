---
name: geo
description: >
  GEO-first SEO analysis router. Use this skill when the user wants GEO, SEO,
  AI search visibility, citability, llms.txt, crawler access, schema, or a
  client-ready report for a website. This file routes to the correct workflow
  and keeps V1 and V2 report paths separate.
allowed-tools: Read, Grep, Glob, Bash, WebFetch, Write
---

# GEO-SEO Analysis Router

This file is the top-level index for GEO work in this repo.

Use it to decide which workflow to run, not as the detailed source of truth for
every report implementation detail.

## When To Use Which Flow

| Need | Workflow |
|---|---|
| Final client-ready report on the stable path | `geo-strategy-report` |
| Analysis-first audit run | `geo-audit` |
| Test the next-generation report pipeline | `geo-strategy-report-v2` |

## Quick Reference

| Command | What It Does |
|---|---|
| `/geo audit <url>` | Run the audit-oriented workflow |
| `/geo citability <url>` | Score content for citation readiness |
| `/geo crawlers <url>` | Check robots.txt and AI crawler access |
| `/geo llmstxt <url>` | Analyze or generate `llms.txt` guidance |
| `/geo schema <url>` | Inspect structured data and gaps |
| `/geo technical <url>` | Review technical SEO foundations |
| `/geo content <url>` | Review content quality and E-E-A-T signals |
| `/geo strategy-report <url>` | Run the stable combined report flow |
| `/geo quick <url>` | Fast GEO visibility snapshot |

## V1 And V2

- `V1` is the stable production-style path.
- `V2` is the next-generation report path with stricter evidence gating, a separate output root, and a different report contract.
- Keep them separate in docs and outputs until V2 becomes the default.

## Output Conventions

Stable V1 flow:
- `output/reports/<site>-<date>/GEO-STRATEGY-REPORT.md`
- `output/reports/<site>-<date>/audit-data.json`
- `output/reports/<site>-<date>/GEO-STRATEGY-REPORT.pdf`

V2 preview flow:
- `output/reports-v2/<run>/GEO-STRATEGY-REPORT-V2.md`
- `output/reports-v2/<run>/GEO-STRATEGY-REPORT-V2.manifest.json`
- `output/reports-v2/<run>/GEO-STRATEGY-REPORT-V2.evidence.json`
- `output/reports-v2/<run>/GEO-STRATEGY-REPORT-V2.pdf`
- `output/reports-v2/<site>-latest/...` for the latest published V2 artifacts

## Notes

- Do not describe the stable strategist flow as a `ReScience` pass. That wording is legacy.
- Do not treat old subagent diagrams as the canonical execution model unless the current workflow doc says so.
- Prefer TransGlobal examples when showing commands in this repo.
