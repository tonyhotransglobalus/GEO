from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from .comparison import normalize_comparison_run
from .markdown import MARKDOWN_FILENAME, render_v2_markdown_report
from .pdf import generate_v2_pdf_report

DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[2] / "output" / "reports-v2"
VERSIONED_MARKDOWN_FILENAME = MARKDOWN_FILENAME
PDF_FILENAME = "GEO-STRATEGY-REPORT-V2.pdf"
MANIFEST_FILENAME = "GEO-STRATEGY-REPORT-V2.manifest.json"
EVIDENCE_FILENAME = "GEO-STRATEGY-REPORT-V2.evidence.json"
COMPARISON_METADATA_FILENAME = "GEO-STRATEGY-REPORT-V2.comparison-metadata.json"
DEFAULT_RETAIN_RUNS = 3


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


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _write_pdf(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    generate_v2_pdf_report(payload, str(path))


def _cleanup_old_runs(
    reports_dir: Path,
    *,
    report_slug: str,
    retained_dirs: set[Path],
    retain_runs: int | None,
) -> None:
    if retain_runs is None or retain_runs < 0:
        return
    candidates = [
        path
        for path in reports_dir.iterdir()
        if path.is_dir()
        and path.name.startswith(f"{report_slug}-")
        and path not in retained_dirs
    ]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)

    def _remove_readonly_and_retry(func, path, exc_info):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            raise exc_info[1]

    for stale_dir in candidates[retain_runs:]:
        shutil.rmtree(stale_dir, onerror=_remove_readonly_and_retry)


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
    latest_dir = reports_dir / f"{report_slug}-latest"
    shadow_latest_dir = reports_dir / f"{report_slug}-shadow-latest"
    return {
        "report_dir": report_dir,
        "markdown_path": report_dir / VERSIONED_MARKDOWN_FILENAME,
        "pdf_path": report_dir / PDF_FILENAME,
        "compat_markdown_path": reports_dir / VERSIONED_MARKDOWN_FILENAME,
        "manifest_path": report_dir / MANIFEST_FILENAME,
        "evidence_path": report_dir / EVIDENCE_FILENAME,
        "comparison_metadata_path": report_dir / COMPARISON_METADATA_FILENAME,
        "latest_dir": latest_dir,
        "latest_markdown_path": latest_dir / VERSIONED_MARKDOWN_FILENAME,
        "latest_pdf_path": latest_dir / PDF_FILENAME,
        "latest_manifest_path": latest_dir / MANIFEST_FILENAME,
        "latest_evidence_path": latest_dir / EVIDENCE_FILENAME,
        "latest_comparison_metadata_path": latest_dir / COMPARISON_METADATA_FILENAME,
        "shadow_latest_dir": shadow_latest_dir,
        "shadow_latest_markdown_path": shadow_latest_dir / VERSIONED_MARKDOWN_FILENAME,
        "shadow_latest_pdf_path": shadow_latest_dir / PDF_FILENAME,
        "shadow_latest_manifest_path": shadow_latest_dir / MANIFEST_FILENAME,
        "shadow_latest_evidence_path": shadow_latest_dir / EVIDENCE_FILENAME,
        "shadow_latest_comparison_metadata_path": shadow_latest_dir / COMPARISON_METADATA_FILENAME,
    }


def _comparison_metadata(payload: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _coerce_mapping(payload.get("manifest"))
    adjudication = _coerce_mapping(payload.get("adjudication"))
    qa = _coerce_mapping(payload.get("qa"))
    comparison = _coerce_mapping(manifest.get("comparison_eligibility"))
    normalized_run = normalize_comparison_run(payload)
    return {
        "target_url": manifest.get("target_url"),
        "target_domain": manifest.get("target_domain"),
        "locale": manifest.get("locale"),
        "platforms": list(normalized_run.get("platforms") or []),
        "competitors": list(normalized_run.get("competitors") or []),
        "query_set": list(normalized_run.get("query_set") or []),
        "geo_score": normalized_run.get("geo_score"),
        "citation_count": normalized_run.get("citation_count"),
        "referral_visits": normalized_run.get("referral_visits"),
        "authority_gap_count": normalized_run.get("authority_gap_count"),
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
    retain_runs: int | None = DEFAULT_RETAIN_RUNS,
) -> dict[str, Path]:
    report_slug = slugify(brand_name, fallback=run_seed or date_stamp)
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
    artifact_policy = _coerce_mapping(payload_map.get("artifact_policy"))
    update_latest = bool(artifact_policy.get("update_latest", True))
    latest_channel = _clean_text(artifact_policy.get("latest_channel")) or ("shadow" if shadow_run else "published")
    should_write_compat = write_compat_markdown if write_compat_markdown is not None else not shadow_run

    _write_text(paths["markdown_path"], markdown_report)
    _write_pdf(paths["pdf_path"], payload_map)
    if should_write_compat:
        _write_text(paths["compat_markdown_path"], markdown_report)
    _write_json(paths["manifest_path"], manifest)
    _write_json(paths["evidence_path"], evidence)
    if comparison_requested:
        _write_json(paths["comparison_metadata_path"], _comparison_metadata(payload_map))

    latest_prefix = "latest" if latest_channel == "published" else "shadow_latest"
    if update_latest:
        _copy_file(paths["markdown_path"], paths[f"{latest_prefix}_markdown_path"])
        _copy_file(paths["pdf_path"], paths[f"{latest_prefix}_pdf_path"])
        _copy_file(paths["manifest_path"], paths[f"{latest_prefix}_manifest_path"])
        _copy_file(paths["evidence_path"], paths[f"{latest_prefix}_evidence_path"])
        if comparison_requested:
            _copy_file(
                paths["comparison_metadata_path"],
                paths[f"{latest_prefix}_comparison_metadata_path"],
            )

    _cleanup_old_runs(
        _coerce_dir(base_dir),
        report_slug=report_slug,
        retained_dirs={paths["latest_dir"], paths["shadow_latest_dir"]},
        retain_runs=retain_runs,
    )
    return paths
