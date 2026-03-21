# GEO-SEO Analyzer — Usage Guide

## What This Tool Does

Analyzes websites for **AI search visibility** — how well AI engines (ChatGPT, Claude, Perplexity, Gemini, Google AI Overviews) can discover, understand, and cite your content.

Based on [geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude), adapted for **Antigravity / Gemini CLI** on Windows.

---

---

## Using with Antigravity / Gemini CLI

Open this project folder and use these slash commands or natural language:

### Slash Commands (Workflows)

```
/geo-strategy-report https://example.com # Preferred single entrypoint -> final PDF
/geo-report-pdf https://example.com      # Legacy alias -> final PDF
/geo-audit https://example.com          # Combined audit without PDF
/geo-quick https://example.com          # 60-second snapshot
/geo-citability https://example.com     # AI citation scoring
/geo-crawlers https://example.com       # AI crawler access check
```

### Natural Language

Just ask:
- *"Generate the GEO PDF report for https://example.com"*
- *"Run a GEO audit on https://example.com"*
- *"Check AI crawler access for example.com"*
- *"Score this page for AI citability: https://example.com/blog/post"*
- *"Analyze the schema markup on example.com"*

The preferred full flow now uses one orchestrator script that combines the
`geo-seo-claude` audit/scoring logic with a separate ReScience `seo-geo`
optimization pass and then generates one final PDF deliverable.

---

## Python Scripts (Direct Usage)

All scripts are in `scripts/` and can be run directly:

```powershell
# Preferred full flow
python scripts/strategy_report.py https://example.com

# Page analysis (returns JSON)
python scripts/fetch_page.py https://example.com page
python scripts/fetch_page.py https://example.com robots    # robots.txt
python scripts/fetch_page.py https://example.com llms      # llms.txt
python scripts/fetch_page.py https://example.com sitemap   # sitemap
python scripts/fetch_page.py https://example.com full      # everything

# Citability scoring
python scripts/citability_scorer.py https://example.com

# Brand mention scanning
python scripts/brand_scanner.py "Brand Name" example.com

# llms.txt analysis
python scripts/llmstxt_generator.py https://example.com

# Standalone PDF report (after collecting audit data as JSON)
python scripts/generate_pdf_report.py data.json report.pdf
```

---

## Scoring Methodology

**GEO Score (0-100)** — Weighted across 6 dimensions:

| Category | Weight | What It Measures |
|----------|--------|-----------------|
| AI Citability | 25% | Quotable, extractable content passages |
| Brand Authority | 20% | Mentions on YouTube, Reddit, Wikipedia |
| Content E-E-A-T | 20% | Expertise, Authoritativeness, Trust |
| Technical GEO | 15% | AI crawler access, rendering, speed |
| Schema Markup | 10% | JSON-LD structured data quality |
| Platform Optimization | 10% | Platform-specific readiness |

**Citability Score** grades individual passages:
- **A** (80+) — Highly citable by AI
- **B** (65-79) — Good citability
- **C** (50-64) — Moderate
- **D** (35-49) — Low
- **F** (<35) — Poor

The sweet spot for AI-cited passages: **134-167 words**, self-contained, fact-rich.

---

## Project Structure

```
geo-seo/
├── .agent/workflows/       # Antigravity workflow files
│   ├── geo-strategy-report.md # Preferred strategist PDF workflow
│   ├── geo-report-pdf.md    # Legacy PDF workflow alias
│   ├── geo-audit.md         # Combined audit workflow
│   ├── geo-quick.md         # Quick scan workflow
│   ├── geo-citability.md    # Citability workflow
│   └── geo-crawlers.md      # Crawler analysis workflow
├── geo/SKILL.md             # Main skill orchestrator
├── skills/                  # 11 specialized sub-skills
├── agents/                  # 5 subagent definitions
├── scripts/                 # Python analysis scripts
│   ├── strategy_report.py   # Single public strategist entrypoint
│   ├── full_audit.py        # Shared audit orchestrator
├── schema/                  # JSON-LD templates
├── setup.ps1                # Windows setup script
└── USAGE.md                 # This file
```
