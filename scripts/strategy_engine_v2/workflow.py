from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import urlparse

import requests

from .adjudication import adjudicate_v2_sections
from .comparison import compare_runs, normalize_comparison_run
from .evidence import build_v2_evidence_ledger
from .manifest import build_run_manifest
from .publish import publish_v2_artifacts
from .qa import run_release_checks
from .reporting import build_v2_report_sections

try:
    from ..full_audit import orchestrate_audit
    from ..strategy_engine.plugins import opportunity as opportunity_plugin
except ImportError:
    from full_audit import orchestrate_audit
    from strategy_engine.plugins import opportunity as opportunity_plugin


class PublishV2Artifacts(Protocol):
    def __call__(
        self,
        *,
        brand_name: str,
        date_stamp: str,
        payload: dict[str, Any],
        base_dir: Path | str | None = None,
        run_seed: str | None = None,
        write_compat_markdown: bool | None = None,
    ) -> dict[str, Path]: ...


def _run_v1_audit(
    *,
    url: str,
    competitor_domains: list[str] | None = None,
    seed_topics: list[str] | None = None,
    locale: str = "en-us",
) -> dict[str, Any]:
    with _bridge_resilient_opportunity_fetchers() as network_fallbacks:
        audit_data = orchestrate_audit(
            url,
            competitor_domains=competitor_domains,
            seed_topics=seed_topics,
            locale=locale,
            generate_pdf_output=False,
        )
    return _record_bridge_fallbacks(audit_data, network_fallbacks)


def _bridge_fallback_record(stage: str, query: str, exc: Exception) -> dict[str, str]:
    return {
        "component": "opportunity",
        "stage": stage,
        "query": str(query).strip(),
        "error": f"{type(exc).__name__}: {exc}",
    }


def _bridge_fallback_text(fallback: dict[str, str]) -> str:
    stage = fallback.get("stage", "network call").replace("_", " ")
    query = fallback.get("query", "").strip()
    if query:
        return f"DuckDuckGo {stage} timed out for '{query}', so benchmark and query evidence stayed partial in this run."
    return f"DuckDuckGo {stage} timed out, so benchmark and query evidence stayed partial in this run."


@contextmanager
def _bridge_resilient_opportunity_fetchers():
    network_fallbacks: list[dict[str, str]] = []
    original_keyword_fetch = opportunity_plugin.fetch_keyword_suggestions
    original_serp_fetch = opportunity_plugin.fetch_serp_snapshot

    # V2 bridge runs should degrade gracefully when external keyword/SERP helpers time out.
    def safe_keyword_fetch(query: str, *args: Any, **kwargs: Any):
        try:
            return original_keyword_fetch(query, *args, **kwargs)
        except requests.RequestException as exc:
            network_fallbacks.append(
                _bridge_fallback_record("keyword_suggestions", query, exc)
            )
            return []

    def safe_serp_fetch(query: str, *args: Any, **kwargs: Any):
        try:
            return original_serp_fetch(query, *args, **kwargs)
        except requests.RequestException as exc:
            network_fallbacks.append(
                _bridge_fallback_record("serp_snapshot", query, exc)
            )
            return []

    opportunity_plugin.fetch_keyword_suggestions = safe_keyword_fetch
    opportunity_plugin.fetch_serp_snapshot = safe_serp_fetch
    try:
        yield network_fallbacks
    finally:
        opportunity_plugin.fetch_keyword_suggestions = original_keyword_fetch
        opportunity_plugin.fetch_serp_snapshot = original_serp_fetch


