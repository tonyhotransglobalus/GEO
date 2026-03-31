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

from .markdown import MARKDOWN_FILENAME, render_v2_markdown_report

try:
    from ..strategy_engine.pdf import generate_report
except ImportError:
    try:
        from scripts.strategy_engine.pdf import generate_report
    except ImportError:
        from strategy_engine.pdf import generate_report

DEFAULT_REPORTS_DIR = Path(__file__).resolve().parents[2] / "output" / "reports"
VERSIONED_MARKDOWN_FILENAME = MARKDOWN_FILENAME
PDF_FILENAME = "GEO-STRATEGY-REPORT-V2.pdf"
MANIFEST_FILENAME = "GEO-STRATEGY-REPORT-V2.manifest.json"
EVIDENCE_FILENAME = "GEO-STRATEGY-REPORT-V2.evidence.json"
COMPARISON_METADATA_FILENAME = "GEO-STRATEGY-REPORT-V2.comparison-metadata.json"
DEFAULT_RETAIN_RUNS = 10


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


def _score_lookup(rows: list[Any], label: str) -> Any:
    normalized_label = label.strip().lower()
    for row in rows:
        if isinstance(row, Mapping) and str(row.get("label", "")).strip().lower() == normalized_label:
            return row.get("score")
    return None


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _sample_completeness(evidence_count: int, trust_value: str) -> str:
    if trust_value.lower() == "high" or evidence_count >= 25:
        return "strong"
    if evidence_count >= 8:
        return "partial"
    return "thin"


