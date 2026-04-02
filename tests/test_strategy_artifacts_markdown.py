import unittest
from pathlib import Path

from scripts.strategy_engine.artifacts import (
    build_combined_audit_data,
    build_output_paths,
    extract_brand_name,
    slugify,
)
from scripts.strategy_engine.markdown import render_markdown_report


class StrategyArtifactsMarkdownTest(unittest.TestCase):
    def test_slugify_and_extract_brand_name(self):
        self.assertEqual(slugify("Example Co!"), "example-co")
        self.assertEqual(
            extract_brand_name(
                {"title": "Example Co | Better GEO"},
                "https://example.com",
            ),
            "Better GEO",
        )

    def test_build_output_paths_and_combined_payload_shape(self):
        paths = build_output_paths("Example Co", "2026-03-20")
        self.assertEqual(paths["report_dir"], Path("output/reports/example-co-2026-03-20"))
        self.assertEqual(paths["markdown_path"].name, "GEO-STRATEGY-REPORT.md")

        combined = build_combined_audit_data(
            url="https://example.com",
            brand_name="Example Co",
            geo_scores={"geo_score": 91, "scores": {"ai_citability": 72}},
            rescience_pass={"priority_actions": {"P0": [], "P1": [], "P2": []}},
            executive_summary="Summary",
            findings=[],
            quick_wins=[],
            medium_term=[],
            strategic=[],
            crawler_access={},
        )
        self.assertEqual(combined["brand_name"], "Example Co")
        self.assertIn("date", combined)

    def test_render_markdown_report_includes_combined_client_report_sections(self):
        markdown = render_markdown_report(
            {
                "brand_name": "Example Co",
                "date": "2026-03-20",
                "url": "https://example.com",
                "report_sections": {
                    "executive_summary": {
                        "overview": "Strategic overview that should stay out of the combined client report."
                    }
                },
                "geo_score": 91,
                "scores": {
                    "ai_citability": 72,
                    "brand_authority": 52,
                    "content_eeat": 75,
                    "technical": 90,
                    "schema": 46,
                    "platform_optimization": 60,
                },
                "executive_summary": "Summary",
                "findings": [
                    {
                        "severity": "high",
                        "title": "Heading architecture is diluted",
                        "summary": "One clear H1 is better.",
                        "leadership_impact": "It matters.",
                        "marketing_action": "Fix copy.",
                        "developer_action": "Fix markup.",
                        "observed_evidence": "Two H1s exist.",
                    }
                ],
                "quick_wins": ["Fix llms.txt"],
                "medium_term": ["Improve schema"],
                "strategic": ["Grow authority"],
                "crawler_access": {},
                "client_report_sections": {
                    "cover_verdict": {
                        "brand_name": "Example Co",
                        "primary_domain": "example.com",
                        "audit_date": "2026-03-20",
                        "analysis_window": "Point-in-time audit",
                        "verdict_status": "partially_visible",
                        "one_sentence_verdict": "Example Co is technically crawlable but not yet consistently cited for high-intent AI queries.",
                        "overall_confidence": "medium",
                        "confidence_reason": "Competitor and query sampling were directionally useful but not exhaustive.",
                        "sample_completeness": "partial",
                    },
                    "decision_summary": {
                        "what_is_working": ["Technical foundations are strong."],
                        "what_is_not_working": ["Citation readiness is lagging."],
                        "top_blockers": [],
                        "top_opportunities": [],
                        "leadership_takeaway": "The site needs stronger proof-rich pages before advanced GEO extras matter.",
                        "top_3_actions": [],
                    },
                    "score_definitions": {
                        "term_guide": [
                            {
                                "term": "Confidence",
                                "plain_english": "How much to trust the current readout.",
                            },
                            {
                                "term": "Directional",
                                "plain_english": "An early signal, not final proof from exact captures.",
                            },
                        ],
                        "weighting": {
                            "summary": "The GEO Score is a weighted blend across citability, authority, content quality, technical access, schema, and platform readiness.",
                            "components": [
                                {
                                    "metric_name": "AI Citability",
                                    "weight": 25,
                                    "why_this_weight_exists": "AI systems need reusable, proof-rich passages before they can cite a page confidently.",
                                }
                            ],
                        },
                        "metrics": [
                            {
                                "metric_key": "geo_score",
                                "metric_name": "GEO Score",
                                "score": 91,
                                "plain_english_definition": "Overall AI visibility readiness.",
                                "what_good_looks_like": "Strong technical access and answer-ready content.",
                                "why_this_score_landed_here": "Technical strength outweighs schema gaps.",
                                "primary_evidence_used": ["live_site", "internal_score"],
                                "confidence": "medium",
                            }
                        ]
                    },
                    "priority_findings": {
                        "items": [
                            {
                                "title": "Low citation readiness",
                                "severity": "critical",
                                "plain_english_summary": "AI systems do not have enough proof-rich passages to quote confidently.",
                                "what_we_observed": "Citability is lagging on the homepage.",
                                "why_it_matters_to_business": "Weak citation pickup reduces branded discovery in AI search.",
                                "evidence_class": "internal_score",
                                "proof": "Citability scored 28/100 in the sampled run.",
                                "confidence": "medium",
                                "counterpoint_or_limitation": "This is still a point-in-time sample.",
                                "marketing_action": "Rewrite service pages into answer-first blocks.",
                                "engineering_action": "Support those pages with clean headings and schema.",
                                "success_metric": "Higher citation pickup on rerun.",
                                "affected_pages_or_queries": ["example ai visibility"],
                            }
                        ]
                    },
                    "competitive_benchmark": {
                        "summary": "Current competitor picture is directional.",
                        "competitor_set": ["Competitor A"],
                        "sample_scope": {"sample_completeness": "partial"},
                        "benchmark_rows": [],
                    },
                    "platform_breakdown": {
                        "platforms": [
                            {
                                "platform": "ChatGPT",
                                "documented_behavior": "Uses live web sources when available.",
                                "observed_site_status": "Accessible",
                                "observed_visibility_status": "Inconsistent",
                                "cautious_inference": "Needs stronger answer blocks.",
                                "recommended_actions": ["Improve proof-rich pages."],
                                "official_sources": ["https://openai.com/gptbot"],
                                "last_verified_at": "2026-03-20",
                                "confidence": "medium",
                            }
                        ]
                    },
                    "prompt_query_proof": {"rows": []},
                    "page_source_evidence": {"priority_pages": [], "source_domains": [], "entity_signal_review": {}},
                    "action_plan_30_60_90": {"actions": []},
                    "technical_proof_appendix": {
                        "methodology": {"summary": "Point-in-time audit."},
                        "crawl_and_fetch_evidence": [],
                        "robots_and_bot_access": [
                            {
                                "crawler": "GPTBot",
                                "platform": "ChatGPT",
                                "status": "Allowed",
                                "recommendation": "Keep it allowed unless legal or security policy changes.",
                            }
                        ],
                        "dom_and_heading_proof": [],
                        "schema_proof": [],
                        "source_inventory": [],
                        "limitations": {"limitations_note": "Competitor sampling is partial."},
                    },
                },
                "rescience_pass": {
                    "summary": "Optimization pass summary",
                    "priority_actions": {"P0": [], "P1": [], "P2": []},
                },
            }
        )

        self.assertTrue(markdown.startswith("# GEO Strategy Report: Example Co"))
        self.assertIn("## Cover + Verdict", markdown)
        self.assertIn("## What The Scores Mean", markdown)
        self.assertIn("## Competitive Benchmark", markdown)
        self.assertIn("## Technical Proof Appendix", markdown)
        self.assertIn("How much to trust this read (confidence): medium", markdown)
        self.assertIn("How much evidence this run captured (sample completeness): partial", markdown)
        self.assertIn("### Term Guide", markdown)
        self.assertIn("### Scoring And Weighting", markdown)
        self.assertIn("Directional", markdown)
        self.assertIn("- Severity: critical", markdown)
        self.assertIn("- What we found:", markdown)
        self.assertIn("GPTBot (ChatGPT): Allowed.", markdown)
        self.assertNotIn("## Key Findings", markdown)
        self.assertNotIn("## Prioritized Action Plan", markdown)
        self.assertNotIn("## ReScience Optimization Pass", markdown)
        self.assertNotIn("ReScience", markdown)
        self.assertNotIn("Strategic overview that should stay out of the combined client report.", markdown)


if __name__ == "__main__":
    unittest.main()
