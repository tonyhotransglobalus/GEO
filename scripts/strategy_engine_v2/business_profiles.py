from __future__ import annotations

from typing import Any, Mapping


BUSINESS_PROFILES: dict[str, dict[str, str]] = {
    "publisher": {
        "label": "Publisher",
        "primary_owner": "editorial",
        "content_surface": "editorial or explainer pages",
    },
    "local": {
        "label": "Local business",
        "primary_owner": "local_marketing",
        "content_surface": "location or service-area pages",
    },
    "ecommerce": {
        "label": "Ecommerce",
        "primary_owner": "merchandising",
        "content_surface": "product or category pages",
    },
    "b2b_services": {
        "label": "B2B services",
        "primary_owner": "marketing",
        "content_surface": "service or solution pages",
    },
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


def infer_business_profile(audit_data: Mapping[str, Any] | None) -> str:
    source = _mapping(audit_data)
    explicit = _string(source.get("business_profile")).lower()
    if explicit in BUSINESS_PROFILES:
        return explicit
    if _mapping(source.get("google_business_profile")).get("present") or _sequence(source.get("locations")):
        return "local"
    if source.get("product_count") or _sequence(source.get("products")):
        return "ecommerce"
    if _string(source.get("content_type")).lower() == "publisher" or source.get("article_count"):
        return "publisher"
    return "b2b_services"


def resolve_business_profile(
    explicit_profile: str | None,
    audit_data: Mapping[str, Any] | None,
) -> dict[str, str]:
    key = _string(explicit_profile).lower()
    if key not in BUSINESS_PROFILES:
        key = infer_business_profile(audit_data)
    profile = dict(BUSINESS_PROFILES.get(key, BUSINESS_PROFILES["b2b_services"]))
    profile["key"] = key
    return profile
