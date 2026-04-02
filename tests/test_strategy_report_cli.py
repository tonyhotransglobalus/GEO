import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import strategy_report


class StrategyReportCliTest(unittest.TestCase):
    def test_parse_args_accepts_only_url(self):
        args = strategy_report.parse_args(["https://example.com"])

        self.assertEqual(args.url, "https://example.com")
        self.assertEqual(args.mode, "script-only")
        self.assertIsNone(args.model)
        self.assertFalse(args.non_interactive)

    def test_parse_args_rejects_removed_flags(self):
        with self.assertRaises(SystemExit):
            strategy_report.parse_args(["https://example.com", "--pdf"])

    def test_parse_args_accepts_run_metadata_flags(self):
        args = strategy_report.parse_args(
            [
                "https://example.com",
                "--mode",
                "agent-assisted",
                "--driver",
                "gemini",
                "--model",
                "gpt-5.4",
                "--refresh-guidance",
                "--non-interactive",
            ]
        )

        self.assertEqual(args.mode, "agent-assisted")
        self.assertEqual(args.driver, "gemini")
        self.assertEqual(args.model, "gpt-5.4")
        self.assertTrue(args.refresh_guidance)
        self.assertTrue(args.non_interactive)

    def test_resolve_guidance_refresh_prompts_in_interactive_mode(self):
        refresh = strategy_report.resolve_guidance_refresh(
            strategy_report.parse_args(["https://example.com"]),
            interactive=True,
            input_func=lambda _: "y",
        )

        self.assertTrue(refresh)

    @patch("scripts.strategy_report.orchestrate_audit")
    @patch("scripts.strategy_report.load_guidance_snapshot")
    def test_main_passes_metadata_and_prints_json(self, load_guidance_snapshot_mock, orchestrate_audit_mock):
        load_guidance_snapshot_mock.return_value = {
            "source": "local-reference",
            "snapshot_path": "output/guidance/shared-guidance.json",
            "reference_path": "skills/geo-executive-report/references/platform-guidance-2026.md",
            "refreshed_at": "2026-03-25T12:00:00Z",
            "platforms": [
                {
                    "name": "Google Search AI Features",
                    "sources": ["https://developers.google.com/search/docs/appearance/ai-features"],
                }
            ],
        }
        orchestrate_audit_mock.return_value = {
            "url": "https://example.com",
            "brand_name": "Example Co",
            "geo_score": 91,
        }

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            result = strategy_report.main(
                [
                    "https://example.com",
                    "--non-interactive",
                    "--mode",
                    "agent-assisted",
                    "--driver",
                    "gemini",
                    "--model",
                    "gpt-5.4",
                ]
            )

        orchestrate_audit_mock.assert_called_once()
        call_args = orchestrate_audit_mock.call_args
        self.assertEqual(call_args.args[0], "https://example.com")
        self.assertEqual(call_args.kwargs["presentation_metadata"]["run_mode"], "agent-assisted")
        self.assertEqual(call_args.kwargs["presentation_metadata"]["driver"], "gemini")
        self.assertEqual(call_args.kwargs["presentation_metadata"]["model"], "gpt-5.4")
        self.assertFalse(call_args.kwargs["presentation_metadata"]["guidance"]["refresh_requested"])
        self.assertEqual(
            call_args.kwargs["presentation_metadata"]["guidance"]["official_sources"],
            ["https://developers.google.com/search/docs/appearance/ai-features"],
        )
        self.assertEqual(result, orchestrate_audit_mock.return_value)
        self.assertEqual(json.loads(stdout.getvalue()), orchestrate_audit_mock.return_value)

    @patch.dict("os.environ", {"ANTIGRAVITY": "1"})
    def test_parse_args_defaults_to_agent_assisted_in_antigravity(self):
        args = strategy_report.parse_args(["https://example.com"])
        self.assertEqual(args.mode, "agent-assisted")
        self.assertEqual(args.driver, "antigravity")

    @patch.dict("os.environ", {"CODEX": "1"})
    def test_parse_args_defaults_to_agent_assisted_in_codex(self):
        args = strategy_report.parse_args(["https://example.com"])
        self.assertEqual(args.mode, "agent-assisted")
        self.assertEqual(args.driver, "codex")

    def test_workflow_docs_reference_combined_strategy_report_artifacts(self):
        strategy_workflow = Path(".agent/workflows/geo-strategy-report.md").read_text(encoding="utf-8")
        pdf_workflow = Path(".agent/workflows/geo-report-pdf.md").read_text(encoding="utf-8")
        geo_skill = Path("geo/SKILL.md").read_text(encoding="utf-8")

        self.assertIn("GEO-STRATEGY-REPORT.md", strategy_workflow)
        self.assertIn("GEO-STRATEGY-REPORT.pdf", strategy_workflow)
        self.assertNotIn("GEO-REPORT-SCRIPT", strategy_workflow)

        self.assertIn("GEO-STRATEGY-REPORT.md", pdf_workflow)
        self.assertIn("GEO-STRATEGY-REPORT.pdf", pdf_workflow)
        self.assertNotIn("GEO-REPORT-SCRIPT", pdf_workflow)

        self.assertIn("GEO-STRATEGY-REPORT.md", geo_skill)
        self.assertIn("GEO-STRATEGY-REPORT.pdf", geo_skill)
        self.assertNotIn("GEO-REPORT-SCRIPT", geo_skill)
        self.assertNotIn("GEO-REPORT-ASSISTED", geo_skill)


if __name__ == "__main__":
    unittest.main()
