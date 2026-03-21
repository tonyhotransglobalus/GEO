from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from .core import AnalysisContext, SiteSnapshot, StrategyOrchestrator
from .plugins.competitive import (
    CitationDiagnosisPlugin,
    CompetitorAnalysisPlugin,
    EntityAnalysisPlugin,
)
from .plugins.opportunity import (
    KeywordResearchPlugin,
    OpportunityInputs,
    OpportunityPlugin,
    SerpAnalysisPlugin,
)
from .plugins.readiness import ReadinessInputs, ReadinessPlugin


@dataclass(slots=True)
class StrategyWorkflowDependencies:
    fetch_page: Callable[[str], dict]
    fetch_robots_txt: Callable[[str], dict]
    fetch_llms_txt: Callable[[str], dict]
    validate_llmstxt: Callable[[str], dict]
    crawl_sitemap: Callable[[str], list[str]]
    analyze_page_citability: Callable[[str], dict]
    generate_brand_report: Callable[[str, str], dict]
    extract_brand_name: Callable[[dict, str], str]
    build_rescience_pass: Callable[..., dict]
    build_findings: Callable[..., list[dict]]
    build_action_lists: Callable[[dict], tuple[list[str], list[str], list[str]]]
    build_crawler_access: Callable[[dict], dict]
    build_executive_summary: Callable[..., str]
    build_combined_audit_data: Callable[..., dict]
    build_output_paths: Callable[[str, str], dict[str, Path]]
    build_report_sections: Callable[[Any, Mapping[str, Any]], dict]
    render_markdown_report: Callable[[dict], str]
    write_text: Callable[[Path, str], None]
    write_json: Callable[[Path, dict], None]
    generate_report: Callable[[dict, str], None]
    orchestrator_cls: type[StrategyOrchestrator]


def _clean_list(values: list[str] | None) -> list[str]:
    return [str(value).strip() for value in (values or []) if str(value).strip()]


