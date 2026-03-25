# Hybrid GEO Orchestrator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one stable entrypoint that runs the `geo-seo-claude` audit, appends a ReScience optimization pass, and outputs one final PDF.

**Architecture:** Introduce a Python orchestrator that imports the existing audit utilities, builds one combined report payload, writes markdown/JSON artifacts, and calls the existing PDF generator with an extended schema. The workflow layer will call that orchestrator instead of spelling out each script invocation.

**Tech Stack:** Python 3, `requests`, `beautifulsoup4`, `reportlab`, `unittest`, existing repo workflows/docs

---

### Task 1: Add failing tests for the new orchestration helpers

**Files:**
- Create: `tests/test_full_audit.py`
- Create: `scripts/__init__.py`

**Step 1: Write the failing test**

Add tests for:
- building a ReScience optimization pass from collected audit signals
- building a combined audit payload that keeps one score and adds a separate ReScience section
- rendering markdown that includes a `ReScience Optimization Pass` section

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: import or attribute failures because the new orchestration module does not exist yet

**Step 3: Write minimal implementation**

Create the minimal module and functions needed for the tests to import and run.

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: PASS

### Task 2: Implement the new full audit orchestrator

**Files:**
- Create: `scripts/full_audit.py`

**Step 1: Write the failing test**

Extend tests to assert:
- the orchestrator can build the combined JSON payload from mocked audit inputs
- the orchestrator writes markdown and JSON filenames in the expected locations

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: FAIL on missing orchestrator behavior

**Step 3: Write minimal implementation**

Implement:
- data collection using existing `fetch_page`, `citability_scorer`, `brand_scanner`, `llmstxt_generator`
- score assembly
- ReScience advisory generation
- markdown rendering
- JSON writing
- optional PDF generation flag

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: PASS

### Task 3: Extend the PDF generator for the ReScience section

**Files:**
- Modify: `scripts/generate_pdf_report.py`
- Test: `tests/test_full_audit.py`

**Step 1: Write the failing test**

Add tests asserting the combined payload schema includes the ReScience section and that PDF generation accepts it without schema errors.

**Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: FAIL because the generator ignores or mishandles the new advisory data

**Step 3: Write minimal implementation**

Add an optional `ReScience Optimization Pass` PDF section that renders:
- summary text
- `P0`, `P1`, `P2` actions
- platform guidance
- Princeton method recommendations

**Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_full_audit -v`

Expected: PASS

### Task 4: Wire the workflow and docs to the single entrypoint

**Files:**
- Modify: `.agent/workflows/geo-audit.md`
- Create: `.agent/workflows/geo-report-pdf.md`
- Modify: `geo/SKILL.md`
- Modify: `USAGE.md`
- Modify: `README.md`

**Step 1: Write the failing test**

No code test required. Use a documentation/workflow verification checklist:
- `/geo report-pdf <url>` is documented as the preferred single entrypoint
- workflow files invoke `scripts/full_audit.py`
- docs no longer imply the user must manually sequence the scripts for the standard full-PDF flow

**Step 2: Verify the current docs fail the checklist**

Read the files and confirm they still reference manual script-by-script orchestration.

**Step 3: Write minimal implementation**

Update the workflow/docs to reflect:
- one preferred entrypoint
- combined `geo-seo-claude` + ReScience result
- single PDF deliverable

**Step 4: Verify the checklist passes**

Re-read the edited docs and confirm the single-entry flow is consistent.

### Task 5: Run end-to-end verification

**Files:**
- Output: `GEO-CLIENT-REPORT.md`
- Output: `output/data/*.json`
- Output: `output/pdf/*.pdf`

**Step 1: Run the full orchestrator**

Run: `.\.venv\Scripts\python.exe scripts\full_audit.py https://www.transglobalus.com/ --pdf`

Expected: markdown, JSON, and PDF outputs are created successfully

**Step 2: Verify PDF rendering**

Run: `pdftoppm -png output\pdf\<generated-file>.pdf tmp\pdfs\verify-report`

Expected: PNG pages generated without broken layout

**Step 3: Review key pages visually**

Check:
- score section
- action plan
- new ReScience section

**Step 4: Report evidence**

Capture:
- command exit status
- generated file paths
- any remaining caveats
