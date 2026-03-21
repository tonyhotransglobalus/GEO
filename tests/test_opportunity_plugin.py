import unittest
from unittest.mock import patch

from scripts.strategy_engine import AnalysisContext, SiteSnapshot, StrategyOrchestrator


class OpportunityPluginTest(unittest.TestCase):
    def test_opportunity_module_exposes_distinct_plugin_units(self):
        from scripts.strategy_engine.plugins.opportunity import (
            KeywordResearchPlugin,
            OpportunityPlugin,
            SerpAnalysisPlugin,
        )

        self.assertEqual(KeywordResearchPlugin.name, "keyword_research")
        self.assertEqual(SerpAnalysisPlugin.name, "serp_analysis")
        self.assertEqual(OpportunityPlugin.name, "opportunity")

    def test_opportunity_plugin_reads_metadata_and_populates_query_clusters(self):
        from scripts.strategy_engine.plugins.opportunity import (
            KeywordResearchPlugin,
            OpportunityPlugin,
            SerpAnalysisPlugin,
        )

        def fake_get(url, params=None, headers=None, timeout=None):
            class FakeResponse:
                status_code = 200

                def __init__(self, url: str):
                    self.url = url

                def json(self):
                    return [
                        {"phrase": "geo strategy examples"},
                        {"phrase": "geo strategy checklist"},
                    ]

                @property
                def text(self):
                    return """
                    <html>
                      <body>
                        <div class="result">
                          <a class="result__a" href="https://competitor-a.com/guide">
                            Competitor A guide
                          </a>
                          <a class="result__snippet">Competitor A is ranked for this topic.</a>
                        </div>
                        <div class="result">
                          <a class="result__a" href="https://competitor-b.com/overview">
                            Competitor B overview
                          </a>
                          <a class="result__snippet">Another public result.</a>
                        </div>
                      </body>
                    </html>
                    """

            return FakeResponse(url)

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
            metadata={
                "opportunity": {
                    "seed_topics": ["geo strategy"],
                    "competitor_domains": ["competitor-a.com"],
                    "result_limit": 2,
                    "locale": "en-us",
                }
            },
        )

        with patch(
            "scripts.strategy_engine.plugins.opportunity.requests.get",
            side_effect=fake_get,
        ):
            result = StrategyOrchestrator(
                [KeywordResearchPlugin(), SerpAnalysisPlugin(), OpportunityPlugin()]
            ).execute(context)

        self.assertIn("keyword_research", result.plugin_results)
        self.assertIn("serp_analysis", result.plugin_results)
        self.assertIn("opportunity", result.plugin_results)
        self.assertGreaterEqual(len(context.query_clusters), 1)
        self.assertEqual(context.query_clusters[0].label, "geo-strategy")
        self.assertIn("geo strategy examples", context.query_clusters[0].queries)
        self.assertFalse(
            result.plugin_results["opportunity"]["opportunities"][0]["site_visible"],
            "expected a high-opportunity query when the site does not appear in sampled results",
        )
        self.assertEqual(
            result.plugin_results["opportunity"]["query_clusters"][0]["metadata"][
                "seed_topic"
            ],
            "geo strategy",
        )
        self.assertEqual(
            result.plugin_results["keyword_research"]["keyword_suggestions"][
                "geo strategy"
            ],
            ["geo strategy examples", "geo strategy checklist"],
        )
        self.assertEqual(
            result.plugin_results["serp_analysis"]["serp_snapshots"]["geo strategy"][0][
                "domain"
            ],
            "competitor-a.com",
        )

    def test_opportunity_plugin_defaults_to_site_title_when_inputs_are_missing(self):
        from scripts.strategy_engine.plugins.opportunity import (
            OpportunityPlugin,
        )

        def fake_get(url, params=None, headers=None, timeout=None):
            class FakeResponse:
                status_code = 200

                def __init__(self, url: str):
                    self.url = url

                def json(self):
                    return []

                @property
                def text(self):
                    return "<html><body></body></html>"

            return FakeResponse(url)

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co | GEO Strategy",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            )
        )

        with patch(
            "scripts.strategy_engine.plugins.opportunity.requests.get",
            side_effect=fake_get,
        ):
            result = StrategyOrchestrator([OpportunityPlugin()]).execute(context)

        self.assertTrue(context.query_clusters)
        self.assertEqual(
            result.plugin_results["opportunity"]["inputs"]["seed_topics"][:2],
            ["Example Co", "GEO Strategy"],
        )
        self.assertEqual(context.query_clusters[0].metadata["site_visible"], False)

    def test_opportunity_plugin_fallback_seed_avoids_raw_url_cluster_labels(self):
        from scripts.strategy_engine.plugins.opportunity import OpportunityPlugin

        def fake_get(url, params=None, headers=None, timeout=None):
            class FakeResponse:
                status_code = 200

                def __init__(self, url: str):
                    self.url = url

                def json(self):
                    return []

                @property
                def text(self):
                    return "<html><body></body></html>"

            return FakeResponse(url)

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://www.example.com/services/geo-seo?ref=home",
                title=None,
                canonical_url="https://www.example.com/services/geo-seo?ref=home",
                fetched_at="2026-03-19T10:00:00Z",
            ),
            metadata={"opportunity": {"result_limit": 1, "locale": "en-us"}},
        )

        with patch(
            "scripts.strategy_engine.plugins.opportunity.requests.get",
            side_effect=fake_get,
        ):
            result = StrategyOrchestrator([OpportunityPlugin()]).execute(context)

        self.assertTrue(result.plugin_results["opportunity"]["inputs"]["seed_topics"])
        self.assertNotEqual(
            result.plugin_results["opportunity"]["query_clusters"][0]["label"],
            "https-example-com-services-geo-seo-ref-home",
        )
        self.assertNotIn(
            "https://www.example.com/services/geo-seo?ref=home",
            result.plugin_results["opportunity"]["query_clusters"][0]["queries"],
        )

    def test_opportunity_plugin_normalizes_long_service_blob_cluster_labels(self):
        from scripts.strategy_engine.plugins.opportunity import (
            KeywordResearchPlugin,
            OpportunityPlugin,
            SerpAnalysisPlugin,
        )

        long_service_blob = (
            "services-we-provide-professional-and-complete-all-in-one-service-for-the-clients-"
            "to-enjoy-services-from-life-insurance-annuity-and-financial-management-to-now-"
            "encompassing-mortgage-financing-real-estate-asset-management-health-insurance-"
            "and-property-casualty-insurance-life-annuities"
        )

        def fake_get(url, params=None, headers=None, timeout=None):
            class FakeResponse:
                status_code = 200

                def __init__(self, url: str):
                    self.url = url

                def json(self):
                    return [
                        {"phrase": "life insurance"},
                        {"phrase": "mortgage financing"},
                        {"phrase": "asset management"},
                    ]

                @property
                def text(self):
                    return """
                    <html>
                      <body>
                        <div class="result">
                          <a class="result__a" href="https://example.com/life-insurance">
                            Life insurance services
                          </a>
                        </div>
                      </body>
                    </html>
                    """

            return FakeResponse(url)

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
            metadata={
                "opportunity": {
                    "seed_topics": [long_service_blob],
                    "competitor_domains": ["competitor-a.com"],
                    "result_limit": 1,
                    "locale": "en-us",
                }
            },
        )

        with patch(
            "scripts.strategy_engine.plugins.opportunity.requests.get",
            side_effect=fake_get,
        ):
            result = StrategyOrchestrator(
                [KeywordResearchPlugin(), SerpAnalysisPlugin(), OpportunityPlugin()]
            ).execute(context)

        cluster_label = result.plugin_results["opportunity"]["query_clusters"][0]["label"]
        self.assertLess(len(cluster_label), 40)
        self.assertNotEqual(cluster_label, "services-we-provide-professional-and-complete-all-in-one-service-for-the-clients-to-enjoy-services-from-life-insurance-annuity-and-financial-management-to-now-encompassing-mortgage-financing-real-estate-asset-management-health-insurance-and-property-casualty-insurance-life-annuities")
        self.assertIn(
            cluster_label,
            {
                "life-insurance",
                "annuities",
                "annuity",
                "mortgage-financing",
                "real-estate",
                "asset-management",
                "health-insurance",
                "property-casualty-insurance",
            },
        )
        self.assertEqual(context.query_clusters[0].label, cluster_label)
        self.assertNotIn(
            long_service_blob,
            result.plugin_results["opportunity"]["query_clusters"][0]["queries"],
        )
        self.assertEqual(
            result.plugin_results["opportunity"]["seed_topics"],
            ["life insurance"],
        )
        self.assertEqual(
            result.plugin_results["keyword_research"]["seed_topics"],
            ["life insurance"],
        )
        self.assertEqual(
            result.plugin_results["serp_analysis"]["seed_topics"],
            ["life insurance"],
        )
        self.assertEqual(
            result.plugin_results["opportunity"]["opportunities"][0]["query"],
            "life insurance",
        )
        self.assertEqual(
            list(result.plugin_results["opportunity"]["keyword_suggestions"].keys()),
            ["life insurance"],
        )
        self.assertEqual(
            list(result.plugin_results["opportunity"]["serp_snapshots"].keys()),
            ["life insurance"],
        )
        self.assertEqual(
            result.plugin_results["opportunity"]["query_clusters"][0]["metadata"][
                "seed_topic_raw"
            ],
            long_service_blob,
        )
        self.assertEqual(
            result.plugin_results["opportunity"]["opportunities"][0]["seed_topic_raw"],
            long_service_blob,
        )

    def test_opportunity_plugin_preserves_raw_traceability_for_surviving_cluster_seed(self):
        from scripts.strategy_engine.plugins.opportunity import (
            KeywordResearchPlugin,
            OpportunityPlugin,
            SerpAnalysisPlugin,
        )

        long_service_blob = (
            "services-we-provide-professional-and-complete-all-in-one-service-for-the-clients-"
            "to-enjoy-consistent-support-with-expert-guidance-and-tailored-solutions-for-every-"
            "customer-needs-and-business-goals"
        )

        def fake_get(url, params=None, headers=None, timeout=None):
            class FakeResponse:
                status_code = 200

                def __init__(self, url: str):
                    self.url = url

                def json(self):
                    return [{"phrase": "life insurance"}]

                @property
                def text(self):
                    return """
                    <html>
                      <body>
                        <div class="result">
                          <a class="result__a" href="https://example.com/life-insurance">
                            Life insurance services
                          </a>
                        </div>
                      </body>
                    </html>
                    """

            return FakeResponse(url)

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
            metadata={
                "opportunity": {
                    "seed_topics": [long_service_blob, "life insurance"],
                    "competitor_domains": ["competitor-a.com"],
                    "result_limit": 1,
                    "locale": "en-us",
                }
            },
        )

        with patch(
            "scripts.strategy_engine.plugins.opportunity.requests.get",
            side_effect=fake_get,
        ):
            result = StrategyOrchestrator(
                [KeywordResearchPlugin(), SerpAnalysisPlugin(), OpportunityPlugin()]
            ).execute(context)

        self.assertEqual(result.plugin_results["opportunity"]["seed_topics"], ["life insurance"])
        self.assertEqual(result.plugin_results["keyword_research"]["seed_topics"], ["life insurance"])
        self.assertEqual(result.plugin_results["serp_analysis"]["seed_topics"], ["life insurance"])
        self.assertEqual(
            result.plugin_results["opportunity"]["query_clusters"][0]["metadata"]["seed_topic"],
            "life insurance",
        )
        self.assertEqual(
            result.plugin_results["opportunity"]["query_clusters"][0]["metadata"]["seed_topic_raw"],
            "life insurance",
        )
        self.assertEqual(
            result.plugin_results["opportunity"]["opportunities"][0]["seed_topic_raw"],
            "life insurance",
        )
        self.assertNotEqual(
            result.plugin_results["opportunity"]["query_clusters"][0]["metadata"]["seed_topic_raw"],
            long_service_blob,
        )
        self.assertNotEqual(
            result.plugin_results["opportunity"]["opportunities"][0]["seed_topic_raw"],
            long_service_blob,
        )

    def test_opportunity_plugin_promotes_service_line_terms_into_short_cluster_labels(self):
        from scripts.strategy_engine.plugins.opportunity import OpportunityPlugin

        def fake_get(url, params=None, headers=None, timeout=None):
            class FakeResponse:
                status_code = 200

                def __init__(self, url: str):
                    self.url = url

                def json(self):
                    return [
                        {"phrase": "life insurance"},
                        {"phrase": "service line overview"},
                    ]

                @property
                def text(self):
                    return "<html><body></body></html>"

            return FakeResponse(url)

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
            metadata={
                "opportunity": {
                    "seed_topics": ["business services"],
                    "result_limit": 1,
                    "locale": "en-us",
                }
            },
        )

        with patch(
            "scripts.strategy_engine.plugins.opportunity.requests.get",
            side_effect=fake_get,
        ):
            result = StrategyOrchestrator([OpportunityPlugin()]).execute(context)

        self.assertEqual(
            result.plugin_results["opportunity"]["query_clusters"][0]["label"],
            "life-insurance",
        )
        self.assertEqual(context.query_clusters[0].label, "life-insurance")
        self.assertEqual(result.plugin_results["opportunity"]["opportunities"][0]["query"], "life insurance")
        self.assertIn("life insurance", result.plugin_results["opportunity"]["query_clusters"][0]["queries"])

    def test_opportunity_plugin_canonicalizes_property_casualty_variants(self):
        from scripts.strategy_engine.plugins.opportunity import (
            KeywordResearchPlugin,
            OpportunityPlugin,
            SerpAnalysisPlugin,
        )

        def fake_get(url, params=None, headers=None, timeout=None):
            class FakeResponse:
                status_code = 200

                def __init__(self, url: str):
                    self.url = url

                def json(self):
                    return [
                        {"phrase": "property/casualty insurance"},
                    ]

                @property
                def text(self):
                    return "<html><body></body></html>"

            return FakeResponse(url)

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
            metadata={
                "opportunity": {
                    "seed_topics": ["property/casualty insurance"],
                    "result_limit": 1,
                    "locale": "en-us",
                }
            },
        )

        with patch(
            "scripts.strategy_engine.plugins.opportunity.requests.get",
            side_effect=fake_get,
        ):
            result = StrategyOrchestrator(
                [KeywordResearchPlugin(), SerpAnalysisPlugin(), OpportunityPlugin()]
            ).execute(context)

        self.assertEqual(
            result.plugin_results["opportunity"]["query_clusters"][0]["label"],
            "property-and-casualty-insurance",
        )
        self.assertEqual(
            result.plugin_results["opportunity"]["seed_topics"],
            ["property and casualty insurance"],
        )
        self.assertEqual(
            result.plugin_results["keyword_research"]["seed_topics"],
            ["property and casualty insurance"],
        )
        self.assertEqual(
            result.plugin_results["serp_analysis"]["seed_topics"],
            ["property and casualty insurance"],
        )
        self.assertEqual(
            result.plugin_results["opportunity"]["opportunities"][0]["query"],
            "property and casualty insurance",
        )
        self.assertEqual(
            list(result.plugin_results["opportunity"]["keyword_suggestions"].keys()),
            ["property and casualty insurance"],
        )
        self.assertEqual(
            list(result.plugin_results["opportunity"]["serp_snapshots"].keys()),
            ["property and casualty insurance"],
        )
        self.assertIn(
            "property and casualty insurance",
            result.plugin_results["opportunity"]["query_clusters"][0]["queries"],
        )

    def test_serp_analysis_plugin_respects_constructor_seed_topics(self):
        from scripts.strategy_engine.plugins.opportunity import (
            OpportunityInputs,
            SerpAnalysisPlugin,
        )

        def fake_get(url, params=None, headers=None, timeout=None):
            class FakeResponse:
                status_code = 200

                def __init__(self, url: str):
                    self.url = url

                @property
                def text(self):
                    return """
                    <html>
                      <body>
                        <div class="result">
                          <a class="result__a" href="https://example.com/explicit">
                            Explicit seed result
                          </a>
                        </div>
                      </body>
                    </html>
                    """

            return FakeResponse(url)

        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
                fetched_at="2026-03-19T10:00:00Z",
            ),
        )
        inputs = OpportunityInputs(
            seed_topics=["explicit seed"],
            result_limit=1,
            locale="en-us",
        )

        with patch(
            "scripts.strategy_engine.plugins.opportunity.requests.get",
            side_effect=fake_get,
        ):
            result = StrategyOrchestrator([SerpAnalysisPlugin(inputs)]).execute(context)

        self.assertEqual(result.plugin_results["serp_analysis"]["seed_topics"], ["explicit seed"])
        self.assertIn("explicit seed", result.plugin_results["serp_analysis"]["serp_snapshots"])
        self.assertEqual(
            result.plugin_results["serp_analysis"]["serp_snapshots"]["explicit seed"][0][
                "title"
            ],
            "Explicit seed result",
        )


if __name__ == "__main__":
    unittest.main()
