from __future__ import annotations

from dataclasses import dataclass, field, replace
import re
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qs, unquote, urlsplit

import requests
from bs4 import BeautifulSoup

from ..core import AnalysisContext, QueryCluster, StrategyPlugin, serialize_model


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

DUCKDUCKGO_AUTOCOMPLETE_URL = "https://duckduckgo.com/ac/"
DUCKDUCKGO_HTML_URL = "https://html.duckduckgo.com/html/"

SERVICE_LINE_CANONICALS = (
    ("life insurance", ("life insurance",)),
    ("annuities", ("annuities", "annuity")),
    ("mortgage financing", ("mortgage financing",)),
    ("real estate", ("real estate",)),
    ("asset management", ("asset management",)),
    ("health insurance", ("health insurance",)),
    (
        "property and casualty insurance",
        (
            "property and casualty insurance",
            "property/casualty insurance",
            "property casualty insurance",
        ),
    ),
)

GENERIC_QUERY_PHRASES = {
    "business services",
    "service line",
    "service lines",
    "service line overview",
    "services",
    "our services",
    "overview",
}


def _clean_text(value: Any) -> str:
    return str(value).strip()


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for item in items:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(cleaned)
    return results


def _slugify(value: str) -> str:
    slug = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            slug.append(char)
            previous_dash = False
        elif not previous_dash:
            slug.append("-")
            previous_dash = True
    return "".join(slug).strip("-") or "opportunity"


def _split_title_phrases(title: str | None) -> list[str]:
    if not title:
        return []
    parts = re.split(r"\s*[|:–—-]\s*", title)
    return _dedupe(part for part in parts if part)


def _normalized_phrase(value: str | None) -> str:
    if not value:
        return ""
    tokens = re.findall(r"[a-z0-9]+", _clean_text(value).lower())
    return " ".join(tokens)


def _is_blob_like(value: str | None) -> bool:
    cleaned = _clean_text(value)
    if not cleaned:
        return True
    normalized_tokens = _normalized_phrase(cleaned).split()
    return len(cleaned) > 72 or len(normalized_tokens) > 6


def _canonical_service_line_phrase(text: str | None) -> str:
    normalized = _normalized_phrase(text)
    if not normalized:
        return ""
    for canonical, variants in SERVICE_LINE_CANONICALS:
        for variant in variants:
            if _normalized_phrase(variant) in normalized:
                return canonical
    return ""


def _query_phrase_from_text(text: str | None) -> str:
    cleaned = _clean_text(text)
    if not cleaned or _is_blob_like(cleaned):
        return ""
    canonical = _canonical_service_line_phrase(cleaned)
    if canonical:
        return canonical
    return re.sub(r"\s+", " ", cleaned)


def _is_generic_topic(phrase: str | None) -> bool:
    normalized = _normalized_phrase(phrase)
    if not normalized:
        return True
    return normalized in GENERIC_QUERY_PHRASES or normalized.startswith("service line")


def _primary_topic_phrase(
    seed_topic: str,
    suggestions: Iterable[str],
    serp_results: Iterable[Mapping[str, Any]],
) -> str:
    seed_phrase = _query_phrase_from_text(seed_topic)
    if seed_phrase and not _is_generic_topic(seed_phrase):
        return seed_phrase

    candidate_texts = [
        *suggestions,
        *(
            str(result.get("title", ""))
            for result in serp_results
            if isinstance(result, Mapping)
        ),
    ]

    for candidate in candidate_texts:
        phrase = _query_phrase_from_text(candidate)
        if phrase and _canonical_service_line_phrase(candidate):
            return phrase

    for candidate in candidate_texts:
        phrase = _query_phrase_from_text(candidate)
        if phrase and not _is_generic_topic(phrase):
            return phrase

    return seed_phrase or "opportunity"


def _normalize_seed_topic(seed_topic: str) -> str:
    cleaned = _clean_text(seed_topic)
    if not cleaned:
        return ""
    canonical = _canonical_service_line_phrase(cleaned)
    if canonical:
        return canonical
    if _is_blob_like(cleaned):
        return ""
    return cleaned


def _seed_topic_origin_map(seed_topics: Iterable[str]) -> dict[str, str]:
    origin_map: dict[str, str] = {}
    for raw_seed_topic in seed_topics:
        normalized_seed_topic = _normalize_seed_topic(raw_seed_topic)
        if normalized_seed_topic and normalized_seed_topic not in origin_map:
            origin_map[normalized_seed_topic] = raw_seed_topic
    return origin_map


