from __future__ import annotations

from .manifest import build_run_manifest


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
    return {
        "version": "v2",
        "manifest": manifest,
        "status": "stub",
    }
