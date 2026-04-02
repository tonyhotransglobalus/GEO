from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_REPORTS_DIR = Path("output/reports")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "site"


def filename_token(value: str | None) -> str | None:
    if not value:
        return None
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return token or None


def extract_brand_name(page_data: dict, fallback_url: str) -> str:
    title = (page_data.get("title") or "").strip()
    if title:
        brand = re.split(r"\s+[|\-]\s+", title)[-1].strip()
        if brand:
            return brand

    structured = page_data.get("structured_data") or []
    for entry in structured:
        graph = entry.get("@graph") if isinstance(entry, dict) else None
        if not graph:
            continue
        for node in graph:
            if node.get("@type") == "Organization" and node.get("name"):
                return node["name"].strip()

    parsed = urlparse(fallback_url)
    return parsed.netloc.replace("www.", "")


def build_combined_audit_data(
    url: str,
    brand_name: str,
    geo_scores: dict,
    rescience_pass: dict,
    executive_summary: str,
    findings: list[dict],
    quick_wins: list[str],
    medium_term: list[str],
    strategic: list[str],
    crawler_access: dict,
    date: str | None = None,
    platforms: dict | None = None,
    query_clusters: list[dict] | None = None,
    competitor_profiles: list[dict] | None = None,
    entity_graph: dict | None = None,
    citation_failures: list[dict] | None = None,
    plugin_results: dict | None = None,
    report_model: dict | None = None,
    report_sections: dict | None = None,
    client_report_sections: dict | None = None,
    presentation_metadata: dict | None = None,
) -> dict:
    combined = {
        "url": url,
        "brand_name": brand_name,
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "geo_score": geo_scores["geo_score"],
        "scores": geo_scores["scores"],
        "platforms": platforms or {},
        "executive_summary": executive_summary,
        "findings": findings,
        "quick_wins": quick_wins,
        "medium_term": medium_term,
        "strategic": strategic,
        "crawler_access": crawler_access,
        "rescience_pass": rescience_pass,
        "query_clusters": query_clusters or [],
        "competitor_profiles": competitor_profiles or [],
        "entity_graph": entity_graph,
        "citation_failures": citation_failures or [],
        "plugin_results": plugin_results or {},
    }
    if report_model is not None:
        combined["report_model"] = report_model
    if report_sections is not None:
        combined["report_sections"] = report_sections
    if client_report_sections is not None:
        combined["client_report_sections"] = client_report_sections
    if presentation_metadata is not None:
        combined["presentation_metadata"] = presentation_metadata
    return combined


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def build_output_paths(
    brand_name: str,
    date_stamp: str,
    *,
    run_mode: str = "script-only",
    model_name: str | None = None,
) -> dict[str, Path]:
    report_dir = DEFAULT_REPORTS_DIR / f"{slugify(brand_name)}-{date_stamp}"
    
    # Unified output naming to avoid confusion
    pdf_path = report_dir / "GEO-STRATEGY-REPORT.pdf"
    markdown_path = report_dir / "GEO-STRATEGY-REPORT.md"
    
    return {
        "report_dir": report_dir,
        "markdown_path": markdown_path,
        "json_path": report_dir / "audit-data.json",
        "pdf_path": pdf_path,
        "client_pdf_path": pdf_path,
        "script_pdf_path": pdf_path,
        "assisted_pdf_path": pdf_path,
        "script_markdown_path": markdown_path,
        "assisted_markdown_path": markdown_path,
    }
