# Single-Entry Strategy Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the strategist engine so `scripts/strategy_report.py <url>` is the only public entrypoint and the bloated `scripts/full_audit.py` logic is split into focused internal modules.

**Architecture:** Move orchestration, summary building, markdown rendering, and artifact writing into `scripts/strategy_engine/` modules, then collapse the public CLI to a URL-only interface. Keep `scripts/full_audit.py` as a thin compatibility shim that delegates to the new workflow.

**Tech Stack:** Python, pytest, ReportLab, dataclasses, existing strategy plugins

---

### Task 1: Extract Summary Builders

**Files:**
- Create: `scripts/strategy_engine/summary.py`
- Modify: `scripts/full_audit.py`
- Modify: `scripts/strategy_engine/__init__.py`
- Test: `tests/test_full_audit.py`

**Step 1: Write the failing test**

Add a focused regression test that imports the new summary helpers from `scripts.strategy_engine.summary` and asserts one existing behavior, such as action list bucketing or executive summary handling.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_full_audit.py -k summary -q`
Expected: FAIL because the new module/functions do not exist yet.

**Step 3: Write minimal implementation**

Move these functions from `scripts/full_audit.py` into `scripts/strategy_engine/summary.py` without changing behavior:

- `build_rescience_pass`
- `build_findings`
- `build_action_lists`
- `build_crawler_access`
- `build_executive_summary`

Update imports and re-export only what is needed.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_full_audit.py -k summary -q`
Expected: PASS

**Step 5: Run related tests**

Run: `python -m pytest tests/test_full_audit.py tests/test_reporting.py -q`
Expected: PASS

### Task 2: Extract Markdown and Artifact Helpers

**Files:**
- Create: `scripts/strategy_engine/markdown.py`
- Create: `scripts/strategy_engine/artifacts.py`
- Modify: `scripts/full_audit.py`
- Modify: `scripts/strategy_engine/__init__.py`
- Test: `tests/test_full_audit.py`

**Step 1: Write the failing test**

Add focused tests that import `render_markdown_report` and `build_output_paths` from the new modules and assert existing report behavior.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_full_audit.py -k "markdown or output_paths" -q`
Expected: FAIL because the new modules/functions do not exist yet.

**Step 3: Write minimal implementation**

Move these functions into internal modules:

- `scripts/strategy_engine/markdown.py`
  - `render_markdown_report`
- `scripts/strategy_engine/artifacts.py`
  - `slugify`
  - `extract_brand_name`
  - `build_combined_audit_data`
  - `build_output_paths`
  - `write_text`
  - `write_json`

Leave behavior unchanged.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_full_audit.py -k "markdown or output_paths" -q`
Expected: PASS

**Step 5: Run related tests**

Run: `python -m pytest tests/test_full_audit.py tests/test_reporting.py tests/test_strategy_engine_core.py -q`
Expected: PASS

### Task 3: Extract Internal Workflow Service

**Files:**
- Create: `scripts/strategy_engine/workflow.py`
- Modify: `scripts/full_audit.py`
- Modify: `scripts/strategy_engine/__init__.py`
- Test: `tests/test_full_audit.py`
- Create or Modify: `tests/test_strategy_workflow.py`

**Step 1: Write the failing test**

Add a focused test for a new internal function such as `run_strategy_report(url)` that verifies it returns a combined payload and writes artifact metadata without going through the public CLI.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_strategy_workflow.py -q`
Expected: FAIL because the workflow module/function does not exist yet.

**Step 3: Write minimal implementation**

Create `scripts/strategy_engine/workflow.py` to own:

- raw page/robots/llms/sitemap/citability/brand collection
- default seed topic derivation
- plugin orchestration
- report section assembly
- markdown generation
- artifact writing

Refactor `scripts/full_audit.py` so `orchestrate_audit()` becomes a thin delegating wrapper around the new workflow service.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_strategy_workflow.py -q`
Expected: PASS

**Step 5: Run related tests**

Run: `python -m pytest tests/test_full_audit.py tests/test_strategy_workflow.py tests/test_reporting.py -q`
Expected: PASS

### Task 4: Collapse the Public CLI to URL-Only

**Files:**
- Modify: `scripts/strategy_report.py`
- Modify: `scripts/full_audit.py`
- Modify: `tests/test_strategy_report_cli.py`
- Modify: `README.md`
- Modify: `USAGE.md`
- Modify: `.agent/workflows/geo-audit.md`
- Modify: `.agent/workflows/geo-report-pdf.md`
- Modify: `.agent/workflows/geo-strategy-report.md`

**Step 1: Write the failing test**

Replace the current CLI tests with URL-only expectations:

- accepts one positional `url`
- rejects removed flags such as `--competitor`, `--topic`, and `--no-pdf`
- delegates to the internal workflow with default full-run behavior

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_strategy_report_cli.py -q`
Expected: FAIL because the CLI still accepts extra flags.

**Step 3: Write minimal implementation**

Update `scripts/strategy_report.py` so it:

- accepts only `url`
- always runs the full strategist workflow
- returns structured data for tests

Keep `scripts/full_audit.py` as compatibility-only, not the recommended public path.

Update docs/workflows to present one preferred entrypoint.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_strategy_report_cli.py -q`
Expected: PASS

**Step 5: Run related tests**

Run: `python -m pytest tests/test_strategy_report_cli.py tests/test_full_audit.py -q`
Expected: PASS

### Task 5: Final Regression Sweep

**Files:**
- Modify: any touched files from Tasks 1-4 only if needed
- Test: `tests/`

**Step 1: Run full suite**

Run: `python -m pytest -q`
Expected: PASS

**Step 2: Run command smoke test**

Run: `python .\\scripts\\strategy_report.py --help`
Expected: usage output with only the `url` positional argument.

**Step 3: Review public docs**

Confirm README, usage guide, and workflow files all point to `scripts/strategy_report.py <url>` as the preferred path.

**Step 4: Commit**

Stage only the refactor files once tests are green.
