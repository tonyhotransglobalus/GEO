from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..core import AnalysisContext, StrategyPlugin, serialize_model


def clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _list_of_strings(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None and str(item)]
    return [str(value)]


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


def _node_types(node: Mapping[str, Any]) -> set[str]:
    raw_type = node.get("@type")
    return {str(item) for item in _list_of_strings(raw_type)}


def _same_as_count(node: Mapping[str, Any]) -> int:
    return len(_list_of_strings(node.get("sameAs")))


def _has_schema_type(page_data: Mapping[str, Any], schema_type: str) -> bool:
    structured = page_data.get("structured_data") or []
    for node in _json_ld_nodes(structured):
        if schema_type in _node_types(node):
            return True
    return False


def count_social_links(page_data: dict[str, Any]) -> int:
    social_domains = (
        "facebook.com",
        "linkedin.com",
        "youtube.com",
        "instagram.com",
        "x.com",
        "twitter.com",
        "reddit.com",
        "wikipedia.org",
        "wikidata.org",
    )
    seen = set()
    for link in page_data.get("external_links", []):
        url = link.get("url", "")
        if any(domain in url for domain in social_domains):
            seen.add(url)
    return len(seen)


def score_brand_authority(page_data: dict[str, Any], brand_data: dict[str, Any]) -> int:
    score = 25
    score += min(count_social_links(page_data) * 4, 20)

    structured = page_data.get("structured_data") or []
    same_as_count = 0
    for node in _json_ld_nodes(structured):
        if "Organization" in _node_types(node):
            same_as_count += _same_as_count(node)
    score += min(same_as_count * 3, 15)

    wiki = ((brand_data or {}).get("platforms") or {}).get("wikipedia") or {}
    if wiki.get("has_wikipedia_page"):
        score += 20
    elif wiki.get("has_wikidata_entry"):
        score += 10

    return clamp_score(score)