def _query_phrases_for_output(
    seed_topic: str,
    suggestions: Iterable[str],
    serp_results: Iterable[Mapping[str, Any]],
    primary_topic: str,
) -> list[str]:
    candidates = [primary_topic, *suggestions]
    candidates.extend(
        str(result.get("title", ""))
        for result in serp_results
        if isinstance(result, Mapping)
    )
    seed_phrase = _query_phrase_from_text(seed_topic)
    if seed_phrase:
        candidates.append(seed_phrase)
    return _dedupe(
        phrase
        for phrase in (_query_phrase_from_text(candidate) for candidate in candidates)
        if phrase
    )


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


def _infer_intent(query: str) -> str:
    normalized = query.lower()
    if any(token in normalized for token in (" price", " pricing", " cost", " quote", " buy", " hire ")):
        return "transactional"
    if any(token in normalized for token in ("best", "top", "vs", "versus", "alternative", "compare", "comparison")):
        return "commercial"
    if any(token in normalized for token in ("near me", "local", "service area")):
        return "local"
    if any(token in normalized for token in ("how", "what", "why", "guide", "checklist", "examples", "template", "tips")):
        return "informational"
    return "informational"


def _domain_tokens_from_url(value: str | None) -> list[str]:
    if not value:
        return []
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path).lower().removeprefix("www.")
    tokens = [
        token
        for token in re.split(r"[.\-]+", host)
        if token and token not in {"com", "net", "org", "co", "io", "app", "www"}
    ]
    return _dedupe(tokens)


def _priority_from_score(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _score_opportunity(
    *,
    site_visible: bool,
    search_intent: str,
    suggestion_count: int,
    competitor_hits: int,
) -> int:
    score = 35
    if search_intent == "transactional":
        score += 15
    elif search_intent == "commercial":
        score += 20
    elif search_intent == "local":
        score += 18
    else:
        score += 10

    if site_visible:
        score -= 15
    else:
        score += 25

    score += min(suggestion_count * 3, 12)
    score += min(competitor_hits * 4, 12)
    return max(0, min(100, score))


def _extract_target_url(href: str) -> str:
    if not href:
        return ""
    parsed = urlsplit(href)
    query = parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return unquote(query["uddg"][0])
    return href


def _parse_suggestions(payload: Any) -> list[str]:
    suggestions: list[str] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, Mapping):
                for key in ("phrase", "suggestion", "query", "text"):
                    if item.get(key):
                        suggestions.append(str(item[key]))
                        break
            elif item:
                suggestions.append(str(item))
        return _dedupe(suggestions)
    if isinstance(payload, Mapping):
        for key in ("suggestions", "results", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return _parse_suggestions(value)
    return []


def _resolve_seed_topics_from_context(context: AnalysisContext) -> list[str]:
    metadata = context.metadata.get("opportunity")
    if isinstance(metadata, Mapping):
        seed_topics = _dedupe(metadata.get("seed_topics") or [])
        if seed_topics:
            return seed_topics

    if isinstance(context.metadata.get("seed_topics"), list):
        seed_topics = _dedupe(context.metadata.get("seed_topics") or [])
        if seed_topics:
            return seed_topics

    candidates = []
    for value in (
        context.metadata.get("site_name"),
        context.metadata.get("brand_name"),
    ):
        if value:
            candidates.append(str(value))

    candidates.extend(_split_title_phrases(context.site_snapshot.title))
    if candidates:
        return _dedupe(candidates)

    fallback_url = context.site_snapshot.canonical_url or context.site_snapshot.url
    return _domain_tokens_from_url(fallback_url) or ["site"]


def _effective_inputs(
    inputs: "OpportunityInputs",
    context: AnalysisContext,
) -> "OpportunityInputs":
    site_domain = inputs.site_domain or _normalize_domain(
        context.site_snapshot.canonical_url or context.site_snapshot.url
    )
    competitor_domains = sorted(
        {
            _normalize_domain(domain)
            for domain in inputs.competitor_domains
            if _normalize_domain(domain)
        }
    )
    seed_topics = inputs.seed_topics or _resolve_seed_topics_from_context(context)
    normalized_seed_topics: list[str] = []
    for seed_topic in seed_topics:
        normalized_seed_topic = _normalize_seed_topic(seed_topic)
        if normalized_seed_topic:
            normalized_seed_topics.append(normalized_seed_topic)
    seed_topics = _dedupe(normalized_seed_topics)
    if not seed_topics:
        seed_topics = _resolve_seed_topics_from_context(context)
    return replace(
        inputs,
        seed_topics=seed_topics,
        competitor_domains=competitor_domains,
        site_domain=site_domain or None,
    )


def fetch_keyword_suggestions(
    query: str,
    locale: str = "en-us",
    timeout: int = 15,
) -> list[str]:
    response = requests.get(
        DUCKDUCKGO_AUTOCOMPLETE_URL,
        params={"q": query, "kl": locale},
        headers=DEFAULT_HEADERS,
        timeout=timeout,
    )
    try:
        payload = response.json()
    except Exception:
        return []
    return _parse_suggestions(payload)


@dataclass(frozen=True, slots=True)
class SerpResult:
    query: str
    rank: int
    title: str
    url: str
    domain: str
    snippet: str | None = None
    source: str = "duckduckgo"

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)


