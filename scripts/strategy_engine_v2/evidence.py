from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _clean_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _clean_list(values: list[Any] | None) -> list[str]:
    return [str(value).strip() for value in (values or []) if str(value).strip()]


def build_evidence_item(
    *,
    evidence_type: str,
    source_class: str,
    observed_vs_inferred: str,
    platform: str | None,
    query_theme: str | None,
    url_or_domain: str | None,
    raw_observation: Any,
    normalized_summary: str,
    confidence: str,
) -> dict:
    return {
        "evidence_type": evidence_type,
        "source_class": source_class,
        "observed_vs_inferred": observed_vs_inferred,
        "platform": _clean_text(platform),
        "query_theme": _clean_text(query_theme),
        "url_or_domain": _clean_text(url_or_domain),
        "raw_observation": raw_observation,
        "normalized_summary": normalized_summary,
        "confidence": confidence,
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def build_page_fetch_evidence(page_data: dict[str, Any], *, url: str, query_theme: str | None = None) -> dict:
    return build_evidence_item(
        evidence_type="page_fetch",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=query_theme,
        url_or_domain=url,
        raw_observation=page_data,
        normalized_summary=_clean_text(page_data.get("title")) or "Page fetch observation captured.",
        confidence="high",
    )


def build_robots_evidence(robots_data: dict[str, Any], *, url: str) -> dict:
    return build_evidence_item(
        evidence_type="robots",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=None,
        url_or_domain=url,
        raw_observation=robots_data,
        normalized_summary="Robots access rules captured.",
        confidence="high",
    )


def build_llms_evidence(llms_data: dict[str, Any], *, url: str, observed_vs_inferred: str) -> dict:
    summary = "llms.txt guidance captured." if llms_data.get("found") else "llms.txt guidance not found."
    return build_evidence_item(
        evidence_type="llms",
        source_class="live_site",
        observed_vs_inferred=observed_vs_inferred,
        platform=None,
        query_theme=None,
        url_or_domain=url,
        raw_observation=llms_data,
        normalized_summary=summary,
        confidence="medium",
    )


def build_citability_evidence(citability_data: dict[str, Any], *, url: str, query_theme: str | None = None) -> dict:
    return build_evidence_item(
        evidence_type="page_citability",
        source_class="internal_score",
        observed_vs_inferred="inferred",
        platform=None,
        query_theme=query_theme,
        url_or_domain=url,
        raw_observation=citability_data,
        normalized_summary="Citability score calculated for the current page sample.",
        confidence="high",
    )


def build_brand_evidence(brand_data: dict[str, Any], *, url: str) -> dict:
    return build_evidence_item(
        evidence_type="brand_entity",
        source_class="third_party_reference",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=None,
        url_or_domain=url,
        raw_observation=brand_data,
        normalized_summary="Brand and entity signals captured.",
        confidence="medium",
    )


def build_v2_evidence_ledger(
    *,
    manifest: dict[str, Any],
    page_data: dict[str, Any] | None = None,
    robots_data: dict[str, Any] | None = None,
    llms_data: dict[str, Any] | None = None,
    llms_observed_vs_inferred: str = "observed",
    citability_data: dict[str, Any] | None = None,
    brand_data: dict[str, Any] | None = None,
    plugin_results: dict[str, Any] | None = None,
) -> dict:
    items: list[dict] = []
    target_url = manifest.get("target_url")

    items.append(
        build_evidence_item(
            evidence_type="run_manifest",
            source_class="internal_metadata",
            observed_vs_inferred="observed",
            platform=None,
            query_theme=None,
            url_or_domain=target_url,
            raw_observation={
                "mode": manifest.get("mode"),
                "driver": manifest.get("driver"),
                "shadow_run": manifest.get("shadow_run"),
                "comparison_eligibility": manifest.get("comparison_eligibility"),
                "platforms": _clean_list(manifest.get("platforms")),
                "competitors": _clean_list(manifest.get("competitors")),
            },
            normalized_summary="Run scope captured in the V2 manifest.",
            confidence="high",
        )
    )

    if page_data is not None:
        items.append(build_page_fetch_evidence(page_data, url=target_url))
    if robots_data is not None:
        items.append(build_robots_evidence(robots_data, url=target_url))
    if llms_data is not None:
        items.append(build_llms_evidence(llms_data, url=target_url, observed_vs_inferred=llms_observed_vs_inferred))
    if citability_data is not None:
        items.append(build_citability_evidence(citability_data, url=target_url))
    if brand_data is not None:
        items.append(build_brand_evidence(brand_data, url=target_url))
    if plugin_results is not None:
        items.append(
            build_evidence_item(
                evidence_type="plugin_results",
                source_class="internal_score",
                observed_vs_inferred="inferred",
                platform=None,
                query_theme=None,
                url_or_domain=target_url,
                raw_observation=plugin_results,
                normalized_summary="V1 plugin outputs reused where safe.",
                confidence="medium",
            )
        )

    return {
        "items": items,
        "count": len(items),
        "target_url": target_url,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
