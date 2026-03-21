from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields, is_dataclass, replace
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

ENTITY_GRAPH_UNSET = object()


def _serialize_value(value: Any) -> Any:
    if is_dataclass(value):
        return {field_info.name: _serialize_value(getattr(value, field_info.name)) for field_info in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(item) for item in value]
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def serialize_model(model: Any) -> Any:
    return _serialize_value(model)


def serialize_report_model(model: Any) -> Any:
    return serialize_model(model)


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    return [dict(item) for item in value]


def _list_of_strings(value: Any) -> list[str]:
    if not value:
        return []
    return [str(item) for item in value]


def _derive_brand_name(snapshot: SiteSnapshot) -> str:
    if snapshot.title:
        return snapshot.title.strip()

    parsed = urlsplit(snapshot.canonical_url or snapshot.url)
    host = parsed.netloc or parsed.path
    return host.replace("www.", "") or snapshot.url


EVIDENCE_SOURCE_TAGS: dict[str, str] = {
    "academic": "Academic",
    "official": "Official",
    "live_site": "Live Site",
    "live_serp": "Live SERP",
    "heuristic": "Heuristic",
}


def _normalize_evidence_source_type(source_type: str | None) -> str:
    if not source_type:
        return ""
    return str(source_type).strip().lower().replace("-", "_").replace(" ", "_")


def evidence_source_tag(source_type: str | None) -> str | None:
    normalized = _normalize_evidence_source_type(source_type)
    if not normalized:
        return None
    return EVIDENCE_SOURCE_TAGS.get(
        normalized,
        normalized.replace("_", " ").title(),
    )


