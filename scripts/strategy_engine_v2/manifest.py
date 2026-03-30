from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse


def _normalize_domain(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if domain.startswith("www."):
        return domain[4:]
    return domain


def build_run_manifest(
    *,
    url: str,
    locale: str,
    platforms: list[str] | None,
    competitors: list[str] | None,
    mode: str,
    driver: str,
    model: str | None = None,
    interactive: bool = False,
    seed_topics: list[str] | None = None,
    compare_to_v1: bool = False,
    shadow_run: bool = False,
) -> dict:
    cleaned_platforms = [str(platform).strip() for platform in (platforms or []) if str(platform).strip()]
    cleaned_competitors = [str(competitor).strip() for competitor in (competitors or []) if str(competitor).strip()]
    cleaned_seed_topics = [str(topic).strip() for topic in (seed_topics or []) if str(topic).strip()]
    return {
        "target_url": url,
        "target_domain": _normalize_domain(url),
        "locale": locale,
        "platforms": cleaned_platforms,
        "competitors": cleaned_competitors,
        "query_framework": "seed_topics",
        "seed_topics": cleaned_seed_topics,
        "mode": mode,
        "driver": driver,
        "model": model,
        "interactive": interactive,
        "shadow_run": shadow_run,
        "run_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "comparison_eligibility": {
            "requested": compare_to_v1,
            "eligible": compare_to_v1,
            "requires_same_target": True,
            "requires_same_locale": True,
            "requires_same_platform_set": True,
        },
    }
