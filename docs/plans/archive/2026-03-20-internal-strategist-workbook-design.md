# Internal Strategist Workbook Design

**Date:** 2026-03-20

## Goal

Redesign the final GEO/SEO PDF from an audit-first deliverable into an internal strategist workbook for the team.

The workbook should:

- lead with actionable business analysis, not just audit scores
- organize recommendations by service line first
- include competitor, earned-media, citation-failure, and citation-strength analysis
- attach evidence citations to important claims so readers can trust the conclusions
- still preserve the technical GEO layer, but later in the document

## Why The Current PDF Falls Short

The current PDF already contains strategist sections, but they still read as secondary to the legacy audit layout:

- early pages are dominated by scorecards and platform tables
- competitor analysis is too thin when discovery is weak
- opportunity clusters can degrade into scraped page text instead of clean business themes
- citation failure diagnosis is present but not yet diagnostic enough to drive execution
- entity analysis is closer to a raw link dump than an authority-gap analysis

For an internal team artifact, this is the wrong emphasis. The report should behave like a working decision document rather than a branded audit export.

## Research Basis

The workbook should reflect several current research-backed ideas:

- Generative Engine Optimization can improve visibility materially, and citations, statistics, and quotations are especially strong levers: Princeton GEO paper (`arXiv:2311.09735`)
- Citation failure modes should be diagnosed explicitly instead of relying on generic optimization guidance: AgentGEO (`arXiv:2603.09296`)
- AI search often favors earned media over brand-owned content and varies by engine and phrasing: comparative AI search study (`arXiv:2509.08919`)
- Metadata, freshness, semantic HTML, and structured data are strongly associated with citation likelihood: GEO-16 (`arXiv:2509.10762`)
- Citations increase trust in AI answers, so the report should distinguish stronger and weaker evidence, not just visibility: trust experiment (`arXiv:2504.06435`)
- `llms.txt` is a useful guidance layer, but it complements rather than replaces sitemap, schema, crawl controls, and content structure: [llms.txt proposal](https://llmstxt.org/index.html)

## Product Positioning

This report is optimized for **our internal team**.

That means:

- the primary unit is the service line, not the AI engine
- the report should map directly to execution owners
- the report should show not only what is wrong, but why we believe it, and what exact fixes matter most

Engine-specific notes can still appear, but only inside service-line analysis.

## Information Architecture

### 1. Decision Summary

Open with a one-page decision memo:

- biggest blockers
- biggest opportunities
- strongest competitor or market threats
- 30-day actions
- evidence tags next to every non-obvious claim

### 2. Service-Line Scorecard

One row per business line, such as:

- life insurance
- annuities
- mortgage
- health insurance
- real estate
- property and casualty
- asset management

Each row should show:

- visibility
- citation readiness
- citation strength
- earned-media strength
- technical readiness
- priority

### 3. Query Universe

Query clusters must be normalized into clean business topics instead of being allowed to degrade into long homepage text.

For each service line, show:

- informational queries
- commercial queries
- comparison queries
- trust or review queries
- advisor or agent queries

### 4. Competitor Visibility Map

For each service line:

- which domains appear in search and AI-answer contexts
- which competitors dominate which query types
- whether the visible sources are owned domains or earned-media domains

When no strong competitors are discovered, the report should say that directly instead of rendering an empty-looking section.

### 5. Earned-Media Gap

Separate this from competitor analysis.

Show:

- third-party domains cited or surfaced in the category
- whether those domains support us, support competitors, or ignore both
- gaps between owned-site quality and off-site authority

### 6. Citation Failure Diagnosis

Replace generic “not cited” messaging with explicit failure modes such as:

- not retrieved
- retrieved but not cited
- weak answer block
- weak evidence or statistics
- weak entity grounding
- freshness gap
- competitor evidence advantage

### 7. Citation Strength Analysis

Add a formal citation-strength layer for both:

- owned pages
- earned media

Measure:

- source authority
- relevance
- recency
- factual specificity
- attribution clarity
- convergence across engines when available

### 8. Content Surgery Map

For each priority page:

- target service line
- target query cluster
- failure mode
- exact content changes
- evidence or statistics needed
- schema or FAQ changes needed
- rewrite pattern recommended

### 9. Entity And Trust Graph

This section should diagnose:

- sameAs/profile consistency
- profile fragmentation
- brand ambiguity
- authority anchors
- missing trust reinforcements

### 10. Technical GEO Gates

Keep the technical layer, but move it later:

- llms.txt
- robots and AI crawler access
- schema completeness
- rendering and semantic HTML
- security headers where relevant
- freshness or update signals

### 11. 30/60/90 Execution Ledger

Each action should include:

- owner
- service line
- expected lift
- effort
- dependency
- evidence basis

### 12. Evidence And Methodology Appendix

This should make the report auditable.

For each important claim, track:

- claim
- source type
- source detail
- capture date
- related query or page
- confidence note

## Evidence Citation System

Add short inline tags throughout the report:

- `[Academic]`
- `[Official]`
- `[Live Site]`
- `[Live SERP]`
- `[Heuristic]`

Important rule:

- every strategic claim should show how we know it
- every recommendation should trace back to observed evidence, research, or both

## Analysis Changes Needed

The workbook redesign requires deeper upstream analyzers:

- service-line classifier
- query-cluster normalizer
- competitor discovery by service line
- earned-media source collector
- citation-strength scorer
- evidence registry / source-tagging system
- stronger citation-failure diagnostics
- page-level rewrite prescription generator

## PDF Design Direction

Use an analyst-workbook style rather than a brochure style:

- stronger typography hierarchy
- compact tables
- decision cards
- evidence callouts
- cleaner page headers
- fewer decorative score widgets
- primary content should be the strategist analysis, not the cover-page gauge

The `pdf` skill quality bar applies:

- render and inspect the actual PDF visually
- verify layout and readability page by page
- treat formatting issues as product issues, not cosmetic extras

## Recommended Build Order

1. Fix analysis quality first:
   - service-line clustering
   - competitor and earned-media discovery
   - citation-strength and failure-mode analysis
2. Add the evidence registry and inline source tags
3. Redesign the report section schema
4. Redesign the PDF layout around the new schema
5. Validate with a live site run and rendered PDF review