@dataclass(frozen=True, slots=True)
class SiteSnapshot:
    url: str
    title: str | None = None
    canonical_url: str | None = None
    fetched_at: str | None = None
    language: str | None = None
    word_count: int | None = None
    headings: list[str] = field(default_factory=list)
    structured_data: list[dict[str, Any]] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    text_excerpt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SiteSnapshot":
        return cls(
            url=str(data["url"]),
            title=data.get("title"),
            canonical_url=data.get("canonical_url"),
            fetched_at=data.get("fetched_at"),
            language=data.get("language"),
            word_count=data.get("word_count"),
            headings=_list_of_strings(data.get("headings")),
            structured_data=_list_of_dicts(data.get("structured_data")),
            internal_links=_list_of_strings(data.get("internal_links")),
            external_links=_list_of_strings(data.get("external_links")),
            text_excerpt=data.get("text_excerpt"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class QueryCluster:
    label: str
    queries: list[str] = field(default_factory=list)
    search_intent: str | None = None
    priority: str | None = None
    related_entities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "QueryCluster":
        return cls(
            label=str(data["label"]),
            queries=_list_of_strings(data.get("queries")),
            search_intent=data.get("search_intent"),
            priority=data.get("priority"),
            related_entities=_list_of_strings(data.get("related_entities")),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class CompetitorProfile:
    name: str
    domain: str | None = None
    source_urls: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CompetitorProfile":
        return cls(
            name=str(data["name"]),
            domain=data.get("domain"),
            source_urls=_list_of_strings(data.get("source_urls")),
            strengths=_list_of_strings(data.get("strengths")),
            weaknesses=_list_of_strings(data.get("weaknesses")),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class EntityGraph:
    entity_name: str
    canonical_url: str | None = None
    same_as: list[str] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EntityGraph":
        return cls(
            entity_name=str(data["entity_name"]),
            canonical_url=data.get("canonical_url"),
            same_as=_list_of_strings(data.get("same_as")),
            related_entities=_list_of_strings(data.get("related_entities")),
            attributes=dict(data.get("attributes") or {}),
            confidence=data.get("confidence"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class CitationFailure:
    query: str
    target_url: str | None = None
    failure_mode: str | None = None
    evidence: list[str] = field(default_factory=list)
    recommended_fix: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CitationFailure":
        return cls(
            query=str(data["query"]),
            target_url=data.get("target_url"),
            failure_mode=data.get("failure_mode"),
            evidence=_list_of_strings(data.get("evidence")),
            recommended_fix=data.get("recommended_fix"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class EvidenceEntry:
    label: str
    source_type: str
    evidence: list[str] = field(default_factory=list)
    source_tag: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceEntry":
        source_type = str(data["source_type"])
        source_tag = data.get("source_tag") or evidence_source_tag(source_type)
        return cls(
            label=str(data["label"]),
            source_type=source_type,
            evidence=_list_of_strings(data.get("evidence")),
            source_tag=source_tag,
            url=data.get("url"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class ReportModel:
    brand_name: str
    site_snapshot: SiteSnapshot
    query_clusters: list[QueryCluster] = field(default_factory=list)
    competitor_profiles: list[CompetitorProfile] = field(default_factory=list)
    entity_graph: EntityGraph | None = None
    citation_failures: list[CitationFailure] = field(default_factory=list)
    plugin_results: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    generated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return serialize_model(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReportModel":
        entity_graph_data = data.get("entity_graph")
        return cls(
            brand_name=str(data["brand_name"]),
            site_snapshot=SiteSnapshot.from_dict(data["site_snapshot"]),
            query_clusters=[
                QueryCluster.from_dict(item)
                for item in data.get("query_clusters", [])
            ],
            competitor_profiles=[
                CompetitorProfile.from_dict(item)
                for item in data.get("competitor_profiles", [])
            ],
            entity_graph=(
                EntityGraph.from_dict(entity_graph_data)
                if isinstance(entity_graph_data, Mapping)
                else None
            ),
            citation_failures=[
                CitationFailure.from_dict(item)
                for item in data.get("citation_failures", [])
            ],
            plugin_results=dict(data.get("plugin_results") or {}),
            metadata=dict(data.get("metadata") or {}),
            generated_at=data.get("generated_at"),
        )


@dataclass
class AnalysisContext:
    site_snapshot: SiteSnapshot
    query_clusters: list[QueryCluster] = field(default_factory=list)
    competitor_profiles: list[CompetitorProfile] = field(default_factory=list)
    entity_graph: EntityGraph | None | object = field(default=ENTITY_GRAPH_UNSET)
    citation_failures: list[CitationFailure] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    generative_search_first: bool = True
    open_source_first: bool = True
    report_model: ReportModel | None = None

    def __post_init__(self) -> None:
        if self.report_model is None:
            entity_graph = (
                None if self.entity_graph is ENTITY_GRAPH_UNSET else self.entity_graph
            )
            self.report_model = ReportModel(
                brand_name=_derive_brand_name(self.site_snapshot),
                site_snapshot=self.site_snapshot,
                query_clusters=list(self.query_clusters),
                competitor_profiles=list(self.competitor_profiles),
                entity_graph=entity_graph if isinstance(entity_graph, EntityGraph) else None,
                citation_failures=list(self.citation_failures),
                metadata=dict(self.metadata),
            )


class StrategyPlugin(ABC):
    name: str

    @abstractmethod
    def analyze(self, context: AnalysisContext) -> Mapping[str, Any] | Any | None:
        raise NotImplementedError


class StrategyOrchestrator:
    def __init__(self, plugins: Iterable[StrategyPlugin] | None = None) -> None:
        self._plugins: list[StrategyPlugin] = []
        if plugins:
            for plugin in plugins:
                self.register_plugin(plugin)

    @property
    def plugins(self) -> tuple[StrategyPlugin, ...]:
        return tuple(self._plugins)

    def register_plugin(self, plugin: StrategyPlugin) -> "StrategyOrchestrator":
        self._validate_plugin(plugin)
        if any(existing.name == plugin.name for existing in self._plugins):
            raise ValueError(f"Plugin '{plugin.name}' is already registered.")
        self._plugins.append(plugin)
        return self

    def execute(self, context: AnalysisContext) -> ReportModel:
        report = context.report_model
        if report is None:
            report = ReportModel(
                brand_name=_derive_brand_name(context.site_snapshot),
                site_snapshot=context.site_snapshot,
            )

        report = self._compose_report(report, context, {})

        plugin_results: dict[str, Any] = {}

        for plugin in self._plugins:
            plugin_results[plugin.name] = self._normalize_plugin_result(
                plugin.analyze(context)
            )
            report = self._compose_report(report, context, plugin_results)

        context.report_model = report
        return report

    @staticmethod
    def _normalize_plugin_result(result: Mapping[str, Any] | Any | None) -> Any:
        if result is None:
            return {}
        if isinstance(result, Mapping):
            return serialize_model(result)
        return serialize_model(result)

    @staticmethod
    def _validate_plugin(plugin: Any) -> None:
        if not isinstance(plugin, StrategyPlugin):
            raise TypeError(
                "plugin must be a StrategyPlugin instance with a callable analyze() method"
            )
        name = getattr(plugin, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise TypeError("plugin.name must be a non-empty string")
        analyze = getattr(plugin, "analyze", None)
        if not callable(analyze):
            raise TypeError("plugin must define a callable analyze() method")

    @staticmethod
    def _compose_report(
        report: ReportModel,
        context: AnalysisContext,
        plugin_results: dict[str, Any],
    ) -> ReportModel:
        entity_graph = (
            report.entity_graph
            if context.entity_graph is ENTITY_GRAPH_UNSET
            else context.entity_graph
        )
        composed = replace(
            report,
            site_snapshot=context.site_snapshot,
            query_clusters=list(context.query_clusters),
            competitor_profiles=list(context.competitor_profiles),
            entity_graph=entity_graph,
            citation_failures=list(context.citation_failures),
            plugin_results={**report.plugin_results, **plugin_results},
            metadata={**report.metadata, **context.metadata},
        )
        context.report_model = composed
        return composed


def deserialize_report_model(data: Mapping[str, Any]) -> ReportModel:
    return ReportModel.from_dict(data)
