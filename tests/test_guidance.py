import tempfile
import unittest
from pathlib import Path

from scripts.strategy_engine.guidance import (
    load_guidance_snapshot,
    refresh_guidance_snapshot,
)


class GuidanceSnapshotTest(unittest.TestCase):
    def test_refresh_guidance_snapshot_writes_structured_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir) / "shared-guidance.json"
            snapshot = refresh_guidance_snapshot(snapshot_path=snapshot_path)

            self.assertTrue(snapshot_path.exists())
            self.assertEqual(snapshot["source"], "local-reference")
            self.assertEqual(snapshot["snapshot_path"], str(snapshot_path))
            self.assertTrue(snapshot["platforms"])
            self.assertTrue(any(item["name"] == "Google Search AI Features" for item in snapshot["platforms"]))

    def test_load_guidance_snapshot_uses_existing_snapshot_without_refresh(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            snapshot_path = Path(tmpdir) / "shared-guidance.json"
            snapshot_path.write_text(
                '{"source":"cached","snapshot_path":"cached.json","reference_path":"ref.md","refreshed_at":"2026-03-25T00:00:00Z","platforms":[{"name":"Cached"}]}',
                encoding="utf-8",
            )

            snapshot = load_guidance_snapshot(snapshot_path=snapshot_path, refresh=False)

            self.assertEqual(snapshot["source"], "cached")
            self.assertEqual(snapshot["platforms"][0]["name"], "Cached")


if __name__ == "__main__":
    unittest.main()
