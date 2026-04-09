from __future__ import annotations

from typing import Any, Mapping


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


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _sorted_strings(values: Any) -> list[str]:
    return sorted({_string(value) for value in _sequence(values) if _string(value)})


def normalize_comparison_run(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    source = _mapping(payload)
    manifest = _mapping(source.get("manifest"))
    audit_data = _mapping(source.get("audit_data"))
    evidence = _mapping(source.get("evidence"))
    metadata = _mapping(source.get("comparison_metadata"))

    items = [item for item in _sequence(evidence.get("items")) if isinstance(item, Mapping)]
    query_set: set[str] = set()
    prompt_set: set[str] = set()

    for cluster in _sequence(audit_data.get("query_clusters")):
        if not isinstance(cluster, Mapping):
            continue
        for query in _sequence(cluster.get("queries")):
            text = _string(query)
            if text:
                query_set.add(text)

    citation_count = 0
    referral_visits = 0
    authority_gap_count = 0
    for item in items:
        evidence_type = _string(item.get("evidence_type"))
        raw = _mapping(item.get("raw_observation"))
        if evidence_type == "citation_share_signal":
            citation_count += _int(raw.get("cited_count"))
        elif evidence_type == "platform_measurement":
            citation_count += _int(raw.get("citation_count"))
            referral_visits += _int(raw.get("referral_visits"))
        elif evidence_type == "referral_signal":
            referral_visits += _int(raw.get("visits"))
        elif evidence_type == "offsite_authority_gap":
            authority_gap_count += 1
        if evidence_type in {"query_cluster", "prompt_proof", "citation_failure"}:
            query = _string(raw.get("query_or_prompt")) or _string(item.get("query_theme"))
            if query:
                query_set.add(query)
        if evidence_type == "prompt_proof":
            prompt = _string(raw.get("query_or_prompt")) or _string(item.get("query_theme"))
            if prompt:
                prompt_set.add(prompt)

    return {
        "target_url": _string(manifest.get("target_url")) or _string(metadata.get("target_url")),
        "locale": _string(manifest.get("locale")) or _string(metadata.get("locale")),
        "platforms": _sorted_strings(manifest.get("platforms") or metadata.get("platforms")),
        "competitors": _sorted_strings(manifest.get("competitors") or metadata.get("competitors")),
        "query_set": sorted(query_set) or _sorted_strings(metadata.get("query_set")),
        "prompt_set": sorted(prompt_set) or _sorted_strings(metadata.get("prompt_set")),
        "geo_score": _int(audit_data.get("geo_score")) or _int(metadata.get("geo_score")),
        "citation_count": citation_count or _int(metadata.get("citation_count")),
        "referral_visits": referral_visits or _int(metadata.get("referral_visits")),
        "authority_gap_count": authority_gap_count or _int(metadata.get("authority_gap_count")),
    }


def compare_runs(current: Mapping[str, Any] | None, previous: Mapping[str, Any] | None) -> dict[str, Any]:
    current_run = _mapping(current)
    previous_run = _mapping(previous)
    reasons: list[str] = []

    if not previous_run:
        reasons.append("No comparable prior run was found.")
    else:
        for field, label in (
            ("target_url", "target URL"),
            ("locale", "locale"),
            ("platforms", "platform set"),
            ("competitors", "competitor set"),
            ("query_set", "query set"),
            ("prompt_set", "prompt set"),
        ):
            current_value = current_run.get(field)
            previous_value = previous_run.get(field)
            if current_value and previous_value and current_value != previous_value:
                reasons.append(f"The {label} changed between runs.")

    comparable = not reasons
    delta_items: list[dict[str, Any]] = []
    for metric, label in (
        ("geo_score", "GEO score"),
        ("citation_count", "Citations"),
        ("referral_visits", "Referral visits"),
        ("authority_gap_count", "Authority gaps"),
    ):
        current_value = _int(current_run.get(metric))
        previous_value = _int(previous_run.get(metric))
        if not previous_run and current_value == 0 and previous_value == 0:
            continue
        delta = current_value - previous_value
        if delta > 0:
            direction = "up"
        elif delta < 0:
            direction = "down"
        else:
            direction = "flat"
        delta_items.append(
            {
                "metric": metric,
                "label": label,
                "current": current_value,
                "previous": previous_value,
                "delta": delta,
                "direction": direction,
            }
        )

    if comparable:
        phrases: list[str] = []
        for item in delta_items:
            if item["direction"] == "flat":
                continue
            verb = "improved by" if item["direction"] == "up" else "declined by"
            phrases.append(f"{item['label']} {verb} {abs(int(item['delta']))}")
        summary = (
            "Comparable run found. " + ", ".join(phrases) + "."
            if phrases
            else "Comparable run found, but tracked metrics were flat."
        )
    else:
        summary = " ".join(reasons) if reasons else "Runs are not fully comparable yet, so deltas stay directional."

    return {
        "comparable": comparable,
        "summary": summary,
        "delta_items": delta_items,
        "what_upgrades_this": "Keep the same query, competitor, and prompt sets in the next run.",
        "reasons": reasons,
    }
