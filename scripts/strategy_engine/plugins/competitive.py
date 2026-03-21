from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Mapping
from urllib.parse import urlsplit

from ..core import (
    AnalysisContext,
    CitationFailure,
    CompetitorProfile,
    EntityGraph,
    StrategyPlugin,
    serialize_model,
)


def _clean_text(value: Any) -> str:
    return str(value).strip()


_TITLE_GENERIC_SEGMENTS = {
    "home",
    "homepage",
    "about",
    "about us",
    "contact",
    "contact us",
    "services",
    "service",
    "products",
    "product",
    "blog",
    "news",
    "faq",
    "support",
    "docs",
}

_ENTITY_STOPWORDS = {
    "co",
    "company",
    "inc",
    "inc.",
    "llc",
    "ltd",
    "corp",
    "corporation",
    "the",
}

_EARNED_MEDIA_DOMAIN_HINTS = {
    "news",
    "press",
    "blog",
    "review",
    "reviews",
    "magazine",
    "journal",
    "medium",
    "forbes",
    "reuters",
    "bloomberg",
    "marketwatch",
    "investopedia",
    "wsj",
    "yahoo",
    "linkedin",
    "youtube",
}

_COMPETITOR_PAGE_HINTS = {
    "competitor",
    "official",
    "company",
    "services",
    "service",
    "solutions",
    "solution",
    "pricing",
    "quote",
    "contact",
    "about",
    "overview",
    "product",
    "products",
    "home",
    "homepage",
}

_FRESHNESS_QUERY_HINTS = {
    "latest",
    "current",
    "new",
    "newest",
    "recent",
    "today",
    "updated",
    "update",
    "this year",
    "2026",
    "2025",
}

_ATTRIBUTION_QUERY_HINTS = {
    "source",
    "sources",
    "citation",
    "citations",
    "cite",
    "cited",
    "according to",
    "reference",
    "references",
    "proof",
}


