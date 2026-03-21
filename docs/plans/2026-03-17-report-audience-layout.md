# Report Audience and Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the GEO report so key findings speak to executives, marketers, and developers, while fixing PDF clipping and overlap caused by brittle table rendering.

**Architecture:** Keep `scripts/full_audit.py` as the data orchestrator and extend its finding model with audience-specific fields. Refactor `scripts/generate_pdf_report.py` to render findings as structured blocks and to build wrapped ReportLab tables from reusable paragraph cell helpers so long text flows cleanly across pages.

**Tech Stack:** Python, unittest, ReportLab, Poppler (`pdftotext`, `pdftoppm`)

---

### Task 1: Lock the new finding contract with tests

**Files:**
- Modify: `tests/test_full_audit.py`
- Test: `tests/test_full_audit.py`

**Step 1: Write the failing test**

Add tests that assert:
- `build_findings()` returns `summary`, `leadership_impact`, `marketing_action`, `developer_action`, and `observed_evidence`
- `render_markdown_report()` includes labeled audience sections inside each finding

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: failures showing the new fields or labels are missing.

**Step 3: Write minimal implementation**

Update `scripts/full_audit.py` to produce the richer finding structure and markdown rendering.

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: the new findings tests pass.

### Task 2: Lock wrapped table rendering with tests

**Files:**
- Modify: `tests/test_full_audit.py`
- Modify: `scripts/generate_pdf_report.py`
- Test: `tests/test_full_audit.py`

**Step 1: Write the failing test**

Add tests that assert:
- a reusable wrapped table helper returns `Paragraph` cells for body content
- generated PDF text includes long crawler recommendations and labeled finding sections

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: failures showing the helper does not exist or the labels are absent from extracted PDF text.

**Step 3: Write minimal implementation**

Refactor `scripts/generate_pdf_report.py` to:
- add paragraph-based table cell helpers
- use wrapped paragraph tables for details, scores, platforms, crawler access, and glossary
- rebalance widths and spacing

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: all PDF helper and text extraction tests pass.

### Task 3: Improve PDF finding presentation

**Files:**
- Modify: `scripts/generate_pdf_report.py`
- Test: `tests/test_full_audit.py`

**Step 1: Write the failing test**

Add a test that extracts text from a generated PDF and confirms:
- `Why this matters to leadership`
- `What marketing should do`
- `What dev should change`
- `Observed evidence`

appear in the key findings section.

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: the new labels are missing.

**Step 3: Write minimal implementation**

Render each finding as a compact, styled block with the new labeled subsections.

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: extracted PDF text includes the new finding labels.

### Task 4: Visual verification on a real PDF

**Files:**
- Modify: `scripts/full_audit.py` if any output data cleanup is needed
- Modify: `scripts/generate_pdf_report.py` if visual issues remain

**Step 1: Generate a real report**

Run: `.\.venv\Scripts\python.exe scripts\full_audit.py https://www.transglobalus.com/`

**Step 2: Render pages for inspection**

Run: `pdftoppm -png output/reports/transglobal-holding-company-2026-03-17/GEO-REPORT.pdf tmp/pdfs/transglobal-report`

**Step 3: Inspect visual output**

Check dense pages for:
- clipped table values
- overlapping text
- awkward page breaks
- crowded finding blocks

**Step 4: Make minimal follow-up tweaks if needed**

Adjust widths, padding, or spacing only where the screenshots show a real defect.

**Step 5: Re-run verification**

Run:
- `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`
- `.\.venv\Scripts\python.exe scripts\full_audit.py https://www.transglobalus.com/`

Expected: tests pass and the regenerated PDF renders cleanly.
