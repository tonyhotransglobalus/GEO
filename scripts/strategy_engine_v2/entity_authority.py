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


def normalize_entity_authority_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    source = _mapping(payload)
    mentions: list[dict[str, Any]] = []
    for item in _sequence(source.get("mentions")):
        if not isinstance(item, Mapping):
            continue
        platform = _string(item.get("platform"))
        mention_url = _string(item.get("mention_url"))
        if not platform or not mention_url:
            continue
        mentions.append(
            {
                "platform": platform,
                "mention_type": _string(item.get("mention_type")),
                "mention_url": mention_url,
                "entity_name": _string(item.get("entity_name")),
                "brand_match": _string(item.get("brand_match")) or "unknown",
                "source_quality_tier": _string(item.get("source_quality_tier")) or "unknown",
                "profile_status": _string(item.get("profile_status")) or "unknown",
            }
        )
    return {"mentions": mentions}


def build_entity_authority_summary(normalized: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(normalized)
    mentions = [row for row in _sequence(payload.get("mentions")) if isinstance(row, Mapping)]
    matched_mention_count = sum(1 for row in mentions if _string(row.get("brand_match")) == "exact")
    gap_count = sum(
        1
        for row in mentions
        if _string(row.get("brand_match")) != "exact" or _string(row.get("profile_status")) != "complete"
    )
    return {
        "mention_count": len(mentions),
        "matched_mention_count": matched_mention_count,
        "gap_count": gap_count,
    }
