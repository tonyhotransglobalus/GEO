from __future__ import annotations

from pathlib import Path

from .adjudication import adjudicate_v2_sections
from .evidence import build_v2_evidence_ledger
from .manifest import build_run_manifest
from .publish import publish_v2_artifacts
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
    reports_dir: Path | None = None,
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
    target_domain = manifest.get("target_domain") or ""
    target_url = manifest.get("target_url") or ""
    artifact_paths = publish_v2_artifacts(
        brand_name=target_domain or target_url or "",
        date_stamp=str(manifest.get("run_timestamp") or "")[:10] or "unknown-date",
        run_seed=target_url or target_domain or str(manifest.get("run_timestamp") or ""),
        payload={
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": adjudication,
            "qa": qa,
            "report_sections": report_sections,
        },
        base_dir=reports_dir,
    )
    return {
        "version": "v2",
        "manifest": manifest,
        "evidence": evidence,
        "adjudication": adjudication,
        "report_sections": report_sections,
        "qa": qa,
        "release_warnings": list(qa.get("warnings") or []),
        "artifact_paths": {key: str(value) for key, value in artifact_paths.items()},
        "status": "stub",
    }
