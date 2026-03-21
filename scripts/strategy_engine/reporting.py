from __future__ import annotations

from typing import Any, Mapping

from .core import EvidenceEntry, ReportModel, evidence_source_tag, serialize_model


REPORT_SECTION_ORDER = (
    "decision_summary",
    "service_line_scorecard",
    "query_universe",
    "competitor_visibility",
    "earned_media_gap",
    "citation_diagnosis",
    "entity_trust_graph",
    "technical_geo_gates",
    "execution_ledger",
    "developer_appendix",
    "evidence_appendix",
)

EVIDENCE_APPENDIX_TITLE = "Evidence and Methodology Appendix"
LEGACY_REPORT_SECTION_KEYS = (
    "executive_summary",
    "readiness_scorecard",
    "opportunity_map",
    "competitor_gap_analysis",
    "citation_diagnosis",
    "entity_authority_analysis",
    "roadmap",
    "developer_appendix",
    "evidence_appendix",
)

_EVIDENCE_METADATA_LABELS = (
    ("search_intent", "Search Intent"),
    ("priority", "Priority"),
    ("failure_mode", "Failure Mode"),
    ("recommended_fix", "Recommended Fix"),
    ("recommendation", "Recommendation"),
)

_WORKBOOK_SERVICE_LINES = (
    ("Life Insurance", ("life insurance", "insurance")),
    ("Annuities", ("annuities", "annuity", "life & annuities")),
    ("Mortgage Financing", ("mortgage financing", "mortgage", "lending")),
    ("Health Insurance", ("health insurance",)),
    ("Real Estate", ("real estate", "real-estate")),
    (
        "Property and Casualty Insurance",
        (
            "property and casualty insurance",
            "property & casualty insurance",
            "property/casualty insurance",
            "property casualty insurance",
        ),
    ),
    ("Asset Management", ("asset management", "financial management", "wealth management")),
    ("Investment", ("investment",)),
    ("Tax Services", ("tax services", "tax")),
)


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


def _source_tag(value: Any) -> str:
    return _string(value)


def _gap_label(value: Any) -> str:
    text = _string(value)
    if not text:
        return ""
    return text.replace("_", " ").strip().title()


def _average_score(*values: Any) -> int:
    scores = [_int_score(value) for value in values if value is not None]
    if not scores:
        return 0
    return round(sum(scores) / len(scores))


def _dimension_payload(score: Any, *, note: str) -> dict[str, Any]:
    numeric = _int_score(score)
    return {
        "score": numeric,
        "label": _score_label(numeric),
        "note": _string(note),
    }


def _freshness_signal_score(page_data: Mapping[str, Any]) -> tuple[int, str]:
    meta_tags = _mapping(page_data.get("meta_tags"))
    structured_data = page_data.get("structured_data")
    freshness_keys = {
        "article:modified_time",
        "article:published_time",
        "og:updated_time",
        "last-modified",
        "last_modified",
        "updated",
        "updated_at",
        "published",
        "published_at",
    }
    if any(_string(key).lower() in freshness_keys for key in meta_tags):
        return 82, "Visible freshness metadata was captured."
    if isinstance(structured_data, list):
        serialized = str(structured_data).lower()
        if any(token in serialized for token in ("datemodified", "datepublished", "modified", "published")):
            return 76, "Structured data includes date-like freshness signals."
    if page_data.get("word_count"):
        return 55, "No explicit freshness marker was captured, so the analysis leans on general page completeness."
    return 35, "No explicit freshness marker was captured."


def _specificity_signal_score(page_data: Mapping[str, Any], citability_data: Mapping[str, Any]) -> tuple[int, str]:
    word_count = _int_score(page_data.get("word_count"))
    heading_count = len(_sequence(page_data.get("h1_tags")))
    citability = _int_score(citability_data.get("average_citability_score"))
    score = _average_score(
        min(100, word_count),
        100 if heading_count == 1 else 60 if heading_count else 35,
        citability,
    )
    note = "The page has enough structure for answer-ready extraction." if score >= 60 else "The page still needs tighter answer blocks and clearer sectioning."
    return score, note


def _attribution_signal_score(entity_graph: Mapping[str, Any], scores: Mapping[str, Any], llms_validation: Mapping[str, Any]) -> tuple[int, str]:
    same_as_count = len(_dedupe_text(entity_graph.get("same_as")))
    schema_score = _int_score(scores.get("schema"))
    llms_exists = bool(llms_validation.get("exists"))
    llms_valid = bool(llms_validation.get("format_valid")) and not llms_validation.get("issues")
    score = _average_score(
        schema_score,
        78 if same_as_count else 42,
        72 if llms_exists and llms_valid else 45,
    )
    note = "The report has a readable entity trail and structured source support." if score >= 60 else "Attribution cues are thin or inconsistently exposed."
    return score, note


