from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlparse


def _clean_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _clean_list(values: list[Any] | None) -> list[str]:
    return [str(value).strip() for value in (values or []) if str(value).strip()]


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _dedupe_text(values: Any) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for value in _sequence(values):
        text = _clean_text(value)
        if not text:
            continue
        normalized = text.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        items.append(text)
    return items


def _normalized_url(value: str | None) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.netloc or parsed.path).lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return f"{host}{path}"


def _same_page(left: str | None, right: str | None) -> bool:
    return bool(_normalized_url(left)) and _normalized_url(left) == _normalized_url(right)


def _path_from_url(value: str | None) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return path


def _is_high_signal_link(url: str | None, label: str | None = None) -> bool:
    path = _path_from_url(url).lower()
    clean_label = (_clean_text(label) or "").strip()
    normalized_label = clean_label.lower()
    if not path or path == "/":
        return False
    if path.startswith(("/author/", "/category/", "/tag/", "/wp-", "/zh/")):
        return False
    if not clean_label:
        return False
    if normalized_label in {
        "admin",
        "evelle dai",
        "financial news",
        "real estate + lending",
        "latest news",
        "more videos",
        "skip to content",
    }:
        return False
    return True


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


def _build_finding_evidence(finding: Mapping[str, Any], *, url: str) -> dict:
    title = _clean_text(finding.get("title")) or "Audit finding"
    return build_evidence_item(
        evidence_type="finding",
        source_class="internal_score",
        observed_vs_inferred="inferred",
        platform=None,
        query_theme=None,
        url_or_domain=url,
        raw_observation=dict(finding),
        normalized_summary=title,
        confidence=_clean_text(finding.get("severity")) or "medium",
    )


def _build_query_cluster_evidence(cluster: Mapping[str, Any], *, url: str) -> dict:
    label = _clean_text(cluster.get("label")) or "query-cluster"
    return build_evidence_item(
        evidence_type="query_cluster",
        source_class="live_serp_or_platform",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=label,
        url_or_domain=url,
        raw_observation=dict(cluster),
        normalized_summary=f"Query cluster captured: {label}.",
        confidence=_clean_text(cluster.get("priority")) or "medium",
    )


def _build_citation_failure_evidence(failure: Mapping[str, Any]) -> dict:
    query = _clean_text(failure.get("query")) or "query"
    return build_evidence_item(
        evidence_type="citation_failure",
        source_class="live_serp_or_platform",
        observed_vs_inferred="inferred",
        platform=None,
        query_theme=query,
        url_or_domain=_clean_text(failure.get("target_url")),
        raw_observation=dict(failure),
        normalized_summary=f"Citation failure recorded for '{query}'.",
        confidence=_clean_text(_mapping(failure.get("metadata")).get("label")) or "medium",
    )


def _build_benchmark_row_evidence(row: Mapping[str, Any], *, url: str) -> dict:
    competitor = _clean_text(row.get("competitor_name")) or "competitor"
    return build_evidence_item(
        evidence_type="benchmark_row",
        source_class="live_serp_or_platform",
        observed_vs_inferred="observed",
        platform=_clean_text(row.get("platform")),
        query_theme=", ".join(_dedupe_text(row.get("top_winning_queries"))) or None,
        url_or_domain=url,
        raw_observation=dict(row),
        normalized_summary=f"Benchmark row captured for {competitor}.",
        confidence=_clean_text(row.get("confidence")) or "medium",
    )


def _build_platform_observation_evidence(row: Mapping[str, Any], *, url: str) -> dict:
    platform = _clean_text(row.get("platform")) or "platform"
    return build_evidence_item(
        evidence_type="platform_observation",
        source_class="live_serp_or_platform",
        observed_vs_inferred="inferred",
        platform=platform,
        query_theme=None,
        url_or_domain=url,
        raw_observation=dict(row),
        normalized_summary=f"{platform} platform note reused from the bridged audit.",
        confidence=_clean_text(row.get("confidence")) or "medium",
    )


def _first_query(cluster: Mapping[str, Any]) -> str | None:
    queries = _dedupe_text(cluster.get("queries"))
    if queries:
        return queries[0]
    label = _clean_text(cluster.get("label"))
    return label or None


