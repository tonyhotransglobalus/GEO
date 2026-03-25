# Single-Entry Strategy Refactor Design

**Date:** 2026-03-20

## Goal

Refactor the strategist engine so the product has one public entrypoint:

```bash
python scripts/strategy_report.py <url>
```

The command should always run the full GEO/SEO strategist workflow, use AI-assisted analysis where available, and write the combined JSON, markdown, and PDF artifacts without exposing secondary workflow flags.

## Problem

The current implementation works, but the public shape is still bloated:

- `scripts/strategy_report.py` is the preferred entrypoint, but `scripts/full_audit.py` still behaves like a second public CLI.
- `scripts/full_audit.py` mixes raw collection, orchestration, report synthesis, markdown rendering, artifact pathing, and file writing in one large module.
- Docs and workflow files have needed repeated cleanup because the public/private boundary is not obvious in the code.

This makes the product harder to maintain and makes the “single entrypoint” promise feel weaker than it should.

## Target Shape

### Public interface

- Keep `scripts/strategy_report.py` as the only public CLI.
- Accept only one positional argument: `url`.
- Always run the full strategist workflow.
- Always write report artifacts to the report directory.
- Keep the Python return value structured for tests and internal callers.

### Internal structure

Move the bloated internals from `scripts/full_audit.py` into focused internal modules under `scripts/strategy_engine/`:

- `workflow.py`
  - Build fetched inputs.
  - Build the analysis context.
  - Run the plugin orchestrator.
  - Return the final `ReportModel` plus raw audit inputs needed for rendering.
- `summary.py`
  - `build_rescience_pass`
  - `build_findings`
  - `build_action_lists`
  - `build_crawler_access`
  - `build_executive_summary`
- `artifacts.py`
  - `slugify`
  - `extract_brand_name`
  - `build_combined_audit_data`
  - `build_output_paths`
  - `write_text`
  - `write_json`
- `markdown.py`
  - `render_markdown_report`

### Compatibility stance

- Keep `scripts/full_audit.py` as a thin compatibility shim for now.
- The shim should delegate to the new internal workflow instead of owning orchestration logic.
- Top-level docs and workflow files should continue to present `strategy_report.py` as the preferred path.

## Data Flow

```text
URL
-> strategy_report.py
-> strategy_engine.workflow.run_strategy_report()
-> fetch raw inputs
-> StrategyOrchestrator plugins
-> summary/artifact builders
-> combined JSON payload
-> markdown renderer
-> PDF renderer
-> output/report directory
```

## AI Role

The refactor preserves the existing product stance:

- deterministic collectors gather the facts
- plugins structure opportunity/competitor/entity/citation data
- AI-assisted analysis is used in the interpretation and synthesis layer of the strategist report

The refactor is about clarifying boundaries, not reducing analytical depth.

## Testing Strategy

- Add focused tests around the new internal workflow boundary.
- Preserve existing end-to-end orchestrator tests.
- Update CLI tests so the public entrypoint only accepts a URL.
- Keep markdown/report regression coverage intact during the extraction.

## Recommendation

Use a staged refactor:

1. Extract internal workflow and report-building helpers first.
2. Keep behavior stable with tests.
3. Simplify the public CLI only after the internal modules are in place.
4. Leave `full_audit.py` as a compatibility shim rather than deleting it immediately.