def _map_v2_status_to_verdict(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "decision-grade":
        return "visible"
    if normalized == "directional":
        return "partially_visible"
    return "not_yet_competitive"


def _structured_priority_findings(report_sections: dict[str, Any]) -> list[dict[str, Any]]:
    findings_section = _coerce_mapping(report_sections.get("priority_findings"))
    items: list[dict[str, Any]] = []
    for finding in findings_section.get("findings") or []:
        if not isinstance(finding, Mapping):
            continue
        evidence_items = [
            dict(item)
            for item in finding.get("evidence_items") or []
            if isinstance(item, Mapping)
        ]
        items.append(
            {
                "title": _clean_text(finding.get("section")).replace("_", " ").title(),
                "severity": _clean_text(finding.get("status")),
                "plain_english_summary": _clean_text(finding.get("summary")),
                "what_we_observed": _clean_text(finding.get("visible_reason")),
                "why_it_matters_to_business": _clean_text(finding.get("leadership_impact")),
                "evidence_class": ", ".join(
                    _clean_list([item.get("source_class") for item in evidence_items])
                ),
                "proof": ", ".join(
                    _clean_list([item.get("normalized_summary") for item in evidence_items])
                ),
                "confidence": _clean_text(
                    next((item.get("confidence") for item in evidence_items if item.get("confidence")), "")
                ),
                "counterpoint_or_limitation": _clean_text(finding.get("visible_reason")),
                "marketing_action": _clean_text(finding.get("marketing_action")),
                "engineering_action": _clean_text(finding.get("engineering_action")),
                "success_metric": _clean_text(finding.get("success_metric")),
                "affected_pages_or_queries_text": ", ".join(
                    _clean_list([item.get("query_theme") or item.get("url_or_domain") for item in evidence_items])
                ),
            }
        )
    return items


def _prompt_query_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = _coerce_mapping(payload.get("evidence"))
    rows: list[dict[str, Any]] = []
    for item in evidence.get("items") or []:
        if not isinstance(item, Mapping):
            continue
        if _clean_text(item.get("evidence_type")) != "prompt_proof":
            continue
        raw = _coerce_mapping(item.get("raw_observation"))
        if raw:
            rows.append(raw)
    return rows


def _build_v2_client_sections(payload: Mapping[str, Any]) -> dict[str, Any]:
    payload_map = _coerce_mapping(payload)
    manifest = _coerce_mapping(payload_map.get("manifest"))
    audit_data = _coerce_mapping(payload_map.get("audit_data"))
    report_sections = _coerce_mapping(payload_map.get("report_sections"))
    adjudication = _coerce_mapping(payload_map.get("adjudication"))
    evidence = _coerce_mapping(payload_map.get("evidence"))
    score_explanations = _coerce_mapping(report_sections.get("score_explanations"))
    scorecard = list(score_explanations.get("scorecard") or [])
    leadership = _coerce_mapping(report_sections.get("leadership_summary"))
    benchmark = _coerce_mapping(report_sections.get("competitive_benchmark"))
    platform_breakdown = _coerce_mapping(report_sections.get("platform_breakdown"))
    page_source = _coerce_mapping(report_sections.get("page_source_evidence"))
    action_plan = _coerce_mapping(report_sections.get("action_plan"))
    proof_appendix = _coerce_mapping(report_sections.get("proof_appendix"))
    evidence_count = int(evidence.get("count") or len(evidence.get("items") or []))
    trust_value = _clean_text(leadership.get("trust_value")) or "Low"
    findings = _structured_priority_findings(report_sections)
    prompt_rows = _prompt_query_rows(payload_map)

    weighting_items = []
    for item in score_explanations.get("weighting") or []:
        if isinstance(item, Mapping):
            weighting_items.append(
                {
                    "metric_name": _clean_text(item.get("label")),
                    "weight": "Context",
                    "why_this_weight_exists": _clean_text(item.get("why_it_matters")),
                }
            )

    metric_items = []
    for row in scorecard:
        if not isinstance(row, Mapping):
            continue
        metric_items.append(
            {
                "metric_name": _clean_text(row.get("label")),
                "score": _clean_text(row.get("score")),
                "plain_english_definition": _clean_text(row.get("plain_english")),
                "why_this_score_landed_here": _clean_text(score_explanations.get("score_provenance")),
                "what_good_looks_like": _clean_text(row.get("what_good_looks_like")),
                "primary_evidence_used": [_clean_text(score_explanations.get("score_provenance"))] if _clean_text(score_explanations.get("score_provenance")) else [],
                "confidence": trust_value.lower(),
            }
        )

    top_actions = []
    for action in action_plan.get("actions") or []:
        if not isinstance(action, Mapping):
            continue
        top_actions.append(
            {
                "action": _clean_text(action.get("action")),
                "owner": _clean_text(action.get("owner")),
                "expected_outcome": _clean_text(action.get("expected_outcome")),
            }
        )
        if len(top_actions) >= 3:
            break

    blockers = []
    for finding in findings[:3]:
        blockers.append(
            {
                "title": finding.get("title", ""),
                "severity": finding.get("severity", ""),
                "business_impact": finding.get("why_it_matters_to_business", ""),
                "evidence_class": finding.get("evidence_class", ""),
                "confidence": finding.get("confidence", ""),
            }
        )

    opportunities = []
    for action in action_plan.get("actions") or []:
        if not isinstance(action, Mapping):
            continue
        opportunities.append(
            {
                "title": _clean_text(action.get("action")),
                "why_now": _clean_text(action.get("visible_reason")),
                "expected_outcome": _clean_text(action.get("expected_outcome")),
                "confidence": _clean_text(action.get("confidence")) or trust_value.lower(),
            }
        )
        if len(opportunities) >= 3:
            break

    methodology = _coerce_mapping(proof_appendix.get("methodology"))
    limitations = _coerce_mapping(proof_appendix.get("limitations"))

    return {
        "cover_verdict": {
            "brand_name": _clean_text(audit_data.get("brand_name")) or _clean_text(manifest.get("target_domain")),
            "primary_domain": _clean_text(manifest.get("target_domain")),
            "audit_date": _clean_text(audit_data.get("date")) or _clean_text(str(manifest.get("run_timestamp") or "")[:10]),
            "analysis_window": _clean_text(str(manifest.get("run_timestamp") or "")[:10]),
            "verdict_status": _map_v2_status_to_verdict(_clean_text(leadership.get("status"))),
            "one_sentence_verdict": _clean_text((leadership.get("summary") or ["No verdict summary captured."])[0]),
            "overall_confidence": trust_value.lower(),
            "confidence_reason": _clean_text(leadership.get("visible_reason")),
            "sample_completeness": _sample_completeness(evidence_count, trust_value),
        },
        "decision_summary": {
            "what_is_working": _clean_list((leadership.get("summary") or [])[1:3]),
            "what_is_not_working": _clean_list([finding.get("plain_english_summary") for finding in findings[:3]]),
            "top_blockers": blockers,
            "top_opportunities": opportunities,
            "leadership_takeaway": _clean_text(leadership.get("visible_reason")),
            "top_3_actions": top_actions,
        },
        "score_definitions": {
            "term_guide": [
                {
                    "term": _clean_text(item.get("label")),
                    "plain_english": _clean_text(item.get("plain_english")),
                }
                for item in score_explanations.get("terms") or []
                if isinstance(item, Mapping)
            ],
            "weighting": {
                "summary": _clean_text(score_explanations.get("plain_english_note")),
                "components": weighting_items,
            },
            "metrics": metric_items,
        },
        "priority_findings": {"items": findings},
        "competitive_benchmark": {
            "summary": _clean_text(benchmark.get("reason")),
            "competitor_set": _clean_list(benchmark.get("competitors")),
            "sample_scope": _coerce_mapping(benchmark.get("sample_scope")),
            "benchmark_rows": list(benchmark.get("benchmark_rows") or []),
        },
        "platform_breakdown": {
            "platforms": list(platform_breakdown.get("platforms") or []),
        },
        "prompt_query_proof": {
            "sampling_note": _clean_text(_coerce_mapping(adjudication.get("prompt_proof")).get("warning")),
            "rows": prompt_rows,
        },
        "page_source_evidence": {
            "priority_pages": list(page_source.get("priority_pages") or []),
            "source_domains": list(page_source.get("source_domains") or []),
            "entity_signal_review": _coerce_mapping(page_source.get("entity_signal_review")),
        },
        "action_plan_30_60_90": {
            "actions": [
                {
                    "time_horizon": _clean_text(action.get("time_horizon")),
                    "action": _clean_text(action.get("action")),
                    "owner": _clean_text(action.get("owner")),
                    "effort": _clean_text(action.get("effort")) or "medium",
                    "expected_outcome": _clean_text(action.get("expected_outcome")),
                    "confidence": _clean_text(action.get("confidence")) or trust_value.lower(),
                }
                for action in action_plan.get("actions") or []
                if isinstance(action, Mapping)
            ],
        },
        "technical_proof_appendix": {
            "methodology": {
                "summary": _clean_text(methodology.get("summary")) or "V2 bridged the live audit into a stricter evidence-governed report.",
                "confidence_note": _clean_text(methodology.get("confidence_note"))
                or _clean_text(_coerce_mapping(adjudication.get("prompt_proof")).get("warning")),
                "provenance_note": _clean_text(score_explanations.get("score_provenance")),
            },
            "crawl_and_fetch_evidence": list(proof_appendix.get("crawl_and_fetch_evidence") or []),
            "robots_and_bot_access": list(proof_appendix.get("robots_and_bot_access") or []),
            "dom_and_heading_proof": list(proof_appendix.get("dom_and_heading_proof") or []),
            "schema_proof": list(proof_appendix.get("schema_proof") or []),
            "source_inventory": list(proof_appendix.get("source_inventory") or []),
            "limitations": {
                "limitations_note": _clean_text(limitations.get("limitations_note"))
                or _clean_text(_coerce_mapping(adjudication.get("benchmark")).get("warning")),
            },
        },
    }


def _build_v2_pdf_data(payload: Mapping[str, Any]) -> dict[str, Any]:
    payload_map = _coerce_mapping(payload)
    manifest = _coerce_mapping(payload_map.get("manifest"))
    audit_data = dict(_coerce_mapping(payload_map.get("audit_data")))
    report_sections = _coerce_mapping(payload_map.get("report_sections"))
    scorecard = list(_coerce_mapping(report_sections.get("score_explanations")).get("scorecard") or [])

    geo_score = audit_data.get("geo_score")
    if geo_score is None:
        geo_score = _score_lookup(scorecard, "GEO Score")

    scores = dict(_coerce_mapping(audit_data.get("scores")))
    score_map = {
        "AI Citability": "ai_citability",
        "Brand Authority": "brand_authority",
        "Content E-E-A-T": "content_eeat",
        "Technical Foundation": "technical",
        "Schema": "schema",
        "Platform Optimization": "platform_optimization",
    }
    for label, key in score_map.items():
        value = _score_lookup(scorecard, label)
        if value is not None:
            scores[key] = value

    pdf_data = dict(audit_data)
    pdf_data["url"] = _clean_text(audit_data.get("url")) or _clean_text(manifest.get("target_url"))
    pdf_data["brand_name"] = _clean_text(audit_data.get("brand_name")) or _clean_text(manifest.get("target_domain"))
    pdf_data["date"] = _clean_text(audit_data.get("date")) or _clean_text(str(manifest.get("run_timestamp") or "")[:10])
    pdf_data["geo_score"] = geo_score
    pdf_data["scores"] = scores
    pdf_data["executive_summary"] = " ".join(_clean_list(_coerce_mapping(report_sections.get("leadership_summary")).get("summary")))
    pdf_data["client_report_sections"] = _build_v2_client_sections(payload_map)
    return pdf_data


def _write_pdf(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    generate_report(_build_v2_pdf_data(payload), str(path))


def _cleanup_old_runs(
    reports_dir: Path,
    *,
    report_slug: str,
    latest_dir: Path,
    retain_runs: int | None,
) -> None:
    if retain_runs is None or retain_runs < 0:
        return
    candidates = [
        path
        for path in reports_dir.iterdir()
        if path.is_dir()
        and path.name.startswith(f"{report_slug}-")
        and path != latest_dir
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
    should_write_compat = write_compat_markdown if write_compat_markdown is not None else not shadow_run

    _write_text(paths["markdown_path"], markdown_report)
    _write_pdf(paths["pdf_path"], payload_map)
    if should_write_compat:
        _write_text(paths["compat_markdown_path"], markdown_report)
    _write_json(paths["manifest_path"], manifest)
    _write_json(paths["evidence_path"], evidence)
    _copy_file(paths["markdown_path"], paths["latest_markdown_path"])
    _copy_file(paths["pdf_path"], paths["latest_pdf_path"])
    _copy_file(paths["manifest_path"], paths["latest_manifest_path"])
    _copy_file(paths["evidence_path"], paths["latest_evidence_path"])

    if comparison_requested:
        _write_json(paths["comparison_metadata_path"], _comparison_metadata(payload_map))
        _copy_file(paths["comparison_metadata_path"], paths["latest_comparison_metadata_path"])

    _cleanup_old_runs(
        _coerce_dir(base_dir),
        report_slug=report_slug,
        latest_dir=paths["latest_dir"],
        retain_runs=retain_runs,
    )
    return paths
