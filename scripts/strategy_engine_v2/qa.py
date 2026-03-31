from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse
from typing import Any, Mapping


QA_ISSUE_MESSAGES = {
    "missing_score_provenance": "Missing score provenance: the report does not expose where score values came from yet.",
    "unsupported_change_since_last_run": "Unsupported change-since-last-run comparison: the run requested comparison, but no comparable delta was captured.",
    "benchmark_thinness": "Benchmark is not decision-grade in this run because named competitor evidence is still thin.",
    "prompt_proof_thinness": "Prompt proof is not decision-grade in this run because exact prompt or winner capture is still thin.",
    "unexplained_jargon": "Unexplained jargon detected: the report uses specialized terms without enough plain-English explanation.",
    "repeated_phrasing": "Repeated phrasing detected: the report repeats the same wording instead of adding new evidence.",
    "homepage_only_evidence": "Homepage-only evidence detected: the evidence ledger does not yet show breadth beyond the primary page.",
}


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
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


def _collect_text(report_sections: Mapping[str, Any], *, include_visible_reasons: bool = True) -> list[str]:
    text: list[str] = []

    leadership = _mapping(report_sections.get("leadership_summary"))
    text.extend(_sequence(leadership.get("summary")))
    if include_visible_reasons:
        text.append(_string(leadership.get("visible_reason")))

    score_explanations = _mapping(report_sections.get("score_explanations"))
    text.append(_string(score_explanations.get("plain_english_note")))
    for item in _sequence(score_explanations.get("terms")):
        if isinstance(item, Mapping):
            text.append(_string(item.get("label")))
            text.append(_string(item.get("plain_english")))
    for item in _sequence(score_explanations.get("weighting")):
        if isinstance(item, Mapping):
            text.append(_string(item.get("label")))
            text.append(_string(item.get("why_it_matters")))

    priority_findings = _mapping(report_sections.get("priority_findings"))
    for finding in _sequence(priority_findings.get("findings")):
        if isinstance(finding, Mapping):
            text.append(_string(finding.get("summary")))
            if include_visible_reasons:
                text.append(_string(finding.get("visible_reason")))

    for section_name in ("competitive_benchmark", "platform_breakdown", "page_source_evidence", "action_plan", "proof_appendix"):
        section = _mapping(report_sections.get(section_name))
        if include_visible_reasons:
            text.append(_string(section.get("reason")))
            text.append(_string(section.get("visible_reason")))
            text.append(_string(section.get("sample_note")))
        for item in _sequence(section.get("actions")):
            if isinstance(item, Mapping):
                text.append(_string(item.get("action")))
                text.append(_string(item.get("expected_outcome")))
                if include_visible_reasons:
                    text.append(_string(item.get("visible_reason")))
        for item in _sequence(section.get("evidence_items")):
            if isinstance(item, Mapping):
                text.append(_string(item.get("summary")))

    return [item for item in text if item]


