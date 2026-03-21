import io
import json
import unittest
from unittest.mock import patch

from scripts import strategy_report


class StrategyReportCliTest(unittest.TestCase):
    def test_parse_args_accepts_only_url(self):
        args = strategy_report.parse_args(["https://example.com"])

        self.assertEqual(args.url, "https://example.com")

    def test_parse_args_rejects_removed_flags(self):
        with self.assertRaises(SystemExit):
            strategy_report.parse_args(["https://example.com", "--pdf"])

    @patch("scripts.strategy_report.orchestrate_audit")
    def test_main_passes_only_url_and_prints_json(self, orchestrate_audit_mock):
        orchestrate_audit_mock.return_value = {
            "url": "https://example.com",
            "brand_name": "Example Co",
            "geo_score": 91,
        }

        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            result = strategy_report.main(["https://example.com"])

        orchestrate_audit_mock.assert_called_once_with("https://example.com")
        self.assertEqual(result, orchestrate_audit_mock.return_value)
        self.assertEqual(json.loads(stdout.getvalue()), orchestrate_audit_mock.return_value)


if __name__ == "__main__":
    unittest.main()