def fetch_serp_snapshot(
    query: str,
    locale: str = "en-us",
    result_limit: int = 5,
    timeout: int = 15,
) -> list[SerpResult]:
    response = requests.get(
        DUCKDUCKGO_HTML_URL,
        params={"q": query, "kl": locale},
        headers=DEFAULT_HEADERS,
        timeout=timeout,
    )
    soup = BeautifulSoup(response.text, "html.parser")
    results: list[SerpResult] = []

    for block in soup.select("div.result, article.result"):
        title_link = block.select_one("a.result__a, a[data-testid='result-title-a'], h2 a")
        if title_link is None:
            continue

        url = _extract_target_url(str(title_link.get("href", "")))
        if not url:
            continue

        parsed = urlsplit(url)
        domain = parsed.netloc.lower().removeprefix("www.")
        if not domain:
            continue

        snippet_node = block.select_one(".result__snippet, .result__body, a.result__snippet")
        snippet = None
        if snippet_node is not None:
            snippet = snippet_node.get_text(" ", strip=True)

        results.append(
            SerpResult(
                query=query,
                rank=len(results) + 1,
                title=title_link.get_text(" ", strip=True),
                url=url,
                domain=domain,
                snippet=snippet,
            )
        )

        if len(results) >= result_limit:
            break

    return results


@dataclass(frozen=True, slots=True)
class OpportunityInputs:
    seed_topics: list[str] = field(default_factory=list)
    competitor_domains: list[str] = field(default_factory=list)
    result_limit: int = 5
    locale: str = "en-us"
    site_domain: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OpportunityInputs":
        result_limit = data.get("result_limit", 5)
        try:
            result_limit_int = max(1, int(result_limit))
        except (TypeError, ValueError):
            result_limit_int = 5
        return cls(
            seed_topics=_dedupe(data.get("seed_topics") or []),
            competitor_domains=[
                _normalize_domain(item) for item in data.get("competitor_domains") or []
            ],
            result_limit=result_limit_int,
            locale=str(data.get("locale") or "en-us"),
            site_domain=_normalize_domain(data.get("site_domain")),
        )


@dataclass(frozen=True, slots=True)
class KeywordResearchResult:
    inputs: OpportunityInputs
    seed_topics: list[str]
    keyword_suggestions: dict[str, list[str]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)


@dataclass(frozen=True, slots=True)
class SerpAnalysisResult:
    inputs: OpportunityInputs
    seed_topics: list[str]
    serp_snapshots: dict[str, list[dict[str, Any]]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)


@dataclass(frozen=True, slots=True)
class OpportunityResult:
    inputs: OpportunityInputs
    seed_topics: list[str]
    keyword_suggestions: dict[str, list[str]]
    serp_snapshots: dict[str, list[dict[str, Any]]]
    query_clusters: list[QueryCluster]
    opportunities: list[dict[str, Any]]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)


def _derive_seed_topics(context: AnalysisContext) -> list[str]:
    candidates = [
        context.metadata.get("site_name"),
        context.metadata.get("brand_name"),
        context.site_snapshot.title,
        context.site_snapshot.canonical_url,
        context.site_snapshot.url,
    ]

    seeds: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        text = _clean_text(candidate)
        if text:
            seeds.append(text)

    return _dedupe(seeds)


def _keyword_results_from_context(
    context: AnalysisContext,
    inputs: OpportunityInputs,
) -> tuple[OpportunityInputs, list[str], dict[str, list[str]]]:
    effective_inputs = _effective_inputs(inputs, context)
    seed_topics = effective_inputs.seed_topics[: effective_inputs.result_limit]

    keyword_suggestions: dict[str, list[str]] = {}
    for seed_topic in seed_topics:
        keyword_suggestions[seed_topic] = fetch_keyword_suggestions(
            seed_topic,
            locale=effective_inputs.locale,
        )[: effective_inputs.result_limit]

    return effective_inputs, seed_topics, keyword_suggestions


