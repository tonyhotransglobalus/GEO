from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import urlparse

from . import analysis
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

CLIENT_REPORT_SECTION_ORDER = (
    "cover_verdict",
    "decision_summary",
    "score_definitions",
    "priority_findings",
    "competitive_benchmark",
    "platform_breakdown",
    "prompt_query_proof",
    "page_source_evidence",
    "action_plan_30_60_90",
    "technical_proof_appendix",
)

PLAYBOOK_REPORT_SECTION_ORDER = (
    "page1_executive_summary",
    "page2_geo_paradigm",
    "page3_strategic_implementation",
    "page4_content_citability",
    "page5_brand_entity_verification",
    "page6_technical_implementation",
    "page7_audit_process",
    "page8_diagnosis_troubleshooting",
    "page9_faq_by_role",
    "page10_roadmap_future",
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

_SCORE_WEIGHTING_COMPONENTS = (
    (
        "ai_citability",
        "AI Citability",
        25,
        "This carries the most weight because AI systems need quote-ready, proof-rich passages before they can cite a page confidently.",
    ),
    (
        "brand_authority",
        "Brand Authority",
        20,
        "Authority matters because brands with clearer reputation signals are easier for models to trust and reference.",
    ),
    (
        "content_eeat",
        "Content E-E-A-T",
        20,
        "Content quality stays heavily weighted because firsthand detail, specificity, and clarity improve answer reuse.",
    ),
    (
        "technical",
        "Technical Foundation",
        15,
        "Technical access matters because blocked, unstable, or poorly rendered pages cannot be retrieved reliably.",
    ),
    (
        "schema",
        "Schema & Structured Data",
        10,
        "Schema has supporting weight because structured markup helps machines interpret entities, pages, and relationships faster.",
    ),
    (
        "platform_optimization",
        "Platform Optimization",
        10,
        "Platform readiness is weighted last because it matters, but only after content, trust, and access are already strong.",
    ),
)

_TERM_GUIDE_ENTRIES = (
    (
        "Confidence",
        "How much to trust the current readout.",
    ),
    (
        "Directional",
        "An early signal that points to a likely pattern, but not final proof from exact prompt captures or a full benchmark.",
    ),
    (
        "Sample completeness",
        "How much evidence this run captured before drawing conclusions.",
    ),
    (
        "Evidence class",
        "The source type behind a claim, such as live site checks, official documentation, or an internal scoring model.",
    ),
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


def _score_weighting_components() -> list[dict[str, Any]]:
    return [
        {
            "metric_key": metric_key,
            "metric_name": metric_name,
            "weight": weight,
            "why_this_weight_exists": why_this_weight_exists,
        }
        for metric_key, metric_name, weight, why_this_weight_exists in _SCORE_WEIGHTING_COMPONENTS
    ]


def _score_weighting_summary() -> str:
    parts = [
        f"{metric_name} {weight}%"
        for _, metric_name, weight, _ in _SCORE_WEIGHTING_COMPONENTS
    ]
    return (
        "The GEO Score is a weighted blend of "
        + ", ".join(parts[:-1])
        + f", and {parts[-1]}."
    )


def _term_guide_entries() -> list[dict[str, str]]:
    return [
        {"term": term, "plain_english": plain_english}
        for term, plain_english in _TERM_GUIDE_ENTRIES
    ]


def _clean_legacy_rescience_language(text: str) -> str:
    cleaned = _string(text)
    if not cleaned:
        return ""
    replacements = {
        "ReScience optimization pass": "Optimization pass",
        "rescience optimization pass": "optimization pass",
        "Powered by ReScience AI": "",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    return " ".join(cleaned.split()).strip()


def _is_legacy_rescience_finding(finding: Mapping[str, Any]) -> bool:
    haystack = " ".join(
        _string(
            finding.get(key)
        )
        for key in ("title", "summary", "description", "observed_evidence")
    ).lower()
    return "rescience" in haystack


def _default_marketing_action(title: str) -> str:
    normalized = _normalized_text(title)
    if "citation" in normalized or "citability" in normalized:
        return "Marketing should rewrite the affected page into answer-first sections with concrete facts, examples, and source-ready proof."
    if "heading" in normalized:
        return "Marketing should tighten the page thesis so one primary topic leads the page and supporting sections do not compete with it."
    if "llms" in normalized:
        return "Marketing should treat llms.txt as a secondary hint and keep the main focus on stronger page copy, proof points, and FAQs."
    if "entity" in normalized or "trust" in normalized:
        return "Marketing should strengthen trust signals with clearer company proof, authoritative references, and consistent profile language."
    return "Marketing should turn this finding into a page-level update, FAQ, comparison asset, or proof section on the affected topic."


def _default_engineering_action(title: str) -> str:
    normalized = _normalized_text(title)
    if "citation" in normalized or "citability" in normalized:
        return "Engineering should support the rewrite with clean headings, stable rendering, and structured data on the priority page."
    if "heading" in normalized:
        return "Engineering should enforce one clear H1 on the page and keep supporting sections nested under the right heading levels."
    if "llms" in normalized:
        return "Engineering should only publish llms.txt after confirming robots.txt, crawl access, and page structure are already stable."
    if "entity" in normalized or "trust" in normalized:
        return "Engineering should reinforce machine-readable brand signals through structured data, canonical links, and consistent profile references."
    return "Engineering should remove structural blockers that make this page harder for crawlers and answer engines to interpret."


def _is_branded_noise_opportunity(report_model: ReportModel, audit_data: Mapping[str, Any], query: str) -> bool:
    normalized_query = _normalized_text(query)
    if not normalized_query:
        return True
    page_data = _mapping(audit_data.get("page_data"))
    candidates = {
        _normalized_text(report_model.brand_name),
        _normalized_text(report_model.site_snapshot.title),
        _normalized_text(page_data.get("title")),
        _normalized_text(page_data.get("description")),
        _normalized_text(report_model.site_snapshot.url),
        _normalized_text(report_model.site_snapshot.canonical_url),
        _normalized_text(_primary_domain(report_model)),
    }
    if normalized_query in candidates:
        return True
    if normalized_query.startswith("home ") and _normalized_text(report_model.brand_name) in normalized_query:
        return True
    brand_tokens = set(_normalized_text(report_model.brand_name).split())
    query_tokens = set(normalized_query.split())
    return bool(brand_tokens) and query_tokens.issubset(brand_tokens)


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
        58 if llms_exists and llms_valid else 50,
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


def _display_label(value: Any, *, fallback: str = "") -> str:
    text = " ".join(_string(value).split())
    fallback_text = " ".join(_string(fallback).split())
    if not text:
        return fallback_text

    if text.startswith("http://") or text.startswith("https://"):
        return text

    if len(text) > 96:
        if fallback_text:
            return fallback_text
        text = text[:93].rstrip(" -_,.;:") + "..."

    if "-" in text and " " not in text and text.count("-") >= 2:
        humanized = text.replace("-", " ").strip().title()
        return humanized or fallback_text

    return text


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
        label = _display_label(
            cluster.get("label"),
            fallback=_string(_mapping(cluster.get("metadata")).get("seed_topic")) or "Priority Topic",
        )
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
        overview_parts.append("An optional llms.txt discoverability hint is not published.")
    elif not llms_valid:
        overview_parts.append("An optional llms.txt discoverability hint exists but is not yet valid.")
    if h1_count != 1:
        overview_parts.append(f"The homepage heading structure still needs attention because it exposes {h1_count} H1 tags.")
    if failure_count:
        overview_parts.append(f"Citation diagnosis surfaced {failure_count} failure item(s).")
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
                "Stabilize the rendering and machine-readable layer first: keep a single H1, preserve SSR content, "
                "support the entity graph with schema and sameAs references, and maintain optional llms.txt guidance only if you choose to publish it."
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
        metric_key: metric_name
        for metric_key, metric_name, _, _ in _SCORE_WEIGHTING_COMPONENTS
    }
    weights = {
        metric_key: weight
        for metric_key, _, weight, _ in _SCORE_WEIGHTING_COMPONENTS
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
                "issue": "Optional AI guidance file (llms.txt) is not published",
                "severity": "medium",
                "why_it_matters": "Some platforms may consult it, but it is less important than crawlability, content clarity, and evidence-rich pages.",
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
                "issue": "Key pages are still hard for AI systems to quote (low citability)",
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
    sixty_day_seen = {_normalized_text(item) for item in sixty_day_items}
    thirty_day_seen = {_normalized_text(item) for item in thirty_day_items}
    ninety_day_items = [
        item
        for item in _dedupe_text([*strategic, *priority_actions.get("P2", [])])
        if _normalized_text(item) not in sixty_day_seen
        and _normalized_text(item) not in thirty_day_seen
    ]

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
        technical_actions.append(
            "Consider publishing llms.txt and llms-full.txt as optional discoverability hints for supported platforms."
        )
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
    cluster_count = len(_sequence(opportunity_map.get("clusters")))
    failure_count = len(report_model.citation_failures)

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

    recommended_decision = (
        "Prioritize answer-ready content upgrades and structural clarity before investing in advanced platform-specific GEO extras."
    )
    if _int_score(_mapping(_mapping(audit_data.get("geo_scores")).get("scores")).get("ai_citability")) >= 60:
        recommended_decision = (
            "Build on the current content foundation by expanding proof-rich topic coverage and platform-specific distribution."
        )

    proof_points = [
        f"GEO score: {_int_score(_mapping(audit_data.get('geo_scores')).get('geo_score'))}/100",
        f"AI citability: {_int_score(_mapping(_mapping(audit_data.get('geo_scores')).get('scores')).get('ai_citability'))}/100",
        f"Opportunity clusters observed: {cluster_count}",
        f"Citation failures observed: {failure_count}",
    ]
    confidence = "medium" if discovery_note else "high"

    return {
        "overview": executive_summary.get("overview"),
        "recommended_decision": recommended_decision,
        "confidence": confidence,
        "proof_points": proof_points,
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
            "issue": "Optional llms.txt discoverability hint",
            "severity": "steady" if llms_validation.get("exists") else "medium",
            "why_it_matters": (
                "llms.txt is present as an optional discoverability hint for platforms that may use it."
                if llms_validation.get("exists")
                else "llms.txt is not published; this is optional and usually secondary to crawlability, citations, and page clarity."
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


def _client_cover(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    geo_scores = _mapping(audit_data.get("geo_scores"))
    scores = _mapping(geo_scores.get("scores"))
    date_value = _string(audit_data.get("date"))
    return {
        "title": "GEO Client Brief",
        "subtitle": f"Business roadmap for {report_model.brand_name}",
        "website": _string(report_model.site_snapshot.canonical_url or report_model.site_snapshot.url),
        "analysis_date": date_value,
        "readiness_snapshot": [
            {"label": "GEO", "value": f"{_int_score(geo_scores.get('geo_score'))}/100"},
            {"label": "AI Citability", "value": f"{_int_score(scores.get('ai_citability'))}/100"},
            {"label": "Technical", "value": f"{_int_score(scores.get('technical'))}/100"},
            {"label": "Schema", "value": f"{_int_score(scores.get('schema'))}/100"},
        ],
    }


def _client_priority_risks(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    findings = [item for item in _sequence(audit_data.get("findings")) if isinstance(item, Mapping)]
    risks = []
    for finding in findings[:3]:
        title = _display_label(finding.get("title"))
        evidence = _string(finding.get("observed_evidence") or finding.get("description"))
        severity = _string(finding.get("severity")) or "medium"
        risks.append(
            {
                "title": title,
                "severity": severity,
                "what_happened": _string(finding.get("summary") or finding.get("description")),
                "why_it_matters": _string(finding.get("leadership_impact") or finding.get("summary")),
                "proof": evidence,
                "confidence": "medium" if "llms.txt" in title.lower() else "high" if evidence else "medium",
                "marketing_action": _string(finding.get("marketing_action")),
                "engineering_action": _string(finding.get("developer_action")),
                "measurement": _measurement_for_title(title),
            }
        )
    return {"items": risks}


def _client_top_opportunities(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    opportunity_map = _build_opportunity_map(report_model, audit_data)
    items = []
    for item in _sequence(opportunity_map.get("opportunities")):
        if not isinstance(item, Mapping):
            continue
        if _string(item.get("label")).lower() != "high":
            continue
        if _is_branded_noise_opportunity(report_model, audit_data, _string(item.get("query"))):
            continue
        items.append(
            {
                "title": _display_label(item.get("query")),
                "priority": _string(item.get("label")) or "high",
                "opportunity_score": _int_score(item.get("opportunity_score")),
                "what_happened": "This topic is still open in the sampled market and the brand was not strongly visible for it.",
                "why_it_matters": "This topic is strategically open in the current sample.",
                "proof": f"Opportunity score {_int_score(item.get('opportunity_score'))}/100 with site visibility marked as {bool(item.get('site_visible'))}.",
                "confidence": "medium",
                "marketing_action": "Create or refresh a proof-rich answer page mapped to this topic and its adjacent questions.",
                "engineering_action": "Support the page with clean headings, schema where relevant, and internal linking from core navigation.",
                "measurement": "Track AI citations, referral sessions, assisted conversions, and query-level visibility for this topic.",
            }
        )
        if len(items) == 3:
            break
    if items:
        return {"items": items}

    service_lines = _service_line_rows(report_model, audit_data)
    fallback_items = []
    for row in service_lines[:3]:
        fallback_items.append(
            {
                "title": _display_label(row.get("service_line")),
                "priority": _string(row.get("priority")) or "medium",
                "opportunity_score": _int_score(row.get("opportunity_score")),
                "what_happened": "This service line is in scope even though direct opportunity sampling was thin.",
                "why_it_matters": "The service line is in scope for the current GEO audit.",
                "proof": f"Observed opportunity score {_int_score(row.get('opportunity_score'))}/100.",
                "confidence": "limited",
                "marketing_action": "Develop a clear answer-first page or comparison asset for this service line.",
                "engineering_action": "Ensure the service line page has clean hierarchy, strong metadata, and supporting internal links.",
                "measurement": "Track impressions, citations, and referral traffic for service-line queries after publishing.",
            }
        )
    return {"items": fallback_items}


def _client_market_snapshot(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    competitor_gap = _build_competitor_gap_analysis(report_model, audit_data)
    source_inventory = _mapping(competitor_gap.get("source_inventory"))
    competitor_owned = _dedupe_text(source_inventory.get("competitor_owned"))
    earned_media = _dedupe_text(source_inventory.get("earned_media"))
    supported = len(competitor_owned) + len(earned_media) >= 2

    benchmark_rows = []
    if supported:
        for domain in competitor_owned[:3]:
            benchmark_rows.append(
                {
                    "label": _display_label(domain),
                    "bucket": "Competitor-owned",
                    "summary": "Observed in the current market sample.",
                }
            )
        for domain in earned_media[:3]:
            benchmark_rows.append(
                {
                    "label": _display_label(domain),
                    "bucket": "Earned-media",
                    "summary": "Third-party sources are part of the citation picture.",
                }
            )

    summary_text = _string(_mapping(competitor_gap.get("summary")).get("discovery_note"))
    if supported:
        summary_text = summary_text or "Competitor and third-party signals were strong enough to support a concise market benchmark."
    else:
        summary_text = (
            "The competitive picture is still incomplete in this sample, so this page highlights the known gap rather than forcing a weak benchmark."
        )

    return {
        "title": "Market Visibility Snapshot",
        "summary": summary_text,
        "confidence": "supported" if supported else "limited",
        "benchmark_rows": benchmark_rows,
    }


def _client_roadmap(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    roadmap = _build_roadmap(report_model, audit_data)
    return {
        "thirty_day": [_string(item.get("action")) for item in _sequence(roadmap.get("thirty_day")) if isinstance(item, Mapping) and _string(item.get("action"))],
        "sixty_day": [_string(item.get("action")) for item in _sequence(roadmap.get("sixty_day")) if isinstance(item, Mapping) and _string(item.get("action"))],
        "ninety_day": [_string(item.get("action")) for item in _sequence(roadmap.get("ninety_day")) if isinstance(item, Mapping) and _string(item.get("action"))],
    }


def _client_methodology(report_model: ReportModel, audit_data: Mapping[str, Any]) -> dict[str, Any]:
    market_snapshot = _client_market_snapshot(report_model, audit_data)
    presentation_metadata = _mapping(audit_data.get("presentation_metadata"))
    guidance_metadata = _mapping(presentation_metadata.get("guidance"))
    provenance_parts: list[str] = []
    run_mode = _string(presentation_metadata.get("run_mode"))
    driver = _string(presentation_metadata.get("driver"))
    if run_mode:
        provenance_parts.append(f"Run mode: {run_mode}.")
    if driver:
        provenance_parts.append(f"Driver: {driver}.")
    refreshed_at = _string(guidance_metadata.get("refreshed_at"))
    official_sources = _dedupe_text(guidance_metadata.get("official_sources"))
    if refreshed_at:
        if guidance_metadata.get("refresh_requested"):
            provenance_parts.append(
                f"Shared guidance was refreshed before this run at {refreshed_at}."
            )
        else:
            provenance_parts.append(
                f"This run used the latest saved shared guidance snapshot from {refreshed_at}."
            )
    return {
        "summary": "Point-in-time GEO audit based on live crawl, content scoring, and visibility sampling.",
        "confidence_note": (
            "The market view is useful as an early signal (directional), but it is not a full benchmark in this run."
            if _string(market_snapshot.get("confidence")) == "limited"
            else "The market view was broad enough to support a concise benchmark readout."
        ),
        "provenance_note": " ".join(provenance_parts).strip(),
        "official_sources": official_sources,
    }


def _primary_domain(report_model: ReportModel) -> str:
    url = _string(report_model.site_snapshot.canonical_url or report_model.site_snapshot.url)
    parsed = urlparse(url)
    return _string(parsed.netloc or parsed.path or url)


def _sample_completeness(
    report_model: ReportModel,
    audit_data: Mapping[str, Any],
    competitor_gap: Mapping[str, Any],
) -> str:
    query_count = max(
        len(report_model.query_clusters),
        len(_sequence(_mapping(_build_opportunity_map(report_model, audit_data)).get("clusters"))),
    )
    source_inventory = _mapping(competitor_gap.get("source_inventory"))
    observed_market_sources = len(_dedupe_text(source_inventory.get("competitor_owned"))) + len(
        _dedupe_text(source_inventory.get("earned_media"))
    )
    if observed_market_sources >= 2 and query_count >= 1:
        return "strong"
    if observed_market_sources >= 1 or query_count >= 2:
        return "partial"
    return "thin"


def _overall_confidence(sample_completeness: str, geo_score: int, citability_score: int) -> str:
    if sample_completeness == "strong" and geo_score >= 70 and citability_score >= 55:
        return "high"
    if sample_completeness == "thin":
        return "low"
    return "medium"


def _confidence_reason(
    sample_completeness: str,
    market_snapshot: Mapping[str, Any],
    methodology: Mapping[str, Any],
) -> str:
    if sample_completeness == "strong":
        return "Competitor, source, and query sampling were strong enough to support direct recommendations."
    if sample_completeness == "partial":
        return _string(methodology.get("confidence_note")) or "The sample was useful as an early signal (directional), but it was not exhaustive."
    return _string(market_snapshot.get("summary")) or "The competitive picture is still incomplete in this sample."


def _verdict_status(geo_score: int, citability_score: int) -> str:
    if geo_score >= 75 and citability_score >= 60:
        return "visible"
    if geo_score >= 50 or citability_score >= 40:
        return "partially_visible"
    return "not_yet_competitive"


def _one_sentence_verdict(verdict_status: str, technical_score: int, citability_score: int) -> str:
    if verdict_status == "visible":
        return (
            "The brand is already visible in sampled AI search, with a credible technical base and enough citation readiness to build on."
        )
    if verdict_status == "partially_visible":
        if technical_score >= 60 and citability_score < 60:
            return (
                "The brand is technically crawlable, but not yet consistently cited for the sampled high-intent AI queries."
            )
        return "The brand shows partial AI visibility, but it still needs stronger proof-rich content and clearer signals."
    return "The brand is technically available, but not yet competitive in AI visibility for the sampled market."


def _finding_evidence_class(title: str, proof: str) -> str:
    normalized = _normalized_text(f"{title} {proof}")
    if any(token in normalized for token in ("h1", "heading", "schema", "robots", "crawl", "ssr", "markup")):
        return "live_site"
    if any(token in normalized for token in ("score", "citability", "/100")):
        return "internal_score"
    if any(token in normalized for token in ("competitor", "market", "sample")):
        return "heuristic_inference"
    return "live_site" if proof else "heuristic_inference"


def _metric_confidence(sample_completeness: str, metric_key: str) -> str:
    if metric_key in {"geo_score", "citability_score", "technical_readiness_score"} and sample_completeness != "thin":
        return "high"
    if metric_key == "competitor_visibility_score" and sample_completeness == "thin":
        return "low"
    return "medium"


def _has_decision_grade_benchmark(report_model: ReportModel, audit_data: Mapping[str, Any]) -> bool:
    market_snapshot = _client_market_snapshot(report_model, audit_data)
    return any(isinstance(row, Mapping) for row in _sequence(market_snapshot.get("benchmark_rows")))


def _has_explicit_verification(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    return _normalized_text(value) in {"yes", "no", "true", "false"}


def _citation_failure_has_direct_prompt_evidence(failure: Any) -> bool:
    metadata = _mapping(getattr(failure, "metadata", None))
    if not metadata:
        return False
    platform_label = _string(metadata.get("platform") or metadata.get("model_surface"))
    winning_domains = _dedupe_text(metadata.get("winning_domains"))
    winning_urls = _dedupe_text(metadata.get("winning_urls") or metadata.get("cited_urls"))
    has_verification = _has_explicit_verification(metadata.get("brand_mentioned")) or _has_explicit_verification(
        metadata.get("brand_cited")
    )
    return bool(platform_label and (has_verification or winning_domains or winning_urls))


def _score_definition_rows(
    report_model: ReportModel,
    audit_data: Mapping[str, Any],
    competitor_gap: Mapping[str, Any],
    sample_completeness: str,
) -> list[dict[str, Any]]:
    geo_scores = _mapping(audit_data.get("geo_scores"))
    scores = _mapping(geo_scores.get("scores"))
    entity_confidence = int(round(float(_mapping(report_model.entity_graph.to_dict() if report_model.entity_graph else {}).get("confidence") or 0) * 100))
    competitor_sources = _mapping(competitor_gap.get("source_inventory"))
    benchmark_supported = _has_decision_grade_benchmark(report_model, audit_data)
    competitor_visibility_score = _average_score(
        min(100, len(_dedupe_text(competitor_sources.get("competitor_owned"))) * 35),
        min(100, len(_dedupe_text(competitor_sources.get("earned_media"))) * 25),
        68 if sample_completeness == "strong" else 52 if sample_completeness == "partial" else 34,
    )
    metric_specs = [
        (
            "geo_score",
            "GEO Score",
            _int_score(geo_scores.get("geo_score")),
            "Overall AI visibility readiness across content, technical access, structure, and market signals.",
            "A strong GEO score means the brand is both machine-readable and useful enough to be reused in AI answers.",
            "live_site, internal_score, and market-sample evidence",
        ),
        (
            "citability_score",
            "Citability Score",
            _int_score(scores.get("ai_citability")),
            "How ready the current pages are to be quoted or grounded by AI systems.",
            "Good citability means answer-first passages, proof-rich sections, and clear extraction points.",
            "live_site and internal_score evidence",
        ),
        (
            "technical_readiness_score",
            "Technical Readiness Score",
            _int_score(scores.get("technical")),
            "How accessible the site is to crawlers and retrieval systems.",
            "Good technical readiness means crawlable pages, stable rendering, and clean structure.",
            "live_site and official_guidance evidence",
        ),
        (
            "entity_trust_score",
            "Entity Trust Score",
            _average_score(scores.get("brand_authority"), entity_confidence),
            "How clearly the brand and its claims are grounded through entity and trust signals.",
            "Good entity trust means strong sameAs support, authority signals, and consistent brand references.",
            "live_site, third_party_reference, and internal_score evidence",
        ),
        (
            "competitor_visibility_score",
            "Competitor Visibility Score",
            competitor_visibility_score,
            "How complete and decision-useful the current competitor visibility sample is.",
            "A strong competitor visibility score means we can compare the brand against real observed rivals and source domains.",
            "live_serp_or_platform and heuristic_inference evidence",
        ),
    ]

    weighting_by_metric = {
        item["metric_key"]: item
        for item in _score_weighting_components()
    }
    rows: list[dict[str, Any]] = []
    for metric_key, metric_name, score, definition, good_looks_like, evidence_used in metric_specs:
        metric_definition = definition
        why_this_score_landed_here = f"{metric_name} landed at {score}/100 based on the current audit sample."
        confidence = _metric_confidence(sample_completeness, metric_key)
        if metric_key == "competitor_visibility_score" and not benchmark_supported:
            metric_definition = (
                f"{definition} This run did not capture enough named rivals or source domains for a decision-grade benchmark, "
                "so treat this score as directional only."
            )
            why_this_score_landed_here = (
                "A benchmark-shaped score was still calculated from limited market signals, but no decision-grade "
                "competitor benchmark rows were captured in this run."
            )
            confidence = "low"
        rows.append(
            {
                "metric_key": metric_key,
                "metric_name": metric_name,
                "score": score,
                "plain_english_definition": metric_definition,
                "what_good_looks_like": good_looks_like,
                "why_this_score_landed_here": why_this_score_landed_here,
                "primary_evidence_used": [item.strip() for item in evidence_used.split(",")],
                "weight": _mapping(weighting_by_metric.get(metric_key)).get("weight"),
                "why_this_weight_exists": _string(_mapping(weighting_by_metric.get(metric_key)).get("why_this_weight_exists")),
                "confidence": confidence,
            }
        )
    return rows


def _combined_cover_verdict(
    report_model: ReportModel,
    audit_data: Mapping[str, Any],
    competitor_gap: Mapping[str, Any],
    market_snapshot: Mapping[str, Any],
    methodology: Mapping[str, Any],
) -> dict[str, Any]:
    geo_scores = _mapping(audit_data.get("geo_scores"))
    scores = _mapping(geo_scores.get("scores"))
    geo_score = _int_score(geo_scores.get("geo_score"))
    citability_score = _int_score(scores.get("ai_citability"))
    technical_score = _int_score(scores.get("technical"))
    sample_completeness = _sample_completeness(report_model, audit_data, competitor_gap)
    overall_confidence = _overall_confidence(sample_completeness, geo_score, citability_score)
    verdict_status = _verdict_status(geo_score, citability_score)
    return {
        "brand_name": report_model.brand_name,
        "primary_domain": _primary_domain(report_model),
        "audit_date": _string(audit_data.get("date")),
        "analysis_window": "Point-in-time audit",
        "verdict_status": verdict_status,
        "one_sentence_verdict": _one_sentence_verdict(verdict_status, technical_score, citability_score),
        "overall_confidence": overall_confidence,
        "confidence_reason": _confidence_reason(sample_completeness, market_snapshot, methodology),
        "sample_completeness": sample_completeness,
    }


def _combined_decision_summary(
    report_model: ReportModel,
    audit_data: Mapping[str, Any],
    summary: Mapping[str, Any],
    cover_verdict: Mapping[str, Any],
) -> dict[str, Any]:
    geo_scores = _mapping(audit_data.get("geo_scores"))
    scores = _mapping(geo_scores.get("scores"))
    technical_score = _int_score(scores.get("technical"))
    schema_score = _int_score(scores.get("schema"))
    llms_validation = _mapping(audit_data.get("llms_validation"))
    working: list[str] = []
    if technical_score >= 60:
        working.append("Technical foundations are workable for crawler access and retrieval.")
    if schema_score >= 60:
        working.append("Structured data is present enough to support cleaner entity interpretation.")
    if llms_validation.get("exists") and llms_validation.get("format_valid"):
        working.append("Supporting crawl guidance is already published in a valid format.")
    if not working:
        working.append("The site has a usable foundation to improve from.")

    blockers = []
    for item in _sequence(summary.get("blockers"))[:3]:
        if not isinstance(item, Mapping):
            continue
        title = _string(item.get("issue") or item.get("title") or "Observed blocker")
        blockers.append(
            {
                "title": title,
                "severity": _string(item.get("severity")) or "medium",
                "business_impact": _string(item.get("why_it_matters") or item.get("summary") or title),
                "evidence_class": _finding_evidence_class(title, _string(item.get("why_it_matters"))),
                "confidence": cover_verdict.get("overall_confidence", "medium"),
            }
        )

    what_is_not_working = [item["title"] for item in blockers[:3]]

    top_opportunities = []
    opportunity_section = _client_top_opportunities(report_model, audit_data)
    for item in _sequence(opportunity_section.get("items"))[:3]:
        if not isinstance(item, Mapping):
            continue
        top_opportunities.append(
            {
                "title": _string(item.get("title")),
                "why_now": _string(item.get("why_it_matters") or item.get("what_happened")),
                "expected_outcome": _string(item.get("measurement") or "Improved query-level visibility and citation pickup."),
                "confidence": _string(item.get("confidence")) or "medium",
            }
        )

    roadmap = _build_roadmap(report_model, audit_data)
    top_actions = []
    for item in _sequence(roadmap.get("thirty_day"))[:3]:
        if not isinstance(item, Mapping):
            continue
        action_text = _string(item.get("action"))
        top_actions.append(
            {
                "action": action_text,
                "owner": _string(item.get("owner")) or _owner_for_action(action_text),
                "expected_outcome": _string(item.get("impact")) or _measurement_for_title(action_text),
            }
        )

    leadership_takeaway = _clean_legacy_rescience_language(
        _string(summary.get("overview") or summary.get("recommended_decision"))
    )
    if not llms_validation.get("exists") and "llms.txt" not in leadership_takeaway.lower():
        leadership_takeaway = (
            f"{leadership_takeaway} If llms.txt comes up, treat it as an optional machine hint rather than the main fix."
        ).strip()

    return {
        "what_is_working": working[:3],
        "what_is_not_working": what_is_not_working[:3],
        "top_blockers": blockers[:3],
        "top_opportunities": top_opportunities[:3],
        "leadership_takeaway": leadership_takeaway,
        "top_3_actions": top_actions,
    }


def _combined_priority_findings(
    audit_data: Mapping[str, Any],
    cover_verdict: Mapping[str, Any],
) -> dict[str, Any]:
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings = [
        item
        for item in _sequence(audit_data.get("findings"))
        if isinstance(item, Mapping) and not _is_legacy_rescience_finding(item)
    ]
    findings = sorted(
        findings,
        key=lambda item: severity_order.get(_string(item.get("severity")).lower(), 99),
    )
    items = []
    fallback_limitation = (
        "This is a point-in-time audit run with directional market sampling."
        if _string(cover_verdict.get("sample_completeness")) != "strong"
        else "This finding is grounded in the current audit run and should be rechecked after implementation."
    )
    for finding in findings[:5]:
        title = _display_label(finding.get("title"))
        proof = _clean_legacy_rescience_language(
            _string(finding.get("observed_evidence") or finding.get("description") or finding.get("summary"))
        )
        items.append(
            {
                "title": title,
                "severity": _string(finding.get("severity")) or "medium",
                "plain_english_summary": _clean_legacy_rescience_language(
                    _string(finding.get("summary") or finding.get("description"))
                ),
                "what_we_observed": proof,
                "why_it_matters_to_business": _clean_legacy_rescience_language(
                    _string(finding.get("leadership_impact") or finding.get("summary"))
                ),
                "evidence_class": _finding_evidence_class(title, proof),
                "proof": proof,
                "confidence": "medium" if "llms.txt" in title.lower() else cover_verdict.get("overall_confidence", "medium"),
                "counterpoint_or_limitation": fallback_limitation,
                "marketing_action": _string(finding.get("marketing_action")) or _default_marketing_action(title),
                "engineering_action": _string(finding.get("developer_action")) or _default_engineering_action(title),
                "success_metric": _measurement_for_title(title),
                "affected_pages_or_queries": _dedupe_text(
                    finding.get("affected_pages_or_queries")
                    or [audit_data.get("url")]
                ),
            }
        )
    return {"items": items}


def _combined_competitive_benchmark(
    report_model: ReportModel,
    audit_data: Mapping[str, Any],
    competitor_gap: Mapping[str, Any],
    cover_verdict: Mapping[str, Any],
) -> dict[str, Any]:
    market_snapshot = _client_market_snapshot(report_model, audit_data)
    competitor_profiles = [profile.to_dict() for profile in report_model.competitor_profiles]
    competitor_lookup = {profile.get("domain"): profile for profile in competitor_profiles if isinstance(profile, Mapping)}
    benchmark_rows = []
    for row in _sequence(market_snapshot.get("benchmark_rows")):
        if not isinstance(row, Mapping):
            continue
        profile = competitor_lookup.get(_string(row.get("label")).lower())
        benchmark_rows.append(
            {
                "competitor_name": _display_label(row.get("label")),
                "platform": "Cross-platform sample",
                "mention_share": "Observed",
                "citation_share": "Observed" if _string(row.get("bucket")).lower() == "earned-media" else "Directional",
                "top_winning_queries": _dedupe_text(
                    [failure.query for failure in report_model.citation_failures][:2]
                ),
                "source_strength": _string(row.get("bucket")),
                "sentiment_or_positioning": ", ".join(_dedupe_text(_mapping(profile).get("strengths"))) if profile else "",
                "our_gap": _string(row.get("summary")),
                "confidence": cover_verdict.get("overall_confidence", "medium"),
            }
        )

    summary = _string(market_snapshot.get("summary"))
    if not benchmark_rows:
        directional_note = "No decision-grade competitor benchmark was captured in this run."
        if directional_note.lower() not in summary.lower():
            summary = f"{summary} {directional_note}".strip() if summary else directional_note

    return {
        "summary": summary,
        "competitor_set": [
            _display_label(profile.name or profile.domain)
            for profile in report_model.competitor_profiles
        ],
        "sample_scope": {
            "platforms": list(_mapping(audit_data.get("platforms")).keys()),
            "query_count": max(len(report_model.query_clusters), len(report_model.citation_failures)),
            "date_range": _string(audit_data.get("date")),
            "locale": _string(audit_data.get("locale") or "en-US"),
            "sample_completeness": _string(cover_verdict.get("sample_completeness")),
        },
        "benchmark_rows": benchmark_rows,
    }


def _combined_platform_breakdown(
    report_model: ReportModel,
    audit_data: Mapping[str, Any],
    cover_verdict: Mapping[str, Any],
) -> dict[str, Any]:
    platform_scores = _mapping(audit_data.get("platforms"))
    technical_gates = _build_technical_geo_gates(report_model, audit_data)
    crawler_access = _mapping(audit_data.get("crawler_access") or technical_gates.get("crawler_access"))
    platform_defaults = [
        (
            "ChatGPT",
            "Uses live retrieval when available and answer-ready pages are easier to ground.",
            ("chatgpt", "gptbot", "openai"),
        ),
        (
            "Google AI features",
            "Rewards crawlable, structured, high-confidence pages that are easy to excerpt.",
            ("google ai features", "google ai overviews", "google ai overview", "google ai"),
        ),
        (
            "Gemini",
            "Benefits from clear, trustworthy web content and machine-readable signals when grounded answers are available.",
            ("gemini", "google extended"),
        ),
        (
            "Claude",
            "Depends on accessible content and strong source grounding when retrieval is available.",
            ("claude", "claudebot"),
        ),
        (
            "Perplexity",
            "Leans on cited sources and clear supporting domains in its answers.",
            ("perplexity", "perplexitybot"),
        ),
        (
            "Bing/Copilot",
            "Benefits from clear crawl signals, indexing support, and structured source cues.",
            ("bing copilot", "bing", "copilot", "microsoft copilot", "bingbot"),
        ),
    ]

    normalized_scores = [
        (_normalized_text(key), _int_score(value))
        for key, value in platform_scores.items()
        if _string(key)
    ]

    def matches_alias(text: Any, aliases: tuple[str, ...]) -> bool:
        normalized = _normalized_text(text)
        if not normalized:
            return False
        for alias in aliases:
            alias_text = _normalized_text(alias)
            if not alias_text:
                continue
            if (
                normalized == alias_text
                or normalized.startswith(alias_text)
                or alias_text.startswith(normalized)
                or alias_text in normalized
                or normalized in alias_text
            ):
                return True
        return False

    def platform_score_for(aliases: tuple[str, ...]) -> int | None:
        for normalized_key, score in normalized_scores:
            if matches_alias(normalized_key, aliases):
                return score
        return None

    def platform_has_direct_capture(aliases: tuple[str, ...]) -> bool:
        for failure in report_model.citation_failures:
            metadata = _mapping(getattr(failure, "metadata", None))
            platform_label = metadata.get("platform") or metadata.get("model_surface")
            if matches_alias(platform_label, aliases) and _citation_failure_has_direct_prompt_evidence(failure):
                return True
        return False

    def crawler_note_for(aliases: tuple[str, ...]) -> str:
        statuses: list[str] = []
        for crawler_name, info in crawler_access.items():
            info_map = _mapping(info)
            if matches_alias(crawler_name, aliases) or matches_alias(info_map.get("platform"), aliases):
                status = _string(info_map.get("status"))
                if status:
                    statuses.append(status)
        deduped_statuses = _dedupe_text(statuses)
        if not deduped_statuses:
            return ""
        status_text = " ".join(item.lower() for item in deduped_statuses)
        if any(token in status_text for token in ("block", "disallow", "deny", "restricted")):
            return f"Crawler access appears restricted ({', '.join(deduped_statuses)})."
        if any(token in status_text for token in ("allow", "accessible", "open")):
            return f"Crawler access appears open ({', '.join(deduped_statuses)})."
        return f"Crawler access needs review ({', '.join(deduped_statuses)})."

    platforms = []
    guidance_sources = _dedupe_text(_build_platform_guidance(report_model, audit_data).get("official_sources"))
    for platform_name, documented_behavior, aliases in platform_defaults:
        score = platform_score_for(aliases)
        crawler_note = crawler_note_for(aliases)
        direct_capture = platform_has_direct_capture(aliases)
        if score is None:
            observed_site_status = crawler_note or "No direct platform sample was captured in this run."
            observed_visibility_status = "Not sampled in this run"
            cautious_inference = (
                "This platform was not directly sampled, so recommendations stay directional until a platform-specific capture is added."
            )
            recommended_actions = [
                "Run a platform-specific query capture before escalating this section.",
                "Keep crawler access and machine-readable structure stable in the meantime.",
            ]
            confidence = "low"
        elif not direct_capture:
            observed_site_status = (
                f"{crawler_note} No platform-specific answer capture was attached to this run.".strip()
                if crawler_note
                else "Platform scoring was available, but no platform-specific answer capture was attached to this run."
            )
            observed_visibility_status = "Directional only in this run"
            cautious_inference = (
                "This platform has directional readiness signals, but the current run did not capture exact prompts, "
                "answers, or cited URLs strongly enough to treat the visibility readout as decision-grade."
            )
            recommended_actions = [
                "Capture exact prompts, answers, and cited URLs for this platform before escalating the visibility verdict.",
                "Keep crawler access and machine-readable structure stable in the meantime.",
            ]
            confidence = "low"
        else:
            observed_site_status = crawler_note or (
                "Accessible" if score >= 50 else "Needs stronger visibility signals"
            )
            observed_visibility_status = (
                "Visible in sample" if score >= 70 else "Inconsistent in sample" if score >= 45 else "Weak in sample"
            )
            cautious_inference = (
                "The site has a workable base, but the current content and entity signals still limit consistent pickup."
            )
            recommended_actions = [
                "Improve proof-rich answer blocks on priority pages.",
                "Keep crawler access and machine-readable structure stable.",
            ]
            confidence = cover_verdict.get("overall_confidence", "medium")
        platforms.append(
            {
                "platform": platform_name,
                "documented_behavior": documented_behavior,
                "observed_site_status": observed_site_status,
                "observed_visibility_status": observed_visibility_status,
                "cautious_inference": cautious_inference,
                "recommended_actions": recommended_actions,
                "official_sources": guidance_sources,
                "last_verified_at": _string(audit_data.get("date")),
                "confidence": confidence,
            }
        )
    return {"platforms": platforms}


def _combined_prompt_query_proof(
    report_model: ReportModel,
    audit_data: Mapping[str, Any],
    cover_verdict: Mapping[str, Any],
) -> dict[str, Any]:
    cluster_lookup = {
        _normalized_text(query): cluster
        for cluster in report_model.query_clusters
        for query in cluster.queries
    }

    def verification_status(value: Any) -> str:
        if isinstance(value, bool):
            return "yes" if value else "no"
        text = _normalized_text(value)
        if text in {"yes", "true"}:
            return "yes"
        if text in {"no", "false"}:
            return "no"
        if text in {"not directly verified", "not_directly_verified", "sampled_not_verified"}:
            return "not_directly_verified"
        return "not_directly_verified"

    rows = []
    timestamp = f"{_string(audit_data.get('date'))}T00:00:00Z" if _string(audit_data.get("date")) else ""
    for failure in report_model.citation_failures:
        if not _citation_failure_has_direct_prompt_evidence(failure):
            continue
        matched_cluster = cluster_lookup.get(_normalized_text(failure.query))
        query_theme = ""
        if matched_cluster:
            query_theme = _string(matched_cluster.metadata.get("seed_topic")) or matched_cluster.label
        failure_metadata = _mapping(failure.metadata)
        winning_urls = _dedupe_text(
            failure_metadata.get("winning_urls")
            or failure_metadata.get("cited_urls")
        )
        winning_domains = _dedupe_text(failure_metadata.get("winning_domains"))
        rows.append(
            {
                "query_or_prompt": failure.query,
                "query_theme": _display_label(query_theme, fallback="Sampled query theme"),
                "platform": _display_label(failure_metadata.get("platform"), fallback="Cross-platform sampled theme"),
                "model_surface": _display_label(failure_metadata.get("model_surface"), fallback="sampled_query_theme"),
                "locale": _string(audit_data.get("locale") or "en-US"),
                "capture_timestamp": timestamp,
                "brand_mentioned": verification_status(failure_metadata.get("brand_mentioned")),
                "brand_cited": verification_status(failure_metadata.get("brand_cited")),
                "winning_domains": winning_domains,
                "winning_urls": winning_urls,
                "response_summary": _string(
                    failure_metadata.get("response_summary")
                    or failure_metadata.get("answer_summary")
                    or (failure.evidence[0] if failure.evidence else "")
                    or "Sampled evidence suggested stronger competing sources, but the exact answer text was not captured in this run."
                ),
                "why_we_lost_or_won": _string(
                    failure.recommended_fix
                    or failure_metadata.get("why_we_lost_or_won")
                    or "The sample suggests stronger external proof than the brand pages, but exact winners were not consistently captured."
                ),
                "evidence_link_or_snapshot_id": _string(
                    failure_metadata.get("snapshot_id")
                    or failure_metadata.get("evidence_link")
                    or failure.target_url
                ),
                "confidence": cover_verdict.get("overall_confidence", "medium"),
            }
        )
    if not rows:
        sampling_note = (
            "This run did not capture exact prompts, platform answers, or winner URLs strongly enough to include "
            "decision-grade proof rows from the sampled queries."
        )
    elif len(rows) < len(report_model.citation_failures):
        sampling_note = (
            "Only directly captured prompts sampled in this run are shown here. Other sampled failures without exact "
            "answers or winner URLs were excluded."
        )
    else:
        sampling_note = "These rows reflect directly captured prompts sampled in the current run."
    return {
        "sampling_note": sampling_note,
        "rows": rows,
    }


def _combined_page_source_evidence(
    report_model: ReportModel,
    audit_data: Mapping[str, Any],
    competitor_gap: Mapping[str, Any],
    cover_verdict: Mapping[str, Any],
) -> dict[str, Any]:
    page_data = _mapping(audit_data.get("page_data"))
    citability_data = _mapping(audit_data.get("citability_data"))
    geo_scores = _mapping(audit_data.get("geo_scores"))
    scores = _mapping(geo_scores.get("scores"))
    source_inventory = _mapping(competitor_gap.get("source_inventory"))
    priority_pages = [
        {
            "page_url": _string(page_data.get("url") or report_model.site_snapshot.canonical_url or report_model.site_snapshot.url),
            "page_type": "homepage" if _string(page_data.get("url")).rstrip("/").count("/") <= 2 else "priority_page",
            "citability_score": _int_score(citability_data.get("average_citability_score")),
            "technical_observations": [
                f"Observed H1 count: {len(_sequence(page_data.get('h1_tags')))}.",
            ],
            "content_observations": [
                f"Observed word count: {_int_score(page_data.get('word_count'))}.",
            ],
            "schema_observations": [
                f"Schema score: {_int_score(scores.get('schema'))}/100.",
            ],
            "trust_observations": [
                f"Entity confidence: {int(round(float(report_model.entity_graph.confidence) * 100))}/100."
                if report_model.entity_graph is not None
                else "Entity confidence is still thin in this run.",
            ],
            "recommended_fix": "Tighten answer-first structure, proof points, and structured data on the highest-value pages.",
            "confidence": cover_verdict.get("overall_confidence", "medium"),
        }
    ]

    source_domains = []
    for domain in _dedupe_text(source_inventory.get("site_owned")):
        source_domains.append(
            {
                "domain": domain,
                "source_type": "owned",
                "why_it_matters": "Owned pages are the most direct source of reusable brand proof.",
                "observed_role_in_answers": "Brand-controlled source domain",
                "gap_or_advantage": "Owned pages need to be stronger than generic summaries to win citations.",
            }
        )
    for domain in _dedupe_text(source_inventory.get("competitor_owned")):
        source_domains.append(
            {
                "domain": domain,
                "source_type": "competitor",
                "why_it_matters": "Direct competitors shape the current answer landscape.",
                "observed_role_in_answers": "Competing source domain",
                "gap_or_advantage": "Competitor proof appears stronger in the sampled market.",
            }
        )
    for domain in _dedupe_text(source_inventory.get("earned_media")):
        source_domains.append(
            {
                "domain": domain,
                "source_type": "publisher",
                "why_it_matters": "Third-party sources can outrank owned pages when authority is stronger.",
                "observed_role_in_answers": "Third-party citation source",
                "gap_or_advantage": "These domains may be winning trust where owned pages are still thin.",
            }
        )

    entity_signal_review = {
        "entity_name": report_model.entity_graph.entity_name if report_model.entity_graph is not None else report_model.brand_name,
        "same_as_count": len(_dedupe_text(report_model.entity_graph.same_as if report_model.entity_graph is not None else [])),
        "confidence": int(round(float(report_model.entity_graph.confidence) * 100)) if report_model.entity_graph is not None else 0,
    }
    return {
        "priority_pages": priority_pages,
        "source_domains": source_domains,
        "entity_signal_review": entity_signal_review,
    }


def _combined_action_plan(
    report_model: ReportModel,
    audit_data: Mapping[str, Any],
    cover_verdict: Mapping[str, Any],
) -> dict[str, Any]:
    roadmap = _build_roadmap(report_model, audit_data)
    rows = []
    for time_horizon, bucket, effort in (
        ("30_days", _sequence(roadmap.get("thirty_day")), "low"),
        ("60_days", _sequence(roadmap.get("sixty_day")), "medium"),
        ("90_days", _sequence(roadmap.get("ninety_day")), "high"),
    ):
        for item in bucket:
            if not isinstance(item, Mapping):
                continue
            action_text = _string(item.get("action"))
            rows.append(
                {
                    "time_horizon": time_horizon,
                    "action": action_text,
                    "owner": _string(item.get("owner")) or _owner_for_action(action_text),
                    "effort": effort,
                    "dependency": "Current crawl access and page ownership remain stable.",
                    "expected_outcome": _string(item.get("impact")) or _measurement_for_title(action_text),
                    "success_metric": _measurement_for_title(action_text),
                    "evidence_basis": _string(item.get("source")) or "reporting_roadmap",
                    "confidence": cover_verdict.get("overall_confidence", "medium"),
                }
            )
    return {"actions": rows}


def _combined_technical_proof_appendix(
    report_model: ReportModel,
    audit_data: Mapping[str, Any],
    competitor_gap: Mapping[str, Any],
    cover_verdict: Mapping[str, Any],
) -> dict[str, Any]:
    methodology = _client_methodology(report_model, audit_data)
    page_data = _mapping(audit_data.get("page_data"))
    crawler_access = _mapping(audit_data.get("crawler_access"))
    technical = _build_technical_geo_gates(report_model, audit_data)
    if not crawler_access:
        crawler_access = _mapping(technical.get("crawler_access"))
    source_inventory = _mapping(competitor_gap.get("source_inventory"))
    llms_validation = _mapping(audit_data.get("llms_validation"))
    schema_score = _int_score(_mapping(_mapping(audit_data.get("geo_scores")).get("scores")).get("schema"))
    return {
        "methodology": methodology,
        "crawl_and_fetch_evidence": [
            f"Primary URL analyzed: {_string(page_data.get('url') or report_model.site_snapshot.url)}.",
            f"Observed word count: {_int_score(page_data.get('word_count'))}.",
        ],
        "robots_and_bot_access": [
            (
                f"{crawler_name}"
                + (f" ({_string(info.get('platform'))})" if _string(info.get("platform")) else "")
                + f": {_string(info.get('status')) or 'Status not captured.'}."
                + (
                    f" Recommendation: {_string(info.get('recommendation'))}"
                    if _string(info.get("recommendation"))
                    else ""
                )
            )
            for crawler_name, info in crawler_access.items()
            if isinstance(info, Mapping)
        ],
        "dom_and_heading_proof": [
            f"Primary headings found on the page: {len(_sequence(page_data.get('h1_tags')))}.",
            f"Server-rendered page content was present: {bool(page_data.get('has_ssr_content', True))}.",
        ],
        "schema_proof": [
            f"Structured data score: {schema_score}/100.",
            f"An llms.txt guidance file was present: {bool(llms_validation.get('exists'))}.",
        ],
        "source_inventory": _dedupe_text(
            [
                *source_inventory.get("site_owned", []),
                *source_inventory.get("competitor_owned", []),
                *source_inventory.get("earned_media", []),
            ]
        ),
        "limitations": {
            "limitations_note": _confidence_reason(
                _string(cover_verdict.get("sample_completeness")),
                _client_market_snapshot(report_model, audit_data),
                methodology,
            )
        },
    }


def _measurement_for_title(title: str) -> str:
    normalized = _normalized_text(title)
    if "citation" in normalized:
        return "Re-measure AI citability, cited passages, AI referral traffic, and assisted conversions after the content refresh."
    if "heading" in normalized:
        return "Verify one H1 per priority page, then track changes in engagement, excerpt quality, and citation pickup."
    if "llms" in normalized:
        return "If published, monitor crawler access logs and any downstream citation or referral changes rather than expecting ranking movement by itself."
    if "entity" in normalized or "trust" in normalized:
        return "Track growth in sameAs coverage, authoritative mentions, and branded citation consistency."
    return "Track the before/after metric tied to this finding and confirm whether citations, referrals, or conversions improve."


def build_playbook_report_sections(
    report_model: ReportModel,
    audit_data: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = _get_report_context(report_model, audit_data or {})

    sections = {
        "page1_executive_summary": _build_page1_executive_summary(report_model, context),
        "page2_geo_paradigm": _build_page2_geo_paradigm(report_model, context),
        "page3_strategic_implementation": _build_page3_strategic_implementation(report_model, context),
        "page4_content_citability": _build_page4_content_citability(report_model, context),
        "page5_brand_entity_verification": _build_page5_brand_entity_verification(report_model, context),
        "page6_technical_implementation": _build_page6_technical_implementation(report_model, context),
        "page7_audit_process": _build_page7_audit_process(report_model, context),
        "page8_diagnosis_troubleshooting": _build_page8_diagnosis_troubleshooting(report_model, context),
        "page9_faq_by_role": _build_page9_faq_by_role(report_model, context),
        "page10_roadmap_future": _build_page10_roadmap_future(report_model, context),
    }
    return serialize_model({key: sections[key] for key in PLAYBOOK_REPORT_SECTION_ORDER})


def _build_page1_executive_summary(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    exec_summary = _build_executive_summary(report_model, context)
    readiness = _build_readiness_scorecard(context)
    return {
        "brand_name": report_model.brand_name,
        "geo_score": readiness.get("geo_score"),
        "overview": exec_summary.get("overview"),
        "key_takeaways": exec_summary.get("key_takeaways"),
    }


def _build_page2_geo_paradigm(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    technical = _build_technical_geo_gates(report_model, context)
    page_data = _mapping(context.get("page_data"))
    text_content = _string(page_data.get("text_content"))
    
    # Advanced analysis from the new engine
    citability_analysis = analysis.analyze_block_citability(text_content, report_model.brand_name)
    metrics = citability_analysis.get("metrics", {})
    
    # Precise funnel mapping
    crawler_access = _mapping(technical.get("crawler_access"))
    is_crawled = any("Allow" in _string(c.get("status")) for c in crawler_access.values() if isinstance(c, Mapping))
    is_indexed = page_data.get("has_ssr_content", True) and len(_sequence(page_data.get("h1_tags"))) >= 1
    
    return {
        "funnel_status": {
            "crawl": "allowed" if is_crawled else "blocked",
            "index": "verified" if is_indexed else "missing",
            "retrieval": "high" if metrics.get("answer_block_score", 0) > 70 else "medium",
        },
        "pillars": [
            "Technical Accessibility: Machine-readable architecture (SSR, Schema, llms.txt).",
            "Content Citability: High-density 'Answer Blocks' (40-60 words) with entities.",
            "Entity Verification: Brand identity grounded in Knowledge Graph & authority signals.",
            "Topical Authority: Deep query coverage in high-opportunity clusters.",
        ]
    }



def _build_page3_strategic_implementation(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    query_universe = _build_query_universe(report_model, context)
    rescience_pass = _mapping(context.get("rescience_pass"))
    return {
        "service_line_themes": query_universe.get("service_lines"),
        "answer_blocks_status": "present" if rescience_pass.get("geo_methods") else "missing",
        "recommended_methods": rescience_pass.get("geo_methods"),
    }


def _build_page4_content_citability(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    diagnosis = _build_citation_diagnosis(report_model, context)
    scores = _mapping(_mapping(context.get("geo_scores")).get("scores"))
    page_data = _mapping(context.get("page_data"))
    text_content = _string(page_data.get("text_content"))
    
    # Advanced analysis from the new engine
    citability_analysis = analysis.analyze_block_citability(text_content, report_model.brand_name)
    metrics = citability_analysis.get("metrics", {})
    
    # Map checklist to expected playbook keys
    return {
        "citability_score": _int_score(scores.get("ai_citability")),
        "failures": diagnosis.get("failures"),
        "checklist_status": {
            "answer_block_readiness": metrics.get("answer_block_score", 0),
            "self_containment": metrics.get("self_contain_score", 0),
            "statistical_density": metrics.get("stat_density_score", 0),
            "entity_grounding": metrics.get("entity_ground_score", 0),
            "citation_readiness": _int_score(scores.get("ai_citability")),
        },
        "granular_metrics": [
            {"label": "Answer Blocks", "value": f"{metrics.get('answer_blocks', 0)} detected"},
            {"label": "Avg Block Length", "value": f"{metrics.get('avg_block_length', 0)} words"},
            {"label": "Fact Density", "value": f"{metrics.get('fact_density', 0)}%"},
            {"label": "Self-Containment", "value": "High" if metrics.get("self_contain_score", 0) > 70 else "Medium"},
        ]
    }



def _build_page5_brand_entity_verification(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    trust_graph = _build_entity_trust_graph(report_model, context)
    return {
        "entity_name": report_model.brand_name,
        "knowledge_graph_confidence": trust_graph.get("analysis", {}).get("confidence"),
        "profile_links": trust_graph.get("profile_links"),
        "trust_signals": trust_graph.get("trust_signals"),
    }


def _build_page6_technical_implementation(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    technical = _build_technical_geo_gates(report_model, context)
    llms_validation = _mapping(context.get("llms_validation"))
    return {
        "llms_txt_exists": llms_validation.get("exists"),
        "crawler_access": technical.get("crawler_access"),
        "ssr_status": context.get("page_data", {}).get("has_ssr_content", True),
        "schema_score": _int_score(_mapping(_mapping(context.get("geo_scores")).get("scores")).get("schema")),
    }


def _build_page7_audit_process(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    readiness = _build_readiness_scorecard(context)
    return {
        "geo_score": readiness.get("geo_score"),
        "components": readiness.get("components"),
        "platforms": readiness.get("platforms"),
    }


def _build_page8_diagnosis_troubleshooting(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    readiness = _build_readiness_scorecard(context)
    diagnosis = _build_citation_diagnosis(report_model, context)
    return {
        "visibility_issues": readiness.get("priority_risks"),
        "citation_failures": diagnosis.get("failures"),
        "troubleshooting_notes": [
            "Check robots.txt if GPTBot visibility is zero.",
            "Review H1 structure if main thesis is not recognized.",
            "Add llms.txt if the site structure is complex.",
        ],
    }


def _build_page9_faq_by_role(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    exec_summary = _build_executive_summary(report_model, context)
    by_audience = _mapping(exec_summary.get("by_audience"))
    
    # Fallback to standard role-based FAQs if summary is missing
    role_summaries = {}
    
    # CEO/Leadership
    role_summaries["Executive Leadership"] = by_audience.get("executive") or (
        "Focus on Brand Authority and business-critical entity grounding. "
        "The primary objective is ensuring AI engines recognize the brand as a source of truth for its core products."
    )
    
    # Marketing
    role_summaries["Marketing & Content"] = by_audience.get("marketing") or (
        "Focus on Content Citability and 'Answer Block' architecture. "
        "Move from keyword density to 40-60 word high-density information passages that directly answer user queries."
    )
    
    # Engineering/Dev
    role_summaries["IT & Engineering"] = by_audience.get("technical") or (
        "Focus on machine-readability, SSR, and schema. "
        "Provide clear structured data (JSON-LD) and ensure bots can access full-fidelity HTML content without execution bottlenecks."
    )
    
    return {
        "role_summaries": role_summaries,
    }



def _build_page10_roadmap_future(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    roadmap = _build_roadmap(report_model, context)
    return {
        "thirty_day": roadmap.get("thirty_day"),
        "sixty_day": roadmap.get("sixty_day"),
        "ninety_day": roadmap.get("ninety_day"),
    }


def build_client_report_sections(
    report_model: ReportModel,
    audit_data: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = _get_report_context(report_model, audit_data or {})
    decision_summary = _build_decision_summary(report_model, context)
    competitor_gap = _build_competitor_gap_analysis(report_model, context)
    market_snapshot = _client_market_snapshot(report_model, context)
    methodology = _client_methodology(report_model, context)
    cover_verdict = _combined_cover_verdict(
        report_model,
        context,
        competitor_gap,
        market_snapshot,
        methodology,
    )

    sections = {
        "cover_verdict": cover_verdict,
        "decision_summary": _combined_decision_summary(report_model, context, decision_summary, cover_verdict),
        "score_definitions": {
            "term_guide": _term_guide_entries(),
            "weighting": {
                "summary": _score_weighting_summary(),
                "components": _score_weighting_components(),
            },
            "metrics": _score_definition_rows(
                report_model,
                context,
                competitor_gap,
                _string(cover_verdict.get("sample_completeness")),
            )
        },
        "priority_findings": _combined_priority_findings(context, cover_verdict),
        "competitive_benchmark": _combined_competitive_benchmark(
            report_model,
            context,
            competitor_gap,
            cover_verdict,
        ),
        "platform_breakdown": _combined_platform_breakdown(report_model, context, cover_verdict),
        "prompt_query_proof": _combined_prompt_query_proof(report_model, context, cover_verdict),
        "page_source_evidence": _combined_page_source_evidence(
            report_model,
            context,
            competitor_gap,
            cover_verdict,
        ),
        "action_plan_30_60_90": _combined_action_plan(report_model, context, cover_verdict),
        "technical_proof_appendix": _combined_technical_proof_appendix(
            report_model,
            context,
            competitor_gap,
            cover_verdict,
        ),
    }
    return serialize_model({key: sections[key] for key in CLIENT_REPORT_SECTION_ORDER})


def _build_strategic_narrative(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    metadata = report_model.metadata
    driver = _string(metadata.get("driver", "automated"))
    is_assisted = driver.lower() != "automated"
    
    narrative = []
    if is_assisted:
        model = _string(metadata.get("model", "AI Assistant"))
        narrative.append(f"This analysis was enhanced by a strategic session with {model}.")
        narrative.append("The assistant prioritized content depth, additive discovery, and established 2026 platform rules.")
    else:
        narrative.append("This is an automated GEO audit snapshot.")
        
    return {
        "title": "AI Assistant Strategic Narrative",
        "content": " ".join(narrative),
        "is_assisted": is_assisted
    }


def _build_platform_guidance(report_model: ReportModel, context: dict[str, Any]) -> dict[str, Any]:
    guidance = _mapping(report_model.metadata.get("guidance"))
    official_sources = _sequence(guidance.get("official_sources"))
    platform_rules = _sequence(guidance.get("platform_rules"))
    
    if not official_sources and not platform_rules:
        # Fallback to defaults if metadata is missing
        official_sources = [
            "https://openai.com/gptbot",
            "https://claudebot.com",
            "https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers"
        ]
        platform_rules = [
            "Prioritize High-Citability content over crawler hints.",
            "Maintain SSR-complete hydration for machine readability.",
            "Reduce llms.txt weighting in favor of schema-backed proof."
        ]

    return {
        "title": "Platform Guidance 2026",
        "official_sources": official_sources,
        "key_rules": platform_rules,
        "reference_citation": "Source: skills/geo-executive-report/references/platform-guidance-2026.md"
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