def _record_bridge_fallbacks(
    audit_data: dict[str, Any],
    network_fallbacks: list[dict[str, str]],
) -> dict[str, Any]:
    if not network_fallbacks:
        return audit_data

    enriched = dict(audit_data)
    bridge_metadata = enriched.get("v2_bridge_metadata")
    if not isinstance(bridge_metadata, dict):
        bridge_metadata = {}
    else:
        bridge_metadata = dict(bridge_metadata)
    bridge_metadata["network_fallbacks"] = [dict(item) for item in network_fallbacks]
    enriched["v2_bridge_metadata"] = bridge_metadata

    client_sections = enriched.get("client_report_sections")
    if not isinstance(client_sections, dict):
        client_sections = {}
    else:
        client_sections = dict(client_sections)
    technical_proof = client_sections.get("technical_proof_appendix")
    if not isinstance(technical_proof, dict):
        technical_proof = {}
    else:
        technical_proof = dict(technical_proof)
    bridge_warnings = list(technical_proof.get("bridge_warnings") or [])
    for fallback in network_fallbacks:
        text = _bridge_fallback_text(fallback)
        if text not in bridge_warnings:
            bridge_warnings.append(text)
    technical_proof["bridge_warnings"] = bridge_warnings
    client_sections["technical_proof_appendix"] = technical_proof
    enriched["client_report_sections"] = client_sections
    return enriched


def build_rollout_metadata(
    *,
    shadow_run: bool,
    comparable_to_v1: bool | None = None,
    comparison_eligible: bool | None = None,
) -> dict[str, Any]:
    if comparison_eligible is not None:
        comparable = comparison_eligible
    elif comparable_to_v1 is not None:
        comparable = comparable_to_v1
    else:
        comparable = False
    return {
        "shadow_run": shadow_run,
        "comparable_to_v1": bool(comparable),
        "promotion_ready": False,
        "promotion_owner": "TBD",
        "checklist_status": "pending",
    }


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_timestamp(value: Any) -> datetime | None:
    text = _string(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _normalized_platforms(platforms: Any) -> list[str]:
    return sorted(
        _string(platform).lower()
        for platform in _sequence(platforms)
        if _string(platform)
    )


def _normalized_url_parts(value: str | None) -> tuple[str, str]:
    text = _string(value)
    if not text:
        return ("", "")
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.netloc or parsed.path).lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return host, path


def _load_json(path: Path) -> dict[str, Any]:
    return _mapping(json.loads(path.read_text(encoding="utf-8")))