def _serp_results_from_context(
    context: AnalysisContext,
    inputs: OpportunityInputs,
    seed_topics: list[str],
) -> tuple[OpportunityInputs, dict[str, list[dict[str, Any]]]]:
    effective_inputs = _effective_inputs(inputs, context)
    serp_snapshots: dict[str, list[dict[str, Any]]] = {}
    for seed_topic in seed_topics[: effective_inputs.result_limit]:
        serp_snapshots[seed_topic] = [
            result.to_dict()
            for result in fetch_serp_snapshot(
                seed_topic,
                locale=effective_inputs.locale,
                result_limit=effective_inputs.result_limit,
            )
        ]
    return effective_inputs, serp_snapshots


class KeywordResearchPlugin(StrategyPlugin):
    name = "keyword_research"

    def __init__(self, inputs: OpportunityInputs | None = None) -> None:
        self.inputs = inputs

    def analyze(self, context: AnalysisContext) -> KeywordResearchResult:
        inputs = self.inputs
        if inputs is None:
            metadata_inputs = context.metadata.get("opportunity")
            if isinstance(metadata_inputs, Mapping):
                inputs = OpportunityInputs.from_dict(metadata_inputs)
            else:
                inputs = OpportunityInputs()

        effective_inputs, seed_topics, keyword_suggestions = _keyword_results_from_context(
            context, inputs
        )
        summary = {
            "seed_topic_count": len(seed_topics),
            "suggestion_count": sum(len(items) for items in keyword_suggestions.values()),
        }
        return KeywordResearchResult(
            inputs=effective_inputs,
            seed_topics=seed_topics,
            keyword_suggestions=keyword_suggestions,
            summary=summary,
        )


class SerpAnalysisPlugin(StrategyPlugin):
    name = "serp_analysis"

    def __init__(self, inputs: OpportunityInputs | None = None) -> None:
        self.inputs = inputs

    def analyze(self, context: AnalysisContext) -> SerpAnalysisResult:
        inputs = self.inputs
        if inputs is None:
            metadata_inputs = context.metadata.get("opportunity")
            if isinstance(metadata_inputs, Mapping):
                inputs = OpportunityInputs.from_dict(metadata_inputs)
            else:
                inputs = OpportunityInputs()

        effective_inputs = _effective_inputs(inputs, context)
        seed_topics = list(effective_inputs.seed_topics)

        if context.report_model:
            keyword_data = context.report_model.plugin_results.get("keyword_research")
            if isinstance(keyword_data, Mapping):
                resolved = _dedupe(keyword_data.get("seed_topics") or [])
                if resolved and not seed_topics:
                    seed_topics = resolved
        if not seed_topics:
            seed_topics = _resolve_seed_topics_from_context(context)

        effective_inputs, serp_snapshots = _serp_results_from_context(
            context, effective_inputs, seed_topics
        )
        summary = {
            "seed_topic_count": len(seed_topics),
            "result_count": sum(len(items) for items in serp_snapshots.values()),
        }
        return SerpAnalysisResult(
            inputs=effective_inputs,
            seed_topics=seed_topics,
            serp_snapshots=serp_snapshots,
            summary=summary,
        )


