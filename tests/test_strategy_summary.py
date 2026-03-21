import unittest

from scripts.strategy_engine.summary import (
    build_action_lists,
    build_crawler_access,
    build_executive_summary,
    build_findings,
    build_rescience_pass,
)


class StrategySummaryTest(unittest.TestCase):
    def test_build_rescience_pass_groups_priority_actions(self):
        result = build_rescience_pass(
            url="https://example.com",
            page_data={
                "status_code": 500,
                "has_ssr_content": False,
                "h1_tags": ["One", "Two"],
            },
            citability_data={"average_citability_score": 42},
            llms_validation={"exists": False, "format_valid": False, "issues": ["bad"]},
            brand_data={"platforms": {"wikipedia": {}}},
        )

        self.assertEqual(result["priority_actions"]["P0"][:2], [
            "Restore homepage accessibility and eliminate 5xx or unreachable states.",
            "Add server-rendered content so crawlers can see meaningful HTML without JavaScript.",
        ])
        self.assertIn("Publish llms.txt and llms-full.txt at the site root.", result["priority_actions"]["P1"])
        self.assertTrue(result["geo_methods"])

    def test_build_findings_includes_ai_citability_and_heading_findings(self):
        findings = build_findings(
            page_data={"h1_tags": ["One", "Two"]},
            citability_data={"average_citability_score": 42},
            llms_live={"llms_txt": {"exists": False}},
            llms_validation={"exists": False, "format_valid": False, "issues": []},
            brand_data={"platforms": {"wikipedia": {}}},
            rescience_pass={"summary": "Pass", "priority_actions": {"P0": [], "P1": [], "P2": ["Follow up"]}},
        )

        self.assertGreaterEqual(len(findings), 3)
        self.assertEqual(findings[0]["severity"], "critical")
        self.assertEqual(findings[1]["severity"], "high")
        self.assertEqual(findings[2]["title"], "Heading architecture is diluted")

    def test_build_action_lists_uses_rescience_priorities(self):
        quick_wins, medium_term, strategic = build_action_lists(
            {"priority_actions": {"P1": ["One", "Two", "Three"], "P2": ["Four"]}}
        )

        self.assertEqual(quick_wins, ["One", "Two", "Three"])
        self.assertEqual(medium_term, ["Four"])
        self.assertIn("Track AI visibility, referral traffic, and citation wins as ongoing GEO KPIs.", strategic)

    def test_build_crawler_access_normalizes_status(self):
        access = build_crawler_access(
            {"ai_crawler_status": {"GPTBot": "allow", "ClaudeBot": "block"}}
        )

        self.assertEqual(access["GPTBot"]["status"], "Allow")
        self.assertEqual(access["GPTBot"]["recommendation"], "Keep accessible.")
        self.assertEqual(access["ClaudeBot"]["status"], "Block")
        self.assertEqual(access["ClaudeBot"]["recommendation"], "Review access.")

    def test_build_executive_summary_mentions_llms_and_brand(self):
        summary = build_executive_summary(
            brand_name="Example Co",
            geo_score=91,
            page_data={"h1_tags": ["One", "Two"]},
            citability_data={"average_citability_score": 42},
            llms_live={"llms_txt": {"exists": False}},
            llms_validation={"exists": False, "format_valid": False, "issues": []},
            rescience_pass={"summary": "Pass summary"},
        )

        self.assertIn("Example Co", summary)
        self.assertIn("GEO score of 91/100", summary)
        self.assertIn("missing llms.txt guidance layer", summary)
        self.assertIn("exposes 2 H1 tags", summary)


if __name__ == "__main__":
    unittest.main()
