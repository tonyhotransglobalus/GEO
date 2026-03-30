from __future__ import annotations

from pathlib import Path

from .adjudication import adjudicate_v2_sections
from .evidence import build_v2_evidence_ledger
from .manifest import build_run_manifest
from .markdown import MARKDOWN_FILENAME, render_v2_markdown_report
from .qa import run_release_checks
from .reporting import build_v2_report_sections


def run_strategy_report_v2(
    url: str,
    *,
    shadow_run: bool = False,
    compare_to_v1: bool = False,
    locale: str = "en-us",
    platforms: list[str] | None = None,
    competitors: list[str] | None = None,
    mode: str = "script-only",
    driver: str = "script",
    model: str | None = None,
    non_interactive: bool = False,
) -> dict:
    manifest = build_run_manifest(
        url=url,
        locale=locale,
        platforms=platforms,
        competitors=competitors,
        mode=mode,
        driver=driver,
        model=model,
        interactive=not non_interactive,
        compare_to_v1=compare_to_v1,
        shadow_run=shadow_run,
    )
    evidence = build_v2_evidence_ledger(manifest=manifest)
    adjudication = adjudicate_v2_sections(manifest=manifest, evidence=evidence)
    report_sections = build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": adjudication,
        }
    )
    qa = run_release_checks(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": adjudication,
            "report_sections": report_sections,
        }
    )
    markdown_report = render_v2_markdown_report(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": adjudication,
            "report_sections": report_sections,
        }
    )
    markdown_path = Path(__file__).resolve().parents[2] / "output" / "reports" / MARKDOWN_FILENAME
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown_report, encoding="utf-8")
    return {
        "version": "v2",
        "manifest": manifest,
        "evidence": evidence,
        "adjudication": adjudication,
        "report_sections": report_sections,
        "qa": qa,
        "release_warnings": list(qa.get("warnings") or []),
        "status": "stub",
    }