def _dedupe(items: Any) -> list[str]:
    if not items:
        return []
    seen: set[str] = set()
    results: list[str] = []
    for item in items:
        text = _clean_text(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(text)
    return results


def _normalize_domain(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    domain = parsed.netloc or parsed.path
    return domain.lower().removeprefix("www.")


def _domain_matches(candidate: str, target: str) -> bool:
    if not candidate or not target:
        return False
    return candidate == target or candidate.endswith(f".{target}") or target.endswith(
        f".{candidate}"
    )


def _json_ld_nodes(structured_data: Any) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    if isinstance(structured_data, list):
        for item in structured_data:
            nodes.extend(_json_ld_nodes(item))
        return nodes
    if not isinstance(structured_data, dict):
        return nodes

    if "@type" in structured_data:
        nodes.append(structured_data)

    graph = structured_data.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            nodes.extend(_json_ld_nodes(item))
    elif isinstance(graph, dict):
        nodes.extend(_json_ld_nodes(graph))

    return nodes


def _link_urls(value: Any) -> list[str]:
    links: list[str] = []
    if not value:
        return links
    if isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping) and item.get("url"):
                links.append(str(item["url"]))
            elif item:
                links.append(str(item))
    elif isinstance(value, Mapping) and value.get("url"):
        links.append(str(value["url"]))
    elif value:
        links.append(str(value))
    return _dedupe(links)


def _node_types(node: Mapping[str, Any]) -> list[str]:
    raw = node.get("@type")
    if isinstance(raw, list):
        return _dedupe(raw)
    if raw:
        return _dedupe([raw])
    return []


def _extract_site_domain(context: AnalysisContext, explicit: str | None = None) -> str:
    if explicit:
        normalized = _normalize_domain(explicit)
        if normalized:
            return normalized
    fallback = context.site_snapshot.canonical_url or context.site_snapshot.url
    return _normalize_domain(fallback)


def _extract_brand_name(context: AnalysisContext, page_data: Mapping[str, Any]) -> str:
    title = _clean_text(context.site_snapshot.title or page_data.get("title") or "")
    if title:
        parts = re.split(r"\s*[|:–—-]\s*", title)
        if parts:
            if len(parts) == 2:
                left = _clean_text(parts[0])
                right = _clean_text(parts[1])
                left_key = left.lower()
                right_key = right.lower()
                if left_key in _TITLE_GENERIC_SEGMENTS and right:
                    return right
                if right_key in _TITLE_GENERIC_SEGMENTS and left:
                    return left
            return _clean_text(parts[0] or title)

    for node in _json_ld_nodes(
        page_data.get("structured_data") or context.site_snapshot.structured_data
    ):
        if "Organization" in _node_types(node) and node.get("name"):
            return _clean_text(node["name"])

    parsed = urlsplit(context.site_snapshot.canonical_url or context.site_snapshot.url)
    return (parsed.netloc or parsed.path).replace("www.", "") or "site"


def _extract_page_data(context: AnalysisContext) -> dict[str, Any]:
    readiness = context.metadata.get("readiness")
    if isinstance(readiness, Mapping):
        page_data = readiness.get("page_data")
        if isinstance(page_data, Mapping):
            return dict(page_data)
    return {}


def _extract_brand_data(context: AnalysisContext) -> dict[str, Any]:
    brand_data = context.metadata.get("brand_data")
    if isinstance(brand_data, Mapping):
        return dict(brand_data)
    readiness = context.metadata.get("readiness")
    if isinstance(readiness, Mapping):
        nested = readiness.get("brand_data")
        if isinstance(nested, Mapping):
            return dict(nested)
    return {}


def _extract_opportunity_payload(context: AnalysisContext) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if context.report_model is not None:
        for key in ("serp_analysis", "opportunity"):
            value = context.report_model.plugin_results.get(key)
            if isinstance(value, Mapping):
                payload[key] = dict(value)
    metadata = context.metadata.get("opportunity")
    if isinstance(metadata, Mapping):
        payload["opportunity"] = {**payload.get("opportunity", {}), **dict(metadata)}
    competitive = context.metadata.get("competitive")
    if isinstance(competitive, Mapping):
        payload["competitive"] = dict(competitive)
    return payload


def _extract_serp_snapshots(payload: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    snapshots: dict[str, list[dict[str, Any]]] = {}
    for key in ("serp_analysis", "opportunity"):
        data = payload.get(key)
        if not isinstance(data, Mapping):
            continue
        raw = data.get("serp_snapshots")
        if not isinstance(raw, Mapping):
            continue
        for query, results in raw.items():
            if not query or not isinstance(results, list):
                continue
            snapshots.setdefault(str(query), [])
            snapshots[str(query)].extend(
                [dict(item) for item in results if isinstance(item, Mapping)]
            )
    return snapshots


def _extract_explicit_competitors(payload: Mapping[str, Any]) -> list[str]:
    explicit: list[str] = []
    for source in (
        payload.get("competitive"),
        payload.get("opportunity"),
    ):
        if not isinstance(source, Mapping):
            continue
        explicit.extend(source.get("competitor_domains") or [])
    return _dedupe(_normalize_domain(item) for item in explicit if _normalize_domain(item))


def _infer_competitor_domains(
    *,
    site_domain: str,
    explicit_domains: list[str],
    serp_snapshots: Mapping[str, list[dict[str, Any]]],
    result_limit: int,
) -> list[str]:
    if explicit_domains:
        return [domain for domain in explicit_domains if domain and not _domain_matches(domain, site_domain)]

    candidates: list[str] = []
    for results in serp_snapshots.values():
        for result in results:
            domain = _normalize_domain(result.get("domain") or result.get("url"))
            if not domain or _domain_matches(domain, site_domain):
                continue
            candidates.append(domain)

    return _dedupe(candidates)[: max(1, result_limit)]


def _profile_name_from_result(domain: str, result: Mapping[str, Any] | None) -> str:
    if isinstance(result, Mapping):
        title = _clean_text(result.get("title"))
        if title:
            return title
        snippet = _clean_text(result.get("snippet"))
        if snippet:
            prefix = snippet.split(".")[0].strip()
            if prefix:
                return prefix[:80]
    cleaned = domain.split(".")[0].replace("-", " ").strip()
    return cleaned.title() if cleaned else domain


def _strengths_from_signals(result: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(result, Mapping):
        return []
    text = " ".join(
        _clean_text(result.get(key))
        for key in ("title", "snippet", "query")
    ).lower()
    strengths: list[str] = []
    if any(token in text for token in ("best", "top", "leader", "award")):
        strengths.append("Strong market positioning")
    if any(token in text for token in ("pricing", "cost", "quote", "plans")):
        strengths.append("Clear commercial intent coverage")
    if any(token in text for token in ("review", "reviews", "comparison", "compare", "alternative")):
        strengths.append("Comparison visibility")
    return strengths


def _query_has_signal(query: str, hints: set[str]) -> bool:
    normalized = query.lower()
    return any(hint in normalized for hint in hints)


def _looks_like_earned_media(domain: str, result: Mapping[str, Any] | None) -> bool:
    if not domain:
        return False
    text = " ".join(
        _clean_text(part)
        for part in (
            domain,
            result.get("title") if isinstance(result, Mapping) else "",
            result.get("snippet") if isinstance(result, Mapping) else "",
        )
    ).lower()
    return any(token in text for token in _EARNED_MEDIA_DOMAIN_HINTS)


def _looks_like_competitor_owned(domain: str, result: Mapping[str, Any] | None) -> bool:
    if not domain:
        return False
    text = " ".join(
        _clean_text(part)
        for part in (
            domain,
            result.get("title") if isinstance(result, Mapping) else "",
            result.get("snippet") if isinstance(result, Mapping) else "",
        )
    ).lower()
    return any(token in text for token in _COMPETITOR_PAGE_HINTS)


def _classify_serp_sources(
    *,
    site_domain: str,
    explicit_domains: list[str],
    serp_snapshots: Mapping[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[str]], dict[str, dict[str, Any]]]:
    result_lookup: dict[str, dict[str, Any]] = {}
    site_owned: list[str] = []
    competitor_owned: list[str] = []
    earned_media: list[str] = []

    explicit_set = {
        domain
        for domain in explicit_domains
        if domain and not _domain_matches(domain, site_domain)
    }

    for results in serp_snapshots.values():
        for result in results:
            domain = _normalize_domain(result.get("domain") or result.get("url"))
            if not domain:
                continue
            if domain not in result_lookup:
                result_lookup[domain] = result

            if _domain_matches(domain, site_domain):
                site_owned.append(domain)
                continue

            if domain in explicit_set:
                competitor_owned.append(domain)
                continue

            if _looks_like_competitor_owned(domain, result):
                competitor_owned.append(domain)
            else:
                earned_media.append(domain)

    for domain in explicit_set:
        if not _domain_matches(domain, site_domain):
            competitor_owned.append(domain)

    return (
        {
            "site_owned": _dedupe(site_owned),
            "competitor_owned": _dedupe(competitor_owned),
            "earned_media": _dedupe(earned_media),
        },
        result_lookup,
    )


def _collect_competitor_profiles(
    site_domain: str,
    competitor_domains: list[str],
    serp_snapshots: Mapping[str, list[dict[str, Any]]],
    result_limit: int,
) -> list[CompetitorProfile]:
    profiles: list[CompetitorProfile] = []
    seen: set[str] = set()

    result_lookup: dict[str, dict[str, Any]] = {}
    for results in serp_snapshots.values():
        for result in results:
            domain = _normalize_domain(result.get("domain") or result.get("url"))
            if domain and domain not in result_lookup:
                result_lookup[domain] = result

    for domain in competitor_domains[: max(1, result_limit)]:
        if not domain or domain in seen or _domain_matches(domain, site_domain):
            continue
        seen.add(domain)
        result = result_lookup.get(domain)
        profiles.append(
            CompetitorProfile(
                name=_profile_name_from_result(domain, result),
                domain=domain,
                source_urls=[str(result.get("url"))] if isinstance(result, Mapping) and result.get("url") else [],
                strengths=_strengths_from_signals(result),
                weaknesses=[],
                metadata={
                    "source_query": result.get("query") if isinstance(result, Mapping) else None,
                    "source_rank": result.get("rank") if isinstance(result, Mapping) else None,
                    "source": result.get("source") if isinstance(result, Mapping) else None,
                },
            )
        )

    return profiles


def _authority_gaps_from_inventory(
    source_inventory: Mapping[str, list[str]],
    competitor_profiles: list[CompetitorProfile],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []

    if not source_inventory.get("competitor_owned"):
        gaps.append(
            {
                "gap_type": "discovery_gap",
                "gap_theme": "No competitor-owned domains were confidently discovered.",
                "why_it_matters": (
                    "The sample set leans on third-party coverage rather than direct rivals, "
                    "so the analysis should explain that the competitive picture is partial."
                ),
            }
        )

    if source_inventory.get("earned_media"):
        gaps.append(
            {
                "gap_type": "earned_media_gap",
                "gap_theme": "Third-party coverage is visible in the category.",
                "why_it_matters": (
                    "Answer engines may lean on earned-media sources unless the brand has "
                    "clearer authority and evidence signals."
                ),
            }
        )

    for profile in competitor_profiles:
        if profile.strengths:
            gaps.append(
                {
                    "gap_type": "competitor_positioning_gap",
                    "competitor": profile.name,
                    "gap_theme": profile.strengths[0],
                    "why_it_matters": "That competitor is already signaling a clearer market position.",
                }
            )

    return gaps


def _citation_mode_for_item(
    *,
    opportunity: Mapping[str, Any],
    readiness_scores: Mapping[str, Any],
    entity_graph: EntityGraph | None,
    competitor_count: int,
) -> str | None:
    query = _clean_text(opportunity.get("query"))
    site_visible = bool(opportunity.get("site_visible"))
    opportunity_score = int(opportunity.get("opportunity_score") or 0)
    ai_citability = int(readiness_scores.get("ai_citability") or 0)
    confidence = float(entity_graph.confidence or 0) if entity_graph else 0.0

    if not site_visible and opportunity_score >= 50:
        return "non_visible_query"

    if ai_citability < 45 and not site_visible:
        return "non_visible_query"

    if _query_has_signal(query, _FRESHNESS_QUERY_HINTS) and opportunity_score >= 25:
        return "freshness_gap"

    if _query_has_signal(query, _ATTRIBUTION_QUERY_HINTS) and opportunity_score >= 20:
        return "attribution_gap"

    def _mentions_entity(query_text: str, entity_name: str | None) -> bool:
        if not query_text or not entity_name:
            return False
        normalized_query = re.sub(r"[^a-z0-9]+", " ", query_text.lower())
        normalized_entity = re.sub(r"[^a-z0-9]+", " ", entity_name.lower())
        if normalized_entity and normalized_entity in normalized_query:
            return True

        entity_tokens = [
            token
            for token in normalized_entity.split()
            if token and token not in _ENTITY_STOPWORDS and len(token) >= 3
        ]
        if not entity_tokens:
            entity_tokens = [token for token in normalized_entity.split() if token]
        return any(token in normalized_query.split() for token in entity_tokens)

    branded_query = _mentions_entity(
        query,
        entity_graph.entity_name if entity_graph and entity_graph.entity_name else None,
    )
    if confidence < 0.6 and branded_query:
        return "weak_entity_support"

    if competitor_count and not site_visible and opportunity_score >= 35:
        return "non_visible_query"

    if ai_citability < 35 and opportunity_score >= 25:
        return "weak_citation_support"

    return None


@dataclass(frozen=True, slots=True)
class CompetitorAnalysisInputs:
    competitor_domains: list[str] = field(default_factory=list)
    serp_snapshots: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    opportunity: dict[str, Any] = field(default_factory=dict)
    site_domain: str | None = None
    result_limit: int = 5

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CompetitorAnalysisInputs":
        try:
            result_limit = max(1, int(data.get("result_limit", 5)))
        except (TypeError, ValueError):
            result_limit = 5
        return cls(
            competitor_domains=[
                _normalize_domain(item)
                for item in data.get("competitor_domains") or []
                if _normalize_domain(item)
            ],
            serp_snapshots={
                str(query): [dict(item) for item in results if isinstance(item, Mapping)]
                for query, results in (data.get("serp_snapshots") or {}).items()
                if query and isinstance(results, list)
            },
            opportunity=dict(data.get("opportunity") or {}),
            site_domain=_normalize_domain(data.get("site_domain")) or None,
            result_limit=result_limit,
        )


@dataclass(frozen=True, slots=True)
class CompetitorAnalysisResult:
    profiles: list[CompetitorProfile]
    summary: dict[str, Any]
    source_inventory: dict[str, list[str]] = field(default_factory=dict)
    authority_gaps: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @property
    def competitor_profiles(self) -> list[CompetitorProfile]:
        return self.profiles


@dataclass(frozen=True, slots=True)
class EntityAnalysisInputs:
    page_data: dict[str, Any] = field(default_factory=dict)
    brand_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EntityAnalysisInputs":
        return cls(
            page_data=dict(data.get("page_data") or {}),
            brand_data=dict(data.get("brand_data") or {}),
        )


@dataclass(frozen=True, slots=True)
class EntityAnalysisResult:
    entity_graph: EntityGraph | dict[str, Any] | None
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)


@dataclass(frozen=True, slots=True)
class CitationDiagnosisInputs:
    readiness: dict[str, Any] = field(default_factory=dict)
    opportunity: dict[str, Any] = field(default_factory=dict)
    competitor_profiles: list[dict[str, Any]] = field(default_factory=list)
    entity_graph: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CitationDiagnosisInputs":
        return cls(
            readiness=dict(data.get("readiness") or {}),
            opportunity=dict(data.get("opportunity") or {}),
            competitor_profiles=[
                dict(item)
                for item in data.get("competitor_profiles") or []
                if isinstance(item, Mapping)
            ],
            entity_graph=dict(data.get("entity_graph") or {}),
        )


@dataclass(frozen=True, slots=True)
class CitationDiagnosisResult:
    citation_failures: list[CitationFailure]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)


class CompetitorAnalysisPlugin(StrategyPlugin):
    name = "competitor_analysis"

    def __init__(self, inputs: CompetitorAnalysisInputs | None = None) -> None:
        self.inputs = inputs

    def analyze(self, context: AnalysisContext) -> CompetitorAnalysisResult:
        inputs = self.inputs
        if inputs is None:
            payload = _extract_opportunity_payload(context)
            explicit = _extract_explicit_competitors(payload)
            serp_snapshots = _extract_serp_snapshots(payload)
            opportunity = payload.get("opportunity") if isinstance(payload.get("opportunity"), Mapping) else {}
            inputs = CompetitorAnalysisInputs(
                competitor_domains=explicit,
                serp_snapshots=serp_snapshots,
                opportunity=dict(opportunity or {}),
                site_domain=_extract_site_domain(context, payload.get("competitive", {}).get("site_domain") if isinstance(payload.get("competitive"), Mapping) else None),
                result_limit=int((opportunity or {}).get("result_limit", 5) or 5),
            )

        site_domain = _extract_site_domain(context, inputs.site_domain)
        explicit_domains = [
            _normalize_domain(domain)
            for domain in inputs.competitor_domains
            if _normalize_domain(domain)
        ]
        serp_snapshots = inputs.serp_snapshots or _extract_serp_snapshots(_extract_opportunity_payload(context))
        source_inventory, _ = _classify_serp_sources(
            site_domain=site_domain,
            explicit_domains=_dedupe(explicit_domains),
            serp_snapshots=serp_snapshots,
        )
        competitor_domains = list(source_inventory.get("competitor_owned") or [])
        profiles = _collect_competitor_profiles(
            site_domain=site_domain,
            competitor_domains=competitor_domains,
            serp_snapshots=serp_snapshots,
            result_limit=inputs.result_limit,
        )
        authority_gaps = _authority_gaps_from_inventory(source_inventory, profiles)

        context.competitor_profiles = profiles
        summary = {
            "competitor_count": len(profiles),
            "site_domain": site_domain,
            "inferred": not bool(explicit_domains),
            "site_owned_count": len(source_inventory.get("site_owned") or []),
            "earned_media_count": len(source_inventory.get("earned_media") or []),
            "authority_gap_count": len(authority_gaps),
            "discovery_note": (
                "No competitor-owned domains were confidently discovered; the sample set is dominated by third-party coverage."
                if not profiles and source_inventory.get("earned_media")
                else (
                    "No competitor-owned or earned-media sources were confidently discovered; the sample set is sparse and the category map is still incomplete."
                    if not profiles and not source_inventory.get("earned_media")
                    else (
                        "Competitor profiles were inferred from live SERP sources because no explicit competitor list was supplied."
                        if not explicit_domains
                        else "Competitor profiles blend explicit domains with live SERP observations."
                    )
                )
            ),
        }
        return CompetitorAnalysisResult(
            profiles=profiles,
            summary=summary,
            source_inventory=source_inventory,
            authority_gaps=authority_gaps,
        )


class EntityAnalysisPlugin(StrategyPlugin):
    name = "entity_analysis"

    def __init__(self, inputs: EntityAnalysisInputs | None = None) -> None:
        self.inputs = inputs

    def analyze(self, context: AnalysisContext) -> EntityAnalysisResult:
        inputs = self.inputs
        if inputs is None:
            inputs = EntityAnalysisInputs.from_dict(
                {
                    "page_data": _extract_page_data(context),
                    "brand_data": _extract_brand_data(context),
                }
            )

        page_data = inputs.page_data
        structured_data = page_data.get("structured_data") or context.site_snapshot.structured_data
        external_links = _link_urls(page_data.get("external_links") or context.site_snapshot.external_links)
        same_as: list[str] = []
        schema_types: set[str] = set()
        related_entities: list[str] = []

        for node in _json_ld_nodes(structured_data):
            node_types = _node_types(node)
            schema_types.update(node_types)
            if "Organization" in node_types:
                same_as.extend(_dedupe(node.get("sameAs")))
                if node.get("name"):
                    related_entities.append(_clean_text(node["name"]))

        same_as.extend(external_links)

        brand_data = inputs.brand_data
        wiki = ((brand_data or {}).get("platforms") or {}).get("wikipedia") or {}
        if wiki.get("has_wikipedia_page"):
            related_entities.append("Wikipedia")
        if wiki.get("has_wikidata_entry"):
            related_entities.append("Wikidata")

        unique_same_as = _dedupe(same_as)
        unique_related = _dedupe(related_entities)
        signals = []
        if schema_types:
            signals.append("schema")
        if unique_same_as:
            signals.append("same_as")
        if unique_related:
            signals.append("brand")
        if wiki.get("has_wikipedia_page"):
            signals.append("wikipedia")
        if wiki.get("has_wikidata_entry"):
            signals.append("wikidata")

        confidence = 0.35
        if schema_types:
            confidence += 0.2
        if unique_same_as:
            confidence += 0.2
        if unique_related:
            confidence += 0.1
        if wiki.get("has_wikidata_entry") or wiki.get("has_wikipedia_page"):
            confidence += 0.15
        confidence = round(min(confidence, 0.99), 2)

        entity_graph = EntityGraph(
            entity_name=_extract_brand_name(context, page_data),
            canonical_url=context.site_snapshot.canonical_url or context.site_snapshot.url,
            same_as=unique_same_as,
            related_entities=unique_related,
            attributes={
                "schema_types": sorted(schema_types),
                "signals": signals,
                "external_link_count": len(_dedupe(external_links)),
                "brand_signals": {
                    "has_wikipedia_page": bool(wiki.get("has_wikipedia_page")),
                    "has_wikidata_entry": bool(wiki.get("has_wikidata_entry")),
                },
            },
            confidence=confidence,
            metadata={
                "page_word_count": page_data.get("word_count"),
                "source": "site_snapshot_and_brand_data",
            },
        )

        context.entity_graph = entity_graph
        summary = {
            "same_as_count": len(unique_same_as),
            "related_entity_count": len(unique_related),
            "confidence": confidence,
        }
        return EntityAnalysisResult(entity_graph=entity_graph, summary=summary)


def _readiness_scores(context: AnalysisContext) -> dict[str, Any]:
    readiness = context.metadata.get("readiness")
    if isinstance(readiness, Mapping):
        geo_scores = readiness.get("geo_scores")
        if isinstance(geo_scores, Mapping):
            return dict(geo_scores.get("scores") or {})
    if context.report_model is not None:
        plugin = context.report_model.plugin_results.get("readiness")
        if isinstance(plugin, Mapping):
            geo_scores = plugin.get("geo_scores")
            if isinstance(geo_scores, Mapping):
                return dict(geo_scores.get("scores") or {})
    return {}


def _opportunity_items(context: AnalysisContext) -> list[dict[str, Any]]:
    payload: Mapping[str, Any] | None = None
    if context.report_model is not None:
        candidate = context.report_model.plugin_results.get("opportunity")
        if isinstance(candidate, Mapping):
            payload = candidate
    if payload is None:
        candidate = context.metadata.get("opportunity")
        if isinstance(candidate, Mapping):
            payload = candidate
    if payload is None:
        readiness = context.metadata.get("readiness")
        if isinstance(readiness, Mapping):
            candidate = readiness.get("opportunity")
            if isinstance(candidate, Mapping):
                payload = candidate
    if payload is None:
        return []
    items = payload.get("opportunities")
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, Mapping)]


