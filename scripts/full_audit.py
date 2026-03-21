#!/usr/bin/env python3
"""
Single-entry GEO audit orchestrator.

Runs the geo-seo-claude scoring flow, adds a ReScience optimization pass,
and generates the final PDF deliverable.
"""

from __future__ import annotations

import argparse
import json

try:
    from .brand_scanner import generate_brand_report
    from .citability_scorer import analyze_page_citability
    from .fetch_page import crawl_sitemap, fetch_llms_txt, fetch_page, fetch_robots_txt
    from .generate_pdf_report import generate_report
    from .llmstxt_generator import validate_llmstxt
    from .strategy_engine.artifacts import (
        build_combined_audit_data,
        build_output_paths,
        extract_brand_name,
        write_json,
        write_text,
    )
    from .strategy_engine.markdown import render_markdown_report
    from .strategy_engine import (
        StrategyOrchestrator,
        build_report_sections,
    )
    from .strategy_engine.summary import (
        build_action_lists,
        build_crawler_access,
        build_executive_summary,
        build_findings,
        build_rescience_pass,
    )
    from .strategy_engine.workflow import (
        StrategyWorkflowDependencies,
        run_strategy_report,
    )
    from .strategy_engine.plugins.competitive import (
        CitationDiagnosisPlugin,
        CompetitorAnalysisPlugin,
        EntityAnalysisPlugin,
    )
    from .strategy_engine.plugins.readiness import ReadinessInputs, ReadinessPlugin
    from .strategy_engine.plugins.opportunity import (
        KeywordResearchPlugin,
        OpportunityInputs,
        OpportunityPlugin,
        SerpAnalysisPlugin,
    )
except ImportError:
    from brand_scanner import generate_brand_report
    from citability_scorer import analyze_page_citability
    from fetch_page import crawl_sitemap, fetch_llms_txt, fetch_page, fetch_robots_txt
    from generate_pdf_report import generate_report
    from llmstxt_generator import validate_llmstxt
    from strategy_engine.artifacts import (
        build_combined_audit_data,
        build_output_paths,
        extract_brand_name,
        write_json,
        write_text,
    )
    from strategy_engine.markdown import render_markdown_report
    from strategy_engine import (
        StrategyOrchestrator,
        build_report_sections,
    )
    from strategy_engine.summary import (
        build_action_lists,
        build_crawler_access,
        build_executive_summary,
        build_findings,
        build_rescience_pass,
    )
    from strategy_engine.workflow import (
        StrategyWorkflowDependencies,
        run_strategy_report,
    )
    from strategy_engine.plugins.competitive import (
        CitationDiagnosisPlugin,
        CompetitorAnalysisPlugin,
        EntityAnalysisPlugin,
    )
    from strategy_engine.plugins.readiness import ReadinessInputs, ReadinessPlugin
    from strategy_engine.plugins.opportunity import (
        KeywordResearchPlugin,
        OpportunityInputs,
        OpportunityPlugin,
        SerpAnalysisPlugin,
    )

def build_workflow_dependencies() -> StrategyWorkflowDependencies:
    return StrategyWorkflowDependencies(
        fetch_page=fetch_page,
        fetch_robots_txt=fetch_robots_txt,
        fetch_llms_txt=fetch_llms_txt,
        validate_llmstxt=validate_llmstxt,
        crawl_sitemap=crawl_sitemap,
        analyze_page_citability=analyze_page_citability,
        generate_brand_report=generate_brand_report,
        extract_brand_name=extract_brand_name,
        build_rescience_pass=build_rescience_pass,
        build_findings=build_findings,
        build_action_lists=build_action_lists,
        build_crawler_access=build_crawler_access,
        build_executive_summary=build_executive_summary,
        build_combined_audit_data=build_combined_audit_data,
        build_output_paths=build_output_paths,
        build_report_sections=build_report_sections,
        render_markdown_report=render_markdown_report,
        write_text=write_text,
        write_json=write_json,
        generate_report=generate_report,
        orchestrator_cls=StrategyOrchestrator,
    )


def orchestrate_audit(
    url: str,
    *,
    competitor_domains: list[str] | None = None,
    seed_topics: list[str] | None = None,
    locale: str = "en-us",
    result_limit: int = 5,
    generate_pdf_output: bool = True,
) -> dict:
    return run_strategy_report(
        url,
        deps=build_workflow_dependencies(),
        competitor_domains=competitor_domains,
        seed_topics=seed_topics,
        locale=locale,
        result_limit=result_limit,
        generate_pdf_output=generate_pdf_output,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the hybrid GEO audit orchestrator.")
    parser.add_argument("url", help="Target website URL")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    result = orchestrate_audit(args.url)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
