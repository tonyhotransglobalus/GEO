from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from .markdown import MARKDOWN_FILENAME, render_v2_markdown_report

DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[2] / "output" / "reports"
VERSIONED_MARKDOWN_FILENAME = MARKDOWN_FILENAME
MANIFEST_FILENAME = "GEO-STRATEGY-REPORT-V2.manifest.json"
EVIDENCE_FILENAME = "GEO-STRATEGY-REPORT-V2.evidence.json"
COMPARISON_METADATA_FILENAME = "GEO-STRATEGY-REPORT-V2.comparison-metadata.json"


def slugify(value: str, *, fallback: str | None = None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if slug:
        return slug
    if fallback:
        fallback_value = _seed_slug(fallback)
        if fallback_value:
            return fallback_value
    return "run"


def _seed_slug(value: str) -> str:
    parsed = urlparse(value)
    seed = parsed.netloc or parsed.path or value
    seed = seed.lower()
    if seed.startswith("www."):
        seed = seed[4:]
    return re.sub(r"[^a-z0-9]+", "-", seed).strip("-")


def _run_suffix(value: str) -> str:
    seed = _seed_slug(value)
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    if seed:
        return f"{seed[:24].rstrip('-')}-{digest}"
    return digest


def _coerce_dir(value: Path | str | None) -> Path:
    if value is None:
        return DEFAULT_REPORTS_DIR
    if isinstance(value, Path):
        return value
    return Path(value)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_v2_output_paths(
    brand_name: str,
    date_stamp: str,
    *,
    base_dir: Path | str | None = None,
    run_seed: str | None = None,
) -> dict[str, Path]:
    reports_dir = _coerce_dir(base_dir)
    report_slug = slugify(brand_name, fallback=run_seed or date_stamp)
    report_dir_name = f"{report_slug}-{date_stamp}"
    if run_seed:
        report_dir_name = f"{report_dir_name}-{_run_suffix(run_seed)}"
    report_dir = reports_dir / report_dir_name
    return {
        "report_dir": report_dir,
        "markdown_path": report_dir / VERSIONED_MARKDOWN_FILENAME,
        "compat_markdown_path": reports_dir / VERSIONED_MARKDOWN_FILENAME,
        "manifest_path": report_dir / MANIFEST_FILENAME,
        "evidence_path": report_dir / EVIDENCE_FILENAME,
        "comparison_metadata_path": report_dir / COMPARISON_METADATA_FILENAME,
    }


def _comparison_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _coerce_mapping(payload.get("manifest"))
    adjudication = _coerce_mapping(payload.get("adjudication"))
    qa = _coerce_mapping(payload.get("qa"))
    comparison = _coerce_mapping(manifest.get("comparison_eligibility"))
    return {
        "target_url": manifest.get("target_url"),
        "target_domain": manifest.get("target_domain"),
        "shadow_run": bool(manifest.get("shadow_run")),
        "compare_to_v1": bool(comparison.get("requested")),
        "comparison_eligible": bool(comparison.get("eligible")),
        "adjudication_statuses": {
            name: _coerce_mapping(section).get("status")
            for name, section in adjudication.items()
            if isinstance(section, Mapping)
        },
        "issues": list(qa.get("issues") or []),
        "warnings": list(qa.get("warnings") or []),
    }


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def publish_v2_artifacts(
    *,
    brand_name: str,
    date_stamp: str,
    payload: Mapping[str, Any],
    base_dir: Path | str | None = None,
    run_seed: str | None = None,
    write_compat_markdown: bool | None = None,
) -> dict[str, Path]:
    paths = build_v2_output_paths(
        brand_name,
        date_stamp,
        base_dir=base_dir,
        run_seed=run_seed,
    )
    payload_map = _coerce_mapping(payload)
    markdown_report = render_v2_markdown_report(payload_map)
    manifest = _coerce_mapping(payload_map.get("manifest"))
    evidence = _coerce_mapping(payload_map.get("evidence"))
    comparison_requested = bool(_coerce_mapping(manifest.get("comparison_eligibility")).get("requested"))
    shadow_run = bool(manifest.get("shadow_run"))
    should_write_compat = write_compat_markdown if write_compat_markdown is not None else not shadow_run

    _write_text(paths["markdown_path"], markdown_report)
    if should_write_compat:
        _write_text(paths["compat_markdown_path"], markdown_report)
    _write_json(paths["manifest_path"], manifest)
    _write_json(paths["evidence_path"], evidence)

    if comparison_requested:
        _write_json(paths["comparison_metadata_path"], _comparison_metadata(payload_map))

    return paths
