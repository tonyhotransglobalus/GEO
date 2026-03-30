from __future__ import annotations

from urllib.parse import urlparse


def run_strategy_report_v2(
    url: str,
    *,
    shadow_run: bool = False,
    compare_to_v1: bool = False,
    locale: str = "en-us",
    platforms: list[str] | None = None,
    competitors: list[str] | None = None,
    non_interactive: bool = False,
) -> dict:
    return {
        "version": "v2",
        "target_url": url,
        "target_domain": urlparse(url).netloc,
        "shadow_run": shadow_run,
        "compare_to_v1": compare_to_v1,
        "locale": locale,
        "platforms": platforms or [],
        "competitors": competitors or [],
        "non_interactive": non_interactive,
        "status": "stub",
    }