def _owned_source_strength(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    plugin_results = _mapping(audit_data.get("plugin_results"))
    readiness = _mapping(plugin_results.get("readiness"))
    geo_scores = _mapping(readiness.get("geo_scores"))
    scores = _mapping(geo_scores.get("scores"))
    if not scores:
        top_level_geo_scores = _mapping(audit_data.get("geo_scores"))
        scores = _mapping(top_level_geo_scores.get("scores"))
    page_data = _mapping(audit_data.get("page_data"))
    citability_data = _mapping(audit_data.get("citability_data"))
    llms_validation = _mapping(audit_data.get("llms_validation"))
    entity_graph = report_model.entity_graph.to_dict() if report_model.entity_graph is not None else {}

    authority_score = _average_score(
        scores.get("brand_authority"),
        scores.get("ai_citability"),
        int(round((float(entity_graph.get("confidence") or 0) * 100))),
    )
    freshness_score, freshness_note = _freshness_signal_score(page_data)
    specificity_score, specificity_note = _specificity_signal_score(page_data, citability_data)
    attribution_score, attribution_note = _attribution_signal_score(entity_graph, scores, llms_validation)

    score = _average_score(authority_score, freshness_score, specificity_score, attribution_score)
    return {
        "score": score,
        "label": _score_label(score),
        "support_type": "owned",
        "dimensions": {
            "authority": _dimension_payload(
                authority_score,
                note="Brand authority and entity confidence are the main owned-source anchors.",
            ),
            "freshness": _dimension_payload(freshness_score, note=freshness_note),
            "specificity": _dimension_payload(specificity_score, note=specificity_note),
            "attribution_clarity": _dimension_payload(attribution_score, note=attribution_note),
        },
        "notes": [
            "Owned pages carry the strongest weight when they are answer-ready and machine-readable.",
            "Freshness and attribution need to be visible enough for answer engines to reuse confidently.",
        ],
    }


def _earned_source_strength(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    plugin_results = _mapping(audit_data.get("plugin_results"))
    competitor_plugin = _mapping(plugin_results.get("competitor_analysis"))
    source_inventory = _mapping(competitor_plugin.get("source_inventory"))
    competitor_profiles = [profile.to_dict() for profile in report_model.competitor_profiles]
    earned_media = _dedupe_text(source_inventory.get("earned_media"))
    competitor_owned = _dedupe_text(source_inventory.get("competitor_owned"))
    authority_gaps = _sequence(competitor_plugin.get("authority_gaps"))

    authority_score = _average_score(
        min(100, len(earned_media) * 25),
        min(100, len(competitor_owned) * 15),
        min(100, len(competitor_profiles) * 10),
    )
    freshness_score = 70 if earned_media else 35
    specificity_score = _average_score(
        45 + len(earned_media) * 8,
        45 + sum(1 for profile in competitor_profiles if _sequence(profile.get("strengths"))),
    )
    attribution_score = _average_score(
        70 if competitor_owned else 40,
        65 if authority_gaps else 45,
    )

    score = _average_score(authority_score, freshness_score, specificity_score, attribution_score)
    return {
        "score": score,
        "label": _score_label(score),
        "support_type": "earned",
        "dimensions": {
            "authority": _dimension_payload(
                authority_score,
                note="Earned-media authority grows when the category has multiple cited third-party sources.",
            ),
            "freshness": _dimension_payload(
                freshness_score,
                note="Earned-media freshness depends on whether live third-party coverage is visible in the sample.",
            ),
            "specificity": _dimension_payload(
                specificity_score,
                note="Specificity improves when coverage points to concrete service lines and comparisons.",
            ),
            "attribution_clarity": _dimension_payload(
                attribution_score,
                note="The report should distinguish direct rivals from publishers and explainers.",
            ),
        },
        "notes": [
            "Earned sources matter because answer engines often cite third-party coverage when owned pages are thin.",
            "A sparse earned-media set means the category map is still incomplete and needs broader discovery.",
        ],
    }


def _merge_gap_items(*values: Any) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for value in values:
        for item in _sequence(value):
            if not isinstance(item, Mapping):
                continue
            normalized = (
                _string(item.get("gap_type")).lower(),
                _string(item.get("gap_theme")).lower(),
                _string(item.get("competitor")).lower(),
                _string(item.get("why_it_matters")).lower(),
            )
            if normalized in seen:
                continue
            seen.add(normalized)
            merged.append(dict(item))
    return merged


def _stringify_evidence_value(value: Any) -> str:
    if isinstance(value, Mapping):
        return _string(value)
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_dedupe_text(value))
    return _string(value)


def format_evidence_item_text(item: Mapping[str, Any]) -> str:
    label = _string(
        item.get("name")
        or item.get("action")
        or item.get("label")
        or item.get("query")
        or item.get("competitor")
        or item.get("issue")
        or item.get("title")
    )
    if not label:
        return serialize_model(item)

    source_tag = _source_tag(item.get("source_tag"))
    heading = f"{label} [{source_tag}]" if source_tag else label

    detail_parts: list[str] = []
    source_type = _string(item.get("source_type"))
    if source_type:
        detail_parts.append(f"Source Type: {source_type}")

    url = _string(item.get("url"))
    if url:
        detail_parts.append(f"Url: {url}")

    evidence = item.get("evidence")
    if evidence:
        detail_parts.append(f"Evidence: {_stringify_evidence_value(evidence)}")

    metadata = _mapping(item.get("metadata"))
    for key, display_label in _EVIDENCE_METADATA_LABELS:
        value = metadata.get(key)
        if value:
            detail_parts.append(f"{display_label}: {_stringify_evidence_value(value)}")

    if detail_parts:
        return f"{heading} ({'; '.join(detail_parts)})"
    return heading


def _is_evidence_item(item: Mapping[str, Any]) -> bool:
    return any(key in item for key in ("source_type", "source_tag", "metadata", "url"))


def _build_evidence_entry(
    label: str,
    source_type: str,
    *,
    evidence: Any = None,
    url: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EvidenceEntry:
    return EvidenceEntry(
        label=_string(label),
        source_type=_string(source_type),
        source_tag=evidence_source_tag(source_type),
        evidence=_dedupe_text(evidence),
        url=_string(url) or None,
        metadata=dict(metadata or {}),
    )


def _score_label(score: Any) -> str:
    try:
        numeric = int(round(float(score)))
    except (TypeError, ValueError):
        numeric = 0
    if numeric >= 85:
        return "strong"
    if numeric >= 65:
        return "steady"
    if numeric >= 45:
        return "watch"
    return "urgent"


def _dedupe_text(items: Any) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for item in _sequence(items):
        text = _string(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(text)
    return results


def _int_score(value: Any) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _normalize_action_item(
    action: Any,
    *,
    owner: str,
    source: str,
    impact: str | None = None,
    evidence: str | None = None,
) -> dict[str, Any]:
    if isinstance(action, Mapping):
        text = _string(action.get("action") or action.get("text") or action.get("title"))
        owner = _string(action.get("owner")) or owner
        source = _string(action.get("source")) or source
        impact = _string(action.get("impact")) or impact
        evidence = _string(action.get("evidence")) or evidence
    else:
        text = _string(action)

    payload: dict[str, Any] = {
        "action": text,
        "owner": owner,
        "source": source,
    }
    if impact:
        payload["impact"] = impact
    if evidence:
        payload["evidence"] = evidence
    return payload


def _owner_for_action(action: str) -> str:
    text = action.lower()
    if any(token in text for token in ("llms", "schema", "ssr", "robots", "heading", "technical", "crawl", "csp")):
        return "developers"
    if any(token in text for token in ("citab", "content", "rewrite", "publish", "faq", "keyword", "marketing", "proof")):
        return "marketing"
    if any(token in text for token in ("entity", "authority", "brand", "earned media", "pr", "press")):
        return "leadership"
    return "cross-functional"


def _get_report_context(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    context = dict(audit_data)
    context.setdefault("query_clusters", [cluster.to_dict() for cluster in report_model.query_clusters])
    context.setdefault("competitor_profiles", [profile.to_dict() for profile in report_model.competitor_profiles])
    context.setdefault(
        "entity_graph",
        report_model.entity_graph.to_dict() if report_model.entity_graph is not None else None,
    )
    context.setdefault(
        "citation_failures",
        [failure.to_dict() for failure in report_model.citation_failures],
    )
    context.setdefault("plugin_results", dict(report_model.plugin_results))
    context.setdefault("metadata", dict(report_model.metadata))
    return context


def _normalized_text(value: Any) -> str:
    return " ".join(
        token
        for token in _string(value).lower().replace("&", " and ").replace("/", " ").split()
        if token
    )


def _service_line_variants(value: str) -> tuple[str, ...]:
    normalized = _normalized_text(value)
    variants = {normalized}
    if "and" in normalized:
        variants.add(normalized.replace(" and ", " "))
    return tuple(item for item in variants if item)


def _service_line_rows(report_model: ReportModel, audit_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    page_data = _mapping(audit_data.get("page_data"))
    heading_structure = _sequence(page_data.get("heading_structure"))
    plugin_results = _mapping(audit_data.get("plugin_results"))
    opportunities = _sequence(_mapping(plugin_results.get("opportunity")).get("opportunities"))
    query_clusters = [cluster.to_dict() for cluster in report_model.query_clusters]
    geo_scores = _mapping(audit_data.get("geo_scores"))
    scores = _mapping(geo_scores.get("scores"))
    citation_strength = _build_citation_diagnosis(report_model, audit_data).get("citation_strength", {})
    owned_strength = _mapping(citation_strength).get("owned_sources", {})
    earned_strength = _mapping(citation_strength).get("earned_sources", {})
    candidate_texts = [
        page_data.get("description"),
        page_data.get("title"),
        page_data.get("text_content"),
        *(item.get("text") for item in heading_structure if isinstance(item, Mapping)),
        *(
            cluster.get("metadata", {}).get("seed_topic")
            for cluster in query_clusters
            if isinstance(cluster, Mapping)
        ),
        *(cluster.get("queries") or [] for cluster in query_clusters if isinstance(cluster, Mapping)),
        *(item.get("query") for item in opportunities if isinstance(item, Mapping)),
    ]
    flattened_candidates: list[str] = []
    for value in candidate_texts:
        if isinstance(value, list):
            flattened_candidates.extend(_string(item) for item in value)
        else:
            flattened_candidates.append(_string(value))
    normalized_candidates = [_normalized_text(value) for value in flattened_candidates if _string(value)]

    rows: list[dict[str, Any]] = []
    seen_service_lines: set[str] = set()
    for service_line, hints in _WORKBOOK_SERVICE_LINES:
        hint_variants = {
            variant
            for hint in hints
            for variant in _service_line_variants(hint)
        }
        matched_queries = [
            _string(item.get("query"))
            for item in opportunities
            if isinstance(item, Mapping)
            and any(variant in _normalized_text(item.get("query")) for variant in hint_variants)
        ]
        matched_clusters = [
            cluster
            for cluster in query_clusters
            if isinstance(cluster, Mapping)
            and (
                any(variant in _normalized_text(cluster.get("label")) for variant in hint_variants)
                or any(
                    variant in _normalized_text(query)
                    for query in _sequence(cluster.get("queries"))
                    for variant in hint_variants
                )
                or any(
                    variant in _normalized_text(_mapping(cluster.get("metadata")).get("seed_topic"))
                    for variant in hint_variants
                )
            )
        ]
        matched_page_signal = any(
            any(variant in candidate for variant in hint_variants)
            for candidate in normalized_candidates
        )
        if not (matched_queries or matched_clusters or matched_page_signal):
            continue

        seen_service_lines.add(service_line)
        matched_opportunities = [
            item
            for item in opportunities
            if isinstance(item, Mapping)
            and _string(item.get("query")) in matched_queries
        ]
        visibility = "not yet sampled"
        if any(item.get("site_visible") is True for item in matched_opportunities):
            visibility = "visible"
        elif matched_opportunities:
            visibility = "not visible"

        opportunity_score = max(
            (_int_score(item.get("opportunity_score")) for item in matched_opportunities),
            default=0,
        )
        priority = "high" if visibility == "not visible" or opportunity_score >= 65 else "medium"
        if not matched_opportunities and matched_page_signal:
            priority = "medium"
        rows.append(
            {
                "service_line": service_line,
                "visibility": visibility,
                "citation_readiness": f"{_int_score(scores.get('ai_citability'))}/100",
                "citation_strength": _string(_mapping(owned_strength).get("label")) or "watch",
                "earned_media_strength": _string(_mapping(earned_strength).get("label")) or "urgent",
                "technical_readiness": f"{_int_score(scores.get('technical'))}/100",
                "priority": priority,
                "opportunity_score": opportunity_score,
                "observed_queries": _dedupe_text(matched_queries)[:5],
                "cluster_labels": _dedupe_text(cluster.get("label") for cluster in matched_clusters)[:5],
            }
        )

    if rows:
        return rows

    fallback_rows: list[dict[str, Any]] = []
    for cluster in query_clusters[:3]:
        if not isinstance(cluster, Mapping):
            continue
        label = _string(cluster.get("label")).replace("-", " ").title() or "Priority Topic"
        if label in seen_service_lines:
            continue
        fallback_rows.append(
            {
                "service_line": label,
                "visibility": "not yet sampled",
                "citation_readiness": f"{_int_score(scores.get('ai_citability'))}/100",
                "citation_strength": _string(_mapping(owned_strength).get("label")) or "watch",
                "earned_media_strength": _string(_mapping(earned_strength).get("label")) or "urgent",
                "technical_readiness": f"{_int_score(scores.get('technical'))}/100",
                "priority": _string(cluster.get("priority")) or "medium",
                "opportunity_score": _int_score(cluster.get("opportunity_score")),
                "observed_queries": _dedupe_text(cluster.get("queries"))[:5],
                "cluster_labels": [label],
            }
        )
    return fallback_rows


def _build_executive_summary(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    geo_scores = _mapping(audit_data.get("geo_scores"))
    scores = _mapping(geo_scores.get("scores"))
    page_data = _mapping(audit_data.get("page_data"))
    llms_validation = _mapping(audit_data.get("llms_validation"))
    citability_data = _mapping(audit_data.get("citability_data"))
    rescience_pass = _mapping(audit_data.get("rescience_pass"))
    query_clusters = _sequence(audit_data.get("query_clusters"))
    citation_failures = _sequence(audit_data.get("citation_failures"))
    geo_score = _int_score(geo_scores.get("geo_score"))
    ai_citability = _int_score(scores.get("ai_citability"))
    brand_name = report_model.brand_name
    cluster_count = len(query_clusters)
    failure_count = len(citation_failures)
    llms_exists = bool(llms_validation.get("exists"))
    llms_valid = bool(llms_validation.get("format_valid")) and not llms_validation.get("issues")
    h1_count = len(_sequence(page_data.get("h1_tags")))

    overview_parts = [
        f"{brand_name} has a GEO score of {geo_score}/100.",
        f"AI citability is {ai_citability}/100, which is the main signal for answer-engine visibility.",
    ]
    if not llms_exists:
        overview_parts.append("The site is missing llms.txt guidance.")
    elif not llms_valid:
        overview_parts.append("The llms.txt guidance layer exists but is not yet valid.")
    if h1_count != 1:
        overview_parts.append(f"The homepage heading structure still needs attention because it exposes {h1_count} H1 tags.")
    if failure_count:
        overview_parts.append(f"Citation diagnosis surfaced {failure_count} failure item(s).")
    if rescience_pass.get("summary"):
        overview_parts.append(_string(rescience_pass.get("summary")))

    overview = " ".join(part for part in overview_parts if part)

    competitor_count = len(report_model.competitor_profiles)
    top_cluster = report_model.query_clusters[0].label if report_model.query_clusters else "priority topics"

    return {
        "overview": overview,
        "by_audience": {
            "cto": (
                f"Treat the site as technically healthy but strategically under-structured: GEO score {geo_score}/100, "
                f"AI citability {ai_citability}/100, {competitor_count} competitor profile(s), and {cluster_count} opportunity cluster(s). "
                f"Prioritize crawler access, schema, and heading consistency before scaling content."
            ),
            "marketing_manager": (
                f"Focus the next content sprint on {top_cluster} and the clusters with the highest opportunity scores. "
                f"Citation diagnosis shows {failure_count} issue(s), so the current content set needs stronger proof points, "
                "shorter answer blocks, and clearer audience alignment."
            ),
            "developers": (
                f"Stabilize the rendering and machine-readable layer first: fix any llms.txt issues, keep a single H1, preserve SSR content, "
                "and support the entity graph with schema and sameAs references."
            ),
        },
        "key_takeaways": [
            f"GEO score: {geo_score}/100",
            f"AI citability: {ai_citability}/100",
            f"Opportunity clusters: {cluster_count}",
            f"Citation failures: {failure_count}",
        ],
    }


def _build_readiness_scorecard(audit_data: Mapping[str, Any]) -> dict[str, Any]:
    geo_scores = _mapping(audit_data.get("geo_scores"))
    scores = _mapping(geo_scores.get("scores"))
    platforms = _mapping(audit_data.get("platforms"))
    page_data = _mapping(audit_data.get("page_data"))

    component_labels = {
        "ai_citability": "AI Citability",
        "brand_authority": "Brand Authority",
        "content_eeat": "Content E-E-A-T",
        "technical": "Technical Foundation",
        "schema": "Schema & Structured Data",
        "platform_optimization": "Platform Optimization",
    }
    weights = {
        "ai_citability": 25,
        "brand_authority": 20,
        "content_eeat": 20,
        "technical": 15,
        "schema": 10,
        "platform_optimization": 10,
    }

    components = []
    for key, label in component_labels.items():
        score = _int_score(scores.get(key))
        components.append(
            {
                "key": key,
                "label": label,
                "score": score,
                "weight": weights[key],
                "status": _score_label(score),
            }
        )

    risks = []
    if not _mapping(audit_data.get("llms_validation")).get("exists"):
        risks.append(
            {
                "issue": "Missing llms.txt guidance layer",
                "severity": "high",
                "why_it_matters": "AI systems lack a machine-readable crawl map.",
            }
        )
    if len(_sequence(page_data.get("h1_tags"))) != 1:
        risks.append(
            {
                "issue": "Heading hierarchy is diluted",
                "severity": "high",
                "why_it_matters": "The homepage thesis is harder for humans and models to parse.",
            }
        )
    if _int_score(scores.get("ai_citability")) < 50:
        risks.append(
            {
                "issue": "Low AI citability",
                "severity": "critical",
                "why_it_matters": "Answer engines will struggle to quote the site consistently.",
            }
        )

    return {
        "geo_score": _int_score(geo_scores.get("geo_score")),
        "components": components,
        "platforms": [
            {
                "platform": name,
                "score": _int_score(score),
                "status": _score_label(score),
            }
            for name, score in platforms.items()
        ],
        "priority_risks": risks,
    }


def _build_opportunity_map(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    opportunities = _mapping(report_model.plugin_results.get("opportunity")).get("opportunities") or []
    opportunities = [dict(item) for item in opportunities if isinstance(item, Mapping)]
    opportunity_index = {
        _string(item.get("query")).lower(): item
        for item in opportunities
        if _string(item.get("query"))
    }

    clusters = []
    for cluster in report_model.query_clusters:
        seed_topic = _string(cluster.metadata.get("seed_topic") or cluster.label).lower()
        match = opportunity_index.get(seed_topic)
        cluster_data = cluster.to_dict()
        cluster_data["opportunity_score"] = _int_score((match or {}).get("opportunity_score"))
        cluster_data["site_visible"] = bool((match or {}).get("site_visible"))
        cluster_data["keyword_suggestions"] = _dedupe_text((match or {}).get("keyword_suggestions"))
        clusters.append(cluster_data)

    return {
        "clusters": clusters,
        "opportunities": [
            {
                "query": _string(item.get("query")),
                "search_intent": _string(item.get("search_intent")),
                "label": _string(item.get("label")),
                "site_visible": bool(item.get("site_visible")),
                "opportunity_score": _int_score(item.get("opportunity_score")),
                "keyword_suggestions": _dedupe_text(item.get("keyword_suggestions")),
                "competitor_hits": _int_score(item.get("competitor_hits")),
            }
            for item in opportunities
        ],
    }


def _build_competitor_gap_analysis(
    report_model: ReportModel,
    audit_data: Mapping[str, Any],
) -> dict[str, Any]:
    plugin_results = _mapping(audit_data.get("plugin_results"))
    competitor_plugin = _mapping(plugin_results.get("competitor_analysis"))
    profiles = [profile.to_dict() for profile in report_model.competitor_profiles]
    source_inventory = _mapping(competitor_plugin.get("source_inventory"))
    if not source_inventory:
        site_domain = _string(report_model.site_snapshot.canonical_url or report_model.site_snapshot.url)
        source_inventory = {
            "site_owned": [site_domain] if site_domain else [],
            "competitor_owned": [profile.domain for profile in report_model.competitor_profiles if profile.domain],
            "earned_media": [],
        }

    gaps = [dict(item) for item in _sequence(competitor_plugin.get("authority_gaps")) if isinstance(item, Mapping)]
    if not gaps:
        if not source_inventory.get("competitor_owned"):
            if source_inventory.get("earned_media"):
                gaps.append(
                    {
                        "gap_type": "discovery_gap",
                        "gap_theme": "No competitor-owned domains were confidently discovered.",
                        "why_it_matters": "The report should explain that the sample set is sparse or skewed toward earned media.",
                    }
                )
            else:
                gaps.append(
                    {
                        "gap_type": "discovery_gap",
                        "gap_theme": "No competitor-owned or earned-media sources were confidently discovered.",
                        "why_it_matters": "The sample set is sparse and the category map is still incomplete.",
                    }
                )
        if source_inventory.get("earned_media"):
            gaps.append(
                {
                    "gap_type": "earned_media_gap",
                    "gap_theme": "Third-party coverage is visible in the category.",
                    "why_it_matters": "Answer engines may cite publishers and explainers instead of the brand until authority signals improve.",
                }
            )
        for profile in report_model.competitor_profiles:
            if profile.strengths:
                gaps.append(
                    {
                        "competitor": profile.name,
                        "gap_type": "positioning_gap",
                        "gap_theme": profile.strengths[0],
                        "why_it_matters": "That competitor is already signaling a clearer market position.",
                    }
                )
            else:
                gaps.append(
                    {
                        "competitor": profile.name,
                        "gap_type": "positioning_gap",
                        "gap_theme": "Positioning clarity is not yet evident in the sample set.",
                        "why_it_matters": "The brand can differentiate with more explicit proof and content structure.",
                    }
                )

    summary = _mapping(competitor_plugin.get("summary"))
    if not summary:
        summary = {
            "competitor_count": len(profiles),
            "site_owned_count": len(_dedupe_text(source_inventory.get("site_owned"))),
            "earned_media_count": len(_dedupe_text(source_inventory.get("earned_media"))),
            "authority_gap_count": len(gaps),
        }
    if not _string(summary.get("discovery_note")):
        competitor_owned = _dedupe_text(source_inventory.get("competitor_owned"))
        earned_media = _dedupe_text(source_inventory.get("earned_media"))
        if not competitor_owned and earned_media:
            summary["discovery_note"] = (
                "No competitor-owned domains were confidently discovered; the sample set is dominated by third-party coverage."
            )
        elif not competitor_owned and not earned_media:
            summary["discovery_note"] = (
                "No competitor-owned or earned-media sources were confidently discovered; the sample set is sparse and the category map is still incomplete."
            )
        else:
            summary["discovery_note"] = "Competitor profiles were inferred from the live sample set."
    return {
        "competitors": profiles,
        "source_inventory": {
            "site_owned": _dedupe_text(source_inventory.get("site_owned")),
            "competitor_owned": _dedupe_text(source_inventory.get("competitor_owned")),
            "earned_media": _dedupe_text(source_inventory.get("earned_media")),
        },
        "gap_themes": gaps,
        "summary": summary,
        "authority_gaps": gaps,
    }


def _build_citation_diagnosis(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    failures = [failure.to_dict() for failure in report_model.citation_failures]
    failure_modes: list[str] = []
    for failure in report_model.citation_failures:
        if failure.failure_mode and failure.failure_mode not in failure_modes:
            failure_modes.append(failure.failure_mode)
    citation_strength = {
        "owned_sources": _owned_source_strength(report_model, audit_data),
        "earned_sources": _earned_source_strength(report_model, audit_data),
    }
    return {
        "failures": failures,
        "failure_modes": failure_modes,
        "citation_strength": citation_strength,
        "summary": {
            "failure_count": len(failures),
            "diagnosis": (
                "The site is missing citation-ready blocks and/or entity grounding."
                if failures
                else "No citation failures were captured in this audit run."
            ),
            "owned_source_strength": citation_strength["owned_sources"]["label"],
            "earned_source_strength": citation_strength["earned_sources"]["label"],
        },
    }


def _build_entity_authority_analysis(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    entity_graph = report_model.entity_graph.to_dict() if report_model.entity_graph is not None else None
    page_data = _mapping(audit_data.get("page_data"))
    external_links = []
    for link in _sequence(page_data.get("external_links")):
        if isinstance(link, Mapping) and link.get("url"):
            external_links.append(_string(link.get("url")))
        elif link:
            external_links.append(_string(link))
    same_as = []
    if isinstance(entity_graph, Mapping):
        same_as = _dedupe_text(entity_graph.get("same_as"))
    earned_media_signals = _dedupe_text([*same_as, *external_links])
    return {
        "entity_graph": entity_graph,
        "earned_media_signals": earned_media_signals,
        "analysis": {
            "confidence": entity_graph.get("confidence") if isinstance(entity_graph, Mapping) else None,
            "signals": entity_graph.get("attributes", {}).get("signals", []) if isinstance(entity_graph, Mapping) else [],
            "same_as_count": len(same_as),
        },
    }


def _build_roadmap(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    rescience_pass = _mapping(audit_data.get("rescience_pass"))
    quick_wins = _dedupe_text(audit_data.get("quick_wins"))
    medium_term = _dedupe_text(audit_data.get("medium_term"))
    strategic = _dedupe_text(audit_data.get("strategic"))
    priority_actions = _mapping(rescience_pass.get("priority_actions"))

    thirty_day_items = _dedupe_text([*priority_actions.get("P0", []), *priority_actions.get("P1", []), *quick_wins])
    sixty_day_items = _dedupe_text([*medium_term, *priority_actions.get("P2", [])])
    ninety_day_items = _dedupe_text([*strategic, *priority_actions.get("P2", [])])

    def build_items(actions: list[str], source: str) -> list[dict[str, Any]]:
        return [
            _normalize_action_item(
                action,
                owner=_owner_for_action(action),
                source=source,
            )
            for action in actions
        ]

    return {
        "thirty_day": build_items(thirty_day_items, "rescience_pass/quick_wins"),
        "sixty_day": build_items(sixty_day_items, "medium_term"),
        "ninety_day": build_items(ninety_day_items, "strategic"),
    }


def _build_developer_appendix(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    page_data = _mapping(audit_data.get("page_data"))
    llms_validation = _mapping(audit_data.get("llms_validation"))
    crawler_access = _mapping(audit_data.get("crawler_access"))
    findings = _sequence(audit_data.get("findings"))

    technical_actions = []
    for finding in findings:
        if isinstance(finding, Mapping) and finding.get("developer_action"):
            technical_actions.append(_string(finding.get("developer_action")))

    for item in _build_roadmap(report_model, audit_data)["thirty_day"]:
        if item.get("owner") == "developers":
            technical_actions.append(item["action"])

    if not llms_validation.get("exists"):
        technical_actions.append("Publish llms.txt and llms-full.txt at the site root.")
    if len(_sequence(page_data.get("h1_tags"))) != 1:
        technical_actions.append("Refactor the homepage to a single H1 and ordered H2/H3 hierarchy.")
    if page_data.get("has_ssr_content") is False:
        technical_actions.append("Restore server-rendered content so crawlers can see the primary answer blocks.")

    return {
        "technical_actions": _dedupe_text(technical_actions),
        "crawler_access": crawler_access,
        "implementation_notes": [
            "Keep report sections driven from the JSON payload so markdown and PDF stay in sync.",
            "Preserve SSR and schema support for every page template that should be cited by AI systems.",
        ],
    }


def _build_evidence_appendix(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    page_data = _mapping(audit_data.get("page_data"))
    findings = _sequence(audit_data.get("findings"))
    query_clusters = _sequence(audit_data.get("query_clusters"))
    citation_failures = _sequence(audit_data.get("citation_failures"))
    crawler_access = _mapping(audit_data.get("crawler_access"))
    plugin_results = _mapping(audit_data.get("plugin_results"))

    methodology = [
        "ReportModel-driven synthesis across readiness, opportunity, competitor, entity, and citation analyses.",
        "Live audit inputs from page fetch, llms.txt validation, robots/crawler checks, and citability scoring.",
        "Strategy-engine plugin outputs used as the canonical source for clusters, competitors, entity graph, and citation failures.",
    ]

    evidence_items: list[EvidenceEntry] = []

    for finding in findings:
        if not isinstance(finding, Mapping):
            continue
        evidence_items.append(
            _build_evidence_entry(
                _string(finding.get("title")),
                "heuristic",
                evidence=[
                    _string(finding.get("observed_evidence")),
                    _string(finding.get("severity")),
                ],
                metadata={"severity": _string(finding.get("severity"))},
            )
        )

    for cluster in query_clusters:
        if not isinstance(cluster, Mapping):
            continue
        evidence_items.append(
            _build_evidence_entry(
                _string(cluster.get("label")),
                "live_serp",
                evidence=_dedupe_text(cluster.get("queries")),
                metadata={
                    "search_intent": _string(cluster.get("search_intent")),
                    "priority": _string(cluster.get("priority")),
                },
            )
        )

    for failure in citation_failures:
        if not isinstance(failure, Mapping):
            continue
        evidence_items.append(
            _build_evidence_entry(
                _string(failure.get("query")),
                "live_site",
                evidence=_dedupe_text(failure.get("evidence")),
                url=_string(failure.get("target_url")) or None,
                metadata={
                    "failure_mode": _string(failure.get("failure_mode")),
                    "recommended_fix": _string(failure.get("recommended_fix")),
                },
            )
        )

    for crawler, info in crawler_access.items():
        if isinstance(info, Mapping):
            evidence_items.append(
                _build_evidence_entry(
                    crawler,
                    "official",
                    evidence=[
                        _string(info.get("status")),
                        _string(info.get("platform")),
                    ],
                    metadata={
                        "recommendation": _string(info.get("recommendation")),
                    },
                )
            )

    readiness = _mapping(plugin_results.get("readiness"))
    geo_scores = _mapping(readiness.get("geo_scores"))
    scores = _mapping(geo_scores.get("scores"))
    evidence_items.append(
        _build_evidence_entry(
            "GEO score",
            "heuristic",
            evidence=[
                f"{_int_score(geo_scores.get('geo_score'))}/100",
                f"AI citability {_int_score(scores.get('ai_citability'))}/100",
            ],
        )
    )

    if page_data.get("url"):
        evidence_items.append(
            _build_evidence_entry(
                "Primary URL",
                "live_site",
                evidence=[_string(page_data.get("url"))],
                url=_string(page_data.get("url")) or None,
            )
        )

    return {
        "methodology": methodology,
        "evidence_items": evidence_items,
    }


def _build_decision_summary(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    executive_summary = _build_executive_summary(report_model, audit_data)
    readiness = _build_readiness_scorecard(audit_data)
    roadmap = _build_roadmap(report_model, audit_data)
    competitor_visibility = _build_competitor_gap_analysis(report_model, audit_data)
    opportunity_map = _build_opportunity_map(report_model, audit_data)
    service_line_rows = _service_line_rows(report_model, audit_data)

    blockers = _sequence(readiness.get("priority_risks"))[:3]
    discovery_note = _string(_mapping(competitor_visibility.get("summary")).get("discovery_note"))
    if discovery_note:
        blockers.append(
            {
                "issue": "Competitive landscape is still partial",
                "severity": "medium",
                "why_it_matters": discovery_note,
            }
        )

    opportunities = []
    for item in _sequence(opportunity_map.get("opportunities")):
        if not isinstance(item, Mapping):
            continue
        if _string(item.get("label")).lower() != "high":
            continue
        opportunities.append(
            {
                "query": _string(item.get("query")),
                "impact": f"Opportunity score {_int_score(item.get('opportunity_score'))}/100",
                "why_it_matters": "This topic is strategically open in the current sample.",
            }
        )

    return {
        "overview": executive_summary.get("overview"),
        "by_audience": executive_summary.get("by_audience"),
        "blockers": blockers[:4],
        "opportunities": opportunities[:4],
        "service_lines": [row.get("service_line") for row in service_line_rows[:5]],
        "next_actions": _sequence(roadmap.get("thirty_day"))[:5],
    }


def _build_service_line_scorecard(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    rows = _service_line_rows(report_model, audit_data)
    return {
        "rows": rows,
        "summary": {
            "line_count": len(rows),
        },
    }


def _build_query_universe(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    opportunity_map = _build_opportunity_map(report_model, audit_data)
    service_lines = _build_service_line_scorecard(report_model, audit_data)
    return {
        "service_lines": [
            {
                "service_line": item.get("service_line"),
                "queries": item.get("observed_queries"),
                "priority": item.get("priority"),
                "opportunity_score": item.get("opportunity_score"),
            }
            for item in _sequence(service_lines.get("rows"))
        ],
        "clusters": opportunity_map.get("clusters"),
        "opportunities": opportunity_map.get("opportunities"),
    }


def _build_competitor_visibility(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    competitor_gap = _build_competitor_gap_analysis(report_model, audit_data)
    return {
        "competitors": competitor_gap.get("competitors"),
        "source_inventory": competitor_gap.get("source_inventory"),
        "summary": competitor_gap.get("summary"),
        "authority_gaps": competitor_gap.get("authority_gaps"),
    }


def _build_earned_media_gap(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    competitor_gap = _build_competitor_gap_analysis(report_model, audit_data)
    source_inventory = _mapping(competitor_gap.get("source_inventory"))
    earned_media = _dedupe_text(source_inventory.get("earned_media"))
    gap_priorities = [
        item
        for item in _sequence(competitor_gap.get("authority_gaps"))
        if isinstance(item, Mapping)
        and _string(item.get("gap_type")) in {"earned_media_gap", "discovery_gap"}
    ]
    if earned_media:
        gap_priorities = [
            item for item in gap_priorities if _string(item.get("gap_type")) != "earned_media_gap"
        ]
    else:
        gap_priorities = [
            item for item in gap_priorities if _string(item.get("gap_type")) != "discovery_gap"
        ]
    return {
        "sources": earned_media,
        "summary_note": (
            "Third-party coverage is visible in the sampled category, so earned-media authority is part of the citation picture."
            if earned_media
            else "No earned-media coverage was confidently discovered in this run; the category map is still incomplete."
        ),
        "gap_priorities": gap_priorities,
    }


def _build_entity_trust_graph(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    entity = _build_entity_authority_analysis(report_model, audit_data)
    entity_graph = _mapping(entity.get("entity_graph"))
    return {
        "entity_graph": entity.get("entity_graph"),
        "profile_links": _dedupe_text(entity_graph.get("same_as")),
        "analysis": entity.get("analysis"),
        "trust_signals": _dedupe_text(_mapping(entity_graph.get("attributes")).get("signals")),
    }


def _build_technical_geo_gates(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    readiness = _build_readiness_scorecard(audit_data)
    llms_validation = _mapping(audit_data.get("llms_validation"))
    page_data = _mapping(audit_data.get("page_data"))
    crawler_access = _mapping(audit_data.get("crawler_access"))
    scores = _mapping(_mapping(audit_data.get("geo_scores")).get("scores"))

    gates = [
        {
            "issue": "llms.txt guidance layer",
            "severity": "steady" if llms_validation.get("exists") else "high",
            "why_it_matters": (
                "llms.txt is present and can help guide AI retrieval."
                if llms_validation.get("exists")
                else "The site is missing llms.txt guidance at the root."
            ),
        },
        {
            "issue": "Heading hierarchy",
            "severity": "steady" if len(_sequence(page_data.get("h1_tags"))) == 1 else "high",
            "why_it_matters": f"Observed H1 count: {len(_sequence(page_data.get('h1_tags')))}.",
        },
        {
            "issue": "Schema support",
            "severity": _score_label(scores.get("schema")),
            "why_it_matters": f"Schema score is {_int_score(scores.get('schema'))}/100.",
        },
        {
            "issue": "Technical foundation",
            "severity": _score_label(scores.get("technical")),
            "why_it_matters": f"Technical score is {_int_score(scores.get('technical'))}/100.",
        },
    ]

    return {
        "summary": {
            "geo_score": readiness.get("geo_score"),
            "platforms": readiness.get("platforms"),
        },
        "priority_gates": gates,
        "crawler_access": crawler_access,
    }


def _build_execution_ledger(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    roadmap = _build_roadmap(report_model, audit_data)
    return {
        "thirty_day": roadmap.get("thirty_day"),
        "sixty_day": roadmap.get("sixty_day"),
        "ninety_day": roadmap.get("ninety_day"),
    }


def build_report_sections(
    report_model: ReportModel,
    audit_data: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = _get_report_context(report_model, audit_data or {})

    sections = {
        "decision_summary": _build_decision_summary(report_model, context),
        "service_line_scorecard": _build_service_line_scorecard(report_model, context),
        "query_universe": _build_query_universe(report_model, context),
        "competitor_visibility": _build_competitor_visibility(report_model, context),
        "earned_media_gap": _build_earned_media_gap(report_model, context),
        "citation_diagnosis": _build_citation_diagnosis(report_model, context),
        "entity_trust_graph": _build_entity_trust_graph(report_model, context),
        "technical_geo_gates": _build_technical_geo_gates(report_model, context),
        "execution_ledger": _build_execution_ledger(report_model, context),
        "developer_appendix": _build_developer_appendix(report_model, context),
        "evidence_appendix": _build_evidence_appendix(report_model, context),
    }
    return serialize_model({key: sections[key] for key in REPORT_SECTION_ORDER})


def _legacy_sections_to_workbook(report_sections: Mapping[str, Any]) -> dict[str, Any]:
    legacy_sections = _mapping(report_sections)
    normalized: dict[str, Any] = {}

    executive = _mapping(legacy_sections.get("executive_summary"))
    if executive:
        overview = _string(executive.get("overview") or executive.get("summary"))
        by_audience = _mapping(executive.get("by_audience"))
        next_actions = []
        for audience, summary in by_audience.items():
            text = _string(summary)
            if text:
                next_actions.append({"action": f"{_gap_label(audience)}: {text}"})
        normalized["decision_summary"] = {
            "overview": overview,
            "by_audience": by_audience,
            "next_actions": next_actions,
        }

    readiness = _mapping(legacy_sections.get("readiness_scorecard"))
    if readiness:
        normalized["technical_geo_gates"] = {
            "summary": {
                "geo_score": readiness.get("geo_score"),
                "platforms": readiness.get("platforms"),
            },
            "priority_gates": readiness.get("priority_risks"),
            "components": readiness.get("components"),
        }

    opportunity_map = _mapping(legacy_sections.get("opportunity_map"))
    if opportunity_map:
        normalized["query_universe"] = {
            "service_lines": [],
            "clusters": opportunity_map.get("clusters"),
            "opportunities": opportunity_map.get("opportunities"),
        }

    competitor_gap = _mapping(legacy_sections.get("competitor_gap_analysis"))
    if competitor_gap:
        source_inventory = _mapping(competitor_gap.get("source_inventory"))
        earned_media = _dedupe_text(source_inventory.get("earned_media"))
        normalized["competitor_visibility"] = {
            "competitors": competitor_gap.get("competitors"),
            "source_inventory": source_inventory,
            "summary": competitor_gap.get("summary"),
            "authority_gaps": competitor_gap.get("authority_gaps"),
        }
        normalized["earned_media_gap"] = {
            "sources": earned_media,
            "summary_note": (
                "Third-party coverage is visible in the sampled category, so earned-media authority is part of the citation picture."
                if earned_media
                else "No earned-media coverage was confidently discovered in this run; the category map is still incomplete."
            ),
            "gap_priorities": [],
        }

    citation = _mapping(legacy_sections.get("citation_diagnosis"))
    if citation:
        normalized["citation_diagnosis"] = citation

    entity = _mapping(legacy_sections.get("entity_authority_analysis"))
    if entity:
        analysis = _mapping(entity.get("analysis"))
        normalized["entity_trust_graph"] = {
            "entity_graph": entity.get("entity_graph")
            or {
                "entity_name": entity.get("entity_name"),
                "confidence": analysis.get("confidence"),
            },
            "profile_links": entity.get("earned_media_signals"),
            "analysis": analysis,
            "trust_signals": analysis.get("signals"),
        }

    roadmap = _mapping(legacy_sections.get("roadmap"))
    if roadmap:
        normalized["execution_ledger"] = {
            "thirty_day": roadmap.get("thirty_day"),
            "sixty_day": roadmap.get("sixty_day"),
            "ninety_day": roadmap.get("ninety_day"),
        }

    developer_appendix = _mapping(legacy_sections.get("developer_appendix"))
    if developer_appendix:
        normalized["developer_appendix"] = {
            "technical_actions": developer_appendix.get("technical_actions"),
            "implementation_notes": developer_appendix.get("implementation_notes")
            or developer_appendix.get("notes"),
        }

    evidence_appendix = _mapping(legacy_sections.get("evidence_appendix"))
    if evidence_appendix:
        normalized["evidence_appendix"] = evidence_appendix

    return normalized


def normalize_report_sections(report_sections: Mapping[str, Any] | None) -> dict[str, Any]:
    sections = _mapping(report_sections)
    if not sections:
        return {}

    normalized: dict[str, Any] = {}
    for key in REPORT_SECTION_ORDER:
        section = _mapping(sections.get(key))
        if section:
            normalized[key] = section

    legacy_sections = _legacy_sections_to_workbook(sections)
    for key, section in legacy_sections.items():
        if key not in normalized and section:
            normalized[key] = section

    return serialize_model(
        {key: normalized[key] for key in REPORT_SECTION_ORDER if key in normalized}
    )


def report_sections_to_markdown(report_sections: Mapping[str, Any]) -> str:
    report_sections = normalize_report_sections(report_sections)
    if not report_sections:
        return ""

    def render_list(items: Any, indent: int = 0) -> list[str]:
        lines: list[str] = []
        prefix = "  " * indent
        for item in _sequence(items):
            if isinstance(item, Mapping):
                if _is_evidence_item(item):
                    text = format_evidence_item_text(item)
                    if text:
                        lines.append(f"{prefix}- {text}")
                    continue
                action = _string(
                    item.get("name")
                    or item.get("action")
                    or item.get("label")
                    or item.get("query")
                    or item.get("competitor")
                    or item.get("issue")
                    or item.get("title")
                    or item.get("service_line")
                    or item.get("gap_theme")
                    or _gap_label(item.get("gap_type"))
                )
                source_tag = _source_tag(item.get("source_tag"))
                tag_suffix = f" [{source_tag}]" if source_tag else ""
                detail_parts = []
                for key in (
                    "owner",
                    "impact",
                    "severity",
                    "failure_mode",
                    "gap_type",
                    "why_it_matters",
                    "priority",
                    "opportunity_score",
                    "visibility",
                    "citation_readiness",
                    "citation_strength",
                    "earned_media_strength",
                    "technical_readiness",
                    "source_type",
                    "url",
                    "evidence",
                ):
                    value = item.get(key)
                    if value:
                        if isinstance(value, list):
                            value = ", ".join(_dedupe_text(value))
                        detail_parts.append(f"{key.replace('_', ' ').title()}: {value}")
                if action:
                    if detail_parts:
                        lines.append(f"{prefix}- **{action}**{tag_suffix} ({'; '.join(detail_parts)})")
                    else:
                        lines.append(f"{prefix}- **{action}**{tag_suffix}")
                else:
                    lines.append(f"{prefix}- {serialize_model(item)}")
            else:
                text = _string(item)
                if text:
                    lines.append(f"{prefix}- {text}")
        return lines

    title_map = {
        "decision_summary": "Decision Summary",
        "service_line_scorecard": "Service-Line Scorecard",
        "query_universe": "Query Universe",
        "competitor_visibility": "Competitor Visibility",
        "earned_media_gap": "Earned-Media Gap",
        "citation_diagnosis": "Citation Diagnosis",
        "entity_trust_graph": "Entity and Trust Graph",
        "technical_geo_gates": "Technical GEO Gates",
        "execution_ledger": "30/60/90 Execution Ledger",
        "developer_appendix": "Developer Appendix",
        "evidence_appendix": EVIDENCE_APPENDIX_TITLE,
    }

    lines: list[str] = []
    for key in REPORT_SECTION_ORDER:
        section = _mapping(report_sections.get(key))
        if not section:
            continue
        lines.extend([f"## {title_map.get(key, key.replace('_', ' ').title())}", ""])

        if key == "decision_summary":
            overview = _string(section.get("overview"))
            if overview:
                lines.extend([overview, ""])
            for subheading, items in (
                ("Top Blockers", section.get("blockers")),
                ("Top Opportunities", section.get("opportunities")),
                ("Service Lines In Scope", section.get("service_lines")),
                ("Next 30 Days", section.get("next_actions")),
            ):
                if _sequence(items):
                    lines.extend([f"### {subheading}", ""])
                    lines.extend(render_list(items))
                    lines.append("")
        elif key == "service_line_scorecard":
            for row in _sequence(section.get("rows")):
                if not isinstance(row, Mapping):
                    continue
                lines.append(
                    f"- **{_string(row.get('service_line'))}** "
                    f"(Visibility: {_string(row.get('visibility'))}; "
                    f"Citation Readiness: {_string(row.get('citation_readiness'))}; "
                    f"Citation Strength: {_string(row.get('citation_strength'))}; "
                    f"Earned-Media Strength: {_string(row.get('earned_media_strength'))}; "
                    f"Technical Readiness: {_string(row.get('technical_readiness'))}; "
                    f"Priority: {_string(row.get('priority'))})"
                )
                observed_queries = _dedupe_text(row.get("observed_queries"))
                if observed_queries:
                    lines.append(f"  Queries: {', '.join(observed_queries)}")
            lines.append("")
        elif key == "query_universe":
            service_lines = _sequence(section.get("service_lines"))
            if service_lines:
                lines.extend(["### Service-Line Query Themes", ""])
                lines.extend(render_list(service_lines))
                lines.append("")
            clusters = _sequence(section.get("clusters"))
            if clusters:
                lines.extend(["### Cluster Inventory", ""])
                lines.extend(render_list(clusters))
                lines.append("")
        elif key == "competitor_visibility":
            summary = _mapping(section.get("summary"))
            discovery_note = _string(summary.get("discovery_note"))
            if discovery_note:
                lines.extend([discovery_note, ""])
            lines.extend(render_list(section.get("competitors")))
            lines.append("")
            source_inventory = _mapping(section.get("source_inventory"))
            if source_inventory:
                lines.append("### Source Inventory")
                lines.append("")
                lines.append(f"- Site-owned domains: {', '.join(_dedupe_text(source_inventory.get('site_owned'))) or 'none discovered'}")
                lines.append(f"- Competitor-owned domains: {', '.join(_dedupe_text(source_inventory.get('competitor_owned'))) or 'none discovered'}")
                lines.append(f"- Earned-media sources: {', '.join(_dedupe_text(source_inventory.get('earned_media'))) or 'none discovered'}")
                lines.append("")
            gap_items = _merge_gap_items(section.get("authority_gaps"))
            if gap_items:
                lines.extend(["### Visibility Gaps", ""])
                lines.extend(render_list(gap_items))
                lines.append("")
        elif key == "earned_media_gap":
            summary_note = _string(section.get("summary_note"))
            if summary_note:
                lines.extend([summary_note, ""])
            sources = _sequence(section.get("sources"))
            if sources:
                lines.extend(["### Observed Sources", ""])
                lines.extend(render_list(sources))
                lines.append("")
            gap_priorities = _sequence(section.get("gap_priorities"))
            if gap_priorities:
                lines.extend(["### Gap Priorities", ""])
                lines.extend(render_list(gap_priorities))
                lines.append("")
        elif key == "citation_diagnosis":
            lines.extend(["### Failure Items", ""])
            lines.extend(render_list(section.get("failures")))
            lines.append("")
            failure_modes = _sequence(section.get("failure_modes"))
            if failure_modes:
                lines.extend(["### Failure Modes", ""])
                lines.extend(f"- {_gap_label(item)}" for item in failure_modes)
                lines.append("")
            citation_strength = _mapping(section.get("citation_strength"))
            if citation_strength:
                lines.extend(["### Citation Strength", ""])
                for bucket_key, bucket_label in (("owned_sources", "Owned Sources"), ("earned_sources", "Earned Sources")):
                    bucket = _mapping(citation_strength.get(bucket_key))
                    if not bucket:
                        continue
                    lines.extend([f"#### {bucket_label}", ""])
                    lines.append(f"- Score: {_int_score(bucket.get('score'))}/100")
                    lines.append(f"- Label: {_string(bucket.get('label'))}")
                    dimensions = _mapping(bucket.get("dimensions"))
                    if dimensions:
                        lines.extend(["", "##### Dimensions", ""])
                        for dimension_key, dimension_value in dimensions.items():
                            if not isinstance(dimension_value, Mapping):
                                continue
                            detail = (
                                f"- {_gap_label(dimension_key)}: "
                                f"{_string(dimension_value.get('label'))} "
                                f"({_int_score(dimension_value.get('score'))}/100)"
                            )
                            note = _string(dimension_value.get("note"))
                            if note:
                                detail = f"{detail} - {note}"
                            lines.append(detail)
                    notes = _sequence(bucket.get("notes"))
                    if notes:
                        lines.append("")
                        lines.extend(render_list(notes))
                    lines.append("")
        elif key == "entity_trust_graph":
            entity_graph = _mapping(section.get("entity_graph"))
            if entity_graph:
                lines.append(f"- Entity: {_string(entity_graph.get('entity_name'))}")
                lines.append(f"- Confidence: {_string(entity_graph.get('confidence'))}")
                lines.append("")
            trust_signals = _sequence(section.get("trust_signals"))
            if trust_signals:
                lines.extend(["### Trust Signals", ""])
                lines.extend(render_list(trust_signals))
                lines.append("")
            profile_links = _sequence(section.get("profile_links"))
            if profile_links:
                lines.extend(["### Profile Links", ""])
                lines.extend(render_list(profile_links))
                lines.append("")
        elif key == "technical_geo_gates":
            summary = _mapping(section.get("summary"))
            if summary:
                lines.append(f"- GEO Score: {_int_score(summary.get('geo_score'))}/100")
                lines.append("")
            lines.extend(["### Priority Gates", ""])
            lines.extend(render_list(section.get("priority_gates")))
            lines.append("")
            crawler_access = _mapping(section.get("crawler_access"))
            if crawler_access:
                lines.extend(["### Crawler Access", ""])
                for crawler_name, info in crawler_access.items():
                    if isinstance(info, Mapping):
                        lines.append(
                            f"- **{crawler_name}** (Platform: {_string(info.get('platform'))}; "
                            f"Status: {_string(info.get('status'))}; "
                            f"Recommendation: {_string(info.get('recommendation'))})"
                        )
                    else:
                        lines.append(f"- {crawler_name}: {_string(info)}")
                lines.append("")
        elif key == "execution_ledger":
            for label, bucket in (("30 Days", section.get("thirty_day")), ("60 Days", section.get("sixty_day")), ("90 Days", section.get("ninety_day"))):
                lines.extend([f"### {label}", ""])
                lines.extend(render_list(bucket))
                lines.append("")
        elif key == "developer_appendix":
            lines.extend(["### Technical Actions", ""])
            lines.extend(render_list(section.get("technical_actions")))
            lines.append("")
            lines.extend(["### Implementation Notes", ""])
            lines.extend(render_list(section.get("implementation_notes")))
            lines.append("")
        elif key == "evidence_appendix":
            methodology = _sequence(section.get("methodology"))
            if methodology:
                lines.extend(["### Methodology", ""])
                lines.extend(render_list(methodology))
                lines.append("")
            evidence_items = _sequence(section.get("evidence_items"))
            if evidence_items:
                lines.extend(["### Evidence Items", ""])
                lines.extend(render_list(evidence_items))
                lines.append("")

    return "\n".join(line for line in lines if line is not None).strip() + "\n"
