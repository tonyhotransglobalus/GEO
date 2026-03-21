import unittest

from scripts.strategy_engine import AnalysisContext, SiteSnapshot
from scripts.strategy_engine.plugins.competitive import (
    CitationDiagnosisPlugin,
    CompetitorAnalysisPlugin,
    EntityAnalysisPlugin,
)


class CompetitivePluginsTest(unittest.TestCase):
    def test_competitor_analysis_infers_profiles_from_serp_and_excludes_site_domain(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                canonical_url="https://example.com",
                title="Example Co",
            ),
            metadata={
                "opportunity": {
                    "site_domain": "example.com",
                    "serp_snapshots": {
                        "Example Co": [
                            {
                                "query": "Example Co",
                                "rank": 1,
                                "title": "Example Co",
                                "url": "https://example.com/",
                                "domain": "example.com",
                                "snippet": "Home",
                                "source": "duckduckgo",
                            },
                            {
                                "query": "Example Co",
                                "rank": 2,
                                "title": "Competitor One",
                                "url": "https://competitor-one.com/",
                                "domain": "competitor-one.com",
                                "snippet": "A direct competitor",
                                "source": "duckduckgo",
                            },
                            {
                                "query": "Example Co",
                                "rank": 3,
                                "title": "Competitor Two",
                                "url": "https://www.competitor-two.com/",
                                "domain": "www.competitor-two.com",
                                "snippet": "Another competitor",
                                "source": "duckduckgo",
                            },
                        ]
                    },
                }
            },
        )

        result = CompetitorAnalysisPlugin().analyze(context)

        self.assertEqual(
            [profile.domain for profile in result.competitor_profiles],
            ["competitor-one.com", "competitor-two.com"],
        )
        self.assertEqual(
            [profile.domain for profile in context.competitor_profiles],
            ["competitor-one.com", "competitor-two.com"],
        )
        self.assertEqual(result.summary["competitor_count"], 2)

    def test_competitor_analysis_separates_competitor_owned_earned_media_and_site_owned_sources(
        self,
    ):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                canonical_url="https://example.com",
                title="Example Co",
            ),
            metadata={
                "opportunity": {
                    "site_domain": "example.com",
                    "competitor_domains": ["competitor-one.com"],
                    "serp_snapshots": {
                        "Example Co": [
                            {
                                "query": "Example Co",
                                "rank": 1,
                                "title": "Example Co",
                                "url": "https://example.com/",
                                "domain": "example.com",
                                "snippet": "Home",
                                "source": "duckduckgo",
                            },
                            {
                                "query": "Example Co",
                                "rank": 2,
                                "title": "Competitor One comparison",
                                "url": "https://competitor-one.com/guide",
                                "domain": "competitor-one.com",
                                "snippet": "Direct competitor coverage",
                                "source": "duckduckgo",
                            },
                            {
                                "query": "Example Co",
                                "rank": 3,
                                "title": "Competitor Two services",
                                "url": "https://competitor-two.com/overview",
                                "domain": "competitor-two.com",
                                "snippet": "Another direct rival",
                                "source": "duckduckgo",
                            },
                            {
                                "query": "Example Co",
                                "rank": 4,
                                "title": "Industry coverage from News Site",
                                "url": "https://news-site.com/article",
                                "domain": "news-site.com",
                                "snippet": "Third-party coverage",
                                "source": "duckduckgo",
                            },
                        ]
                    },
                }
            },
        )

        result = CompetitorAnalysisPlugin().analyze(context)

        self.assertEqual(result.source_inventory["site_owned"], ["example.com"])
        self.assertEqual(
            result.source_inventory["competitor_owned"],
            ["competitor-one.com", "competitor-two.com"],
        )
        self.assertEqual(result.source_inventory["earned_media"], ["news-site.com"])
        self.assertEqual(result.summary["site_owned_count"], 1)
        self.assertEqual(result.summary["competitor_count"], 2)
        self.assertEqual(result.summary["earned_media_count"], 1)
        self.assertGreaterEqual(result.summary["authority_gap_count"], 1)

    def test_competitor_analysis_keeps_ambiguous_third_party_sources_out_of_competitor_owned(
        self,
    ):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                canonical_url="https://example.com",
                title="Example Co",
            ),
            metadata={
                "opportunity": {
                    "site_domain": "example.com",
                    "serp_snapshots": {
                        "Example Co": [
                            {
                                "query": "Example Co",
                                "rank": 1,
                                "title": "Example Co",
                                "url": "https://example.com/",
                                "domain": "example.com",
                                "snippet": "Home",
                                "source": "duckduckgo",
                            },
                            {
                                "query": "Example Co",
                                "rank": 2,
                                "title": "Industry analysis",
                                "url": "https://analysis-hub.com/article",
                                "domain": "analysis-hub.com",
                                "snippet": "Third-party coverage",
                                "source": "duckduckgo",
                            },
                        ]
                    },
                }
            },
        )

        result = CompetitorAnalysisPlugin().analyze(context)

        self.assertNotIn("analysis-hub.com", result.source_inventory["competitor_owned"])
        self.assertIn("analysis-hub.com", result.source_inventory["earned_media"])
        self.assertEqual(result.summary["competitor_count"], 0)

    def test_entity_analysis_builds_graph_from_schema_sameas_and_brand_signals(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                canonical_url="https://example.com",
                title="Example Co",
                structured_data=[
                    {
                        "@graph": [
                            {
                                "@type": "Organization",
                                "name": "Example Co",
                                "sameAs": [
                                    "https://www.linkedin.com/company/example",
                                    "https://www.wikidata.org/wiki/Q123",
                                ],
                            },
                            {
                                "@type": "WebSite",
                                "name": "Example Co",
                            },
                        ]
                    }
                ],
                external_links=["https://www.linkedin.com/company/example"],
            ),
            metadata={
                "brand_data": {
                    "platforms": {
                        "wikipedia": {
                            "has_wikipedia_page": False,
                            "has_wikidata_entry": True,
                        }
                    }
                },
                "readiness": {
                    "page_data": {
                        "structured_data": [
                            {
                                "@graph": [
                                    {
                                        "@type": "Organization",
                                        "sameAs": [
                                            "https://www.linkedin.com/company/example"
                                        ],
                                    }
                                ]
                            }
                        ],
                        "external_links": [
                            {"url": "https://www.linkedin.com/company/example"}
                        ],
                    },
                    "brand_data": {
                        "platforms": {
                            "wikipedia": {
                                "has_wikipedia_page": False,
                                "has_wikidata_entry": True,
                            }
                        }
                    },
                },
            },
        )

        result = EntityAnalysisPlugin().analyze(context)

        self.assertEqual(result.entity_graph.entity_name, "Example Co")
        self.assertIn("https://www.linkedin.com/company/example", result.entity_graph.same_as)
        self.assertIn("wikidata", result.entity_graph.attributes["signals"])
        self.assertIsNotNone(context.entity_graph)
        self.assertEqual(context.entity_graph.entity_name, "Example Co")

    def test_citation_diagnosis_emits_failures_with_recommendations(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                canonical_url="https://example.com",
                title="Example Co",
            ),
            metadata={
                "readiness": {
                    "geo_scores": {"scores": {"ai_citability": 24, "technical": 64}},
                    "opportunity": {
                        "opportunities": [
                            {
                                "query": "Example Co pricing",
                                "site_visible": False,
                                "opportunity_score": 82,
                                "label": "high",
                            },
                            {
                                "query": "Example Co",
                                "site_visible": True,
                                "opportunity_score": 18,
                                "label": "low",
                            },
                        ]
                    },
                },
                "competitive": {
                    "competitor_profiles": [
                        {"name": "Competitor One", "domain": "competitor-one.com"}
                    ]
                },
                "entity_graph": {
                    "entity_name": "Example Co",
                    "same_as": [],
                    "related_entities": [],
                    "attributes": {},
                },
            },
        )

        result = CitationDiagnosisPlugin().analyze(context)

        self.assertGreaterEqual(len(result.citation_failures), 1)
        self.assertIn(
            result.citation_failures[0].failure_mode,
            {"non_visible_query", "weak_entity_support"},
        )
        self.assertTrue(result.citation_failures[0].recommended_fix)
        self.assertEqual(context.citation_failures, result.citation_failures)

    def test_citation_diagnosis_does_not_treat_generic_commercial_queries_as_branded(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                canonical_url="https://example.com",
                title="Example Co",
            ),
            metadata={
                "readiness": {
                    "geo_scores": {"scores": {"ai_citability": 82}},
                    "opportunity": {
                        "opportunities": [
                            {
                                "query": "best crm software",
                                "site_visible": True,
                                "opportunity_score": 18,
                                "label": "low",
                            }
                        ]
                    },
                },
                "entity_graph": {
                    "entity_name": "Example Co",
                    "same_as": [],
                    "related_entities": [],
                    "attributes": {},
                    "confidence": 0.2,
                },
            },
        )

        result = CitationDiagnosisPlugin().analyze(context)

        self.assertEqual(result.citation_failures, [])

    def test_citation_diagnosis_classifies_freshness_and_attribution_gaps(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                canonical_url="https://example.com",
                title="Example Co",
            ),
            metadata={
                "readiness": {
                    "geo_scores": {"scores": {"ai_citability": 78, "technical": 64}},
                    "opportunity": {
                        "opportunities": [
                            {
                                "query": "latest example co pricing",
                                "site_visible": True,
                                "opportunity_score": 34,
                                "label": "medium",
                            },
                            {
                                "query": "example co source citation",
                                "site_visible": True,
                                "opportunity_score": 30,
                                "label": "medium",
                            },
                        ]
                    },
                },
                "entity_graph": {
                    "entity_name": "Example Co",
                    "same_as": [],
                    "related_entities": [],
                    "attributes": {},
                    "confidence": 0.8,
                },
            },
        )

        result = CitationDiagnosisPlugin().analyze(context)

        self.assertIn("freshness_gap", [item.failure_mode for item in result.citation_failures])
        self.assertIn("attribution_gap", [item.failure_mode for item in result.citation_failures])
        self.assertEqual(context.citation_failures, result.citation_failures)

    def test_citation_diagnosis_prefers_non_visible_query_over_freshness_and_attribution(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                canonical_url="https://example.com",
                title="Example Co",
            ),
            metadata={
                "readiness": {
                    "geo_scores": {"scores": {"ai_citability": 78, "technical": 64}},
                    "opportunity": {
                        "opportunities": [
                            {
                                "query": "latest example pricing",
                                "site_visible": False,
                                "opportunity_score": 80,
                                "label": "high",
                            },
                            {
                                "query": "example sources",
                                "site_visible": False,
                                "opportunity_score": 80,
                                "label": "high",
                            },
                        ]
                    },
                },
                "entity_graph": {
                    "entity_name": "Example Co",
                    "same_as": [],
                    "related_entities": [],
                    "attributes": {},
                    "confidence": 0.8,
                },
            },
        )

        result = CitationDiagnosisPlugin().analyze(context)

        self.assertEqual(
            [item.failure_mode for item in result.citation_failures],
            ["non_visible_query", "non_visible_query"],
        )
        self.assertNotIn("freshness_gap", [item.failure_mode for item in result.citation_failures])
        self.assertNotIn("attribution_gap", [item.failure_mode for item in result.citation_failures])

    def test_entity_analysis_prefers_brand_side_of_home_brand_titles(self):
        context = AnalysisContext(
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                canonical_url="https://example.com",
                title="Home | Example Co",
            ),
            metadata={
                "brand_data": {
                    "platforms": {"wikipedia": {"has_wikipedia_page": False}}
                }
            },
        )

        result = EntityAnalysisPlugin().analyze(context)

        self.assertEqual(result.entity_graph.entity_name, "Example Co")
        self.assertEqual(context.entity_graph.entity_name, "Example Co")


if __name__ == "__main__":
    unittest.main()
