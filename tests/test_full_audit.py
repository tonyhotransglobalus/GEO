import inspect
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from reportlab.platypus import Paragraph

from scripts.generate_pdf_report import (
    generate_report,
    generate_workbook_report,
    wrap_table_rows,
)
from scripts.strategy_engine.plugins.readiness import (
    ReadinessInputs,
    ReadinessPlugin,
    ReadinessResult,
)
from scripts.strategy_engine.plugins.opportunity import (
    KeywordResearchPlugin,
    OpportunityInputs,
    OpportunityPlugin,
    OpportunityResult,
    SerpAnalysisPlugin,
)
from scripts.strategy_engine.plugins.competitive import (
    CitationDiagnosisPlugin,
    CitationDiagnosisResult,
    CompetitorAnalysisPlugin,
    CompetitorAnalysisResult,
    EntityAnalysisPlugin,
    EntityAnalysisResult,
)
from scripts.strategy_engine import QueryCluster
from scripts.strategy_engine.reporting import build_report_sections

from scripts.full_audit import (
    build_output_paths,
    build_combined_audit_data,
    build_findings,
    build_executive_summary,
    build_rescience_pass,
    parse_args,
    render_markdown_report,
    orchestrate_audit,
)
from scripts.strategy_engine import ReportModel, SiteSnapshot


