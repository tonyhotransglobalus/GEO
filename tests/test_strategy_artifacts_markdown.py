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
        self.assertEqual(paths["markdown_path"].name, "GEO-CLIENT-REPORT.md")

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

    def test_render_markdown_report_includes_findings_and_actions(self):
        markdown = render_markdown_report(
            {
                "brand_name": "Example Co",
                "date": "2026-03-20",
                "url": "https://example.com",
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
                "rescience_pass": {
                    "summary": "Optimization pass summary",
                    "priority_actions": {"P0": [], "P1": [], "P2": []},
                },
            }
        )

        self.assertIn("## Key Findings", markdown)
        self.assertIn("## Prioritized Action Plan", markdown)
        self.assertIn("## ReScience Optimization Pass", markdown)


if __name__ == "__main__":
    unittest.main()