def _normalized_counts(values: list[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for value in values:
        normalized = " ".join(value.lower().split())
        if normalized:
            counter[normalized] += 1
    return counter


def _word_count(value: str) -> int:
    return len([part for part in value.split() if part])


def _has_score_provenance(report_sections: Mapping[str, Any]) -> bool:
    score_explanations = _mapping(report_sections.get("score_explanations"))
    provenance = score_explanations.get("score_provenance")
    if provenance:
        return True
    run_context = _mapping(score_explanations.get("run_context"))
    return bool(run_context.get("score_provenance") or run_context.get("provenance"))


def _has_explained_jargon(report_sections: Mapping[str, Any]) -> bool:
    score_explanations = _mapping(report_sections.get("score_explanations"))
    explained_terms = {
        _string(item.get("label")).lower()
        for item in _sequence(score_explanations.get("terms"))
        if isinstance(item, Mapping)
    }
    searchable_text = " \n".join(_collect_text(report_sections)).lower()
    jargon_terms = {
        "citability": "citability",
        "decision-grade": "decision-grade",
        "directional": "directional",
        "llms": "llms",
    }
    for label, needle in jargon_terms.items():
        if needle in searchable_text and not any(
            label in explained or needle in explained for explained in explained_terms
        ):
            return False
    return True


def _find_priority_finding(report_sections: Mapping[str, Any], section_name: str) -> dict[str, Any]:
    priority_findings = _mapping(report_sections.get("priority_findings"))
    for item in _sequence(priority_findings.get("findings")):
        if isinstance(item, Mapping) and _string(item.get("section")) == section_name:
            return dict(item)
    return {}


def _clear_reason_for_section(
    report_sections: Mapping[str, Any],
    *,
    section_name: str,
) -> bool:
    section = _mapping(report_sections.get(section_name))
    finding = _find_priority_finding(report_sections, section_name)
    visible_reason = _string(section.get("visible_reason")) or _string(finding.get("visible_reason"))
    reason = _string(section.get("reason")) or _string(finding.get("summary"))
    text = f"{visible_reason} {reason}".lower().strip()
    if len(text) < 36 or _word_count(text) < 8:
        return False
    explanation_markers = (
        "because",
        "since ",
        "due to",
        "therefore",
        "thus",
        "as a result",
        "so that",
        "however",
        "although",
        "while ",
        "limited",
        "partial",
        "incomplete",
        "insufficient",
        "not enough",
        "not captured",
        "missing",
        "thin",
        "narrow",
        "sparse",
        "small",
        "cautious",
        "sampled evidence",
        "what was captured",
        "what was not",
        "what was missing",
    )
    return any(marker in text for marker in explanation_markers)


def _benchmark_thinness(report_sections: Mapping[str, Any], adjudication: Mapping[str, Any]) -> bool:
    benchmark = _mapping(adjudication.get("benchmark"))
    if _string(benchmark.get("status")) not in {"directional", "omitted"}:
        return False
    return not _clear_reason_for_section(
        report_sections,
        section_name="competitive_benchmark",
    )


def _prompt_proof_thinness(report_sections: Mapping[str, Any], adjudication: Mapping[str, Any]) -> bool:
    prompt = _mapping(adjudication.get("prompt_proof"))
    if _string(prompt.get("status")) not in {"directional", "omitted"}:
        return False
    return not _clear_reason_for_section(
        report_sections,
        section_name="prompt_proof",
    )


def _homepage_only_warning(manifest: Mapping[str, Any]) -> str:
    target_url = _string(manifest.get("target_url"))
    parsed = urlparse(target_url)
    is_root_target = parsed.path in {"", "/"} and not parsed.params and not parsed.query and not parsed.fragment
    if is_root_target:
        return QA_ISSUE_MESSAGES["homepage_only_evidence"]
    return "Single-page evidence detected: the evidence ledger does not yet show breadth beyond the primary analyzed page."


def _unsupported_change_since_last_run(manifest: Mapping[str, Any], adjudication: Mapping[str, Any]) -> bool:
    comparison = _mapping(manifest.get("comparison_eligibility"))
    if not comparison.get("requested"):
        return False
    change = _mapping(adjudication.get("change_since_last_run"))
    return _string(change.get("status")) in {"directional", "omitted"}


def _homepage_only_evidence(manifest: Mapping[str, Any], evidence: Mapping[str, Any]) -> bool:
    items = [item for item in _sequence(evidence.get("items")) if isinstance(item, Mapping)]
    if not items:
        return False
    target_url = _string(manifest.get("target_url"))
    target_domain = _string(manifest.get("target_domain"))
    if not target_url and not target_domain:
        return False
    parsed_target = urlparse(target_url)
    target_host = (urlparse(target_url).netloc or target_domain).lower().strip()
    if target_host.startswith("www."):
        target_host = target_host[4:]
    target_path = parsed_target.path or "/"
    if not target_path.startswith("/"):
        target_path = f"/{target_path}"
    if target_path != "/":
        target_path = target_path.rstrip("/")

    def _normalized_path(value: str) -> str:
        parsed = urlparse(value if "://" in value else f"https://{value}")
        path = parsed.path or "/"
        if not path.startswith("/"):
            path = f"/{path}"
        if path != "/":
            path = path.rstrip("/")
        return path

    located_items: list[tuple[str, str]] = []
    for item in items:
        value = _string(item.get("url_or_domain"))
        if not value:
            continue
        parsed = urlparse(value if "://" in value else f"https://{value}")
        host = (parsed.netloc or parsed.path).lower().strip()
        if host.startswith("www."):
            host = host[4:]
        path = _normalized_path(value)
        located_items.append((host, path))

    if not located_items:
        return False

    for host, path in located_items:
        if host != target_host or path != target_path:
            return False
    return True


def _repeated_phrasing(report_sections: Mapping[str, Any]) -> bool:
    counts = _normalized_counts(_collect_text(report_sections, include_visible_reasons=False))
    for value, count in counts.items():
        if count >= 3 and len(value) >= 32 and _word_count(value) >= 6:
            return True
    return False


def run_release_checks(report_payload: Mapping[str, Any] | None) -> dict[str, list[str]]:
    payload = _mapping(report_payload)
    manifest = _mapping(payload.get("manifest"))
    evidence = _mapping(payload.get("evidence"))
    adjudication = _mapping(payload.get("adjudication"))
    report_sections = _mapping(payload.get("report_sections"))

    issues: list[str] = []
    warnings: list[str] = []

    checks = [
        ("missing_score_provenance", not _has_score_provenance(report_sections)),
        ("unsupported_change_since_last_run", _unsupported_change_since_last_run(manifest, adjudication)),
        ("benchmark_thinness", _benchmark_thinness(report_sections, adjudication)),
        ("prompt_proof_thinness", _prompt_proof_thinness(report_sections, adjudication)),
        ("unexplained_jargon", not _has_explained_jargon(report_sections)),
        ("repeated_phrasing", _repeated_phrasing(report_sections)),
        ("homepage_only_evidence", _homepage_only_evidence(manifest, evidence)),
    ]

    for code, triggered in checks:
        if triggered:
            issues.append(code)
            if code == "homepage_only_evidence":
                warnings.append(_homepage_only_warning(manifest))
            else:
                warnings.append(QA_ISSUE_MESSAGES[code])

    return {
        "issues": issues,
        "warnings": warnings,
    }