class OpportunityPlugin(StrategyPlugin):
    name = "opportunity"

    def __init__(self, inputs: OpportunityInputs | None = None) -> None:
        self.inputs = inputs

    def analyze(self, context: AnalysisContext) -> OpportunityResult:
        inputs = self.inputs
        if inputs is None:
            metadata_inputs = context.metadata.get("opportunity")
            if isinstance(metadata_inputs, Mapping):
                inputs = OpportunityInputs.from_dict(metadata_inputs)
            else:
                inputs = OpportunityInputs()

        seed_topic_origin_map = _seed_topic_origin_map(
            inputs.seed_topics or _resolve_seed_topics_from_context(context)
        )

        if context.report_model is None:
            plugin_results: Mapping[str, Any] = {}
        else:
            plugin_results = context.report_model.plugin_results

        keyword_data = plugin_results.get("keyword_research")
        serp_data = plugin_results.get("serp_analysis")

        effective_inputs = _effective_inputs(inputs, context)
        seed_topics = list(effective_inputs.seed_topics)

        keyword_suggestions: dict[str, list[str]] = {}
        if isinstance(keyword_data, Mapping):
            seed_topics = _dedupe(keyword_data.get("seed_topics") or seed_topics)
            keyword_suggestions = {
                str(key): _dedupe(value)
                for key, value in (keyword_data.get("keyword_suggestions") or {}).items()
                if key
            }
        if not keyword_suggestions:
            effective_inputs, seed_topics, keyword_suggestions = _keyword_results_from_context(
                context, effective_inputs
            )

        serp_snapshots: dict[str, list[dict[str, Any]]] = {}
        if isinstance(serp_data, Mapping):
            seed_topics = _dedupe(serp_data.get("seed_topics") or seed_topics)
            serp_snapshots = {
                str(key): [dict(item) for item in value]
                for key, value in (serp_data.get("serp_snapshots") or {}).items()
                if key
            }
        if not serp_snapshots:
            effective_inputs, serp_snapshots = _serp_results_from_context(
                context, effective_inputs, seed_topics
            )

        opportunities: list[dict[str, Any]] = []
        clusters: list[QueryCluster] = []

        site_domain = effective_inputs.site_domain or _normalize_domain(
            context.site_snapshot.canonical_url or context.site_snapshot.url
        )
        competitor_domains = {
            _normalize_domain(domain)
            for domain in effective_inputs.competitor_domains
            if _normalize_domain(domain)
        }

        for seed_topic in seed_topics[: effective_inputs.result_limit]:
            raw_seed_topic = seed_topic_origin_map.get(seed_topic, seed_topic)
            suggestions = keyword_suggestions.get(seed_topic, [])
            serp_results = serp_snapshots.get(seed_topic, [])
            primary_topic = _primary_topic_phrase(seed_topic, suggestions, serp_results)
            top_domains = [
                str(result.get("domain", ""))
                for result in serp_results
                if isinstance(result, Mapping)
            ]
            site_visible = any(
                _domain_matches(domain, site_domain) for domain in top_domains
            )
            competitor_hits = sum(
                1 for domain in top_domains if any(_domain_matches(domain, item) for item in competitor_domains)
            )
            search_intent = _infer_intent(seed_topic)
            opportunity_score = _score_opportunity(
                site_visible=site_visible,
                search_intent=search_intent,
                suggestion_count=len(suggestions),
                competitor_hits=competitor_hits,
            )
            label = _priority_from_score(opportunity_score)
            cluster_label = _slugify(primary_topic)

            cluster_queries = _query_phrases_for_output(
                seed_topic,
                suggestions,
                serp_results,
                primary_topic,
            )
            cluster = QueryCluster(
                label=cluster_label,
                queries=cluster_queries,
                search_intent=search_intent,
                priority=label,
                related_entities=_dedupe(
                    [
                        *sorted(competitor_domains),
                        *top_domains,
                    ]
                ),
                metadata={
                    "seed_topic": primary_topic,
                    "seed_topic_raw": raw_seed_topic,
                    "site_domain": site_domain,
                    "site_visible": site_visible,
                    "opportunity_score": opportunity_score,
                    "label": label,
                    "keyword_suggestions": suggestions[: effective_inputs.result_limit],
                    "serp_result_count": len(serp_results),
                    "top_domains": top_domains,
                },
            )
            clusters.append(cluster)
            context.query_clusters.append(cluster)
            opportunities.append(
                {
                    "query": primary_topic,
                    "seed_topic_raw": raw_seed_topic,
                    "search_intent": search_intent,
                    "site_visible": site_visible,
                    "opportunity_score": opportunity_score,
                    "label": label,
                    "keyword_suggestions": suggestions[: effective_inputs.result_limit],
                    "serp_result_count": len(serp_results),
                    "competitor_hits": competitor_hits,
                    "site_domain": site_domain,
                    "top_domains": top_domains,
                }
            )

        summary = {
            "cluster_count": len(clusters),
            "seed_topic_count": len(seed_topics),
            "high_opportunity_count": sum(
                1 for item in opportunities if item["label"] == "high"
            ),
            "site_visible_queries": sum(1 for item in opportunities if item["site_visible"]),
        }

        return OpportunityResult(
            inputs=effective_inputs,
            seed_topics=seed_topics,
            keyword_suggestions=keyword_suggestions,
            serp_snapshots=serp_snapshots,
            query_clusters=clusters,
            opportunities=opportunities,
            summary=summary,
        )
