import unittest
from pathlib import Path

from scripts.strategy_engine.workflow import (
    StrategyWorkflowDependencies,
    run_strategy_report,
)


class StrategyWorkflowTest(unittest.TestCase):
    def test_run_strategy_report_uses_injected_dependencies(self):
        calls = []

        def fetch_page(url):
            calls.append(("fetch_page", url))
            return {
                "url": url,
                "title": "Example Co | Example Co",
                "canonical_url": url,
                "status_code": 200,
                "has_ssr_content": True,
                "word_count": 640,
                "text_content": "Example Co content.",
                "meta_tags": {},
                "internal_links": [],
                "external_links": [],
                "structured_data": [],
                "security_headers": {},
                "h1_tags": ["Example Co"],
            }

        def fetch_robots_txt(url):
            calls.append(("fetch_robots_txt", url))
            return {"exists": True, "ai_crawler_status": {}}

        def fetch_llms_txt(url):
            calls.append(("fetch_llms_txt", url))
            return {"llms_txt": {"exists": True}}

        def validate_llmstxt(url):
            calls.append(("validate_llmstxt", url))
            return {"exists": True, "format_valid": True, "issues": []}

        def crawl_sitemap(url):
            calls.append(("crawl_sitemap", url))
            return [url]

        def analyze_page_citability(url):
            calls.append(("analyze_page_citability", url))
            return {"average_citability_score": 72.0}

        def generate_brand_report(brand_name, netloc):
            calls.append(("generate_brand_report", brand_name, netloc))
            return {"platforms": {"wikipedia": {"has_wikipedia_page": False}}}

        def extract_brand_name(page_data, fallback_url):
            calls.append(("extract_brand_name", fallback_url))
            return "Example Co"

        def build_rescience_pass(**kwargs):
            calls.append(("build_rescience_pass", kwargs["url"]))
            return {
                "url": kwargs["url"],
                "summary": "Optimization pass summary",
                "priority_actions": {"P0": [], "P1": [], "P2": []},
                "platform_guidance": {},
                "geo_methods": [],
            }

        def build_findings(**kwargs):
            calls.append(("build_findings", kwargs["page_data"]["url"]))
            return []

        def build_action_lists(rescience_pass):
            calls.append(("build_action_lists", rescience_pass["url"]))
            return ["Win"], ["Medium"], ["Strategic"]

        def build_crawler_access(robots_data):
            calls.append(("build_crawler_access", robots_data["exists"]))
            return {"GPTBot": {"platform": "OpenAI", "status": "Allow", "recommendation": "Keep accessible."}}

        def build_executive_summary(**kwargs):
            calls.append(("build_executive_summary", kwargs["brand_name"]))
            return "Summary"

        def build_report_sections(report_model, audit_data):
            calls.append(("build_report_sections", report_model.to_dict()["brand_name"]))
            return {"executive_summary": {"overview": "Strategic overview"}}

        def build_client_report_sections(report_model, audit_data):
            calls.append(("build_client_report_sections", report_model.to_dict()["brand_name"]))
            return {"decision_summary": {"overview": "Client overview"}}

        def build_combined_audit_data(**kwargs):
            calls.append(("build_combined_audit_data", kwargs["brand_name"]))
            return {
                "url": kwargs["url"],
                "brand_name": kwargs["brand_name"],
                "date": "2026-03-20",
                "geo_score": kwargs["geo_scores"]["geo_score"],
                "scores": kwargs["geo_scores"]["scores"],
                "platforms": kwargs["platforms"],
                "executive_summary": kwargs["executive_summary"],
                "findings": kwargs["findings"],
                "quick_wins": kwargs["quick_wins"],
                "medium_term": kwargs["medium_term"],
                "strategic": kwargs["strategic"],
                "crawler_access": kwargs["crawler_access"],
                "rescience_pass": kwargs["rescience_pass"],
                "query_clusters": kwargs["query_clusters"],
                "competitor_profiles": kwargs["competitor_profiles"],
                "entity_graph": kwargs["entity_graph"],
                "citation_failures": kwargs["citation_failures"],
                "plugin_results": kwargs["plugin_results"],
                "report_model": kwargs["report_model"],
                "report_sections": kwargs["report_sections"],
                "client_report_sections": kwargs["client_report_sections"],
            }

        def build_output_paths(brand_name, date_stamp):
            calls.append(("build_output_paths", brand_name, date_stamp))
            return {
                "report_dir": Path("output/reports/example"),
                "markdown_path": Path("output/reports/example/GEO-CLIENT-REPORT.md"),
                "json_path": Path("output/reports/example/audit-data.json"),
                "pdf_path": Path("output/reports/example/GEO-REPORT.pdf"),
                "client_pdf_path": Path("output/reports/example/GEO-REPORT.pdf"),
                "workbook_pdf_path": Path("output/reports/example/GEO-STRATEGIST-WORKBOOK.pdf"),
            }

        def render_markdown_report(data):
            calls.append(("render_markdown_report", data["brand_name"]))
            return "# report"

        def write_text(path, content):
            calls.append(("write_text", str(path), content))

        def write_json(path, data):
            calls.append(("write_json", str(path), data["brand_name"]))

        def generate_report(data, output_path):
            calls.append(("generate_report", output_path, data["brand_name"]))

        def generate_workbook_report(data, output_path):
            calls.append(("generate_workbook_report", output_path, data["brand_name"]))

        class FakeReport:
            def __init__(self):
                self.plugin_results = {
                    "readiness": {
                        "geo_scores": {
                            "geo_score": 91,
                            "scores": {
                                "ai_citability": 72,
                                "brand_authority": 52,
                                "content_eeat": 75,
                                "technical": 90,
                                "schema": 46,
                                "platform_optimization": 60,
                            },
                        },
                        "platforms": {"ChatGPT": 88},
                    },
                }
                self.query_clusters = []
                self.competitor_profiles = []
                self.entity_graph = None
                self.citation_failures = []
                self.metadata = {}

            def to_dict(self):
                return {"brand_name": "Example Co"}

        class FakeStrategyOrchestrator:
            def __init__(self, plugins):
                self.plugins = plugins

            def execute(self, context):
                calls.append(("execute", context.metadata["brand_name"]))
                return FakeReport()

        deps = StrategyWorkflowDependencies(
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
            build_client_report_sections=build_client_report_sections,
            render_markdown_report=render_markdown_report,
            write_text=write_text,
            write_json=write_json,
            generate_report=generate_report,
            generate_workbook_report=generate_workbook_report,
            orchestrator_cls=FakeStrategyOrchestrator,
        )

        result = run_strategy_report("https://example.com", deps=deps)

        self.assertEqual(result["brand_name"], "Example Co")
        self.assertTrue(any(call[0] == "write_text" for call in calls))
        self.assertTrue(any(call[0] == "write_json" for call in calls))
        self.assertTrue(any(call[0] == "generate_report" for call in calls))
        self.assertTrue(any(call[0] == "generate_workbook_report" for call in calls))
        self.assertTrue(any(call[0] == "build_client_report_sections" for call in calls))
        self.assertEqual(result["pdf_path"], str(Path("output/reports/example/GEO-REPORT.pdf")))
        self.assertEqual(
            result["workbook_pdf_path"],
            str(Path("output/reports/example/GEO-STRATEGIST-WORKBOOK.pdf")),
        )


if __name__ == "__main__":
    unittest.main()