def score_content_eeat(page_data: dict[str, Any]) -> int:
    import re

    score = 35
    word_count = page_data.get("word_count", 0)
    if word_count >= 500:
        score += 10
    elif word_count >= 300:
        score += 6

    text_content = page_data.get("text_content", "")
    if re.search(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b", text_content):
        score += 8
    if re.search(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b",
        text_content,
    ):
        score += 5

    meta_tags = page_data.get("meta_tags", {})
    if meta_tags.get("article:modified_time"):
        score += 7

    internal_links = page_data.get("internal_links", [])
    if any("/author/" in link.get("url", "") for link in internal_links):
        score += 10

    return clamp_score(score)


def score_technical(
    page_data: dict[str, Any],
    robots_data: dict[str, Any],
    sitemap_pages: list[str],
) -> int:
    from urllib.parse import urlparse

    score = 0
    if page_data.get("status_code") == 200:
        score += 30
    if page_data.get("has_ssr_content"):
        score += 20
    if robots_data.get("exists"):
        score += 15
    if sitemap_pages:
        score += 10
    if urlparse(page_data.get("url", "")).scheme == "https":
        score += 10

    security_headers = page_data.get("security_headers", {})
    if security_headers.get("Strict-Transport-Security"):
        score += 5

    missing_security = sum(1 for value in security_headers.values() if not value)
    score -= min(missing_security * 2, 10)

    return clamp_score(score)


def score_schema(page_data: dict[str, Any]) -> int:
    score = 20
    structured = page_data.get("structured_data") or []
    schema_types = set()
    same_as_count = 0

    for node in _json_ld_nodes(structured):
        node_types = _node_types(node)
        schema_types.update(node_types)
        if "Organization" in node_types:
            same_as_count += _same_as_count(node)

    for preferred in ("Organization", "WebSite", "WebPage", "BreadcrumbList"):
        if preferred in schema_types:
            score += 12

    score += min(same_as_count * 2, 12)
    return clamp_score(score)


def score_llms_guidance(llms_validation: Mapping[str, Any]) -> int:
    if not llms_validation.get("exists"):
        return 0

    has_issues = bool(llms_validation.get("issues"))
    if llms_validation.get("format_valid") and not has_issues:
        return 12
    if llms_validation.get("format_valid") or not has_issues:
        return 7
    return 4


def score_platform_optimization(
    page_data: dict[str, Any],
    llms_validation: dict[str, Any],
    brand_data: dict[str, Any],
) -> int:
    score = 30
    if (page_data.get("meta_tags") or {}).get("article:modified_time"):
        score += 8
    score += score_llms_guidance(llms_validation)
    if count_social_links(page_data) >= 4:
        score += 10

    wiki = ((brand_data or {}).get("platforms") or {}).get("wikipedia") or {}
    if wiki.get("has_wikipedia_page") or wiki.get("has_wikidata_entry"):
        score += 10

    return clamp_score(score)


def score_geo_audit(
    page_data: dict[str, Any],
    robots_data: dict[str, Any],
    llms_validation: dict[str, Any],
    sitemap_pages: list[str],
    citability_data: dict[str, Any],
    brand_data: dict[str, Any],
) -> dict[str, Any]:
    ai_citability = clamp_score(citability_data.get("average_citability_score", 0))
    brand_authority = score_brand_authority(page_data, brand_data)
    content_eeat = score_content_eeat(page_data)
    technical = score_technical(page_data, robots_data, sitemap_pages)
    schema = score_schema(page_data)
    platform_optimization = score_platform_optimization(
        page_data, llms_validation, brand_data
    )

    geo_score = clamp_score(
        (ai_citability * 0.25)
        + (brand_authority * 0.20)
        + (content_eeat * 0.20)
        + (technical * 0.15)
        + (schema * 0.10)
        + (platform_optimization * 0.10)
    )

    return {
        "geo_score": geo_score,
        "scores": {
            "ai_citability": ai_citability,
            "brand_authority": brand_authority,
            "content_eeat": content_eeat,
            "technical": technical,
            "schema": schema,
            "platform_optimization": platform_optimization,
        },
    }


def build_platform_scores(
    scores: dict[str, Any],
    page_data: Mapping[str, Any],
) -> dict[str, int]:
    faq_bonus = 5 if _has_schema_type(page_data, "FAQPage") else 0

    return {
        "Google AI Overviews": clamp_score(
            (scores["content_eeat"] * 0.35)
            + (scores["schema"] * 0.30)
            + (scores["technical"] * 0.20)
            + (scores["platform_optimization"] * 0.15)
            + faq_bonus
        ),
        "ChatGPT": clamp_score(
            (scores["ai_citability"] * 0.35)
            + (scores["brand_authority"] * 0.25)
            + (scores["technical"] * 0.20)
            + (scores["content_eeat"] * 0.20)
        ),
        "Perplexity": clamp_score(
            (scores["ai_citability"] * 0.35)
            + (scores["technical"] * 0.25)
            + (scores["schema"] * 0.15)
            + (scores["platform_optimization"] * 0.25)
            + faq_bonus
        ),
        "Gemini": clamp_score(
            (scores["schema"] * 0.30)
            + (scores["content_eeat"] * 0.25)
            + (scores["technical"] * 0.20)
            + (scores["brand_authority"] * 0.10)
            + (scores["platform_optimization"] * 0.15)
        ),
        "Bing Copilot": clamp_score(
            (scores["technical"] * 0.35)
            + (scores["brand_authority"] * 0.20)
            + (scores["content_eeat"] * 0.15)
            + (scores["ai_citability"] * 0.15)
            + (scores["platform_optimization"] * 0.15)
        ),
    }

@dataclass(frozen=True, slots=True)
class ReadinessInputs:
    page_data: dict[str, Any]
    robots_data: dict[str, Any]
    llms_validation: dict[str, Any]
    llms_live: dict[str, Any]
    sitemap_pages: list[str] = field(default_factory=list)
    citability_data: dict[str, Any] = field(default_factory=dict)
    brand_data: dict[str, Any] = field(default_factory=dict)
    rescience_pass: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReadinessInputs":
        return cls(
            page_data=dict(data.get("page_data") or {}),
            robots_data=dict(data.get("robots_data") or {}),
            llms_validation=dict(data.get("llms_validation") or {}),
            llms_live=dict(data.get("llms_live") or {}),
            sitemap_pages=list(data.get("sitemap_pages") or []),
            citability_data=dict(data.get("citability_data") or {}),
            brand_data=dict(data.get("brand_data") or {}),
            rescience_pass=dict(data.get("rescience_pass") or {}),
        )


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    inputs: ReadinessInputs
    geo_scores: dict[str, Any]
    platforms: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)


class ReadinessPlugin(StrategyPlugin):
    name = "readiness"

    def __init__(self, inputs: ReadinessInputs | None = None) -> None:
        self.inputs = inputs

    def analyze(self, context: AnalysisContext) -> ReadinessResult:
        inputs = self.inputs
        if inputs is None:
            metadata_inputs = context.metadata.get("readiness")
            if not isinstance(metadata_inputs, Mapping):
                raise ValueError(
                    "Readiness inputs must be provided in context.metadata['readiness'] or via the plugin constructor."
                )
            inputs = ReadinessInputs.from_dict(metadata_inputs)

        geo_scores = score_geo_audit(
            page_data=inputs.page_data,
            robots_data=inputs.robots_data,
            llms_validation=inputs.llms_validation,
            sitemap_pages=inputs.sitemap_pages,
            citability_data=inputs.citability_data,
            brand_data=inputs.brand_data,
        )
        platforms = build_platform_scores(geo_scores["scores"], inputs.page_data)
        return ReadinessResult(
            inputs=inputs,
            geo_scores=geo_scores,
            platforms=platforms,
        )
