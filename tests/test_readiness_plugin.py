import unittest

from scripts.strategy_engine import AnalysisContext, SiteSnapshot, StrategyOrchestrator
from scripts.strategy_engine.plugins.readiness import ReadinessInputs, ReadinessPlugin


class ReadinessPluginTest(unittest.TestCase):
    def test_readiness_plugin_reads_inputs_from_context_metadata(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
            metadata={
                "readiness": {
                    "page_data": {
                        "url": "https://example.com",
                        "title": "Example Co",
                        "word_count": 320,
                        "text_content": "Jane Smith wrote this in March about Example Co.",
                        "meta_tags": {"article:modified_time": "2026-03-18"},
                        "internal_links": [{"url": "https://example.com/author/jane"}],
                        "external_links": [],
                        "structured_data": [],
                        "status_code": 200,
                        "has_ssr_content": True,
                        "security_headers": {
                            "Strict-Transport-Security": "max-age=31536000",
                            "Content-Security-Policy": "default-src 'self'",
                        },
                    },
                    "robots_data": {"exists": True},
                    "llms_validation": {
                        "exists": True,
                        "format_valid": True,
                        "issues": [],
                    },
                    "llms_live": {"llms_txt": {"exists": True}},
                    "sitemap_pages": ["https://example.com/"],
                    "citability_data": {"average_citability_score": 60.0},
                    "brand_data": {},
                    "rescience_pass": {},
                }
            },
        )

        result = StrategyOrchestrator([ReadinessPlugin()]).execute(context)

        self.assertEqual(
            result.plugin_results["readiness"]["inputs"]["page_data"]["title"],
            "Example Co",
        )
        self.assertTrue(
            result.plugin_results["readiness"]["inputs"]["llms_validation"][
                "format_valid"
            ]
        )

    def test_readiness_plugin_emits_geo_scores_and_platform_scores(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
        )

        result = StrategyOrchestrator(
            [
                ReadinessPlugin(
                    ReadinessInputs(
                        page_data={
                            "url": "https://example.com",
                            "title": "Example Co | Example Co",
                            "word_count": 650,
                            "text_content": "Jane Smith wrote this in March about Example Co.",
                            "meta_tags": {"article:modified_time": "2026-03-18"},
                            "internal_links": [{"url": "https://example.com/author/jane"}],
                            "external_links": [
                                {"url": "https://www.linkedin.com/company/example"},
                                {"url": "https://www.wikiwand.com/en/Example"},
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
                            "status_code": 200,
                            "has_ssr_content": True,
                            "security_headers": {
                                "Strict-Transport-Security": "max-age=31536000",
                                "Content-Security-Policy": "default-src 'self'",
                            },
                        },
                        robots_data={"exists": True},
                        llms_validation={
                            "exists": True,
                            "format_valid": True,
                            "issues": [],
                        },
                        llms_live={"llms_txt": {"exists": True}},
                        sitemap_pages=[
                            "https://example.com/",
                            "https://example.com/about",
                        ],
                        citability_data={"average_citability_score": 72.0},
                        brand_data={
                            "platforms": {"wikipedia": {"has_wikipedia_page": True}}
                        },
                    )
                )
            ]
        ).execute(context)
        readiness = result.plugin_results["readiness"]

        self.assertEqual(readiness["geo_scores"]["geo_score"], 68)
        self.assertEqual(readiness["geo_scores"]["scores"]["technical"], 90)
        self.assertEqual(readiness["platforms"]["ChatGPT"], 71)
        self.assertEqual(readiness["platforms"]["Google AI Overviews"], 67)
        self.assertTrue(
            readiness["inputs"]["brand_data"]["platforms"]["wikipedia"]["has_wikipedia_page"]
        )

    def test_readiness_plugin_handles_top_level_schema_and_list_valued_types(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
            metadata={
                "readiness": {
                    "page_data": {
                        "url": "https://example.com",
                        "title": "Example Co",
                        "word_count": 100,
                        "text_content": "Short copy.",
                        "external_links": [],
                        "structured_data": [
                            {
                                "@type": ["Organization", "WebSite"],
                                "sameAs": [
                                    "https://www.linkedin.com/company/example"
                                ],
                            },
                            {
                                "@graph": [
                                    {
                                        "@type": ["Organization", "FAQPage"],
                                        "sameAs": [
                                            "https://x.com/example"
                                        ],
                                    }
                                ]
                            },
                        ],
                        "status_code": 200,
                        "has_ssr_content": True,
                        "security_headers": {},
                    },
                    "robots_data": {"exists": False},
                    "llms_validation": {"exists": False},
                    "llms_live": {"llms_txt": {"exists": False}},
                    "sitemap_pages": [],
                    "citability_data": {"average_citability_score": 10.0},
                    "brand_data": {},
                    "rescience_pass": {},
                }
            },
        )

        result = StrategyOrchestrator([ReadinessPlugin()]).execute(context)
        readiness = result.plugin_results["readiness"]

        self.assertEqual(readiness["geo_scores"]["scores"]["brand_authority"], 31)
        self.assertEqual(readiness["geo_scores"]["scores"]["schema"], 48)

    def test_readiness_platform_scores_do_not_gain_from_rescience_faq_suggestion(self):
        base_inputs = {
            "page_data": {
                "url": "https://example.com",
                "title": "Example Co",
                "word_count": 100,
                "text_content": "Short copy.",
                "external_links": [],
                "structured_data": [],
                "status_code": 200,
                "has_ssr_content": True,
                "security_headers": {},
            },
            "robots_data": {"exists": False},
            "llms_validation": {"exists": False},
            "llms_live": {"llms_txt": {"exists": False}},
            "sitemap_pages": [],
            "citability_data": {"average_citability_score": 10.0},
            "brand_data": {},
        }

        without_rescience = StrategyOrchestrator(
            [ReadinessPlugin(ReadinessInputs(**base_inputs, rescience_pass={}))]
        ).execute(
            AnalysisContext(
                site_snapshot=SiteSnapshot(
                    url="https://example.com",
                    title="Example Co",
                    canonical_url="https://example.com",
                    fetched_at="2026-03-19T10:00:00Z",
                )
            )
        ).plugin_results["readiness"]["platforms"]

        with_rescience = StrategyOrchestrator(
            [
                ReadinessPlugin(
                    ReadinessInputs(
                        **base_inputs,
                        rescience_pass={
                            "geo_methods": [{"method": "FAQ Schema", "impact": "+40%"}]
                        },
                    )
                )
            ]
        ).execute(
            AnalysisContext(
                site_snapshot=SiteSnapshot(
                    url="https://example.com",
                    title="Example Co",
                    canonical_url="https://example.com",
                    fetched_at="2026-03-19T10:00:00Z",
                )
            )
        ).plugin_results["readiness"]["platforms"]

        self.assertEqual(with_rescience, without_rescience)

    def test_readiness_scores_invalid_existing_llms_lower_than_valid(self):
        base_inputs = {
            "page_data": {
                "url": "https://example.com",
                "title": "Example Co",
                "word_count": 100,
                "text_content": "Short copy.",
                "external_links": [],
                "structured_data": [],
                "status_code": 200,
                "has_ssr_content": True,
                "security_headers": {},
            },
            "robots_data": {"exists": False},
            "llms_live": {"llms_txt": {"exists": True}},
            "sitemap_pages": [],
            "citability_data": {"average_citability_score": 10.0},
            "brand_data": {},
            "rescience_pass": {},
        }

        valid = StrategyOrchestrator(
            [
                ReadinessPlugin(
                    ReadinessInputs(
                        **base_inputs,
                        llms_validation={"exists": True, "format_valid": True, "issues": []},
                    )
                )
            ]
        ).execute(
            AnalysisContext(
                site_snapshot=SiteSnapshot(
                    url="https://example.com",
                    title="Example Co",
                    canonical_url="https://example.com",
                    fetched_at="2026-03-19T10:00:00Z",
                )
            )
        ).plugin_results["readiness"]["geo_scores"]["scores"]["platform_optimization"]

        invalid = StrategyOrchestrator(
            [
                ReadinessPlugin(
                    ReadinessInputs(
                        **base_inputs,
                        llms_validation={
                            "exists": True,
                            "format_valid": False,
                            "issues": ["Missing title"],
                        },
                    )
                )
            ]
        ).execute(
            AnalysisContext(
                site_snapshot=SiteSnapshot(
                    url="https://example.com",
                    title="Example Co",
                    canonical_url="https://example.com",
                    fetched_at="2026-03-19T10:00:00Z",
                )
            )
        ).plugin_results["readiness"]["geo_scores"]["scores"]["platform_optimization"]

        self.assertGreater(valid, invalid)


if __name__ == "__main__":
    unittest.main()