class FullAuditHelpersTest(unittest.TestCase):
    def setUp(self):
        self._keyword_suggestions_patch = patch(
            "scripts.strategy_engine.plugins.opportunity.fetch_keyword_suggestions",
            return_value=["Example Co alternatives"],
        )
        self._serp_snapshot_patch = patch(
            "scripts.strategy_engine.plugins.opportunity.fetch_serp_snapshot",
            return_value=[],
        )
        self._keyword_suggestions_patch.start()
        self._serp_snapshot_patch.start()
        self.addCleanup(self._keyword_suggestions_patch.stop)
        self.addCleanup(self._serp_snapshot_patch.stop)

    def test_output_paths_use_central_report_folder(self):
        paths = build_output_paths("Example Co", "2026-03-17")

        self.assertEqual(
            paths["report_dir"],
            Path("output/reports/example-co-2026-03-17"),
        )
        self.assertEqual(
            paths["markdown_path"],
            Path("output/reports/example-co-2026-03-17/GEO-CLIENT-REPORT.md"),
        )
        self.assertEqual(
            paths["json_path"],
            Path("output/reports/example-co-2026-03-17/audit-data.json"),
        )
        self.assertEqual(
            paths["pdf_path"],
            Path("output/reports/example-co-2026-03-17/GEO-REPORT.pdf"),
        )
        self.assertEqual(paths["pdf_path"], paths["client_pdf_path"])
        self.assertEqual(
            paths["workbook_pdf_path"],
            Path("output/reports/example-co-2026-03-17/GEO-STRATEGIST-WORKBOOK.pdf"),
        )

    def test_cli_only_requires_url(self):
        args = parse_args(["https://example.com"])
        self.assertEqual(args.url, "https://example.com")

    def test_orchestrate_audit_generates_pdf_by_default(self):
        default_value = inspect.signature(orchestrate_audit).parameters[
            "generate_pdf_output"
        ].default
        self.assertTrue(default_value)

    @patch("scripts.full_audit.write_json")
    @patch("scripts.full_audit.write_text")
    @patch("scripts.full_audit.generate_workbook_report")
    @patch("scripts.full_audit.generate_report")
    @patch("scripts.full_audit.generate_brand_report")
    @patch("scripts.full_audit.analyze_page_citability")
    @patch("scripts.full_audit.crawl_sitemap")
    @patch("scripts.full_audit.validate_llmstxt")
    @patch("scripts.full_audit.fetch_llms_txt")
    @patch("scripts.full_audit.fetch_robots_txt")
    @patch("scripts.full_audit.fetch_page")
    def test_orchestrate_audit_uses_readiness_plugin_output(
        self,
        fetch_page_mock,
        fetch_robots_mock,
        fetch_llms_mock,
        validate_llms_mock,
        crawl_sitemap_mock,
        citability_mock,
        brand_report_mock,
        generate_report_mock,
        generate_workbook_report_mock,
        write_text_mock,
        write_json_mock,
    ):
        page_data = {
            "url": "https://example.com",
            "title": "Example Co | Example Co",
            "canonical_url": "https://example.com",
            "status_code": 200,
            "has_ssr_content": True,
            "word_count": 640,
            "text_content": "Jane Smith wrote this in March about Example Co.",
            "meta_tags": {"article:modified_time": "2026-03-18"},
            "internal_links": [{"url": "https://example.com/author/jane"}],
            "external_links": [
                {"url": "https://www.linkedin.com/company/example"}
            ],
            "structured_data": [
                {
                    "@graph": [
                        {
                            "@type": "Organization",
                            "sameAs": [
                                "https://www.linkedin.com/company/example"
                            ],
                        },
                        {"@type": "WebSite"},
                    ]
                }
            ],
            "security_headers": {
                "Strict-Transport-Security": "max-age=31536000",
                "Content-Security-Policy": "default-src 'self'",
            },
            "h1_tags": ["Example Co"],
        }
        fetch_page_mock.return_value = page_data
        fetch_robots_mock.return_value = {"exists": True}
        fetch_llms_mock.return_value = {"llms_txt": {"exists": True}}
        validate_llms_mock.return_value = {"exists": True}
        crawl_sitemap_mock.return_value = ["https://example.com/"]
        citability_mock.return_value = {"average_citability_score": 72.0}
        brand_report_mock.return_value = {
            "platforms": {"wikipedia": {"has_wikipedia_page": False}}
        }

        readiness_result = ReadinessResult(
            inputs=ReadinessInputs(
                page_data=page_data,
                robots_data={"exists": True},
                llms_validation={
                    "exists": True,
                    "format_valid": True,
                    "issues": [],
                },
                llms_live={"llms_txt": {"exists": True}},
                sitemap_pages=["https://example.com/"],
                citability_data={"average_citability_score": 72.0},
                brand_data={
                    "platforms": {"wikipedia": {"has_wikipedia_page": False}}
                },
            ),
            geo_scores={
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
            platforms={"ChatGPT": 88, "Google AI Overviews": 89},
        )

        def analyze_side_effect(*args, **kwargs):
            context = args[-1]
            self.assertIn("readiness", context.metadata)
            self.assertIn("llms_validation", context.metadata["readiness"])
            self.assertEqual(
                context.metadata["readiness"]["page_data"]["title"],
                "Example Co | Example Co",
            )
            return readiness_result

        with patch.object(ReadinessPlugin, "analyze", side_effect=analyze_side_effect):
            result = orchestrate_audit(
                "https://example.com",
                generate_pdf_output=False,
            )

        self.assertEqual(result["geo_score"], 91)
        self.assertEqual(result["platforms"]["ChatGPT"], 88)
        self.assertEqual(
            result["plugin_results"]["readiness"]["geo_scores"]["geo_score"], 91
        )
        self.assertFalse(generate_report_mock.called)
        self.assertFalse(generate_workbook_report_mock.called)
        self.assertTrue(write_text_mock.called)
        self.assertTrue(write_json_mock.called)

    @patch("scripts.full_audit.write_json")
    @patch("scripts.full_audit.write_text")
    @patch("scripts.full_audit.generate_workbook_report")
    @patch("scripts.full_audit.generate_report")
    @patch("scripts.full_audit.generate_brand_report")
    @patch("scripts.full_audit.analyze_page_citability")
    @patch("scripts.full_audit.crawl_sitemap")
    @patch("scripts.full_audit.validate_llmstxt")
    @patch("scripts.full_audit.fetch_llms_txt")
    @patch("scripts.full_audit.fetch_robots_txt")
    @patch("scripts.full_audit.fetch_page")
    def test_orchestrate_audit_includes_opportunity_plugin_output_and_query_clusters(
        self,
        fetch_page_mock,
        fetch_robots_mock,
        fetch_llms_mock,
        validate_llms_mock,
        crawl_sitemap_mock,
        citability_mock,
        brand_report_mock,
        generate_report_mock,
        generate_workbook_report_mock,
        write_text_mock,
        write_json_mock,
    ):
        page_data = {
            "url": "https://example.com",
            "title": "Example Co | Example Co",
            "canonical_url": "https://example.com",
            "status_code": 200,
            "has_ssr_content": True,
            "word_count": 640,
            "text_content": "Jane Smith wrote this in March about Example Co.",
            "meta_tags": {"article:modified_time": "2026-03-18"},
            "internal_links": [{"url": "https://example.com/author/jane"}],
            "external_links": [],
            "structured_data": [],
            "security_headers": {},
            "h1_tags": ["Example Co"],
        }
        fetch_page_mock.return_value = page_data
        fetch_robots_mock.return_value = {"exists": True}
        fetch_llms_mock.return_value = {"llms_txt": {"exists": True}}
        validate_llms_mock.return_value = {"exists": True}
        crawl_sitemap_mock.return_value = ["https://example.com/"]
        citability_mock.return_value = {"average_citability_score": 72.0}
        brand_report_mock.return_value = {
            "platforms": {"wikipedia": {"has_wikipedia_page": False}}
        }

        readiness_result = ReadinessResult(
            inputs=ReadinessInputs(
                page_data=page_data,
                robots_data={"exists": True},
                llms_validation={
                    "exists": True,
                    "format_valid": True,
                    "issues": [],
                },
                llms_live={"llms_txt": {"exists": True}},
                sitemap_pages=["https://example.com/"],
                citability_data={"average_citability_score": 72.0},
                brand_data={
                    "platforms": {"wikipedia": {"has_wikipedia_page": False}}
                },
            ),
            geo_scores={
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
            platforms={"ChatGPT": 88, "Google AI Overviews": 89},
        )
        opportunity_result = OpportunityResult(
            inputs=OpportunityInputs(
                seed_topics=["Example Co"],
                competitor_domains=[],
                result_limit=2,
                locale="en-us",
            ),
            seed_topics=["Example Co"],
            keyword_suggestions={
                "Example Co": ["Example Co alternatives", "Example Co pricing"]
            },
            serp_snapshots={
                "Example Co": [
                    {
                        "query": "Example Co",
                        "rank": 1,
                        "title": "Example Co",
                        "url": "https://example.com/",
                        "domain": "example.com",
                        "snippet": "Example Co home",
                        "source": "duckduckgo",
                    }
                ]
            },
            query_clusters=[
                QueryCluster(
                    label="example-co",
                    queries=["Example Co", "Example Co alternatives"],
                    search_intent="navigational",
                    priority="medium",
                    metadata={"seed_topic": "Example Co"},
                )
            ],
            opportunities=[
                {
                    "query": "Example Co",
                    "site_visible": True,
                    "opportunity_score": 42,
                    "label": "medium",
                }
            ],
            summary={"cluster_count": 1},
        )

        keyword_result = {
            "seed_topics": ["Example Co"],
            "keyword_suggestions": {
                "Example Co": ["Example Co alternatives", "Example Co pricing"]
            },
        }
        serp_result = {
            "seed_topics": ["Example Co"],
            "serp_snapshots": opportunity_result.serp_snapshots,
        }

        def readiness_side_effect(*args, **kwargs):
            return readiness_result

        def keyword_side_effect(*args, **kwargs):
            return keyword_result

        def serp_side_effect(*args, **kwargs):
            return serp_result

        def opportunity_side_effect(*args, **kwargs):
            context = args[-1]
            self.assertIn("keyword_research", context.report_model.plugin_results)
            self.assertIn("serp_analysis", context.report_model.plugin_results)
            self.assertIn("opportunity", context.metadata)
            self.assertEqual(
                context.metadata["opportunity"]["seed_topics"][0],
                "Example Co",
            )
            context.query_clusters.append(
                QueryCluster(
                    label="example-co",
                    queries=["Example Co", "Example Co alternatives"],
                    search_intent="navigational",
                    priority="medium",
                    metadata={"seed_topic": "Example Co"},
                )
            )
            return opportunity_result

        with patch.object(ReadinessPlugin, "analyze", side_effect=readiness_side_effect), patch.object(
            KeywordResearchPlugin, "analyze", side_effect=keyword_side_effect
        ), patch.object(
            SerpAnalysisPlugin, "analyze", side_effect=serp_side_effect
        ), patch.object(
            OpportunityPlugin, "analyze", side_effect=opportunity_side_effect
        ):
            result = orchestrate_audit(
                "https://example.com",
                generate_pdf_output=False,
            )

        self.assertEqual(result["geo_score"], 91)
        self.assertIn("keyword_research", result["plugin_results"])
        self.assertIn("serp_analysis", result["plugin_results"])
        self.assertEqual(result["plugin_results"]["opportunity"]["summary"]["cluster_count"], 1)
        self.assertEqual(
            result["plugin_results"]["keyword_research"]["keyword_suggestions"][
                "Example Co"
            ],
            ["Example Co alternatives", "Example Co pricing"],
        )
        self.assertEqual(
            result["plugin_results"]["serp_analysis"]["serp_snapshots"]["Example Co"][0][
                "domain"
            ],
            "example.com",
        )
        self.assertEqual(result["query_clusters"][0]["label"], "example-co")
        self.assertEqual(
            write_json_mock.call_args.args[1]["plugin_results"]["keyword_research"][
                "keyword_suggestions"
            ]["Example Co"][0],
            "Example Co alternatives",
        )
        self.assertFalse(generate_report_mock.called)
        self.assertFalse(generate_workbook_report_mock.called)
        self.assertTrue(write_text_mock.called)
        self.assertTrue(write_json_mock.called)

    @patch("scripts.full_audit.write_json")
    @patch("scripts.full_audit.write_text")
    @patch("scripts.full_audit.generate_workbook_report")
    @patch("scripts.full_audit.generate_report")
    @patch("scripts.full_audit.generate_brand_report")
    @patch("scripts.full_audit.analyze_page_citability")
    @patch("scripts.full_audit.crawl_sitemap")
    @patch("scripts.full_audit.validate_llmstxt")
    @patch("scripts.full_audit.fetch_llms_txt")
    @patch("scripts.full_audit.fetch_robots_txt")
    @patch("scripts.full_audit.fetch_page")
    def test_orchestrate_audit_includes_competitive_analysis_payloads(
        self,
        fetch_page_mock,
        fetch_robots_mock,
        fetch_llms_mock,
        validate_llms_mock,
        crawl_sitemap_mock,
        citability_mock,
        brand_report_mock,
        generate_report_mock,
        generate_workbook_report_mock,
        write_text_mock,
        write_json_mock,
    ):
        page_data = {
            "url": "https://example.com",
            "title": "Example Co | Example Co",
            "canonical_url": "https://example.com",
            "status_code": 200,
            "has_ssr_content": True,
            "word_count": 640,
            "text_content": "Jane Smith wrote this in March about Example Co.",
            "meta_tags": {"article:modified_time": "2026-03-18"},
            "internal_links": [{"url": "https://example.com/author/jane"}],
            "external_links": [
                {"url": "https://www.linkedin.com/company/example"}
            ],
            "structured_data": [
                {
                    "@graph": [
                        {
                            "@type": "Organization",
                            "name": "Example Co",
                            "sameAs": [
                                "https://www.linkedin.com/company/example"
                            ],
                        }
                    ]
                }
            ],
            "security_headers": {},
            "h1_tags": ["Example Co"],
        }
        fetch_page_mock.return_value = page_data
        fetch_robots_mock.return_value = {"exists": True}
        fetch_llms_mock.return_value = {"llms_txt": {"exists": True}}
        validate_llms_mock.return_value = {"exists": True}
        crawl_sitemap_mock.return_value = ["https://example.com/"]
        citability_mock.return_value = {"average_citability_score": 72.0}
        brand_report_mock.return_value = {
            "platforms": {"wikipedia": {"has_wikipedia_page": False}}
        }

        readiness_result = ReadinessResult(
            inputs=ReadinessInputs(
                page_data=page_data,
                robots_data={"exists": True},
                llms_validation={
                    "exists": True,
                    "format_valid": True,
                    "issues": [],
                },
                llms_live={"llms_txt": {"exists": True}},
                sitemap_pages=["https://example.com/"],
                citability_data={"average_citability_score": 72.0},
                brand_data={
                    "platforms": {"wikipedia": {"has_wikipedia_page": False}}
                },
            ),
            geo_scores={
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
            platforms={"ChatGPT": 88, "Google AI Overviews": 89},
        )
        opportunity_result = OpportunityResult(
            inputs=OpportunityInputs(
                seed_topics=["Example Co"],
                competitor_domains=[],
                result_limit=2,
                locale="en-us",
            ),
            seed_topics=["Example Co"],
            keyword_suggestions={"Example Co": ["Example Co alternatives"]},
            serp_snapshots={
                "Example Co": [
                    {
                        "query": "Example Co",
                        "rank": 1,
                        "title": "Example Co",
                        "url": "https://example.com/",
                        "domain": "example.com",
                        "snippet": "Example Co home",
                        "source": "duckduckgo",
                    }
                ]
            },
            query_clusters=[
                QueryCluster(
                    label="example-co",
                    queries=["Example Co"],
                    search_intent="navigational",
                    priority="medium",
                    metadata={"seed_topic": "Example Co"},
                )
            ],
            opportunities=[],
            summary={"cluster_count": 1},
        )
        competitor_result = CompetitorAnalysisResult(
            profiles=[],
            summary={"competitor_count": 1},
        )
        entity_result = EntityAnalysisResult(
            entity_graph={
                "entity_name": "Example Co",
                "canonical_url": "https://example.com",
                "same_as": ["https://www.linkedin.com/company/example"],
                "related_entities": [],
                "attributes": {},
                "confidence": 0.9,
                "metadata": {},
            },
            summary={"same_as_count": 1},
        )
        citation_result = CitationDiagnosisResult(
            citation_failures=[],
            summary={"failure_count": 1},
        )

        with patch.object(ReadinessPlugin, "analyze", return_value=readiness_result), patch.object(
            KeywordResearchPlugin, "analyze",
            return_value={
                "seed_topics": ["Example Co"],
                "keyword_suggestions": {
                    "Example Co": ["Example Co alternatives"]
                },
            },
        ), patch.object(
            SerpAnalysisPlugin, "analyze",
            return_value={
                "seed_topics": ["Example Co"],
                "serp_snapshots": opportunity_result.serp_snapshots,
            },
        ), patch.object(
            OpportunityPlugin, "analyze", return_value=opportunity_result
        ), patch.object(
            CompetitorAnalysisPlugin, "analyze", return_value=competitor_result
        ), patch.object(
            EntityAnalysisPlugin, "analyze", return_value=entity_result
        ), patch.object(
            CitationDiagnosisPlugin, "analyze", return_value=citation_result
        ):
            result = orchestrate_audit("https://example.com", generate_pdf_output=False)

        self.assertIn("competitor_profiles", result)
        self.assertIn("entity_graph", result)
        self.assertIn("citation_failures", result)
        self.assertIn("competitor_analysis", result["plugin_results"])
        self.assertIn("entity_analysis", result["plugin_results"])
        self.assertIn("citation_diagnosis", result["plugin_results"])
        self.assertFalse(generate_report_mock.called)
        self.assertFalse(generate_workbook_report_mock.called)
        self.assertTrue(write_text_mock.called)
        self.assertTrue(write_json_mock.called)

    def test_build_rescience_pass_prioritizes_missing_llms_and_heading_issues(self):
        page_data = {
            "title": "HOME - Example",
            "h1_tags": ["One", "Two"],
            "security_headers": {
                "Strict-Transport-Security": "max-age=1",
                "Content-Security-Policy": None,
            },
        }
        citability_data = {"average_citability_score": 28.0}
        llms_data = {
            "exists": False,
            "issues": ["llms.txt returned status 404"],
        }
        brand_data = {"platforms": {"wikipedia": {"has_wikipedia_page": False}}}

        advisory = build_rescience_pass(
            url="https://example.com",
            page_data=page_data,
            citability_data=citability_data,
            llms_validation=llms_data,
            brand_data=brand_data,
        )

        self.assertIn("P0", advisory["priority_actions"])
        self.assertIn("P1", advisory["priority_actions"])
        self.assertTrue(
            any("llms.txt" in item for item in advisory["priority_actions"]["P1"])
        )
        self.assertTrue(
            any("H1" in item for item in advisory["priority_actions"]["P1"])
        )

    def test_build_rescience_pass_recommends_llms_work_when_existing_file_is_invalid(self):
        page_data = {
            "title": "HOME - Example",
            "h1_tags": ["One"],
            "security_headers": {"Content-Security-Policy": "default-src 'self'"},
        }
        citability_data = {"average_citability_score": 60.0}
        llms_data = {
            "exists": True,
            "format_valid": False,
            "issues": ["Missing description"],
        }
        brand_data = {"platforms": {"wikipedia": {"has_wikipedia_page": True}}}

        advisory = build_rescience_pass(
            url="https://example.com",
            page_data=page_data,
            citability_data=citability_data,
            llms_validation=llms_data,
            brand_data=brand_data,
        )

        self.assertTrue(
            any("llms.txt" in item for item in advisory["priority_actions"]["P1"])
        )

    def test_build_executive_summary_mentions_malformed_llms_guidance(self):
        summary = build_executive_summary(
            brand_name="Example Co",
            geo_score=52,
            page_data={"h1_tags": ["One"]},
            citability_data={"average_citability_score": 28.0},
            llms_live={"llms_txt": {"exists": True}},
            llms_validation={
                "exists": True,
                "format_valid": False,
                "issues": ["Missing description"],
            },
            rescience_pass={"summary": "Optimization pass summary"},
        )

        self.assertIn("exists but the guidance layer is malformed", summary)

    def test_build_findings_distinguishes_malformed_llms_from_missing(self):
        findings = build_findings(
            page_data={"h1_tags": ["One"]},
            citability_data={"average_citability_score": 80.0},
            llms_live={"llms_txt": {"exists": True}},
            llms_validation={
                "exists": True,
                "format_valid": False,
                "issues": ["Missing description"],
            },
            brand_data={"platforms": {"wikipedia": {"has_wikipedia_page": True}}},
            rescience_pass={
                "summary": "Optimization pass summary",
                "priority_actions": {"P0": [], "P1": [], "P2": []},
            },
        )

        self.assertTrue(
            any(
                finding["title"] == "llms.txt guidance files are present but malformed"
                for finding in findings
            )
        )

    def test_build_combined_audit_data_keeps_geo_score_and_adds_rescience_section(self):
        geo_scores = {
            "geo_score": 52,
            "scores": {
                "ai_citability": 28,
                "brand_authority": 40,
                "content_eeat": 65,
                "technical": 80,
                "schema": 70,
                "platform_optimization": 50,
            },
        }
        rescience = {
            "summary": "Optimization pass summary",
            "priority_actions": {"P0": [], "P1": ["Fix llms.txt"], "P2": []},
            "platform_guidance": {"ChatGPT": ["Refresh content"]},
            "geo_methods": [{"method": "Cite Sources", "impact": "+40%"}],
        }

        combined = build_combined_audit_data(
            url="https://example.com",
            brand_name="Example Co",
            geo_scores=geo_scores,
            rescience_pass=rescience,
            executive_summary="Summary",
            findings=[],
            quick_wins=["Win"],
            medium_term=["Medium"],
            strategic=["Strategic"],
            crawler_access={},
        )

        self.assertEqual(combined["geo_score"], 52)
        self.assertEqual(combined["brand_name"], "Example Co")
        self.assertIn("rescience_pass", combined)
        self.assertEqual(
            combined["rescience_pass"]["summary"], "Optimization pass summary"
        )

    @patch("scripts.full_audit.write_json")
    @patch("scripts.full_audit.write_text")
    @patch("scripts.full_audit.generate_workbook_report")
    @patch("scripts.full_audit.generate_report")
    @patch("scripts.full_audit.generate_brand_report")
    @patch("scripts.full_audit.analyze_page_citability")
    @patch("scripts.full_audit.crawl_sitemap")
    @patch("scripts.full_audit.validate_llmstxt")
    @patch("scripts.full_audit.fetch_llms_txt")
    @patch("scripts.full_audit.fetch_robots_txt")
    @patch("scripts.full_audit.fetch_page")
    def test_orchestrate_audit_includes_report_model_and_report_sections(
        self,
        fetch_page_mock,
        fetch_robots_mock,
        fetch_llms_mock,
        validate_llms_mock,
        crawl_sitemap_mock,
        citability_mock,
        brand_report_mock,
        generate_report_mock,
        generate_workbook_report_mock,
        write_text_mock,
        write_json_mock,
    ):
        page_data = {
            "url": "https://example.com",
            "title": "Example Co | Example Co",
            "canonical_url": "https://example.com",
            "status_code": 200,
            "has_ssr_content": True,
            "word_count": 640,
            "text_content": "Jane Smith wrote this in March about Example Co.",
            "meta_tags": {"article:modified_time": "2026-03-18"},
            "internal_links": [{"url": "https://example.com/author/jane"}],
            "external_links": [],
            "structured_data": [],
            "security_headers": {},
            "h1_tags": ["Example Co"],
        }
        fetch_page_mock.return_value = page_data
        fetch_robots_mock.return_value = {"exists": True}
        fetch_llms_mock.return_value = {"llms_txt": {"exists": True}}
        validate_llms_mock.return_value = {"exists": True}
        crawl_sitemap_mock.return_value = ["https://example.com/"]
        citability_mock.return_value = {"average_citability_score": 72.0}
        brand_report_mock.return_value = {
            "platforms": {"wikipedia": {"has_wikipedia_page": False}}
        }

        readiness_result = ReadinessResult(
            inputs=ReadinessInputs(
                page_data=page_data,
                robots_data={"exists": True},
                llms_validation={
                    "exists": True,
                    "format_valid": True,
                    "issues": [],
                },
                llms_live={"llms_txt": {"exists": True}},
                sitemap_pages=["https://example.com/"],
                citability_data={"average_citability_score": 72.0},
                brand_data={
                    "platforms": {"wikipedia": {"has_wikipedia_page": False}}
                },
            ),
            geo_scores={
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
            platforms={"ChatGPT": 88, "Google AI Overviews": 89},
        )

        with patch.object(ReadinessPlugin, "analyze", return_value=readiness_result):
            result = orchestrate_audit(
                "https://example.com",
                generate_pdf_output=False,
            )

        self.assertIn("report_model", result)
        self.assertIn("report_sections", result)
        self.assertIn("client_report_sections", result)
        self.assertEqual(result["report_model"]["brand_name"], "Example Co")
        self.assertIn("decision_summary", result["report_sections"])
        self.assertIn("decision_summary", result["client_report_sections"])
        self.assertFalse(generate_report_mock.called)
        self.assertFalse(generate_workbook_report_mock.called)
        self.assertTrue(write_text_mock.called)
        self.assertTrue(write_json_mock.called)

    @patch("scripts.full_audit.write_json")
    @patch("scripts.full_audit.write_text")
    @patch("scripts.full_audit.generate_workbook_report")
    @patch("scripts.full_audit.generate_report")
    @patch("scripts.full_audit.generate_brand_report")
    @patch("scripts.full_audit.analyze_page_citability")
    @patch("scripts.full_audit.crawl_sitemap")
    @patch("scripts.full_audit.validate_llmstxt")
    @patch("scripts.full_audit.fetch_llms_txt")
    @patch("scripts.full_audit.fetch_robots_txt")
    @patch("scripts.full_audit.fetch_page")
    def test_orchestrate_audit_threads_strategy_options_into_metadata(
        self,
        fetch_page_mock,
        fetch_robots_mock,
        fetch_llms_mock,
        validate_llms_mock,
        crawl_sitemap_mock,
        citability_mock,
        brand_report_mock,
        generate_report_mock,
        generate_workbook_report_mock,
        write_text_mock,
        write_json_mock,
    ):
        page_data = {
            "url": "https://example.com",
            "title": "Example Co | Example Co",
            "canonical_url": "https://example.com",
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
        fetch_page_mock.return_value = page_data
        fetch_robots_mock.return_value = {"exists": True}
        fetch_llms_mock.return_value = {"llms_txt": {"exists": True}}
        validate_llms_mock.return_value = {"exists": True, "format_valid": True, "issues": []}
        crawl_sitemap_mock.return_value = ["https://example.com/"]
        citability_mock.return_value = {"average_citability_score": 72.0}
        brand_report_mock.return_value = {
            "platforms": {"wikipedia": {"has_wikipedia_page": False}}
        }

        readiness_result = ReadinessResult(
            inputs=ReadinessInputs(
                page_data=page_data,
                robots_data={"exists": True},
                llms_validation={
                    "exists": True,
                    "format_valid": True,
                    "issues": [],
                },
                llms_live={"llms_txt": {"exists": True}},
                sitemap_pages=["https://example.com/"],
                citability_data={"average_citability_score": 72.0},
                brand_data={"platforms": {"wikipedia": {"has_wikipedia_page": False}}},
            ),
            geo_scores={
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
            platforms={"ChatGPT": 88, "Google AI Overviews": 89},
        )

        def execute_side_effect(context):
            self.assertEqual(
                context.metadata["opportunity"]["seed_topics"],
                ["geo seo", "ai visibility"],
            )
            self.assertEqual(
                context.metadata["opportunity"]["competitor_domains"],
                ["alpha.com", "beta.com"],
            )
            self.assertEqual(context.metadata["opportunity"]["locale"], "en-gb")
            self.assertEqual(context.metadata["opportunity"]["result_limit"], 7)
            self.assertEqual(
                context.metadata["competitive"]["competitor_domains"],
                ["alpha.com", "beta.com"],
            )
            return ReportModel(
                brand_name="Example Co",
                site_snapshot=SiteSnapshot(
                    url="https://example.com",
                    title="Example Co",
                    canonical_url="https://example.com",
                ),
                plugin_results={
                    "readiness": readiness_result.to_dict(),
                    "opportunity": {"opportunities": []},
                },
                metadata=dict(context.metadata),
            )

        with patch("scripts.full_audit.StrategyOrchestrator.execute", side_effect=execute_side_effect):
            result = orchestrate_audit(
                "https://example.com",
                competitor_domains=["alpha.com", "beta.com"],
                seed_topics=["geo seo", "ai visibility"],
                locale="en-gb",
                result_limit=7,
                generate_pdf_output=False,
            )

        self.assertEqual(result["geo_score"], 91)
        self.assertFalse(generate_report_mock.called)
        self.assertFalse(generate_workbook_report_mock.called)
        self.assertTrue(write_text_mock.called)
        self.assertTrue(write_json_mock.called)

    def test_build_findings_returns_multi_audience_fields(self):
        findings = build_findings(
            page_data={"h1_tags": ["One", "Two"]},
            citability_data={"average_citability_score": 28.0},
            llms_live={"llms_txt": {"exists": False}},
            llms_validation={"exists": False},
            brand_data={"platforms": {"wikipedia": {"has_wikipedia_page": False}}},
            rescience_pass={
                "summary": "Optimization pass summary",
                "priority_actions": {"P0": [], "P1": [], "P2": ["Strengthen entity trust"]},
            },
        )

        first_finding = findings[0]
        self.assertIn("summary", first_finding)
        self.assertIn("leadership_impact", first_finding)
        self.assertIn("marketing_action", first_finding)
        self.assertIn("developer_action", first_finding)
        self.assertIn("observed_evidence", first_finding)

    def test_render_markdown_report_includes_rescience_section(self):
        report_data = {
            "url": "https://example.com",
            "brand_name": "Example Co",
            "date": "2026-03-17",
            "geo_score": 52,
            "scores": {
                "ai_citability": 28,
                "brand_authority": 40,
                "content_eeat": 65,
                "technical": 80,
                "schema": 70,
                "platform_optimization": 50,
            },
            "executive_summary": "Summary",
            "findings": [
                {
                    "severity": "critical",
                    "title": "Key pages are not AI-citation ready",
                    "summary": "Current content does not earn strong AI citations.",
                    "leadership_impact": "Weak AI visibility limits branded discovery and demand capture.",
                    "marketing_action": "Rewrite service pages into answer-first blocks with stronger proof points.",
                    "developer_action": "Support clearer heading hierarchy and FAQ/schema placement for those pages.",
                    "observed_evidence": "Citability scored 28/100 and multiple heading signals were weak.",
                }
            ],
            "quick_wins": ["Win"],
            "medium_term": ["Medium"],
            "strategic": ["Strategic"],
            "crawler_access": {},
            "rescience_pass": {
                "summary": "Optimization pass summary",
                "priority_actions": {
                    "P0": ["Critical item"],
                    "P1": ["Important item"],
                    "P2": ["Recommended item"],
                },
                "platform_guidance": {"ChatGPT": ["Refresh content"]},
                "geo_methods": [{"method": "Cite Sources", "impact": "+40%"}],
            },
        }

        markdown = render_markdown_report(report_data)

        self.assertIn("## ReScience Optimization Pass", markdown)
        self.assertIn("Critical item", markdown)
        self.assertIn("Cite Sources", markdown)
        self.assertIn("Why this matters to leadership", markdown)
        self.assertIn("What marketing should do", markdown)
        self.assertIn("What dev should change", markdown)
        self.assertIn("Observed evidence", markdown)

    def test_render_markdown_report_preserves_legacy_sections_with_report_sections(self):
        report_data = {
            "url": "https://example.com",
            "brand_name": "Example Co",
            "date": "2026-03-17",
            "geo_score": 52,
            "scores": {
                "ai_citability": 28,
                "brand_authority": 40,
                "content_eeat": 65,
                "technical": 80,
                "schema": 70,
                "platform_optimization": 50,
            },
            "executive_summary": "Summary",
            "report_sections": {
                "executive_summary": {
                    "overview": "Strategic overview",
                    "by_audience": {
                        "cto": "CTO summary",
                        "marketing_manager": "Marketing summary",
                        "developers": "Developer summary",
                    },
                },
                "readiness_scorecard": {
                    "geo_score": 52,
                    "components": [{"label": "AI Citability", "score": 28, "weight": 25, "status": "urgent"}],
                    "priority_risks": [{"issue": "Low AI citability"}],
                },
            },
            "findings": [],
            "quick_wins": ["Win"],
            "medium_term": ["Medium"],
            "strategic": ["Strategic"],
            "crawler_access": {},
            "findings": [
                {
                    "severity": "critical",
                    "title": "Key pages are not AI-citation ready",
                    "summary": "Current content does not earn strong AI citations.",
                    "leadership_impact": "Weak AI visibility limits branded discovery and demand capture.",
                    "marketing_action": "Rewrite service pages into answer-first blocks with stronger proof points.",
                    "developer_action": "Support clearer heading hierarchy and FAQ/schema placement for those pages.",
                    "observed_evidence": "Citability scored 28/100 and multiple heading signals were weak.",
                }
            ],
            "rescience_pass": {
                "summary": "Optimization pass summary",
                "priority_actions": {
                    "P0": ["Critical item"],
                    "P1": ["Important item"],
                    "P2": ["Recommended item"],
                },
            },
        }

        markdown = render_markdown_report(report_data)

        self.assertIn("## Prioritized Action Plan", markdown)
        self.assertIn("## ReScience Optimization Pass", markdown)
        self.assertIn("## Key Findings", markdown)
        self.assertIn("Key pages are not AI-citation ready", markdown)
        self.assertIn("Critical item", markdown)
        self.assertIn("Strategic overview", markdown)

    def test_wrap_table_rows_builds_paragraph_cells(self):
        wrapped = wrap_table_rows(
            [["Crawler", "Recommendation"], ["GPTBot", "Use a longer recommendation that must wrap cleanly in the PDF table."]]
        )

        self.assertIsInstance(wrapped[0][0], Paragraph)
        self.assertIsInstance(wrapped[1][1], Paragraph)

    def test_client_pdf_generation_uses_client_brief_structure_and_excludes_workbook_sections(self):
        report_data = {
            "url": "https://example.com",
            "brand_name": "Example Co",
            "date": "2026-03-17",
            "geo_score": 52,
            "scores": {
                "ai_citability": 28,
                "brand_authority": 40,
                "content_eeat": 65,
                "technical": 80,
                "schema": 70,
                "platform_optimization": 50,
            },
            "executive_summary": "Summary",
            "findings": [
                {
                    "severity": "critical",
                    "title": "Key pages are not AI-citation ready",
                    "summary": "Current content does not earn strong AI citations.",
                    "leadership_impact": "Weak AI visibility limits branded discovery and demand capture.",
                    "marketing_action": "Rewrite service pages into answer-first blocks with stronger proof points.",
                    "developer_action": "Support clearer heading hierarchy and FAQ/schema placement for those pages.",
                    "observed_evidence": "Citability scored 28/100 and multiple heading signals were weak.",
                }
            ],
            "quick_wins": ["Win"],
            "medium_term": ["Medium"],
            "strategic": ["Strategic"],
            "crawler_access": {
                "GPTBot": {
                    "platform": "ChatGPT",
                    "status": "Allowed",
                    "recommendation": "Keep accessible with a clearly documented policy so future site changes do not accidentally block high-value AI retrieval traffic.",
                }
            },
            "rescience_pass": {
                "summary": "Optimization pass summary",
                "priority_actions": {
                    "P0": ["Critical item"],
                    "P1": ["Important item"],
                    "P2": ["Recommended item"],
                },
                "platform_guidance": {"ChatGPT": ["Refresh content"]},
                "geo_methods": [{"method": "Cite Sources", "impact": "+40%"}],
            },
            "client_report_sections": {
                "cover": {
                    "title": "GEO Client Brief",
                    "subtitle": "Executive summary for Example Co",
                    "readiness_snapshot": [
                        {"label": "GEO", "value": "52/100"},
                        {"label": "AI Citability", "value": "28/100"},
                    ],
                },
                "decision_summary": {
                    "overview": "Example Co has a workable technical base but weak AI citation readiness.",
                },
                "priority_risks": {
                    "items": [
                        {
                            "title": "Low citation readiness",
                            "business_impact": "The brand is missing AI-assisted discovery demand.",
                            "evidence": "Citability scored 28/100.",
                        }
                    ]
                },
                "top_opportunities": {
                    "items": [
                        {
                            "title": "Answer-first service pages",
                            "why_it_matters": "High-intent queries are still open.",
                            "priority": "high",
                        }
                    ]
                },
                "market_snapshot": {
                    "title": "Market Visibility Snapshot",
                    "summary": "The competitive picture is still incomplete in this sample, so this page highlights the known gap rather than forcing a weak benchmark.",
                    "confidence": "limited",
                    "benchmark_rows": [],
                },
                "roadmap": {
                    "thirty_day": ["Publish llms.txt."],
                    "sixty_day": ["Improve schema."],
                    "ninety_day": ["Build recurring GEO content."],
                },
                "methodology": {
                    "summary": "Point-in-time GEO audit based on live crawl, content scoring, and visibility sampling.",
                    "confidence_note": "Competitor data is sparse in this run.",
                },
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "report.pdf"
            txt_path = Path(temp_dir) / "report.txt"

            generate_report(report_data, str(pdf_path))
            subprocess.run(
                ["pdftotext", str(pdf_path), str(txt_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            pdf_text = txt_path.read_text(encoding="utf-8")

        self.assertIn("Decision Summary", pdf_text)
        self.assertIn("Top Risks", pdf_text)
        self.assertIn("Top Opportunities", pdf_text)
        self.assertIn("Market Visibility Snapshot", pdf_text)
        self.assertIn("30/60/90 Roadmap", pdf_text)
        self.assertIn("Methodology and Confidence", pdf_text)
        self.assertIn("competitive picture is still incomplete", pdf_text.lower())
        self.assertNotIn("Developer Appendix", pdf_text)
        self.assertNotIn("Citation Diagnosis", pdf_text)
        self.assertNotIn("Evidence and Methodology Appendix", pdf_text)

    def test_workbook_pdf_generation_with_report_sections_renders_strategist_headings(self):
        report_data = {
            "url": "https://example.com",
            "brand_name": "Example Co",
            "date": "2026-03-17",
            "geo_score": 52,
            "scores": {
                "ai_citability": 28,
                "brand_authority": 40,
                "content_eeat": 65,
                "technical": 80,
                "schema": 70,
                "platform_optimization": 50,
            },
            "executive_summary": "Summary",
            "report_sections": {
                "executive_summary": {
                    "overview": "Strategic overview",
                    "by_audience": {
                        "cto": "CTO summary",
                        "marketing_manager": "Marketing summary",
                        "developers": "Developer summary",
                    },
                },
                "readiness_scorecard": {
                    "geo_score": 52,
                    "components": [{"label": "AI Citability", "score": 28}],
                },
                "opportunity_map": {
                    "clusters": [{"label": "example-co", "priority": "high"}]
                },
                "competitor_gap_analysis": {
                    "competitors": [{"name": "Competitor A"}]
                },
                "citation_diagnosis": {
                    "failures": [{"query": "example geo strategy"}]
                },
                "entity_authority_analysis": {
                    "entity_name": "Example Co"
                },
                "roadmap": {
                    "thirty_day": ["Fix llms.txt"],
                    "sixty_day": ["Improve schema"],
                    "ninety_day": ["Expand entity authority"],
                },
                "developer_appendix": {
                    "notes": ["Keep SSR enabled"]
                },
                "evidence_appendix": {
                    "methodology": ["ReportModel-driven"],
                    "evidence_items": ["Citability scored 28/100"],
                },
            },
            "findings": [],
            "quick_wins": [],
            "medium_term": [],
            "strategic": [],
            "crawler_access": {},
            "rescience_pass": {},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "report.pdf"
            txt_path = Path(temp_dir) / "report.txt"

            generate_workbook_report(report_data, str(pdf_path))
            subprocess.run(
                ["pdftotext", str(pdf_path), str(txt_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            pdf_text = txt_path.read_text(encoding="utf-8")

        self.assertIn("Decision Summary", pdf_text)
        self.assertIn("Query Universe", pdf_text)
        self.assertIn("Competitor Visibility", pdf_text)
        self.assertIn("Competitor A", pdf_text)
        self.assertIn("Citation Diagnosis", pdf_text)
        self.assertIn("Entity and Trust Graph", pdf_text)
        self.assertIn("30/60/90 Execution Ledger", pdf_text)
        self.assertIn("Developer Appendix", pdf_text)
        self.assertIn("Evidence and Methodology Appendix", pdf_text)

    def test_workbook_pdf_generation_normalizes_long_labels_and_keeps_strategist_tables_within_page_width(self):
        report_data = {
            "url": "https://example.com",
            "brand_name": "Example Co",
            "date": "2026-03-17",
            "geo_score": 52,
            "scores": {
                "ai_citability": 28,
                "brand_authority": 40,
                "content_eeat": 65,
                "technical": 80,
                "schema": 70,
                "platform_optimization": 50,
            },
            "executive_summary": "Summary",
            "report_sections": {
                "executive_summary": {
                    "overview": "Strategic overview",
                    "by_audience": {
                        "cto": "CTO summary",
                        "marketing_manager": "Marketing summary",
                        "developers": "Developer summary",
                    },
                },
                "readiness_scorecard": {
                    "geo_score": 52,
                    "components": [
                        {"label": "AI Citability", "score": 28, "weight": 25, "status": "urgent"}
                    ],
                    "platforms": [
                        {"platform": "ChatGPT", "score": 74, "status": "steady"}
                    ],
                    "priority_risks": [{"issue": "Low AI citability"}],
                },
                "opportunity_map": {"clusters": [{"label": "example-co"}]},
                "competitor_gap_analysis": {"competitors": [{"name": "Competitor A"}]},
                "citation_diagnosis": {
                    "failures": [
                        {
                            "query": "services-we-provide-professional-and-complete-all-in-one-service-for-the-clients-to-enjoy-services-from-life-insurance-annuity-and-financial-management",
                        }
                    ]
                },
                "entity_authority_analysis": {
                    "earned_media_signals": [
                        "https://www.linkedin.com/company/example",
                        "https://www.youtube.com/channel/example",
                    ]
                },
                "roadmap": {
                    "thirty_day": ["Fix llms.txt", "Fix llms.txt"],
                    "sixty_day": ["Improve schema", "Improve schema"],
                    "ninety_day": ["Expand entity authority", "Expand entity authority"],
                },
                "developer_appendix": {"technical_actions": ["Keep SSR enabled"]},
                "evidence_appendix": {
                    "methodology": ["ReportModel-driven"],
                    "evidence_items": ["Citability scored 28/100"],
                },
            },
            "findings": [],
            "quick_wins": [],
            "medium_term": [],
            "strategic": [],
            "crawler_access": {},
            "rescience_pass": {},
        }

        widths = []

        from scripts import generate_pdf_report as pdf_module

        original = pdf_module.build_wrapped_table

        def capture_widths(rows, col_widths, styles, header_rows=1, header_color=None):
            widths.append(sum(col_widths))
            return original(
                rows,
                col_widths,
                styles,
                header_rows=header_rows,
                header_color=header_color if header_color is not None else pdf_module.PRIMARY,
            )

        with patch("scripts.generate_pdf_report.build_wrapped_table", side_effect=capture_widths):
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_path = Path(temp_dir) / "report.pdf"
                txt_path = Path(temp_dir) / "report.txt"
                generate_workbook_report(report_data, str(pdf_path))
                subprocess.run(
                    ["pdftotext", str(pdf_path), str(txt_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                pdf_text = txt_path.read_text(encoding="utf-8")

        self.assertFalse(any(total > 512 for total in widths))
        self.assertNotIn(
            "services-we-provide-professional-and-complete-all-in-one-service-for-the-clients-to-enjoy",
            pdf_text,
        )
        self.assertEqual(pdf_text.count("Fix llms.txt"), 1)


if __name__ == "__main__":
    unittest.main()
