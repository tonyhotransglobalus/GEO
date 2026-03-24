# GEO Client Report: TransGlobal Holding Company

**Audit Date:** 2026-03-17
**Primary URL:** https://www.transglobalus.com/

---

## Executive Summary

A live GEO audit of TransGlobal Holding Company found a technically accessible site with a GEO score of 58/100. The numeric score comes from the geo-seo-claude audit model, while the advisory recommendations come from a separate ReScience optimization pass. The most urgent content issue is low citability at 28.0/100. The most urgent structural issue is the missing llms.txt guidance layer. The homepage also needs cleaner information architecture because it currently exposes 10 H1 tags. ReScience optimization pass focuses on actionable SEO/GEO execution rather than a second weighted score. The biggest structural gap is the missing llms.txt guidance layer. The biggest content gap is weak answer-first formatting and low factual density.

---

## GEO Readiness Score: 58/100

| Component | Score |
|---|---:|
| AI Citability | 28/100 |
| Brand Authority | 57/100 |
| Content E-E-A-T | 75/100 |
| Technical Foundation | 80/100 |
| Schema & Structured Data | 76/100 |
| Platform Optimization | 48/100 |

---

## Key Findings

### [CRITICAL] Key pages are not AI-citation ready

Average citability scored 28.0/100, which means priority pages are still weak candidates for extraction into AI-generated answers.

**Why this matters to leadership:** Low citation readiness reduces the brand's chance of appearing in AI answers during high-intent discovery, which directly limits awareness, assisted conversion, and competitive share of voice.

**What marketing should do:** Rewrite service, solution, and explainer pages into answer-first sections with sourced statistics, clear proof points, and short extractable paragraphs.

**What dev should change:** Support content templates with one clear H1, stronger H2/H3 structure, and reusable placements for FAQ and supporting schema on high-priority pages.

**Observed evidence:** The live audit measured average citability at 28.0/100, below the threshold where pages are typically easy for AI systems to quote and attribute.

### [HIGH] llms.txt guidance files are missing

The site does not expose llms.txt guidance files at the root, so AI systems receive no direct guidance about priority pages, document structure, or recommended crawl targets.

**Why this matters to leadership:** Without a machine-readable guidance layer, the company has less control over how AI systems discover and prioritize its most valuable content.

**What marketing should do:** Publish llms.txt and llms-full.txt that point AI systems to the pages most aligned with brand messaging, core services, and thought-leadership assets.

**What dev should change:** Create and deploy root-level llms.txt files, keep them versioned with the site, and update them whenever priority URLs or content architecture changes.

**Observed evidence:** The live fetch did not find llms.txt at the expected root path, so no AI guidance document is currently published.

### [HIGH] Heading architecture is diluted

The homepage currently exposes 10 H1 tags instead of one clear primary page thesis, which weakens how both users and AI systems interpret topical focus.

**Why this matters to leadership:** A diluted page thesis makes the brand's most important landing page less clear, which can suppress message retention and reduce AI confidence in the page's core topic.

**What marketing should do:** Clarify the homepage message hierarchy so the primary value proposition is unmistakable, then align supporting sections to secondary audience and service themes.

**What dev should change:** Refactor heading markup to a single H1 with semantically ordered H2 and H3 sections, and remove layout-driven heading misuse.

**Observed evidence:** The homepage audit found 10 H1 tags, a strong sign that content hierarchy is being split across multiple competing signals.

### [MEDIUM] Optimization opportunities remain after the base audit

ReScience optimization pass focuses on actionable SEO/GEO execution rather than a second weighted score. The biggest structural gap is the missing llms.txt guidance layer. The biggest content gap is weak answer-first formatting and low factual density.

**Why this matters to leadership:** The site has a workable foundation, but unresolved optimization gaps will keep the brand from reaching stronger AI visibility gains without a coordinated follow-through plan.

**What marketing should do:** Turn the ReScience recommendations into an execution backlog for content refreshes, proof-point additions, and platform-specific improvements.

**What dev should change:** Bundle the structural recommendations into roadmap work so schema, content modules, and technical trust signals are implemented consistently.

**Observed evidence:** The advisory pass still flagged medium-priority optimization work, which indicates the site can improve even after the baseline audit score is calculated.

### [MEDIUM] Entity trust signals are still thin

Brand identity appears across social platforms, but stronger authoritative entity reinforcement is still missing.

**Why this matters to leadership:** Thin entity trust makes it harder for AI systems to confidently associate the brand with its services, expertise, and authority.

**What marketing should do:** Strengthen third-party validation through consistent profile governance, citation-worthy proof points, and broader entity reinforcement across trusted platforms.

**What dev should change:** Align visible profile links, organization schema, and sameAs references so the site publishes one consistent entity graph.

**Observed evidence:** The audit found social presence but did not confirm stronger authority anchors such as Wikipedia or Wikidata-level entity reinforcement.

---

## Prioritized Action Plan

### Quick Wins

- Publish llms.txt and llms-full.txt at the site root.
- Normalize heading hierarchy so each page has a single H1.
- Rewrite key pages into answer-first blocks with facts, citations, and concise paragraphs.

### Medium-Term Improvements

- Add stronger security headers, starting with Content-Security-Policy.
- Strengthen entity trust with consistent profiles, citations, and a future Wikidata path if eligible.

### Strategic Initiatives

- Build recurring AI-native content that answers high-intent user questions directly.
- Develop stronger entity authority through third-party citations and consistent profile governance.
- Track AI visibility, referral traffic, and citation wins as ongoing GEO KPIs.

---

## ReScience Optimization Pass

ReScience optimization pass focuses on actionable SEO/GEO execution rather than a second weighted score. The biggest structural gap is the missing llms.txt guidance layer. The biggest content gap is weak answer-first formatting and low factual density.

### P0 Priorities

- None identified.

### P1 Priorities

- Publish llms.txt and llms-full.txt at the site root.
- Normalize heading hierarchy so each page has a single H1.
- Rewrite key pages into answer-first blocks with facts, citations, and concise paragraphs.

### P2 Priorities

- Add stronger security headers, starting with Content-Security-Policy.
- Strengthen entity trust with consistent profiles, citations, and a future Wikidata path if eligible.

### Platform Guidance

#### ChatGPT

- Refresh high-value pages regularly and keep answer blocks factual and quotable.
- Strengthen branded entity signals and align visible profiles with schema.

#### Perplexity

- Add FAQ schema and publish comparison or explainer content with atomic paragraphs.
- Consider downloadable PDF resources for dense advisory topics.

#### Google AI Overviews

- Improve E-E-A-T with stronger expert identity, citations, and service-specific schema.
- Use cleaner heading hierarchy and tightly focused topical sections.

#### Bing Copilot

- Preserve Bing crawlability and improve entity clarity across LinkedIn and branded mentions.

#### Claude

- Increase factual density and structural clarity so Brave-indexed retrieval has better snippets to cite.

### Recommended GEO Methods

- **Cite Sources** (+40%): Add authoritative citations to key service and explainer sections.
- **Statistics Addition** (+37%): Add concrete numbers and sourced facts to answer blocks.
- **Fluency Optimization** (+15-30%): Tighten paragraphs and improve extractability for AI answers.
- **Answer-first Structure** (Structural): Use one H1 and clearer H2/H3 sections with direct answers near the top.
- **FAQ Schema** (+40% AI visibility): Add FAQ content and FAQPage schema on priority service pages.
