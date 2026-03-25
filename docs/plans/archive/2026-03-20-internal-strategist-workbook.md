# Internal Strategist Workbook Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the strategist report into an internal service-line-first workbook with stronger competitor, earned-media, citation-failure, citation-strength, and evidence-backed analysis.

**Architecture:** Expand the strategy-engine analyzers and report schema first, then redesign the PDF layout around the richer structured output. Preserve the single public entrypoint while deepening the internal analysis and evidence system.

**Tech Stack:** Python, pytest, ReportLab, existing strategy-engine modules, live web collection, PDF rendering workflow

---

### Task 1: Add Evidence Registry And Source Tags

**Files:**
- Modify: `scripts/strategy_engine/reporting.py`
- Modify: `scripts/strategy_engine/core.py` if a structured evidence model is needed
- Modify: `scripts/generate_pdf_report.py`
- Test: `tests/test_reporting.py`

**Step 1: Write the failing test**

Add a test asserting that report sections can include evidence entries and short source tags such as `Academic`, `Official`, `Live Site`, `Live SERP`, and `Heuristic`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reporting.py -k evidence -q`
Expected: FAIL because the evidence registry structure does not exist yet.

**Step 3: Write minimal implementation**

Add a structured evidence layer that:

- stores claim-support entries in report sections
- preserves source type
- supports inline tags in markdown/PDF renderers

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_reporting.py -k evidence -q`
Expected: PASS

**Step 5: Run related tests**

Run: `python -m pytest tests/test_reporting.py tests/test_full_audit.py -q`
Expected: PASS

### Task 2: Normalize Service-Line Query Clusters

**Files:**
- Modify: `scripts/strategy_engine/plugins/opportunity.py`
- Modify: `scripts/strategy_engine/reporting.py`
- Test: `tests/test_opportunity_plugin.py`
- Test: `tests/test_reporting.py`

**Step 1: Write the failing test**

Add a test showing that long scraped homepage text should not become a query-cluster label, and that service lines are promoted into cleaner cluster names.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_opportunity_plugin.py -k cluster -q`
Expected: FAIL because cluster normalization is not strong enough yet.

**Step 3: Write minimal implementation**

Improve cluster normalization so:

- service-line terms are favored
- long raw text blobs are collapsed or discarded
- cluster labels are short and business-meaningful

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_opportunity_plugin.py -k cluster -q`
Expected: PASS

**Step 5: Run related tests**

Run: `python -m pytest tests/test_opportunity_plugin.py tests/test_reporting.py -q`
Expected: PASS

### Task 3: Build Competitor And Earned-Media Gap Analysis

**Files:**
- Modify: `scripts/strategy_engine/plugins/competitive.py`
- Modify: `scripts/strategy_engine/reporting.py`
- Test: `tests/test_competitive_plugins.py`
- Test: `tests/test_reporting.py`

**Step 1: Write the failing test**

Add tests proving the report distinguishes:

- competitors
- earned-media sources
- absence of discovered competitors

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_competitive_plugins.py tests/test_reporting.py -k "competitor or earned" -q`
Expected: FAIL because those richer distinctions are not represented yet.

**Step 3: Write minimal implementation**

Enhance analysis and reporting so:

- competitor sections never look empty without explanation
- earned-media sources are separate from brand-owned or competitor-owned domains
- service-line analysis can show authority gaps

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_competitive_plugins.py tests/test_reporting.py -k "competitor or earned" -q`
Expected: PASS

**Step 5: Run related tests**

Run: `python -m pytest tests/test_competitive_plugins.py tests/test_reporting.py tests/test_full_audit.py -q`
Expected: PASS

### Task 4: Add Citation Failure Modes And Citation Strength

**Files:**
- Modify: `scripts/strategy_engine/plugins/competitive.py`
- Modify: `scripts/strategy_engine/reporting.py`
- Test: `tests/test_competitive_plugins.py`
- Test: `tests/test_reporting.py`

**Step 1: Write the failing test**

Add tests asserting:

- citation failures are classified into explicit modes
- report sections expose citation-strength summaries for owned and earned sources

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_competitive_plugins.py tests/test_reporting.py -k citation -q`
Expected: FAIL because the richer citation models are not present yet.

**Step 3: Write minimal implementation**

Add:

- explicit failure mode classification
- citation strength scoring fields
- report section summaries for those models

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_competitive_plugins.py tests/test_reporting.py -k citation -q`
Expected: PASS

**Step 5: Run related tests**

Run: `python -m pytest tests/test_competitive_plugins.py tests/test_reporting.py tests/test_full_audit.py -q`
Expected: PASS

### Task 5: Redesign Report Section Schema For Workbook Mode

**Files:**
- Modify: `scripts/strategy_engine/reporting.py`
- Modify: `scripts/strategy_engine/markdown.py`
- Test: `tests/test_reporting.py`
- Test: `tests/test_full_audit.py`

**Step 1: Write the failing test**

Add tests asserting the new workbook-oriented section set includes:

- decision summary
- service-line scorecard
- competitor visibility
- earned-media gap
- citation strength
- evidence appendix

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reporting.py -k workbook -q`
Expected: FAIL because the old report section model is still in place.

**Step 3: Write minimal implementation**

Update the report section schema and markdown rendering so the workbook structure replaces the current audit-first emphasis.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_reporting.py -k workbook -q`
Expected: PASS

**Step 5: Run related tests**

Run: `python -m pytest tests/test_reporting.py tests/test_full_audit.py -q`
Expected: PASS

### Task 6: Redesign PDF Layout For Internal Workbook Use

**Files:**
- Modify: `scripts/generate_pdf_report.py`
- Test: `tests/test_full_audit.py`
- Add visual validation artifacts as needed under `tmp/`

**Step 1: Write the failing test**

Add PDF-oriented tests for workbook headings and critical section ordering.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_full_audit.py -k pdf -q`
Expected: FAIL because the old audit-first PDF layout still dominates.

**Step 3: Write minimal implementation**

Redesign the PDF so:

- page 1 is a decision summary, not a decorative scorecard cover
- strategist sections are visually primary
- score widgets become supporting context
- evidence and action layouts are more analyst-friendly

Use the `pdf` skill workflow: render and inspect the output visually.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_full_audit.py -k pdf -q`
Expected: PASS

**Step 5: Run visual checks**

Render the PDF pages and inspect them for hierarchy, spacing, and readability.

### Task 7: Live Validation Against A Real Site

**Files:**
- No required code changes unless live issues surface
- Outputs: `output/reports/...`

**Step 1: Run full suite**

Run: `python -m pytest -q`
Expected: PASS

**Step 2: Run a live strategist report**

Run: `python .\\scripts\\strategy_report.py https://www.transglobalus.com/`
Expected: successful JSON and PDF artifact generation.

**Step 3: Review workbook output**

Check:

- section usefulness
- competitor depth
- earned-media analysis
- citation-strength visibility
- evidence citations
- PDF readability

**Step 4: Fix any live-only issues**

If live validation reveals issues, add focused failing tests first, then fix them.
