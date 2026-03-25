import unittest

from scripts.strategy_engine import (
    CitationFailure,
    CompetitorProfile,
    EntityGraph,
    QueryCluster,
    ReportModel,
    SiteSnapshot,
)
from scripts.strategy_engine.core import evidence_source_tag
from scripts.strategy_engine.reporting import (
    build_client_report_sections,
    build_report_sections,
)


class ReportSectionsBuilderTest(unittest.TestCase):
    def test_build_client_report_sections_returns_expected_keys_and_market_metadata(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
            query_clusters=[
                QueryCluster(
                    label="example-co-ai-visibility",
                    queries=["example ai visibility"],
                    search_intent="informational",
                    priority="high",
                    metadata={"seed_topic": "Example AI visibility"},
                )
            ],
            competitor_profiles=[
                CompetitorProfile(
                    name="Competitor A",
                    domain="competitor-a.com",
                    strengths=["clear positioning"],
                )
            ],
            entity_graph=EntityGraph(
                entity_name="Example Co",
                canonical_url="https://example.com",
                same_as=["https://www.linkedin.com/company/example"],
                confidence=0.82,
            ),
            citation_failures=[
                CitationFailure(
                    query="example ai visibility",
                    target_url="https://example.com/guide",
                    failure_mode="weak_citation_support",
                    evidence=["AI citability is low"],
                    recommended_fix="Add answer-first blocks and supporting citations",
                )
            ],
            plugin_results={
                "readiness": {
                    "geo_scores": {
                        "geo_score": 78,
                        "scores": {
                            "ai_citability": 64,
                            "brand_authority": 58,
                            "content_eeat": 70,
                            "technical": 82,
                            "schema": 61,
                            "platform_optimization": 66,
                        },
                    },
                    "platforms": {"ChatGPT": 74, "Google AI Overviews": 79},
                },
                "opportunity": {
                    "opportunities": [
                        {
                            "query": "example ai visibility",
                            "search_intent": "informational",
                            "site_visible": False,
                            "opportunity_score": 67,
                            "label": "high",
                            "keyword_suggestions": ["example ai visibility guide"],
                            "serp_result_count": 3,
                            "competitor_hits": 2,
                            "site_domain": "example.com",
                            "top_domains": ["competitor-a.com", "review-site.com"],
                        }
                    ]
                },
                "competitor_analysis": {
                    "summary": {
                        "competitor_count": 1,
                        "earned_media_count": 1,
                    },
                    "source_inventory": {
                        "site_owned": ["example.com"],
                        "competitor_owned": ["competitor-a.com"],
                        "earned_media": ["review-site.com"],
                    },
                },
            },
        )

        sections = build_client_report_sections(
            report_model,
            {
                "geo_scores": {
                    "geo_score": 78,
                    "scores": {
                        "ai_citability": 64,
                        "brand_authority": 58,
                        "content_eeat": 70,
                        "technical": 82,
                        "schema": 61,
                        "platform_optimization": 66,
                    },
                },
                "platforms": {"ChatGPT": 74, "Google AI Overviews": 79},
                "page_data": {
                    "url": "https://example.com",
                    "title": "Example Co",
                    "h1_tags": ["Example Co"],
                    "word_count": 720,
                },
                "citability_data": {"average_citability_score": 64},
                "llms_validation": {"exists": True, "format_valid": True},
                "plugin_results": report_model.plugin_results,
                "findings": [
                    {
                        "severity": "critical",
                        "title": "Low citation readiness",
                        "summary": "AI systems struggle to quote the site.",
                        "leadership_impact": "The brand is missing high-intent AI visibility.",
                    }
                ],
                "quick_wins": ["Publish llms.txt."],
                "medium_term": ["Improve schema."],
                "strategic": ["Build recurring GEO content."],
            },
        )

        self.assertEqual(
            set(sections),
            {
                "cover",
                "decision_summary",
                "priority_risks",
                "top_opportunities",
                "market_snapshot",
                "roadmap",
                "methodology",
            },
        )
        self.assertEqual(sections["market_snapshot"]["confidence"], "supported")
        self.assertGreaterEqual(len(sections["market_snapshot"]["benchmark_rows"]), 2)
        self.assertIn("readiness_snapshot", sections["cover"])

    def test_build_client_report_sections_uses_sparse_market_fallback_and_dedupes_roadmap(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
            query_clusters=[
                QueryCluster(
                    label="services-we-provide-professional-and-complete-all-in-one-service-for-the-clients-to-enjoy",
                    queries=["service query"],
                    search_intent="informational",
                    priority="high",
                    metadata={"seed_topic": "Life Insurance"},
                )
            ],
        )

        sections = build_client_report_sections(
            report_model,
            {
                "geo_scores": {
                    "geo_score": 58,
                    "scores": {
                        "ai_citability": 28,
                        "brand_authority": 57,
                        "content_eeat": 75,
                        "technical": 80,
                        "schema": 76,
                        "platform_optimization": 48,
                    },
                },
                "platforms": {"ChatGPT": 55},
                "page_data": {
                    "url": "https://example.com",
                    "title": "Example Co",
                    "h1_tags": ["One", "Two"],
                    "word_count": 620,
                },
                "citability_data": {"average_citability_score": 28},
                "llms_validation": {"exists": False, "format_valid": False},
                "plugin_results": {
                    "competitor_analysis": {
                        "summary": {
                            "competitor_count": 0,
                            "earned_media_count": 0,
                        },
                        "source_inventory": {
                            "site_owned": ["example.com"],
                            "competitor_owned": [],
                            "earned_media": [],
                        },
                        "authority_gaps": [],
                    }
                },
                "findings": [
                    {
                        "severity": "high",
                        "title": "Heading hierarchy is diluted",
                        "summary": "The homepage has too many H1 tags.",
                        "leadership_impact": "The main message is harder to parse.",
                    }
                ],
                "quick_wins": [
                    "Publish llms.txt.",
                    "Publish llms.txt.",
                ],
                "medium_term": [
                    "Normalize heading hierarchy.",
                    "Normalize heading hierarchy.",
                ],
                "strategic": [
                    "Build recurring GEO content.",
                    "Build recurring GEO content.",
                ],
            },
        )

        self.assertEqual(sections["market_snapshot"]["confidence"], "limited")
        self.assertIn(
            "competitive picture is still incomplete",
            sections["market_snapshot"]["summary"].lower(),
        )
        self.assertEqual(sections["roadmap"]["thirty_day"], ["Publish llms.txt."])
        self.assertEqual(
            sections["roadmap"]["sixty_day"],
            ["Normalize heading hierarchy."],
        )
        self.assertEqual(
            sections["roadmap"]["ninety_day"],
            ["Build recurring GEO content."],
        )

    def test_build_report_sections_returns_required_keys_and_role_summaries(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
            query_clusters=[
                QueryCluster(
                    label="core-intent",
                    queries=["example geo strategy"],
                    search_intent="informational",
                    priority="high",
                    metadata={"seed_topic": "Example GEO strategy"},
                )
            ],
            competitor_profiles=[
                CompetitorProfile(
                    name="Competitor A",
                    domain="competitor-a.com",
                    strengths=["clear positioning"],
                )
            ],
            entity_graph=EntityGraph(
                entity_name="Example Co",
                canonical_url="https://example.com",
                same_as=["https://www.linkedin.com/company/example"],
                confidence=0.82,
            ),
            citation_failures=[
                CitationFailure(
                    query="example geo strategy",
                    target_url="https://example.com/guide",
                    failure_mode="weak_citation_support",
                    evidence=["AI citability is low"],
                    recommended_fix="Add answer-first blocks and supporting citations",
                )
            ],
            plugin_results={
                "readiness": {
                    "geo_scores": {
                        "geo_score": 78,
                        "scores": {
                            "ai_citability": 64,
                            "brand_authority": 58,
                            "content_eeat": 70,
                            "technical": 82,
                            "schema": 61,
                            "platform_optimization": 66,
                        },
                    },
                    "platforms": {"ChatGPT": 74, "Google AI Overviews": 79},
                },
                "opportunity": {
                    "opportunities": [
                        {
                            "query": "example geo strategy",
                            "search_intent": "informational",
                            "site_visible": False,
                            "opportunity_score": 67,
                            "label": "high",
                            "keyword_suggestions": ["example geo strategy guide"],
                            "serp_result_count": 3,
                            "competitor_hits": 2,
                            "site_domain": "example.com",
                            "top_domains": ["competitor-a.com"],
                        }
                    ]
                },
                "competitor_analysis": {"summary": {"competitor_count": 1}},
                "entity_analysis": {"summary": {"confidence": 0.82}},
                "citation_diagnosis": {"summary": {"failure_count": 1}},
            },
            metadata={
                "readiness": {
                    "page_data": {
                        "url": "https://example.com",
                        "title": "Example Co",
                        "h1_tags": ["Example Co"],
                        "word_count": 720,
                    },
                    "citability_data": {"average_citability_score": 64},
                    "llms_validation": {"exists": True, "format_valid": True},
                    "llms_live": {"llms_txt": {"exists": True}},
                    "brand_data": {
                        "platforms": {"wikipedia": {"has_wikipedia_page": False}}
                    },
                    "robots_data": {"exists": True},
                    "sitemap_pages": ["https://example.com/"],
                    "rescience_pass": {
                        "summary": "Optimization pass summary",
                        "priority_actions": {
                            "P0": ["Restore homepage accessibility."],
                            "P1": ["Publish llms.txt."],
                            "P2": ["Strengthen entity trust."],
                        },
                    },
                }
            },
        )

        sections = build_report_sections(
            report_model,
            {
                "geo_scores": {
                    "geo_score": 78,
                    "scores": {
                        "ai_citability": 64,
                        "brand_authority": 58,
                        "content_eeat": 70,
                        "technical": 82,
                        "schema": 61,
                        "platform_optimization": 66,
                    },
                },
                "platforms": {"ChatGPT": 74, "Google AI Overviews": 79},
                "page_data": {
                    "url": "https://example.com",
                    "title": "Example Co",
                    "h1_tags": ["Example Co"],
                    "word_count": 720,
                },
                "citability_data": {"average_citability_score": 64},
                "llms_validation": {"exists": True, "format_valid": True},
                "llms_live": {"llms_txt": {"exists": True}},
                "brand_data": {
                    "platforms": {"wikipedia": {"has_wikipedia_page": False}}
                },
                "robots_data": {"exists": True},
                "sitemap_pages": ["https://example.com/"],
                "rescience_pass": {
                    "summary": "Optimization pass summary",
                    "priority_actions": {
                        "P0": ["Restore homepage accessibility."],
                        "P1": ["Publish llms.txt."],
                        "P2": ["Strengthen entity trust."],
                    },
                },
            },
        )

        self.assertEqual(
            set(sections),
            {
                "decision_summary",
                "service_line_scorecard",
                "query_universe",
                "competitor_visibility",
                "earned_media_gap",
                "citation_diagnosis",
                "entity_trust_graph",
                "technical_geo_gates",
                "execution_ledger",
                "developer_appendix",
                "evidence_appendix",
            },
        )
        self.assertIn("cto", sections["decision_summary"]["by_audience"])
        self.assertIn("marketing_manager", sections["decision_summary"]["by_audience"])
        self.assertIn("developers", sections["decision_summary"]["by_audience"])
        self.assertTrue(sections["execution_ledger"]["thirty_day"])
        self.assertTrue(sections["execution_ledger"]["sixty_day"])
        self.assertIn("ninety_day", sections["execution_ledger"])
        self.assertTrue(sections["evidence_appendix"]["methodology"])

    def test_report_sections_markdown_includes_readiness_priority_risks(self):
        markdown = build_report_sections(
            ReportModel(
                brand_name="Example Co",
                site_snapshot=SiteSnapshot(
                    url="https://example.com",
                    title="Example Co",
                    canonical_url="https://example.com",
                ),
            ),
            {
                "geo_scores": {
                    "geo_score": 52,
                    "scores": {
                        "ai_citability": 42,
                        "brand_authority": 58,
                        "content_eeat": 70,
                        "technical": 82,
                        "schema": 61,
                        "platform_optimization": 66,
                    },
                },
                "platforms": {},
                "page_data": {"h1_tags": ["One", "Two"]},
                "llms_validation": {"exists": False},
            },
        )

        from scripts.strategy_engine.reporting import report_sections_to_markdown

        rendered = report_sections_to_markdown(markdown)

        self.assertIn("Priority Gates", rendered)
        self.assertIn("Missing llms.txt guidance layer", rendered)
        self.assertIn("Heading hierarchy is diluted", rendered)
        self.assertIn("Low AI citability", rendered)

    def test_report_sections_markdown_uses_competitor_name_labels(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
            competitor_profiles=[
                CompetitorProfile(
                    name="Competitor A",
                    domain="competitor-a.com",
                    strengths=["clear positioning"],
                )
            ],
        )

        rendered = build_report_sections(
            report_model,
            {
                "geo_scores": {"geo_score": 52, "scores": {}},
                "platforms": {},
                "page_data": {"h1_tags": ["One"]},
                "llms_validation": {"exists": True, "format_valid": True},
            },
        )

        from scripts.strategy_engine.reporting import report_sections_to_markdown

        markdown = report_sections_to_markdown(rendered)

        self.assertIn("Competitor A", markdown)
        self.assertNotIn("'name': 'Competitor A'", markdown)

    def test_competitor_gap_analysis_separates_source_buckets_and_explains_sparse_discovery(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
        )

        sections = build_report_sections(
            report_model,
            {
                "geo_scores": {"geo_score": 52, "scores": {}},
                "platforms": {},
                "page_data": {"h1_tags": ["One"]},
                "llms_validation": {"exists": True, "format_valid": True},
                "plugin_results": {
                    "competitor_analysis": {
                        "summary": {
                            "competitor_count": 0,
                            "site_owned_count": 1,
                            "earned_media_count": 1,
                        },
                        "source_inventory": {
                            "site_owned": ["example.com"],
                            "competitor_owned": [],
                            "earned_media": ["news-site.com"],
                        },
                        "authority_gaps": [
                            {
                                "gap_type": "discovery_gap",
                                "gap_theme": "No competitor-owned domains were confidently discovered.",
                                "why_it_matters": "The report should explain that the live sample set leaned on third-party coverage rather than direct rivals.",
                            }
                        ],
                    }
                },
            },
        )

        self.assertEqual(
            sections["competitor_visibility"]["source_inventory"]["earned_media"],
            ["news-site.com"],
        )
        self.assertEqual(
            sections["competitor_visibility"]["authority_gaps"][0]["gap_type"],
            "discovery_gap",
        )

        from scripts.strategy_engine.reporting import report_sections_to_markdown

        rendered = report_sections_to_markdown(sections)

        self.assertIn("Competitor Visibility", rendered)
        self.assertIn("No competitor-owned domains were confidently discovered", rendered)
        self.assertIn("news-site.com", rendered)

    def test_competitor_gap_analysis_renders_authority_gaps_once(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
        )

        sections = build_report_sections(
            report_model,
            {
                "geo_scores": {"geo_score": 52, "scores": {}},
                "platforms": {},
                "page_data": {"h1_tags": ["One"]},
                "llms_validation": {"exists": True, "format_valid": True},
                "plugin_results": {
                    "competitor_analysis": {
                        "summary": {
                            "competitor_count": 0,
                            "site_owned_count": 1,
                            "earned_media_count": 1,
                        },
                        "source_inventory": {
                            "site_owned": ["example.com"],
                            "competitor_owned": [],
                            "earned_media": ["news-site.com"],
                        },
                        "authority_gaps": [
                            {
                                "gap_type": "earned_media_gap",
                                "gap_theme": "Third-party coverage is visible in the category.",
                                "why_it_matters": "Answer engines may cite publishers and explainers instead of the brand until authority signals improve.",
                            }
                        ],
                    }
                },
            },
        )

        from scripts.strategy_engine.reporting import report_sections_to_markdown

        rendered = report_sections_to_markdown(sections)

        self.assertEqual(rendered.count("Third-party coverage is visible in the category."), 1)
        self.assertNotIn("{'gap_type':", rendered)
        self.assertIn("Gap Type: earned_media_gap", rendered)

    def test_competitor_gap_analysis_uses_neutral_copy_when_inventory_is_empty(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
        )

        sections = build_report_sections(
            report_model,
            {
                "geo_scores": {"geo_score": 52, "scores": {}},
                "platforms": {},
                "page_data": {"h1_tags": ["One"]},
                "llms_validation": {"exists": True, "format_valid": True},
                "plugin_results": {
                    "competitor_analysis": {
                        "summary": {
                            "competitor_count": 0,
                            "site_owned_count": 1,
                            "earned_media_count": 0,
                        },
                        "source_inventory": {
                            "site_owned": ["example.com"],
                            "competitor_owned": [],
                            "earned_media": [],
                        },
                        "authority_gaps": [],
                    }
                },
            },
        )

        from scripts.strategy_engine.reporting import report_sections_to_markdown

        rendered = report_sections_to_markdown(sections)

        self.assertIn(
            "No competitor-owned or earned-media sources were confidently discovered",
            rendered,
        )
        self.assertIn(
            "The sample set is sparse and the category map is still incomplete.",
            rendered,
        )
        self.assertEqual(
            sections["competitor_visibility"]["authority_gaps"][0]["gap_theme"],
            "No competitor-owned or earned-media sources were confidently discovered.",
        )
        self.assertEqual(
            sections["competitor_visibility"]["authority_gaps"][0]["why_it_matters"],
            "The sample set is sparse and the category map is still incomplete.",
        )
        self.assertNotIn("leans on earned-media sources and live SERP observations", rendered)

    def test_citation_diagnosis_exposes_owned_and_earned_source_strength_summaries(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
            entity_graph=EntityGraph(
                entity_name="Example Co",
                canonical_url="https://example.com",
                same_as=["https://www.linkedin.com/company/example"],
                confidence=0.78,
            ),
            citation_failures=[
                CitationFailure(
                    query="latest example co pricing",
                    target_url="https://example.com/pricing",
                    failure_mode="freshness_gap",
                    evidence=["The page is not visibly updated in the sampled content."],
                    recommended_fix="Add a visible update date and fresh proof points.",
                )
            ],
            plugin_results={
                "readiness": {
                    "geo_scores": {
                        "geo_score": 74,
                        "scores": {
                            "ai_citability": 62,
                            "brand_authority": 68,
                            "content_eeat": 71,
                            "technical": 80,
                            "schema": 77,
                            "platform_optimization": 64,
                        },
                    },
                    "platforms": {"ChatGPT": 72},
                },
                "competitor_analysis": {
                    "summary": {"competitor_count": 1, "earned_media_count": 2},
                    "source_inventory": {
                        "site_owned": ["example.com"],
                        "competitor_owned": ["competitor-a.com"],
                        "earned_media": ["news-site.com", "review-site.com"],
                    },
                    "authority_gaps": [
                        {
                            "gap_type": "earned_media_gap",
                            "gap_theme": "Third-party coverage is visible in the category.",
                            "why_it_matters": "Answer engines may cite publishers and explainers instead of the brand until authority signals improve.",
                        }
                    ],
                },
            },
            metadata={
                "readiness": {
                    "page_data": {
                        "url": "https://example.com",
                        "title": "Example Co",
                        "h1_tags": ["Example Co"],
                        "word_count": 840,
                    },
                    "citability_data": {"average_citability_score": 62},
                    "llms_validation": {"exists": True, "format_valid": True},
                    "llms_live": {"llms_txt": {"exists": True}},
                    "brand_data": {
                        "platforms": {"wikipedia": {"has_wikipedia_page": False}}
                    },
                    "robots_data": {"exists": True},
                    "sitemap_pages": ["https://example.com/"],
                    "rescience_pass": {"summary": "Optimization pass summary"},
                }
            },
        )

        sections = build_report_sections(
            report_model,
            {
                "geo_scores": {
                    "geo_score": 74,
                    "scores": {
                        "ai_citability": 62,
                        "brand_authority": 68,
                        "content_eeat": 71,
                        "technical": 80,
                        "schema": 77,
                        "platform_optimization": 64,
                    },
                },
                "platforms": {"ChatGPT": 72},
                "page_data": {
                    "url": "https://example.com",
                    "title": "Example Co",
                    "h1_tags": ["Example Co"],
                    "word_count": 840,
                },
                "citability_data": {"average_citability_score": 62},
                "llms_validation": {"exists": True, "format_valid": True},
                "llms_live": {"llms_txt": {"exists": True}},
                "brand_data": {
                    "platforms": {"wikipedia": {"has_wikipedia_page": False}}
                },
                "robots_data": {"exists": True},
                "sitemap_pages": ["https://example.com/"],
                "rescience_pass": {"summary": "Optimization pass summary"},
                "plugin_results": report_model.plugin_results,
            },
        )

        citation_strength = sections["citation_diagnosis"]["citation_strength"]

        self.assertIn("owned_sources", citation_strength)
        self.assertIn("earned_sources", citation_strength)
        self.assertIn("authority", citation_strength["owned_sources"]["dimensions"])
        self.assertIn("freshness", citation_strength["owned_sources"]["dimensions"])
        self.assertIn("specificity", citation_strength["owned_sources"]["dimensions"])
        self.assertIn("attribution_clarity", citation_strength["owned_sources"]["dimensions"])
        self.assertIn("authority", citation_strength["earned_sources"]["dimensions"])
        self.assertIn("freshness", citation_strength["earned_sources"]["dimensions"])

        from scripts.strategy_engine.reporting import report_sections_to_markdown

        rendered = report_sections_to_markdown(sections)
        self.assertIn("Citation Strength", rendered)
        self.assertIn("Owned Sources", rendered)
        self.assertIn("Earned Sources", rendered)
        self.assertIn("Attribution Clarity", rendered)

    def test_citation_diagnosis_uses_top_level_geo_scores_when_readiness_payload_is_missing(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
            citation_failures=[
                CitationFailure(
                    query="example co pricing",
                    target_url="https://example.com/pricing",
                    failure_mode="non_visible_query",
                    evidence=["The site is absent from the sampled SERP set."],
                    recommended_fix="Improve answer blocks and supporting citations.",
                )
            ],
        )

        sections = build_report_sections(
            report_model,
            {
                "geo_scores": {
                    "geo_score": 74,
                    "scores": {
                        "ai_citability": 62,
                        "brand_authority": 68,
                        "content_eeat": 71,
                        "technical": 80,
                        "schema": 77,
                        "platform_optimization": 64,
                    },
                },
                "platforms": {"ChatGPT": 72},
                "page_data": {
                    "url": "https://example.com",
                    "title": "Example Co",
                    "h1_tags": ["Example Co"],
                    "word_count": 840,
                    "meta_tags": {"article:modified_time": "2026-03-19T12:00:00Z"},
                },
                "citability_data": {"average_citability_score": 62},
                "llms_validation": {"exists": True, "format_valid": True},
                "llms_live": {"llms_txt": {"exists": True}},
                "brand_data": {
                    "platforms": {"wikipedia": {"has_wikipedia_page": False}}
                },
                "robots_data": {"exists": True},
                "sitemap_pages": ["https://example.com/"],
                "rescience_pass": {"summary": "Optimization pass summary"},
            },
        )

        owned_sources = sections["citation_diagnosis"]["citation_strength"]["owned_sources"]

        self.assertGreater(owned_sources["score"], 0)
        self.assertGreater(owned_sources["dimensions"]["authority"]["score"], 40)
        self.assertEqual(owned_sources["dimensions"]["freshness"]["score"], 82)
        self.assertIn("steady", owned_sources["label"])

    def test_entity_authority_analysis_does_not_invent_earned_media_signals(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
            competitor_profiles=[
                CompetitorProfile(
                    name="Competitor A",
                    domain="competitor-a.com",
                    strengths=["clear positioning"],
                )
            ],
        )

        sections = build_report_sections(
            report_model,
            {
                "geo_scores": {"geo_score": 52, "scores": {}},
                "platforms": {},
                "page_data": {},
                "llms_validation": {"exists": True, "format_valid": True},
            },
        )

        self.assertEqual(sections["entity_trust_graph"]["profile_links"], [])
        self.assertNotIn(
            "competitor-a.com",
            str(sections["entity_trust_graph"]),
        )

    def test_evidence_appendix_uses_structured_evidence_entries_and_source_tags(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
            query_clusters=[
                QueryCluster(
                    label="core-intent",
                    queries=["example geo strategy"],
                    search_intent="informational",
                    priority="high",
                    metadata={"seed_topic": "Example GEO strategy"},
                )
            ],
            citation_failures=[
                CitationFailure(
                    query="example geo strategy",
                    target_url="https://example.com/guide",
                    failure_mode="weak_citation_support",
                    evidence=["AI citability is low"],
                    recommended_fix="Add answer-first blocks and supporting citations",
                )
            ],
        )

        sections = build_report_sections(
            report_model,
            {
                "geo_scores": {
                    "geo_score": 78,
                    "scores": {
                        "ai_citability": 64,
                        "brand_authority": 58,
                        "content_eeat": 70,
                        "technical": 82,
                        "schema": 61,
                        "platform_optimization": 66,
                    },
                },
                "platforms": {"ChatGPT": 74},
                "page_data": {"url": "https://example.com"},
                "llms_validation": {"exists": True, "format_valid": True},
            },
        )

        evidence_items = sections["evidence_appendix"]["evidence_items"]
        source_tags = {item["source_tag"] for item in evidence_items}

        self.assertTrue(all("source_type" in item for item in evidence_items))
        self.assertTrue(all("source_tag" in item for item in evidence_items))
        self.assertIn("Live SERP", source_tags)
        self.assertIn("Live Site", source_tags)
        self.assertIn("Heuristic", source_tags)

        from scripts.strategy_engine.pdf import _report_item_text
        from scripts.strategy_engine.reporting import report_sections_to_markdown

        markdown = report_sections_to_markdown(sections)

        self.assertIn("Live SERP", markdown)
        self.assertIn("Live Site", markdown)
        self.assertIn("Heuristic", markdown)
        self.assertIn("Live SERP", _report_item_text(evidence_items[0]))

    def test_evidence_source_tag_normalizes_source_types(self):
        self.assertEqual(evidence_source_tag("academic"), "Academic")
        self.assertEqual(evidence_source_tag("Official"), "Official")
        self.assertEqual(evidence_source_tag("live-site"), "Live Site")
        self.assertEqual(evidence_source_tag("live serp"), "Live SERP")
        self.assertEqual(evidence_source_tag("heuristic"), "Heuristic")

        from scripts.strategy_engine.pdf import EVIDENCE_APPENDIX_TITLE as pdf_title
        from scripts.strategy_engine.reporting import EVIDENCE_APPENDIX_TITLE as markdown_title

        self.assertEqual(markdown_title, pdf_title)

    def test_evidence_metadata_is_rendered_in_appendix_output(self):
        report_model = ReportModel(
            brand_name="Example Co",
            site_snapshot=SiteSnapshot(
                url="https://example.com",
                title="Example Co",
                canonical_url="https://example.com",
            ),
            query_clusters=[
                QueryCluster(
                    label="core-intent",
                    queries=["example geo strategy"],
                    search_intent="informational",
                    priority="high",
                    metadata={"seed_topic": "Example GEO strategy"},
                )
            ],
            citation_failures=[
                CitationFailure(
                    query="example geo strategy",
                    target_url="https://example.com/guide",
                    failure_mode="weak_citation_support",
                    evidence=["AI citability is low"],
                    recommended_fix="Add answer-first blocks and supporting citations",
                )
            ],
        )

        sections = build_report_sections(
            report_model,
            {
                "geo_scores": {
                    "geo_score": 78,
                    "scores": {
                        "ai_citability": 64,
                        "brand_authority": 58,
                        "content_eeat": 70,
                        "technical": 82,
                        "schema": 61,
                        "platform_optimization": 66,
                    },
                },
                "platforms": {"ChatGPT": 74},
                "page_data": {"url": "https://example.com"},
                "llms_validation": {"exists": True, "format_valid": True},
            },
        )

        from scripts.strategy_engine.reporting import report_sections_to_markdown

        rendered = report_sections_to_markdown(sections)

        self.assertIn("## Evidence and Methodology Appendix", rendered)
        self.assertIn("Search Intent: informational", rendered)
        self.assertIn("Priority: high", rendered)
        self.assertIn("Failure Mode: weak_citation_support", rendered)
        self.assertIn("Recommended Fix: Add answer-first blocks and supporting citations", rendered)

    def test_official_evidence_items_surface_crawler_access_metadata(self):
        sections = build_report_sections(
            ReportModel(
                brand_name="Example Co",
                site_snapshot=SiteSnapshot(
                    url="https://example.com",
                    title="Example Co",
                    canonical_url="https://example.com",
                ),
            ),
            {
                "geo_scores": {"geo_score": 78, "scores": {"ai_citability": 64}},
                "platforms": {},
                "page_data": {"url": "https://example.com"},
                "crawler_access": {
                    "GPTBot": {
                        "platform": "ChatGPT",
                        "status": "Allowed",
                        "recommendation": "Keep accessible with a clearly documented policy.",
                    }
                },
                "llms_validation": {"exists": True, "format_valid": True},
            },
        )

        evidence_items = sections["evidence_appendix"]["evidence_items"]
        official_items = [item for item in evidence_items if item["source_tag"] == "Official"]

        self.assertTrue(official_items)
        self.assertIn("recommendation", official_items[0]["metadata"])

        from scripts.strategy_engine.reporting import report_sections_to_markdown

        rendered = report_sections_to_markdown(sections)
        self.assertIn("Official", rendered)
        self.assertIn("Recommendation: Keep accessible with a clearly documented policy.", rendered)

        from scripts.strategy_engine.pdf import _report_item_text

        self.assertIn("Recommendation: Keep accessible with a clearly documented policy.", _report_item_text(official_items[0]))


if __name__ == "__main__":
    unittest.main()