def build_sampled_query_prompt_rows(audit_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    query_clusters = [
        _mapping(cluster)
        for cluster in _sequence(audit_data.get("query_clusters"))
        if isinstance(cluster, Mapping)
    ]
    citation_failures = [
        _mapping(failure)
        for failure in _sequence(audit_data.get("citation_failures"))
        if isinstance(failure, Mapping)
    ]
    locale = _clean_text(
        _mapping(
            _mapping(
                _mapping(audit_data.get("client_report_sections")).get("competitive_benchmark")
            ).get("sample_scope")
        ).get("locale")
    )
    capture_timestamp = _clean_text(audit_data.get("date"))
    failures_by_query = {
        _string(failure.get("query")).lower(): failure
        for failure in citation_failures
        if _string(failure.get("query"))
    }
    rows: list[dict[str, Any]] = []
    seen_queries: set[str] = set()

    for cluster in query_clusters:
        primary_query = _first_query(cluster)
        if not primary_query:
            continue
        normalized_query = primary_query.lower()
        if normalized_query in seen_queries:
            continue
        seen_queries.add(normalized_query)
        metadata = _mapping(cluster.get("metadata"))
        failure = failures_by_query.get(normalized_query, {})
        rows.append(
            {
                "capture_mode": "sampled_query_bridge",
                "query_or_prompt": primary_query,
                "query_theme": _clean_text(cluster.get("label")) or primary_query,
                "platform": None,
                "model_surface": "bridge-sampled-query",
                "locale": locale,
                "capture_timestamp": capture_timestamp,
                "brand_mentioned": bool(metadata.get("site_visible")),
                "brand_cited": bool(metadata.get("site_visible")),
                "winning_domains": _dedupe_text(metadata.get("top_domains")),
                "winning_urls": [],
                "response_summary": (
                    "Sampled search visibility did not retain the brand in the observed result set."
                    if failure
                    else "Sampled query evidence was retained from the bridged audit."
                ),
                "why_we_lost_or_won": _clean_text(failure.get("recommended_fix"))
                or "Use sampled query evidence as a directional signal until exact prompt captures are available.",
                "confidence": _clean_text(cluster.get("priority"))
                or _clean_text(metadata.get("label"))
                or _clean_text(_mapping(failure.get("metadata")).get("label"))
                or "medium",
            }
        )

    for failure in citation_failures:
        query = _clean_text(failure.get("query"))
        if not query:
            continue
        normalized_query = query.lower()
        if normalized_query in seen_queries:
            continue
        seen_queries.add(normalized_query)
        rows.append(
            {
                "capture_mode": "sampled_query_bridge",
                "query_or_prompt": query,
                "query_theme": query,
                "platform": None,
                "model_surface": "bridge-sampled-query",
                "locale": locale,
                "capture_timestamp": capture_timestamp,
                "brand_mentioned": bool(_mapping(failure.get("metadata")).get("site_visible")),
                "brand_cited": bool(_mapping(failure.get("metadata")).get("site_visible")),
                "winning_domains": [],
                "winning_urls": [],
                "response_summary": "Sampled search visibility did not retain the brand for this query.",
                "why_we_lost_or_won": _clean_text(failure.get("recommended_fix"))
                or "Use sampled query evidence as a directional signal until exact prompt captures are available.",
                "confidence": _clean_text(_mapping(failure.get("metadata")).get("label")) or "medium",
            }
        )

    return rows


def _build_prompt_proof_evidence(row: Mapping[str, Any], *, url: str) -> dict:
    query = _clean_text(row.get("query_or_prompt")) or "prompt"
    capture_mode = _clean_text(row.get("capture_mode"))
    is_sampled_query_bridge = capture_mode == "sampled_query_bridge"
    return build_evidence_item(
        evidence_type="prompt_proof",
        source_class="live_serp_or_platform",
        observed_vs_inferred="inferred" if is_sampled_query_bridge else "observed",
        platform=_clean_text(row.get("platform")),
        query_theme=_clean_text(row.get("query_theme")) or query,
        url_or_domain=url,
        raw_observation=dict(row),
        normalized_summary=(
            f"Sampled query proof bridged for {query}."
            if is_sampled_query_bridge
            else f"Prompt proof captured for {query}."
        ),
        confidence=_clean_text(row.get("confidence")) or "medium",
    )


def _build_priority_page_evidence(row: Mapping[str, Any]) -> dict:
    page_url = _clean_text(row.get("page_url"))
    return build_evidence_item(
        evidence_type="priority_page",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=_clean_text(row.get("page_type")),
        url_or_domain=page_url,
        raw_observation=dict(row),
        normalized_summary=f"Priority page evidence captured for {page_url or 'page sample'}.",
        confidence=_clean_text(row.get("confidence")) or "medium",
    )


def _build_source_domain_evidence(row: Mapping[str, Any]) -> dict:
    domain = _clean_text(row.get("domain"))
    return build_evidence_item(
        evidence_type="source_domain",
        source_class="third_party_reference",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=_clean_text(row.get("source_type")),
        url_or_domain=domain,
        raw_observation=dict(row),
        normalized_summary=f"Source domain evidence captured for {domain or 'domain'}.",
        confidence="medium",
    )


def _build_linked_page_evidence(url: str, *, source: str, label: str | None = None) -> dict:
    summary_label = _clean_text(label) or url
    return build_evidence_item(
        evidence_type="linked_page",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=source,
        url_or_domain=url,
        raw_observation={"url": url, "source": source, "label": summary_label},
        normalized_summary=f"Observed linked page candidate: {summary_label}.",
        confidence="medium",
    )


def build_v2_evidence_ledger(
    *,
    manifest: dict[str, Any],
    audit_data: dict[str, Any] | None = None,
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
    bridged_audit = _mapping(audit_data)
    bridged_plugin_results = _mapping(bridged_audit.get("plugin_results"))
    readiness = _mapping(bridged_plugin_results.get("readiness"))
    readiness_inputs = _mapping(readiness.get("inputs"))
    client_sections = _mapping(bridged_audit.get("client_report_sections"))

    if page_data is None and readiness_inputs.get("page_data") is not None:
        page_data = _mapping(readiness_inputs.get("page_data"))
    if robots_data is None and readiness_inputs.get("robots_data") is not None:
        robots_data = _mapping(readiness_inputs.get("robots_data"))
    if llms_data is None and readiness_inputs.get("llms_validation") is not None:
        llms_data = _mapping(readiness_inputs.get("llms_validation"))
        llms_observed_vs_inferred = "inferred"
    if citability_data is None and readiness_inputs.get("citability_data") is not None:
        citability_data = _mapping(readiness_inputs.get("citability_data"))
    if brand_data is None:
        if readiness_inputs.get("brand_data") is not None:
            brand_data = _mapping(readiness_inputs.get("brand_data"))
        elif bridged_audit.get("entity_graph") is not None:
            brand_data = _mapping(bridged_audit.get("entity_graph"))
    if plugin_results is None and bridged_plugin_results:
        plugin_results = bridged_plugin_results

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
        seen_page_urls: set[str] = set()
        accepted_internal_links = 0
        for row in _sequence(_mapping(page_data).get("internal_links")):
            if isinstance(row, Mapping):
                linked_url = _clean_text(row.get("url"))
                label = _clean_text(row.get("text"))
            else:
                linked_url = _clean_text(row)
                label = None
            normalized = _normalized_url(linked_url)
            if (
                not normalized
                or normalized in seen_page_urls
                or _same_page(linked_url, target_url)
                or not _is_high_signal_link(linked_url, label)
            ):
                continue
            seen_page_urls.add(normalized)
            items.append(
                _build_linked_page_evidence(
                    linked_url,
                    source="internal_link",
                    label=label,
                )
            )
            accepted_internal_links += 1
            if accepted_internal_links >= 12:
                break
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

    for finding in _sequence(bridged_audit.get("findings")):
        if isinstance(finding, Mapping):
            items.append(_build_finding_evidence(finding, url=target_url))

    for cluster in _sequence(bridged_audit.get("query_clusters")):
        if isinstance(cluster, Mapping):
            items.append(_build_query_cluster_evidence(cluster, url=target_url))

    for failure in _sequence(bridged_audit.get("citation_failures")):
        if isinstance(failure, Mapping):
            items.append(_build_citation_failure_evidence(failure))

    benchmark = _mapping(client_sections.get("competitive_benchmark"))
    for row in _sequence(benchmark.get("benchmark_rows")):
        if isinstance(row, Mapping):
            items.append(_build_benchmark_row_evidence(row, url=target_url))

    platform_breakdown = _mapping(client_sections.get("platform_breakdown"))
    for row in _sequence(platform_breakdown.get("platforms")):
        if isinstance(row, Mapping):
            items.append(_build_platform_observation_evidence(row, url=target_url))

    prompt_query_proof = _mapping(client_sections.get("prompt_query_proof"))
    explicit_prompt_rows = [
        row
        for row in _sequence(prompt_query_proof.get("rows"))
        if isinstance(row, Mapping)
    ]
    prompt_rows = explicit_prompt_rows or build_sampled_query_prompt_rows(bridged_audit)
    for row in prompt_rows:
        if isinstance(row, Mapping):
            items.append(_build_prompt_proof_evidence(row, url=target_url))

    page_source_evidence = _mapping(client_sections.get("page_source_evidence"))
    for row in _sequence(page_source_evidence.get("priority_pages")):
        if isinstance(row, Mapping):
            items.append(_build_priority_page_evidence(row))
    for row in _sequence(page_source_evidence.get("source_domains")):
        if isinstance(row, Mapping):
            items.append(_build_source_domain_evidence(row))
    sitemap_pages = _sequence(readiness_inputs.get("sitemap_pages"))
    seen_sitemap_urls = {
        _normalized_url(_clean_text(item.get("url")) if isinstance(item, Mapping) else _clean_text(item))
        for item in items
        if _string(item.get("evidence_type")) == "linked_page"
    }
    if not any(_string(item.get("evidence_type")) == "linked_page" for item in items):
        for row in sitemap_pages[:5]:
            sitemap_url = _clean_text(row.get("url")) if isinstance(row, Mapping) else _clean_text(row)
            normalized = _normalized_url(sitemap_url)
            if (
                not normalized
                or normalized in seen_sitemap_urls
                or _same_page(sitemap_url, target_url)
                or not _is_high_signal_link(sitemap_url, _path_from_url(sitemap_url).split("/")[-1].replace("-", " "))
            ):
                continue
            seen_sitemap_urls.add(normalized)
            items.append(
                _build_linked_page_evidence(
                    sitemap_url,
                    source="sitemap",
                )
            )

    return {
        "items": items,
        "count": len(items),
        "target_url": target_url,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
