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


def _clean_text(value: Any) -> str | None:
    text = _string(value)
    return text or None


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float_value(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe_strings(values: Any) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for value in _sequence(values):
        text = _clean_text(value)
        if not text:
            continue
        marker = text.lower()
        if marker in seen:
            continue
        seen.add(marker)
        items.append(text)
    return items


def _normalize_date_range(value: Any) -> dict[str, str]:
    row = _mapping(value)
    return {
        "start": _string(row.get("start")),
        "end": _string(row.get("end")),
    }


def _captured_date_range(date_range: Mapping[str, Any]) -> str:
    start = _string(date_range.get("start"))
    end = _string(date_range.get("end"))
    if start and end:
        return f"{start} to {end}"
    return start or end


def _normalize_page_metric(value: Any) -> dict[str, Any]:
    row = _mapping(value)
    grounding_queries = _dedupe_strings(row.get("grounding_queries"))
    return {
        "page_url": _string(row.get("page_url")),
        "page_title": _string(row.get("page_title")),
        "cited_count": _int_value(row.get("cited_count")),
        "grounding_queries": grounding_queries,
        "grounding_query_count": len(grounding_queries),
    }


def _normalize_referrals(value: Any) -> dict[str, Any]:
    row = _mapping(value)
    change_pct = _float_value(row.get("change_pct"))
    return {
        "visits": _int_value(row.get("visits")),
        "change_pct": change_pct,
        "utm_source": _string(row.get("utm_source")),
    }


def normalize_measurement_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    source = _mapping(payload)
    platforms: list[dict[str, Any]] = []
    for item in _sequence(source.get("platforms")):
        if not isinstance(item, Mapping):
            continue
        platform = _string(item.get("platform"))
        if not platform:
            continue
        date_range = _normalize_date_range(item.get("date_range"))
        page_metrics = [_normalize_page_metric(row) for row in _sequence(item.get("page_metrics")) if isinstance(row, Mapping)]
        platforms.append(
            {
                "platform": platform,
                "source": _string(item.get("source")),
                "date_range": date_range,
                "captured_date_range": _captured_date_range(date_range),
                "page_metrics": page_metrics,
                "referrals": _normalize_referrals(item.get("referrals")),
            }
        )
    return {"platforms": platforms}


def build_measurement_summary(normalized: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(normalized)
    platforms: list[dict[str, Any]] = []
    for item in _sequence(payload.get("platforms")):
        if not isinstance(item, Mapping):
            continue
        page_metrics = [row for row in _sequence(item.get("page_metrics")) if isinstance(row, Mapping)]
        referrals = _mapping(item.get("referrals"))
        platforms.append(
            {
                "platform": _string(item.get("platform")),
                "source": _string(item.get("source")),
                "captured_date_range": _string(item.get("captured_date_range")),
                "citation_count": sum(_int_value(row.get("cited_count")) for row in page_metrics),
                "grounding_query_count": sum(_int_value(row.get("grounding_query_count")) for row in page_metrics),
                "page_count": len(page_metrics),
                "referral_visits": _int_value(referrals.get("visits")),
                "referral_change_pct": _float_value(referrals.get("change_pct")),
                "utm_source": _string(referrals.get("utm_source")),
            }
        )
    return {"platforms": platforms}