def run_strategy_report(
    url: str,
    *,
    deps: StrategyWorkflowDependencies,
    competitor_domains: list[str] | None = None,
    seed_topics: list[str] | None = None,
    locale: str = "en-us",
    result_limit: int = 5,
    generate_pdf_output: bool = True,
) -> dict:
    page_data = deps.fetch_page(url)
    robots_data = deps.fetch_robots_txt(url)
    llms_live = deps.fetch_llms_txt(url)
    llms_validation = deps.validate_llmstxt(url)
    sitemap_pages = deps.crawl_sitemap(url)
    citability_data = deps.analyze_page_citability(url)

    brand_name = deps.extract_brand_name(page_data, url)
    brand_data = deps.generate_brand_report(brand_name, urlparse(url).netloc)
    cleaned_seed_topics = _clean_list(seed_topics)
    if not cleaned_seed_topics:
        cleaned_seed_topics = [
            topic
            for topic in [
                brand_name,
                page_data.get("title") or "",
                page_data.get("description") or "",
            ]
            if str(topic).strip()
        ]
    cleaned_competitor_domains = _clean_list(competitor_domains)

    rescience_pass = deps.build_rescience_pass(
        url=url,
        page_data=page_data,
        citability_data=citability_data,
        llms_validation=llms_validation,
        brand_data=brand_data,
    )

    readiness_inputs = ReadinessInputs(
        page_data=page_data,
        robots_data=robots_data,
        llms_validation=llms_validation,
        llms_live=llms_live,
        sitemap_pages=sitemap_pages,
        citability_data=citability_data,
        brand_data=brand_data,
        rescience_pass=rescience_pass,
    )
    opportunity_inputs = OpportunityInputs(
        seed_topics=cleaned_seed_topics,
        competitor_domains=cleaned_competitor_domains,
        result_limit=max(1, int(result_limit)),
        locale=locale or "en-us",
        site_domain=urlparse(url).netloc,
    )
    readiness_context = AnalysisContext(
        site_snapshot=SiteSnapshot(
            url=url,
            title=brand_name,
            canonical_url=page_data.get("canonical_url") or url,
        ),
        metadata={
            "brand_name": brand_name,
            "site_name": brand_name,
            "brand_data": brand_data,
            "readiness": readiness_inputs.to_dict(),
            "opportunity": opportunity_inputs.to_dict(),
            "competitive": {
                "site_domain": urlparse(url).netloc,
                "competitor_domains": cleaned_competitor_domains,
            },
        },
    )
    audit_report = deps.orchestrator_cls(
        [
            ReadinessPlugin(),
            KeywordResearchPlugin(),
            SerpAnalysisPlugin(),
            OpportunityPlugin(),
            CompetitorAnalysisPlugin(),
            EntityAnalysisPlugin(),
            CitationDiagnosisPlugin(),
        ]
    ).execute(readiness_context)
    readiness = audit_report.plugin_results["readiness"]
    geo_scores = readiness["geo_scores"]
    platforms = readiness["platforms"]

    findings = deps.build_findings(
        page_data=page_data,
        citability_data=citability_data,
        llms_live=llms_live,
        llms_validation=llms_validation,
        brand_data=brand_data,
        rescience_pass=rescience_pass,
    )
    quick_wins, medium_term, strategic = deps.build_action_lists(rescience_pass)
    crawler_access = deps.build_crawler_access(robots_data)
    executive_summary = deps.build_executive_summary(
        brand_name=brand_name,
        geo_score=geo_scores["geo_score"],
        page_data=page_data,
        citability_data=citability_data,
        llms_live=llms_live,
        llms_validation=llms_validation,
        rescience_pass=rescience_pass,
    )

    combined = deps.build_combined_audit_data(
        url=url,
        brand_name=brand_name,
        geo_scores=geo_scores,
        rescience_pass=rescience_pass,
        executive_summary=executive_summary,
        findings=findings,
        quick_wins=quick_wins,
        medium_term=medium_term,
        strategic=strategic,
        crawler_access=crawler_access,
        platforms=platforms,
        query_clusters=[cluster.to_dict() for cluster in audit_report.query_clusters],
        competitor_profiles=[profile.to_dict() for profile in audit_report.competitor_profiles],
        entity_graph=(
            audit_report.entity_graph.to_dict()
            if audit_report.entity_graph is not None
            else None
        ),
        citation_failures=[failure.to_dict() for failure in audit_report.citation_failures],
        plugin_results=audit_report.plugin_results,
        report_model=audit_report.to_dict(),
        report_sections=deps.build_report_sections(
            audit_report,
            {
                "geo_scores": geo_scores,
                "platforms": platforms,
                "page_data": page_data,
                "citability_data": citability_data,
                "llms_validation": llms_validation,
                "llms_live": llms_live,
                "brand_data": brand_data,
                "robots_data": robots_data,
                "sitemap_pages": sitemap_pages,
                "rescience_pass": rescience_pass,
                "findings": findings,
                "quick_wins": quick_wins,
                "medium_term": medium_term,
                "strategic": strategic,
                "crawler_access": crawler_access,
                "query_clusters": [cluster.to_dict() for cluster in audit_report.query_clusters],
                "competitor_profiles": [profile.to_dict() for profile in audit_report.competitor_profiles],
                "entity_graph": (
                    audit_report.entity_graph.to_dict()
                    if audit_report.entity_graph is not None
                    else None
                ),
                "citation_failures": [failure.to_dict() for failure in audit_report.citation_failures],
                "plugin_results": audit_report.plugin_results,
            },
        ),
    )

    report_markdown = deps.render_markdown_report(combined)

    output_paths = deps.build_output_paths(brand_name, combined["date"])
    markdown_path = output_paths["markdown_path"]
    json_path = output_paths["json_path"]
    pdf_path = output_paths["pdf_path"]

    deps.write_text(markdown_path, report_markdown)
    deps.write_json(json_path, combined)

    if generate_pdf_output:
        deps.generate_report(combined, str(pdf_path))
        combined["pdf_path"] = str(pdf_path)

    combined["report_dir"] = str(output_paths["report_dir"])
    combined["markdown_path"] = str(markdown_path)
    combined["json_path"] = str(json_path)
    return combined