class CitationDiagnosisPlugin(StrategyPlugin):
    name = "citation_diagnosis"

    def __init__(self, inputs: CitationDiagnosisInputs | None = None) -> None:
        self.inputs = inputs

    def analyze(self, context: AnalysisContext) -> CitationDiagnosisResult:
        inputs = self.inputs
        if inputs is None:
            entity_graph = context.entity_graph
            if not isinstance(entity_graph, EntityGraph) and context.report_model is not None:
                entity_graph = context.report_model.entity_graph
            inputs = CitationDiagnosisInputs(
                readiness=_readiness_scores(context),
                opportunity={"opportunities": _opportunity_items(context)},
                competitor_profiles=[
                    profile.to_dict()
                    for profile in (context.competitor_profiles or [])
                ],
                entity_graph=entity_graph.to_dict() if isinstance(entity_graph, EntityGraph) else {},
            )

        entity_graph = context.entity_graph
        if not isinstance(entity_graph, EntityGraph) and isinstance(inputs.entity_graph, Mapping):
            if inputs.entity_graph.get("entity_name"):
                entity_graph = EntityGraph.from_dict(inputs.entity_graph)
            else:
                entity_graph = None
        elif not isinstance(entity_graph, EntityGraph):
            entity_graph = None

        competitor_count = len(inputs.competitor_profiles)
        readiness_scores = inputs.readiness
        opportunity_items = inputs.opportunity.get("opportunities") or []
        failures: list[CitationFailure] = []

        for item in opportunity_items:
            if not isinstance(item, Mapping):
                continue
            mode = _citation_mode_for_item(
                opportunity=item,
                readiness_scores=readiness_scores,
                entity_graph=entity_graph,
                competitor_count=competitor_count,
            )
            if mode is None:
                continue

            query = _clean_text(item.get("query")) or "unknown query"
            evidence = []
            if item.get("site_visible") is False:
                evidence.append("The site does not appear in the sampled SERP set.")
            if item.get("opportunity_score") is not None:
                evidence.append(f"Opportunity score: {item.get('opportunity_score')}.")
            if readiness_scores.get("ai_citability") is not None:
                evidence.append(f"AI citability: {readiness_scores.get('ai_citability')}/100.")
            if entity_graph and entity_graph.same_as:
                evidence.append(f"Entity graph contains {len(entity_graph.same_as)} sameAs references.")
            elif entity_graph:
                evidence.append("Entity graph has no sameAs references.")
            if competitor_count:
                evidence.append(f"Competitive set includes {competitor_count} domains.")

            failures.append(
                CitationFailure(
                    query=query,
                    target_url=context.site_snapshot.canonical_url or context.site_snapshot.url,
                    failure_mode=mode,
                    evidence=_dedupe(evidence),
                    recommended_fix=(
                        "Refresh the page with recent proof points, timestamps, and visible update cues."
                        if mode == "freshness_gap"
                        else (
                            "Add explicit source attribution, cite primary references, and keep claims anchored to supporting evidence."
                            if mode == "attribution_gap"
                            else (
                                "Strengthen answer-first content, add supporting citations or schema, and align entity signals with the target query."
                                if mode == "non_visible_query"
                                else "Improve entity grounding with sameAs/profile links and citation-ready supporting evidence."
                            )
                        )
                    ),
                    metadata={
                        "opportunity_score": item.get("opportunity_score"),
                        "site_visible": item.get("site_visible"),
                        "label": item.get("label"),
                    },
                )
            )

        context.citation_failures = failures
        summary = {
            "failure_count": len(failures),
            "failure_modes": _dedupe(failure.failure_mode for failure in failures if failure.failure_mode),
        }
        return CitationDiagnosisResult(citation_failures=failures, summary=summary)
