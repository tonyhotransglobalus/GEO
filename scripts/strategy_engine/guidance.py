from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_GUIDANCE_REFERENCE_PATH = Path(
    "skills/geo-executive-report/references/platform-guidance-2026.md"
)
DEFAULT_GUIDANCE_SNAPSHOT_PATH = Path("output/guidance/shared-guidance.json")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_reference_markdown(reference_path: Path) -> list[dict]:
    text = reference_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    platforms: list[dict] = []
    current: dict | None = None
    mode: str | None = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            platforms.append(current)
            current = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("## "):
            flush()
            current = {
                "name": stripped[3:].strip(),
                "sources": [],
                "guidance": [],
                "reporting_rule": "",
            }
            mode = None
            continue

        if current is None:
            continue

        if stripped == "Source:":
            mode = "sources"
            continue
        if stripped == "Stable guidance:":
            mode = "guidance"
            continue
        if stripped == "Reporting rule:":
            mode = "reporting_rule"
            continue

        if not stripped:
            continue

        if mode == "sources" and stripped.startswith("- "):
            current["sources"].append(stripped[2:].strip())
        elif mode == "guidance" and stripped.startswith("- "):
            current["guidance"].append(stripped[2:].strip())
        elif mode == "reporting_rule":
            if current["reporting_rule"]:
                current["reporting_rule"] += " "
            current["reporting_rule"] += stripped.lstrip("- ").strip()

    flush()
    return platforms


def refresh_guidance_snapshot(
    *,
    reference_path: Path | None = None,
    snapshot_path: Path | None = None,
) -> dict:
    reference_path = reference_path or DEFAULT_GUIDANCE_REFERENCE_PATH
    snapshot_path = snapshot_path or DEFAULT_GUIDANCE_SNAPSHOT_PATH
    platforms = _parse_reference_markdown(reference_path)
    snapshot = {
        "source": "local-reference",
        "reference_path": str(reference_path),
        "snapshot_path": str(snapshot_path),
        "refreshed_at": _utc_timestamp(),
        "platforms": platforms,
    }
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return snapshot


def load_guidance_snapshot(
    *,
    snapshot_path: Path | None = None,
    reference_path: Path | None = None,
    refresh: bool = False,
) -> dict:
    snapshot_path = snapshot_path or DEFAULT_GUIDANCE_SNAPSHOT_PATH
    reference_path = reference_path or DEFAULT_GUIDANCE_REFERENCE_PATH
    if refresh or not snapshot_path.exists():
        return refresh_guidance_snapshot(
            reference_path=reference_path,
            snapshot_path=snapshot_path,
        )
    return json.loads(snapshot_path.read_text(encoding="utf-8"))