def _comparison_snapshot(
    *,
    manifest: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    items = [
        item for item in _sequence(evidence.get("items")) if isinstance(item, dict)
    ]
    target_host, target_path = _normalized_url_parts(manifest.get("target_url"))
    non_primary_pages: set[str] = set()
    prompt_proof_count = 0
    benchmark_row_count = 0
    priority_page_count = 0
    for item in items:
        evidence_type = _string(item.get("evidence_type"))
        if evidence_type == "prompt_proof":
            prompt_proof_count += 1
        if evidence_type == "benchmark_row":
            benchmark_row_count += 1
        if evidence_type == "priority_page":
            priority_page_count += 1
        host, path = _normalized_url_parts(item.get("url_or_domain"))
        if host and host == target_host and path and path != target_path:
            non_primary_pages.add(f"{host}{path}")
    return {
        "evidence_count": len(items) or int(evidence.get("count") or 0),
        "non_primary_page_count": len(non_primary_pages),
        "prompt_proof_count": prompt_proof_count,
        "benchmark_row_count": benchmark_row_count,
        "priority_page_count": priority_page_count,
    }


def _count_snapshot_changes(
    current_snapshot: dict[str, Any],
    previous_snapshot: dict[str, Any],
) -> int:
    fields = (
        "evidence_count",
        "non_primary_page_count",
        "prompt_proof_count",
        "benchmark_row_count",
        "priority_page_count",
    )
    return sum(
        1
        for field in fields
        if current_snapshot.get(field) != previous_snapshot.get(field)
    )


def _is_compatible_manifest(
    candidate: dict[str, Any],
    current: dict[str, Any],
) -> bool:
    return (
        _string(candidate.get("target_url")) == _string(current.get("target_url"))
        and _string(candidate.get("locale")) == _string(current.get("locale"))
        and _normalized_platforms(candidate.get("platforms"))
        == _normalized_platforms(current.get("platforms"))
    )


def _load_previous_comparison_context(
    *,
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    reports_dir: Path | None,
    audit_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    comparison = _mapping(manifest.get("comparison_eligibility"))
    current_snapshot = _comparison_snapshot(manifest=manifest, evidence=evidence)
    current_run = normalize_comparison_run(
        {
            "manifest": manifest,
            "evidence": evidence,
            "audit_data": audit_data,
        }
    )
    if not comparison.get("requested") or not comparison.get("eligible"):
        return {
            "current_snapshot": current_snapshot,
            "previous_snapshot": {},
            "change_points": 0,
            "delta_summary": compare_runs(current_run, {}),
        }

    search_root = reports_dir or Path(__file__).resolve().parents[2] / "output" / "reports-v2"
    if not search_root.exists():
        return {
            "current_snapshot": current_snapshot,
            "previous_snapshot": {},
            "change_points": 0,
            "delta_summary": compare_runs(current_run, {}),
        }

    current_timestamp = _parse_timestamp(manifest.get("run_timestamp"))
    candidates: list[tuple[datetime, dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for manifest_path in search_root.rglob("GEO-STRATEGY-REPORT-V2.manifest.json"):
        try:
            candidate_manifest = _load_json(manifest_path)
        except Exception:
            continue
        if not _is_compatible_manifest(candidate_manifest, manifest):
            continue
        candidate_timestamp = _parse_timestamp(candidate_manifest.get("run_timestamp"))
        if candidate_timestamp is None:
            continue
        if current_timestamp is not None and candidate_timestamp >= current_timestamp:
            continue
        evidence_path = manifest_path.with_name("GEO-STRATEGY-REPORT-V2.evidence.json")
        if not evidence_path.exists():
            continue
        try:
            candidate_evidence = _load_json(evidence_path)
        except Exception:
            continue
        comparison_metadata_path = manifest_path.with_name("GEO-STRATEGY-REPORT-V2.comparison-metadata.json")
        candidate_metadata = {}
        if comparison_metadata_path.exists():
            try:
                candidate_metadata = _load_json(comparison_metadata_path)
            except Exception:
                candidate_metadata = {}
        candidates.append((candidate_timestamp, candidate_manifest, candidate_evidence, candidate_metadata))

    if not candidates:
        return {
            "current_snapshot": current_snapshot,
            "previous_snapshot": {},
            "change_points": 0,
            "delta_summary": compare_runs(current_run, {}),
        }

    _, previous_manifest, previous_evidence, previous_metadata = sorted(
        candidates,
        key=lambda item: item[0],
        reverse=True,
    )[0]
    previous_snapshot = _comparison_snapshot(
        manifest=previous_manifest,
        evidence=previous_evidence,
    )
    previous_run = normalize_comparison_run(
        {
            "manifest": previous_manifest,
            "evidence": previous_evidence,
            "comparison_metadata": previous_metadata,
        }
    )
    return {
        "previous_manifest": previous_manifest,
        "previous_snapshot": previous_snapshot,
        "current_snapshot": current_snapshot,
        "change_points": _count_snapshot_changes(current_snapshot, previous_snapshot),
        "delta_summary": compare_runs(current_run, previous_run),
    }


@dataclass(slots=True)
class StrategyV2WorkflowDependencies:
    build_run_manifest: Callable[..., dict]
    run_v1_audit: Callable[..., dict]
    build_v2_evidence_ledger: Callable[..., dict]
    adjudicate_v2_sections: Callable[..., dict]
    build_v2_report_sections: Callable[[dict[str, Any]], dict[str, Any]]
    run_release_checks: Callable[[dict[str, Any]], dict[str, list[str]]]
    publish_v2_artifacts: PublishV2Artifacts


def build_workflow_dependencies() -> StrategyV2WorkflowDependencies:
    return StrategyV2WorkflowDependencies(
        build_run_manifest=build_run_manifest,
        run_v1_audit=_run_v1_audit,
        build_v2_evidence_ledger=build_v2_evidence_ledger,
        adjudicate_v2_sections=adjudicate_v2_sections,
        build_v2_report_sections=build_v2_report_sections,
        run_release_checks=run_release_checks,
        publish_v2_artifacts=publish_v2_artifacts,
    )


def run_strategy_report_v2(
    url: str,
    *,
    shadow_run: bool = False,
    compare_to_v1: bool = False,
    locale: str = "en-us",
    platforms: list[str] | None = None,
    competitors: list[str] | None = None,
    mode: str = "script-only",
    driver: str = "script",
    model: str | None = None,
    measurement_data: dict[str, Any] | None = None,
    business_profile: str | None = None,
    non_interactive: bool = False,
    reports_dir: Path | None = None,
    deps: StrategyV2WorkflowDependencies | None = None,
) -> dict:
    using_default_deps = deps is None
    deps = deps or build_workflow_dependencies()
    manifest = deps.build_run_manifest(
        url=url,
        locale=locale,
        platforms=platforms,
        competitors=competitors,
        mode=mode,
        driver=driver,
        model=model,
        interactive=not non_interactive,
        compare_to_v1=compare_to_v1,
        shadow_run=shadow_run,
    )
    audit_data = deps.run_v1_audit(
        url=url,
        competitor_domains=competitors,
        seed_topics=list(manifest.get("seed_topics") or []),
        locale=locale,
    )
    if measurement_data is not None:
        audit_data = dict(audit_data)
        audit_data["measurement_data"] = dict(measurement_data)
    if business_profile is not None:
        audit_data = dict(audit_data)
        audit_data["business_profile"] = business_profile
    evidence = deps.build_v2_evidence_ledger(
        manifest=manifest,
        audit_data=audit_data,
    )
    comparison_context = _load_previous_comparison_context(
        manifest=manifest,
        evidence=evidence,
        reports_dir=reports_dir,
        audit_data=audit_data,
    )
    adjudication = deps.adjudicate_v2_sections(
        manifest=manifest,
        evidence=evidence,
        audit_data=audit_data,
        comparison_context=comparison_context,
    )
    report_sections = deps.build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": adjudication,
            "audit_data": audit_data,
            "comparison_context": comparison_context,
        }
    )
    qa = deps.run_release_checks(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": adjudication,
            "report_sections": report_sections,
            "audit_data": audit_data,
            "comparison_context": comparison_context,
        }
    )
    comparison_eligibility = manifest.get("comparison_eligibility") or {}
    comparable_to_v1 = bool(comparison_eligibility.get("eligible"))
    rollout_metadata = build_rollout_metadata(
        shadow_run=shadow_run,
        comparable_to_v1=bool(compare_to_v1),
        comparison_eligible=comparable_to_v1,
    )
    artifact_policy = {
        "source_kind": "live_audit" if using_default_deps else "custom_deps",
        "update_latest": using_default_deps,
        "latest_channel": "shadow" if shadow_run else "published",
    }
    target_domain = manifest.get("target_domain") or ""
    target_url = manifest.get("target_url") or ""
    run_seed = "|".join(
        value
        for value in (
            str(manifest.get("run_timestamp") or ""),
            target_url or target_domain,
            mode,
            driver,
            model or "",
        )
        if value
    )
    artifact_paths = deps.publish_v2_artifacts(
        brand_name=target_domain or target_url or "",
        date_stamp=str(manifest.get("run_timestamp") or "")[:10] or "unknown-date",
        run_seed=run_seed,
        payload={
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": adjudication,
            "qa": qa,
            "report_sections": report_sections,
            "rollout_metadata": rollout_metadata,
            "audit_data": audit_data,
            "comparison_context": comparison_context,
            "artifact_policy": artifact_policy,
        },
        base_dir=reports_dir,
        write_compat_markdown=not shadow_run,
    )
    return {
        "version": "v2",
        "manifest": manifest,
        "evidence": evidence,
        "adjudication": adjudication,
        "report_sections": report_sections,
        "qa": qa,
        "rollout_metadata": rollout_metadata,
        "release_warnings": list(qa.get("warnings") or []),
        "artifact_paths": {key: str(value) for key, value in artifact_paths.items()},
        "status": "shadow" if shadow_run else "generated",
    }
