from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import urlparse

from .entity_authority import (
    build_entity_authority_summary,
    normalize_entity_authority_payload,
)
from .measurement import build_measurement_summary, normalize_measurement_payload


PLATFORM_CONTROL_PROFILES: list[dict[str, Any]] = [
    {
        "platform": "ChatGPT",
        "platform_key": "chatgpt",
        "bot_name": "OAI-SearchBot",
        "lookup_keys": ["oai-searchbot"],
        "surface": "search_bot",
        "surface_label": "Search bot",
        "control_mechanism": "robots.txt",
        "why_it_matters": "Controls whether OpenAI search can crawl and cite pages.",
        "fallback_recommendation": "Keep accessible if ChatGPT search visibility matters.",
        "not_observed_note": "No direct OAI-SearchBot observation was captured in this run.",
    },
    {
        "platform": "ChatGPT",
        "platform_key": "chatgpt",
        "bot_name": "GPTBot",
        "lookup_keys": ["gptbot"],
        "surface": "training_bot",
        "surface_label": "Training bot",
        "control_mechanism": "robots.txt",
        "why_it_matters": "Controls whether OpenAI may crawl pages for model training.",
        "fallback_recommendation": "Set an explicit GPTBot policy instead of assuming search access covers training access.",
        "not_observed_note": "No direct GPTBot observation was captured in this run.",
    },
    {
        "platform": "ChatGPT",
        "platform_key": "chatgpt",
        "bot_name": "ChatGPT user fetch",
        "lookup_keys": ["chatgpt-user", "chatgpt user", "chatgpt-agent", "chatgpt agent"],
        "surface": "user_fetch",
        "surface_label": "User fetch",
        "control_mechanism": "app fetch and accessibility",
        "why_it_matters": "User-directed fetch behavior still depends on accessible, machine-readable pages.",
        "fallback_recommendation": "Review app fetch behavior and page accessibility separately from crawler robots rules.",
        "not_observed_note": "No dedicated ChatGPT user-fetch observation was captured in this run.",
    },
    {
        "platform": "Claude",
        "platform_key": "claude",
        "bot_name": "Claude-SearchBot",
        "lookup_keys": ["claude-searchbot"],
        "surface": "search_bot",
        "surface_label": "Search bot",
        "control_mechanism": "robots.txt",
        "why_it_matters": "Controls whether Claude search can crawl and ground answers from the site.",
        "fallback_recommendation": "Keep accessible if Claude search visibility matters.",
        "not_observed_note": "No direct Claude-SearchBot observation was captured in this run.",
    },
    {
        "platform": "Claude",
        "platform_key": "claude",
        "bot_name": "ClaudeBot",
        "lookup_keys": ["claudebot"],
        "surface": "training_bot",
        "surface_label": "Training bot",
        "control_mechanism": "robots.txt",
        "why_it_matters": "Controls whether Anthropic may crawl pages for training and model improvement.",
        "fallback_recommendation": "Set an explicit ClaudeBot policy instead of assuming search access covers training access.",
        "not_observed_note": "No direct ClaudeBot observation was captured in this run.",
    },
    {
        "platform": "Claude",
        "platform_key": "claude",
        "bot_name": "Claude-User",
        "lookup_keys": ["claude-user"],
        "surface": "user_fetch",
        "surface_label": "User fetch",
        "control_mechanism": "app fetch and accessibility",
        "why_it_matters": "User-directed Claude fetches depend on pages being accessible and usable in app fetch flows.",
        "fallback_recommendation": "Review Claude app fetch behavior separately from crawler robots rules.",
        "not_observed_note": "No direct Claude-User observation was captured in this run.",
    },
    {
        "platform": "Perplexity",
        "platform_key": "perplexity",
        "bot_name": "PerplexityBot",
        "lookup_keys": ["perplexitybot"],
        "surface": "search_bot",
        "surface_label": "Search bot",
        "control_mechanism": "robots.txt and WAF allowlisting",
        "why_it_matters": "Controls whether Perplexity can crawl and cite site content.",
        "fallback_recommendation": "Keep accessible and confirm WAF settings if Perplexity visibility matters.",
        "not_observed_note": "No direct PerplexityBot observation was captured in this run.",
    },
    {
        "platform": "Perplexity",
        "platform_key": "perplexity",
        "bot_name": "Perplexity-User",
        "lookup_keys": ["perplexity-user"],
        "surface": "user_fetch",
        "surface_label": "User fetch",
        "control_mechanism": "WAF allowlisting and app fetch",
        "why_it_matters": "User-directed Perplexity fetches may fail even when crawler access looks open.",
        "fallback_recommendation": "Review WAF and app fetch behavior separately from crawler robots rules.",
        "not_observed_note": "No direct Perplexity-User observation was captured in this run.",
    },
    {
        "platform": "Google",
        "platform_key": "google",
        "bot_name": "Google-Extended",
        "lookup_keys": ["google-extended"],
        "surface": "ai_usage",
        "surface_label": "AI usage control",
        "control_mechanism": "robots.txt",
        "why_it_matters": "Controls AI usage permissions separately from standard Google Search crawling.",
        "fallback_recommendation": "Set an explicit Google-Extended policy instead of assuming Googlebot rules cover AI usage.",
        "not_observed_note": "No direct Google-Extended observation was captured in this run.",
    },
]


_PLATFORM_KEY_ALIASES = {
    "chatgpt": "chatgpt",
    "openai": "chatgpt",
    "claude": "claude",
    "anthropic": "claude",
    "perplexity": "perplexity",
    "google": "google",
    "gemini": "google",
}


_PLATFORM_CONTROL_SOURCES = {
    "chatgpt": {
        "title": "OpenAI bot and crawler controls",
        "url": "https://developers.openai.com/api/docs/bots",
    },
    "claude": {
        "title": "Anthropic crawler guidance",
        "url": "https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler",
    },
    "perplexity": {
        "title": "Perplexity crawler guidance",
        "url": "https://docs.perplexity.ai/docs/resources/perplexity-crawlers",
    },
    "google": {
        "title": "Google common crawlers and controls",
        "url": "https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers",
    },
}


def _clean_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _clean_list(values: list[Any] | None) -> list[str]:
    return [str(value).strip() for value in (values or []) if str(value).strip()]


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


def _normalized_platform_key(value: Any) -> str:
    normalized = _string(value).lower()
    return _PLATFORM_KEY_ALIASES.get(normalized, normalized)


def _lookup_key(value: Any) -> str:
    return _string(value).lower()


def _normalize_access_status(value: Any) -> str:
    text = _string(value).lower()
    if not text:
        return "Not observed"
    if any(token in text for token in ("disallow", "blocked", "deny", "denied", "not allowed")):
        return "Blocked"
    if "allow" in text or "accessible" in text:
        return "Allowed"
    if any(token in text for token in ("review", "unknown", "unclear", "manual", "waf")):
        return "Review"
    return "Review"


def _control_class(surface: str) -> str:
    mapping = {
        "search_bot": "search",
        "training_bot": "training",
        "user_fetch": "user_fetch",
        "ai_usage": "ai_usage",
    }
    return mapping.get(surface, surface)


def _impact_if_blocked(surface: str, platform: str) -> str:
    if surface == "search_bot":
        return f"{platform} may stop indexing or citing the site in search answers."
    if surface == "training_bot":
        return f"{platform} training access to future site content may be limited."
    if surface == "user_fetch":
        return f"User-requested {platform} fetches may fail or become less reliable."
    if surface == "ai_usage":
        return f"{platform} AI usage permissions may change without affecting standard Google Search crawling."
    return "Platform behavior may change if this control is blocked."


def _dedupe_text(values: Any) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for value in _sequence(values):
        text = _clean_text(value)
        if not text:
            continue
        normalized = text.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        items.append(text)
    return items


def _normalized_url(value: str | None) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.netloc or parsed.path).lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return f"{host}{path}"


def _first_visible_date(page_data: Mapping[str, Any]) -> tuple[str | None, str | None]:
    for row in _sequence(page_data.get("visible_dates")):
        if isinstance(row, Mapping):
            text = _clean_text(row.get("text"))
            if text:
                return text, _clean_text(row.get("source"))
        else:
            text = _clean_text(row)
            if text:
                return text, None
    return None, None


def _parse_date_token(value: Any) -> datetime | None:
    text = _clean_text(value)
    if not text:
        return None
    cleaned = (
        text.replace("Updated", "")
        .replace("Published", "")
        .replace("Modified", "")
        .replace("Last updated", "")
        .replace("Last Updated", "")
        .strip(" :")
    )
    iso_candidate = cleaned[:10]
    for candidate, fmt in (
        (iso_candidate, "%Y-%m-%d"),
        (cleaned, "%B %d, %Y"),
        (cleaned, "%b %d, %Y"),
        (cleaned, "%m/%d/%Y"),
    ):
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def _schema_date_source(schema_row: Mapping[str, Any]) -> str | None:
    has_published = bool(_clean_text(schema_row.get("datePublished")))
    has_modified = bool(_clean_text(schema_row.get("dateModified")))
    schema_type = _schema_types(schema_row)[0] if _schema_types(schema_row) else "schema"
    if has_published and has_modified:
        return f"{schema_type}.datePublished/dateModified"
    if has_modified:
        return f"{schema_type}.dateModified"
    if has_published:
        return f"{schema_type}.datePublished"
    return None


def _date_alignment_status(
    visible_date_text: str | None,
    date_published: str | None,
    date_modified: str | None,
) -> str:
    if not visible_date_text and not date_published and not date_modified:
        return "missing"
    if not visible_date_text:
        return "schema_only"
    if not date_published and not date_modified:
        return "visible_only"
    visible_date = _parse_date_token(visible_date_text)
    published_date = _parse_date_token(date_published)
    modified_date = _parse_date_token(date_modified)
    if visible_date and any(
        candidate and candidate.date() == visible_date.date()
        for candidate in (modified_date, published_date)
    ):
        return "aligned"
    if visible_date and (published_date or modified_date):
        return "conflict"
    return "unverified"


def _staleness_bucket(date_text: str | None, *, reference_date: str | None) -> str:
    candidate = _parse_date_token(date_text)
    reference = _parse_date_token(reference_date) or datetime.now(timezone.utc).replace(tzinfo=None)
    if not candidate:
        return "unknown"
    age_days = (reference.date() - candidate.date()).days
    if age_days <= 90:
        return "recent_90d"
    if age_days <= 365:
        return "last_year"
    return "stale_gt_year"


def _normalized_name(value: str | None) -> str:
    text = _clean_text(value) or ""
    return "".join(char for char in text.lower() if char.isalnum())


def _author_alignment_status(byline: str | None, author_name: str | None) -> str:
    normalized_byline = _normalized_name(byline)
    normalized_author = _normalized_name(author_name)
    if normalized_byline and normalized_author:
        return "aligned" if normalized_byline == normalized_author else "conflict"
    if normalized_byline:
        return "visible_only"
    if normalized_author:
        return "schema_only"
    return "missing"


def _credentials_visible(byline: str | None) -> bool:
    text = _clean_text(byline) or ""
    if "," in text:
        return True
    tokens = [token.strip(",.") for token in text.split()]
    return any(token.isupper() and 2 <= len(token) <= 6 for token in tokens)


def _author_page_status(author_pages: list[str]) -> str:
    if not author_pages:
        return "missing"
    return "present"


def _single_main_status(page_data: Mapping[str, Any], aria_landmarks: list[str]) -> str:
    explicit_count = page_data.get("main_landmark_count")
    if isinstance(explicit_count, int):
        if explicit_count == 1:
            return "pass"
        if explicit_count <= 0:
            return "missing"
        return "multiple"
    main_count = sum(1 for item in aria_landmarks if item.lower() == "main")
    if main_count == 1:
        return "pass"
    if main_count == 0:
        return "missing"
    return "multiple"


def _same_page(left: str | None, right: str | None) -> bool:
    return bool(_normalized_url(left)) and _normalized_url(left) == _normalized_url(right)


def _path_from_url(value: str | None) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return path


def _is_high_signal_link(url: str | None, label: str | None = None) -> bool:
    path = _path_from_url(url).lower()
    clean_label = (_clean_text(label) or "").strip()
    normalized_label = clean_label.lower()
    if not path or path == "/":
        return False
    if path.startswith(("/author/", "/category/", "/tag/", "/wp-", "/zh/")):
        return False
    if not clean_label:
        return False
    if normalized_label in {
        "admin",
        "evelle dai",
        "financial news",
        "real estate + lending",
        "latest news",
        "more videos",
        "skip to content",
    }:
        return False
    return True


def build_evidence_item(
    *,
    evidence_type: str,
    source_class: str,
    observed_vs_inferred: str,
    platform: str | None,
    query_theme: str | None,
    url_or_domain: str | None,
    raw_observation: Any,
    normalized_summary: str,
    confidence: str,
) -> dict:
    return {
        "evidence_type": evidence_type,
        "source_class": source_class,
        "observed_vs_inferred": observed_vs_inferred,
        "platform": _clean_text(platform),
        "query_theme": _clean_text(query_theme),
        "url_or_domain": _clean_text(url_or_domain),
        "raw_observation": raw_observation,
        "normalized_summary": normalized_summary,
        "confidence": confidence,
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def build_page_fetch_evidence(page_data: dict[str, Any], *, url: str, query_theme: str | None = None) -> dict:
    return build_evidence_item(
        evidence_type="page_fetch",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=query_theme,
        url_or_domain=url,
        raw_observation=page_data,
        normalized_summary=_clean_text(page_data.get("title")) or "Page fetch observation captured.",
        confidence="high",
    )


def _structured_data_rows(page_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _sequence(page_data.get("structured_data")):
        if isinstance(row, Mapping):
            rows.append(dict(row))
    return rows


def _schema_types(schema_row: Mapping[str, Any]) -> list[str]:
    raw_types = schema_row.get("@type")
    if raw_types is None:
        raw_types = schema_row.get("type")
    if isinstance(raw_types, list):
        return _clean_list(raw_types)
    text = _clean_text(raw_types)
    return [text] if text else []


def _schema_author_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _clean_text(value.get("name")) or _clean_text(value.get("@id"))
    if isinstance(value, list):
        for item in value:
            name = _schema_author_name(item)
            if name:
                return name
        return None
    return _clean_text(value)


def _article_schema_row(page_data: Mapping[str, Any]) -> dict[str, Any]:
    rows = _structured_data_rows(page_data)
    for row in rows:
        schema_types = {_string(item).lower() for item in _schema_types(row)}
        if schema_types.intersection({"article", "newsarticle", "blogposting", "webpage"}):
            return row
        if any(_clean_text(row.get(key)) for key in ("datePublished", "dateModified", "author")):
            return row
    return rows[0] if rows else {}


def build_freshness_evidence(page_data: dict[str, Any], *, url: str, reference_date: str | None = None) -> dict | None:
    schema_row = _article_schema_row(page_data)
    visible_date_text, visible_date_source = _first_visible_date(page_data)
    date_published = (
        _clean_text(page_data.get("date_published"))
        or _clean_text(page_data.get("published_date"))
        or _clean_text(schema_row.get("datePublished"))
    )
    date_modified = (
        _clean_text(page_data.get("date_modified"))
        or _clean_text(page_data.get("modified_date"))
        or _clean_text(schema_row.get("dateModified"))
    )
    if not date_published and not date_modified:
        return None

    parts: list[str] = []
    if visible_date_text:
        parts.append(f"visible date text '{visible_date_text}'")
    if date_published:
        parts.append(f"published {date_published}")
    if date_modified:
        parts.append(f"updated {date_modified}")
    alignment_status = _date_alignment_status(visible_date_text, date_published, date_modified)
    summary = "Freshness signals captured"
    if parts:
        summary = f"{summary}: {' and '.join(parts)}."
    else:
        summary = f"{summary}."
    if _schema_types(schema_row):
        summary = f"{summary[:-1]} in {', '.join(_schema_types(schema_row))} schema."
    if alignment_status == "aligned":
        summary = f"{summary[:-1]}; visible and schema dates are aligned."
    elif alignment_status == "conflict":
        summary = f"{summary[:-1]}; visible and schema dates do not align."
    staleness_bucket = _staleness_bucket(date_modified or date_published, reference_date=reference_date)
    confidence = "medium" if date_published and date_modified else "low"
    if alignment_status == "conflict" or staleness_bucket == "stale_gt_year":
        confidence = "low"

    return build_evidence_item(
        evidence_type="freshness_signal",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=None,
        url_or_domain=url,
        raw_observation={
            "page_url": url,
            "visible_date_text": visible_date_text,
            "visible_date_source": visible_date_source,
            "date_published": date_published,
            "date_modified": date_modified,
            "schema_date_source": _schema_date_source(schema_row),
            "date_alignment_status": alignment_status,
            "staleness_bucket": staleness_bucket,
            "schema_types": _schema_types(schema_row),
            "comparability_key": "freshness_signal:v2",
        },
        normalized_summary=summary,
        confidence=confidence,
    )


def build_authorship_evidence(page_data: dict[str, Any], *, url: str) -> dict | None:
    schema_row = _article_schema_row(page_data)
    byline = _clean_text(page_data.get("byline"))
    author_name = _schema_author_name(schema_row.get("author")) or byline
    author_pages = _dedupe_text(page_data.get("author_pages"))
    if not byline and not author_name and not author_pages:
        return None

    summary_parts: list[str] = []
    if byline:
        summary_parts.append(f"visible byline '{byline}'")
    elif author_name:
        summary_parts.append(f"schema author '{author_name}'")
    if author_pages:
        count = len(author_pages)
        summary_parts.append(f"{count} linked author page{'s' if count != 1 else ''}")
    else:
        summary_parts.append("author page is missing")
    alignment_status = _author_alignment_status(byline, author_name)
    summary = "Authorship signals captured"
    if summary_parts:
        summary = f"{summary}: {', '.join(summary_parts)}."
    else:
        summary = f"{summary}."
    if alignment_status == "aligned":
        summary = f"{summary[:-1]}; visible and schema author are aligned."
    elif alignment_status == "conflict":
        summary = f"{summary[:-1]}; visible and schema author do not align."

    return build_evidence_item(
        evidence_type="authorship_signal",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=None,
        url_or_domain=url,
        raw_observation={
            "page_url": url,
            "byline": byline,
            "author_name": author_name,
            "author_pages": author_pages,
            "visible_byline_present": bool(byline),
            "schema_author_present": bool(_schema_author_name(schema_row.get("author"))),
            "author_alignment_status": alignment_status,
            "credentials_visible": _credentials_visible(byline),
            "author_page_status": _author_page_status(author_pages),
            "schema_types": _schema_types(schema_row),
            "comparability_key": "authorship_signal:v2",
        },
        normalized_summary=summary,
        confidence="medium" if byline and author_pages else "low",
    )


def build_accessibility_evidence(page_data: dict[str, Any], *, url: str) -> dict | None:
    aria_landmarks = _clean_list(page_data.get("aria_landmarks"))
    rendered_state_parity = _mapping(page_data.get("rendered_state_parity"))
    parity_status = _clean_text(rendered_state_parity.get("status"))
    parity_summary = _clean_text(rendered_state_parity.get("summary"))
    parity_failure_elements = _dedupe_text(rendered_state_parity.get("missing_elements"))
    rendered_only_content_detected = bool(rendered_state_parity.get("rendered_only_content_detected"))
    if not aria_landmarks and not parity_status and not parity_summary:
        return None

    summary_parts: list[str] = []
    if aria_landmarks:
        summary_parts.append(f"landmarks {', '.join(aria_landmarks)}")
    single_main_status = _single_main_status(page_data, aria_landmarks)
    if single_main_status == "pass":
        summary_parts.append("single main landmark is present")
    if parity_status:
        parity_text = f"rendered-state parity is {parity_status}"
        if parity_summary:
            parity_text = f"{parity_text} because {parity_summary.rstrip('.')}"
        summary_parts.append(parity_text)
    if parity_failure_elements:
        summary_parts.append(f"parity failures include {', '.join(parity_failure_elements)}")
    elif parity_summary:
        summary_parts.append(parity_summary)
    summary = "Accessibility signals captured"
    if summary_parts:
        summary = f"{summary}: {'; '.join(summary_parts)}."
    else:
        summary = f"{summary}."

    normalized_parity = _string(parity_status).lower()
    if aria_landmarks and normalized_parity in {"full", "aligned", "consistent", "pass"}:
        confidence = "high"
    elif aria_landmarks and normalized_parity:
        confidence = "medium"
    else:
        confidence = "low"

    return build_evidence_item(
        evidence_type="accessibility_signal",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=None,
        url_or_domain=url,
        raw_observation={
            "page_url": url,
            "aria_landmarks": aria_landmarks,
            "single_main_status": single_main_status,
            "landmark_count": len(aria_landmarks),
            "rendered_state_parity_status": parity_status,
            "rendered_state_parity_summary": parity_summary,
            "parity_failure_elements": parity_failure_elements,
            "rendered_only_content_detected": rendered_only_content_detected,
            "comparability_key": "accessibility_signal:v2",
        },
        normalized_summary=summary,
        confidence=confidence,
    )


def build_robots_evidence(robots_data: dict[str, Any], *, url: str) -> dict:
    return build_evidence_item(
        evidence_type="robots",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=None,
        url_or_domain=url,
        raw_observation=robots_data,
        normalized_summary="Robots access rules captured.",
        confidence="high",
    )


def build_llms_evidence(llms_data: dict[str, Any], *, url: str, observed_vs_inferred: str) -> dict:
    summary = "llms.txt guidance captured." if llms_data.get("found") else "llms.txt guidance not found."
    return build_evidence_item(
        evidence_type="llms",
        source_class="live_site",
        observed_vs_inferred=observed_vs_inferred,
        platform=None,
        query_theme=None,
        url_or_domain=url,
        raw_observation=llms_data,
        normalized_summary=summary,
        confidence="medium",
    )


def build_citability_evidence(citability_data: dict[str, Any], *, url: str, query_theme: str | None = None) -> dict:
    return build_evidence_item(
        evidence_type="page_citability",
        source_class="internal_score",
        observed_vs_inferred="inferred",
        platform=None,
        query_theme=query_theme,
        url_or_domain=url,
        raw_observation=citability_data,
        normalized_summary="Citability score calculated for the current page sample.",
        confidence="high",
    )


def build_brand_evidence(brand_data: dict[str, Any], *, url: str) -> dict:
    return build_evidence_item(
        evidence_type="brand_entity",
        source_class="third_party_reference",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=None,
        url_or_domain=url,
        raw_observation=brand_data,
        normalized_summary="Brand and entity signals captured.",
        confidence="medium",
    )


def _build_finding_evidence(finding: Mapping[str, Any], *, url: str) -> dict:
    title = _clean_text(finding.get("title")) or "Audit finding"
    return build_evidence_item(
        evidence_type="finding",
        source_class="internal_score",
        observed_vs_inferred="inferred",
        platform=None,
        query_theme=None,
        url_or_domain=url,
        raw_observation=dict(finding),
        normalized_summary=title,
        confidence=_clean_text(finding.get("confidence")) or "medium",
    )


def _build_query_cluster_evidence(cluster: Mapping[str, Any], *, url: str) -> dict:
    label = _clean_text(cluster.get("label")) or "query-cluster"
    return build_evidence_item(
        evidence_type="query_cluster",
        source_class="live_serp_or_platform",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=label,
        url_or_domain=url,
        raw_observation=dict(cluster),
        normalized_summary=f"Query cluster captured: {label}.",
        confidence=_clean_text(cluster.get("priority")) or "medium",
    )


def _build_citation_failure_evidence(failure: Mapping[str, Any]) -> dict:
    query = _clean_text(failure.get("query")) or "query"
    return build_evidence_item(
        evidence_type="citation_failure",
        source_class="live_serp_or_platform",
        observed_vs_inferred="inferred",
        platform=None,
        query_theme=query,
        url_or_domain=_clean_text(failure.get("target_url")),
        raw_observation=dict(failure),
        normalized_summary=f"Citation failure recorded for '{query}'.",
        confidence=_clean_text(_mapping(failure.get("metadata")).get("label")) or "medium",
    )


def _build_benchmark_row_evidence(row: Mapping[str, Any], *, url: str) -> dict:
    competitor = _clean_text(row.get("competitor_name")) or "competitor"
    return build_evidence_item(
        evidence_type="benchmark_row",
        source_class="live_serp_or_platform",
        observed_vs_inferred="observed",
        platform=_clean_text(row.get("platform")),
        query_theme=", ".join(_dedupe_text(row.get("top_winning_queries"))) or None,
        url_or_domain=url,
        raw_observation=dict(row),
        normalized_summary=f"Benchmark row captured for {competitor}.",
        confidence=_clean_text(row.get("confidence")) or "medium",
    )


def _build_platform_observation_evidence(row: Mapping[str, Any], *, url: str) -> dict:
    platform = _clean_text(row.get("platform")) or "platform"
    return build_evidence_item(
        evidence_type="platform_observation",
        source_class="live_serp_or_platform",
        observed_vs_inferred="inferred",
        platform=platform,
        query_theme=None,
        url_or_domain=url,
        raw_observation=dict(row),
        normalized_summary=f"{platform} platform note reused from the bridged audit.",
        confidence=_clean_text(row.get("confidence")) or "medium",
    )


def _crawler_access_lookup(audit_data: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    root_access = _mapping(audit_data.get("crawler_access"))
    legacy_access = _mapping(
        _mapping(_mapping(audit_data.get("report_sections")).get("technical_geo_gates")).get("crawler_access")
    )
    for source in (root_access, legacy_access):
        for name, details in source.items():
            normalized_name = _lookup_key(name)
            if not normalized_name:
                continue
            if isinstance(details, Mapping):
                lookup[normalized_name] = {"name": _string(name), "details": dict(details)}
            else:
                lookup[normalized_name] = {"name": _string(name), "details": {"status": details}}
    return lookup


def _build_platform_control_rows(
    manifest: Mapping[str, Any],
    audit_data: Mapping[str, Any],
) -> list[dict[str, Any]]:
    access_lookup = _crawler_access_lookup(audit_data)
    if not access_lookup:
        return []
    manifest_platforms = {
        _normalized_platform_key(platform)
        for platform in _sequence(manifest.get("platforms"))
        if _string(platform)
    }
    rows: list[dict[str, Any]] = []
    for profile in PLATFORM_CONTROL_PROFILES:
        profile_platform = _string(profile.get("platform_key"))
        has_observation = any(key in access_lookup for key in profile.get("lookup_keys", []))
        if profile_platform not in manifest_platforms and not has_observation:
            continue

        observed = None
        for key in profile.get("lookup_keys", []):
            observed = access_lookup.get(key)
            if observed:
                break
        observed_details = _mapping((observed or {}).get("details"))
        raw_status = _string(observed_details.get("status"))
        rows.append(
            {
                "platform": _string(profile.get("platform")),
                "platform_key": profile_platform,
                "bot_name": _string(profile.get("bot_name")),
                "surface": _string(profile.get("surface")),
                "surface_label": _string(profile.get("surface_label")),
                "control_class": _control_class(_string(profile.get("surface"))),
                "control_mechanism": _string(profile.get("control_mechanism")),
                "why_it_matters": _string(profile.get("why_it_matters")),
                "impact_if_blocked": _impact_if_blocked(
                    _string(profile.get("surface")),
                    _string(profile.get("platform")),
                ),
                "status": _normalize_access_status(raw_status) if observed else "Not observed",
                "status_detail": raw_status or _string(profile.get("not_observed_note")),
                "recommendation": _string(observed_details.get("recommendation"))
                or _string(profile.get("fallback_recommendation")),
                "observed": bool(observed),
                "observed_from": _string((observed or {}).get("name")),
                "last_verified_at": _clean_text(audit_data.get("date")),
                "source_title": _PLATFORM_CONTROL_SOURCES.get(profile_platform, {}).get("title"),
                "source_url": _PLATFORM_CONTROL_SOURCES.get(profile_platform, {}).get("url"),
            }
        )
    return rows


def _build_platform_control_evidence(row: Mapping[str, Any], *, url: str) -> dict:
    status = _clean_text(row.get("status")) or "Not observed"
    return build_evidence_item(
        evidence_type="platform_control",
        source_class="live_site",
        observed_vs_inferred="observed" if row.get("observed") else "inferred",
        platform=_clean_text(row.get("platform")),
        query_theme=_clean_text(row.get("surface_label")),
        url_or_domain=url,
        raw_observation=dict(row),
        normalized_summary=(
            f"{_clean_text(row.get('platform')) or 'Platform'} "
            f"{_clean_text(row.get('surface_label')) or 'control'} for "
            f"{_clean_text(row.get('bot_name')) or 'bot'} is {status}."
        ),
        confidence="medium" if row.get("observed") else "low",
    )


def _build_platform_measurement_evidence(
    row: Mapping[str, Any],
    *,
    summary: Mapping[str, Any],
    url: str,
) -> dict:
    platform = _clean_text(row.get("platform"))
    citation_count = summary.get("citation_count")
    grounding_query_count = summary.get("grounding_query_count")
    referral_visits = summary.get("referral_visits")
    captured_date_range = _clean_text(summary.get("captured_date_range"))
    parts = [f"{platform or 'Platform'} measurement"]
    if citation_count:
        parts.append(f"{citation_count} citations")
    if grounding_query_count:
        parts.append(f"{grounding_query_count} grounding queries")
    if referral_visits:
        parts.append(f"{referral_visits} referral visits")
    if captured_date_range:
        parts.append(f"captured {captured_date_range}")
    return build_evidence_item(
        evidence_type="platform_measurement",
        source_class="live_platform_measurement",
        observed_vs_inferred="observed",
        platform=platform,
        query_theme=None,
        url_or_domain=url,
        raw_observation={
            **dict(summary),
            "page_metrics": _sequence(row.get("page_metrics")),
            "referrals": _mapping(row.get("referrals")),
        },
        normalized_summary=", ".join(part for part in parts if part) + ".",
        confidence="high",
    )


def _build_citation_share_evidence(
    platform: str | None,
    row: Mapping[str, Any],
    *,
    captured_date_range: str | None,
) -> dict:
    page_url = _clean_text(row.get("page_url"))
    cited_count = row.get("cited_count")
    grounding_query_count = row.get("grounding_query_count")
    captured_suffix = f" during {captured_date_range}" if captured_date_range else ""
    return build_evidence_item(
        evidence_type="citation_share_signal",
        source_class="live_platform_measurement",
        observed_vs_inferred="observed",
        platform=platform,
        query_theme=None,
        url_or_domain=page_url,
        raw_observation=dict(row),
        normalized_summary=(
            f"Measured {cited_count} citations and {grounding_query_count} grounding queries"
            f" for {page_url or 'page'} on {platform or 'platform'}{captured_suffix}."
        ),
        confidence="high",
    )


def _build_referral_signal_evidence(
    platform: str | None,
    referrals: Mapping[str, Any],
    *,
    url: str,
    captured_date_range: str | None,
) -> dict:
    visits = referrals.get("visits")
    change_pct = referrals.get("change_pct")
    trend = ""
    if isinstance(change_pct, (int, float)):
        trend = f", {change_pct:+g}% vs prior period"
    captured_suffix = f" during {captured_date_range}" if captured_date_range else ""
    return build_evidence_item(
        evidence_type="referral_signal",
        source_class="live_platform_measurement",
        observed_vs_inferred="observed",
        platform=platform,
        query_theme=None,
        url_or_domain=url,
        raw_observation=dict(referrals),
        normalized_summary=(
            f"Measured {visits} {platform or 'platform'} referral visits{trend}{captured_suffix}."
        ),
        confidence="high",
    )


def _build_offsite_entity_signal(row: Mapping[str, Any]) -> dict:
    platform = _clean_text(row.get("platform"))
    mention_type = _clean_text(row.get("mention_type")) or "mention"
    entity_name = _clean_text(row.get("entity_name")) or "brand"
    source_quality = _clean_text(row.get("source_quality_tier"))
    summary = f"{platform or 'Offsite'} {mention_type} captured for {entity_name}."
    if source_quality:
        summary = f"{summary[:-1]} Source tier: {source_quality}."
    return build_evidence_item(
        evidence_type="offsite_entity_signal",
        source_class="third_party_reference",
        observed_vs_inferred="observed",
        platform=platform,
        query_theme=mention_type,
        url_or_domain=_clean_text(row.get("mention_url")),
        raw_observation=dict(row),
        normalized_summary=summary,
        confidence="medium",
    )


def _build_offsite_authority_gap(row: Mapping[str, Any]) -> dict:
    platform = _clean_text(row.get("platform"))
    summary = (
        f"{platform or 'Offsite'} authority gap: brand match is {_clean_text(row.get('brand_match')) or 'unknown'} "
        f"and profile status is {_clean_text(row.get('profile_status')) or 'unknown'}."
    )
    return build_evidence_item(
        evidence_type="offsite_authority_gap",
        source_class="third_party_reference",
        observed_vs_inferred="observed",
        platform=platform,
        query_theme=_clean_text(row.get("mention_type")),
        url_or_domain=_clean_text(row.get("mention_url")),
        raw_observation=dict(row),
        normalized_summary=summary,
        confidence="medium",
    )


def _first_query(cluster: Mapping[str, Any]) -> str | None:
    queries = _dedupe_text(cluster.get("queries"))
    if queries:
        return queries[0]
    label = _clean_text(cluster.get("label"))
    return label or None


def build_sampled_query_prompt_rows(audit_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    query_clusters = [
        _mapping(cluster)
        for cluster in _sequence(audit_data.get("query_clusters"))
        if isinstance(cluster, Mapping)
    ]
    citation_failures = [
        _mapping(failure)
        for failure in _sequence(audit_data.get("citation_failures"))
        if isinstance(failure, Mapping)
    ]
    locale = _clean_text(
        _mapping(
            _mapping(
                _mapping(audit_data.get("client_report_sections")).get("competitive_benchmark")
            ).get("sample_scope")
        ).get("locale")
    )
    capture_timestamp = _clean_text(audit_data.get("date"))
    failures_by_query = {
        _string(failure.get("query")).lower(): failure
        for failure in citation_failures
        if _string(failure.get("query"))
    }
    rows: list[dict[str, Any]] = []
    seen_queries: set[str] = set()

    for cluster in query_clusters:
        primary_query = _first_query(cluster)
        if not primary_query:
            continue
        normalized_query = primary_query.lower()
        if normalized_query in seen_queries:
            continue
        seen_queries.add(normalized_query)
        metadata = _mapping(cluster.get("metadata"))
        failure = failures_by_query.get(normalized_query, {})
        rows.append(
            {
                "capture_mode": "sampled_query_bridge",
                "query_or_prompt": primary_query,
                "query_theme": _clean_text(cluster.get("label")) or primary_query,
                "platform": None,
                "model_surface": "bridge-sampled-query",
                "locale": locale,
                "capture_timestamp": capture_timestamp,
                "brand_mentioned": bool(metadata.get("site_visible")),
                "brand_cited": bool(metadata.get("site_visible")),
                "winning_domains": _dedupe_text(metadata.get("top_domains")),
                "winning_urls": [],
                "response_summary": (
                    "Sampled search visibility did not retain the brand in the observed result set."
                    if failure
                    else "Sampled query evidence was retained from the bridged audit."
                ),
                "why_we_lost_or_won": _clean_text(failure.get("recommended_fix"))
                or "Use sampled query evidence as a directional signal until exact prompt captures are available.",
                "confidence": _clean_text(cluster.get("priority"))
                or _clean_text(metadata.get("label"))
                or _clean_text(_mapping(failure.get("metadata")).get("label"))
                or "medium",
            }
        )

    for failure in citation_failures:
        query = _clean_text(failure.get("query"))
        if not query:
            continue
        normalized_query = query.lower()
        if normalized_query in seen_queries:
            continue
        seen_queries.add(normalized_query)
        rows.append(
            {
                "capture_mode": "sampled_query_bridge",
                "query_or_prompt": query,
                "query_theme": query,
                "platform": None,
                "model_surface": "bridge-sampled-query",
                "locale": locale,
                "capture_timestamp": capture_timestamp,
                "brand_mentioned": bool(_mapping(failure.get("metadata")).get("site_visible")),
                "brand_cited": bool(_mapping(failure.get("metadata")).get("site_visible")),
                "winning_domains": [],
                "winning_urls": [],
                "response_summary": "Sampled search visibility did not retain the brand for this query.",
                "why_we_lost_or_won": _clean_text(failure.get("recommended_fix"))
                or "Use sampled query evidence as a directional signal until exact prompt captures are available.",
                "confidence": _clean_text(_mapping(failure.get("metadata")).get("label")) or "medium",
            }
        )

    return rows


def _build_prompt_proof_evidence(row: Mapping[str, Any], *, url: str) -> dict:
    query = _clean_text(row.get("query_or_prompt")) or "prompt"
    capture_mode = _clean_text(row.get("capture_mode"))
    is_sampled_query_bridge = capture_mode == "sampled_query_bridge"
    return build_evidence_item(
        evidence_type="prompt_proof",
        source_class="live_serp_or_platform",
        observed_vs_inferred="inferred" if is_sampled_query_bridge else "observed",
        platform=_clean_text(row.get("platform")),
        query_theme=_clean_text(row.get("query_theme")) or query,
        url_or_domain=url,
        raw_observation=dict(row),
        normalized_summary=(
            f"Sampled query proof bridged for {query}."
            if is_sampled_query_bridge
            else f"Prompt proof captured for {query}."
        ),
        confidence=_clean_text(row.get("confidence")) or "medium",
    )


def _build_priority_page_evidence(row: Mapping[str, Any]) -> dict:
    page_url = _clean_text(row.get("page_url"))
    return build_evidence_item(
        evidence_type="priority_page",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=_clean_text(row.get("page_type")),
        url_or_domain=page_url,
        raw_observation=dict(row),
        normalized_summary=f"Priority page evidence captured for {page_url or 'page sample'}.",
        confidence=_clean_text(row.get("confidence")) or "medium",
    )


def _build_source_domain_evidence(row: Mapping[str, Any]) -> dict:
    domain = _clean_text(row.get("domain"))
    return build_evidence_item(
        evidence_type="source_domain",
        source_class="third_party_reference",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=_clean_text(row.get("source_type")),
        url_or_domain=domain,
        raw_observation=dict(row),
        normalized_summary=f"Source domain evidence captured for {domain or 'domain'}.",
        confidence="medium",
    )


def _build_linked_page_evidence(url: str, *, source: str, label: str | None = None) -> dict:
    summary_label = _clean_text(label) or url
    return build_evidence_item(
        evidence_type="linked_page",
        source_class="live_site",
        observed_vs_inferred="observed",
        platform=None,
        query_theme=source,
        url_or_domain=url,
        raw_observation={"url": url, "source": source, "label": summary_label},
        normalized_summary=f"Observed linked page candidate: {summary_label}.",
        confidence="medium",
    )


def build_v2_evidence_ledger(
    *,
    manifest: dict[str, Any],
    audit_data: dict[str, Any] | None = None,
    page_data: dict[str, Any] | None = None,
    robots_data: dict[str, Any] | None = None,
    llms_data: dict[str, Any] | None = None,
    llms_observed_vs_inferred: str = "observed",
    citability_data: dict[str, Any] | None = None,
    brand_data: dict[str, Any] | None = None,
    plugin_results: dict[str, Any] | None = None,
) -> dict:
    items: list[dict] = []
    target_url = manifest.get("target_url")
    bridged_audit = _mapping(audit_data)
    bridged_plugin_results = _mapping(bridged_audit.get("plugin_results"))
    readiness = _mapping(bridged_plugin_results.get("readiness"))
    readiness_inputs = _mapping(readiness.get("inputs"))
    client_sections = _mapping(bridged_audit.get("client_report_sections"))
    measurement_data = normalize_measurement_payload(
        bridged_audit.get("measurement_data") or readiness_inputs.get("measurement_data")
    )
    entity_authority_data = normalize_entity_authority_payload(bridged_audit.get("entity_authority_data"))

    if page_data is None and readiness_inputs.get("page_data") is not None:
        page_data = _mapping(readiness_inputs.get("page_data"))
    if robots_data is None and readiness_inputs.get("robots_data") is not None:
        robots_data = _mapping(readiness_inputs.get("robots_data"))
    if llms_data is None and readiness_inputs.get("llms_validation") is not None:
        llms_data = _mapping(readiness_inputs.get("llms_validation"))
        llms_observed_vs_inferred = "inferred"
    if citability_data is None and readiness_inputs.get("citability_data") is not None:
        citability_data = _mapping(readiness_inputs.get("citability_data"))
    if brand_data is None:
        if readiness_inputs.get("brand_data") is not None:
            brand_data = _mapping(readiness_inputs.get("brand_data"))
        elif bridged_audit.get("entity_graph") is not None:
            brand_data = _mapping(bridged_audit.get("entity_graph"))
    if plugin_results is None and bridged_plugin_results:
        plugin_results = bridged_plugin_results

    items.append(
        build_evidence_item(
            evidence_type="run_manifest",
            source_class="internal_metadata",
            observed_vs_inferred="observed",
            platform=None,
            query_theme=None,
            url_or_domain=target_url,
            raw_observation={
                "mode": manifest.get("mode"),
                "driver": manifest.get("driver"),
                "shadow_run": manifest.get("shadow_run"),
                "comparison_eligibility": manifest.get("comparison_eligibility"),
                "platforms": _clean_list(manifest.get("platforms")),
                "competitors": _clean_list(manifest.get("competitors")),
            },
            normalized_summary="Run scope captured in the V2 manifest.",
            confidence="high",
        )
    )

    if page_data is not None:
        items.append(build_page_fetch_evidence(page_data, url=target_url))
        freshness_evidence = build_freshness_evidence(
            page_data,
            url=target_url,
            reference_date=_clean_text(bridged_audit.get("date")),
        )
        if freshness_evidence is not None:
            items.append(freshness_evidence)
        authorship_evidence = build_authorship_evidence(page_data, url=target_url)
        if authorship_evidence is not None:
            items.append(authorship_evidence)
        accessibility_evidence = build_accessibility_evidence(page_data, url=target_url)
        if accessibility_evidence is not None:
            items.append(accessibility_evidence)
        seen_page_urls: set[str] = set()
        accepted_internal_links = 0
        for row in _sequence(_mapping(page_data).get("internal_links")):
            if isinstance(row, Mapping):
                linked_url = _clean_text(row.get("url"))
                label = _clean_text(row.get("text"))
            else:
                linked_url = _clean_text(row)
                label = None
            normalized = _normalized_url(linked_url)
            if (
                not normalized
                or normalized in seen_page_urls
                or _same_page(linked_url, target_url)
                or not _is_high_signal_link(linked_url, label)
            ):
                continue
            seen_page_urls.add(normalized)
            items.append(
                _build_linked_page_evidence(
                    linked_url,
                    source="internal_link",
                    label=label,
                )
            )
            accepted_internal_links += 1
            if accepted_internal_links >= 12:
                break
    if robots_data is not None:
        items.append(build_robots_evidence(robots_data, url=target_url))
    if llms_data is not None:
        items.append(build_llms_evidence(llms_data, url=target_url, observed_vs_inferred=llms_observed_vs_inferred))
    if citability_data is not None:
        items.append(build_citability_evidence(citability_data, url=target_url))
    if brand_data is not None:
        items.append(build_brand_evidence(brand_data, url=target_url))
    if plugin_results is not None:
        items.append(
            build_evidence_item(
                evidence_type="plugin_results",
                source_class="internal_score",
                observed_vs_inferred="inferred",
                platform=None,
                query_theme=None,
                url_or_domain=target_url,
                raw_observation=plugin_results,
                normalized_summary="V1 plugin outputs reused where safe.",
                confidence="medium",
            )
        )

    for finding in _sequence(bridged_audit.get("findings")):
        if isinstance(finding, Mapping):
            items.append(_build_finding_evidence(finding, url=target_url))

    for cluster in _sequence(bridged_audit.get("query_clusters")):
        if isinstance(cluster, Mapping):
            items.append(_build_query_cluster_evidence(cluster, url=target_url))

    for failure in _sequence(bridged_audit.get("citation_failures")):
        if isinstance(failure, Mapping):
            items.append(_build_citation_failure_evidence(failure))

    benchmark = _mapping(client_sections.get("competitive_benchmark"))
    for row in _sequence(benchmark.get("benchmark_rows")):
        if isinstance(row, Mapping):
            items.append(_build_benchmark_row_evidence(row, url=target_url))

    platform_breakdown = _mapping(client_sections.get("platform_breakdown"))
    for row in _sequence(platform_breakdown.get("platforms")):
        if isinstance(row, Mapping):
            items.append(_build_platform_observation_evidence(row, url=target_url))
    for row in _build_platform_control_rows(manifest, bridged_audit):
        items.append(_build_platform_control_evidence(row, url=target_url))

    measurement_summary = build_measurement_summary(measurement_data)
    measurement_summary_lookup = {
        _normalized_platform_key(item.get("platform")): item
        for item in _sequence(measurement_summary.get("platforms"))
        if isinstance(item, Mapping)
    }
    for row in _sequence(measurement_data.get("platforms")):
        if not isinstance(row, Mapping):
            continue
        platform_key = _normalized_platform_key(row.get("platform"))
        summary_row = _mapping(measurement_summary_lookup.get(platform_key))
        if not summary_row:
            continue
        items.append(
            _build_platform_measurement_evidence(
                row,
                summary=summary_row,
                url=target_url,
            )
        )
        captured_date_range = _clean_text(summary_row.get("captured_date_range"))
        for page_metric in _sequence(row.get("page_metrics")):
            if not isinstance(page_metric, Mapping):
                continue
            items.append(
                _build_citation_share_evidence(
                    _clean_text(row.get("platform")),
                    page_metric,
                    captured_date_range=captured_date_range,
                )
            )
        referrals = _mapping(row.get("referrals"))
        if referrals.get("visits"):
            items.append(
                _build_referral_signal_evidence(
                    _clean_text(row.get("platform")),
                    referrals,
                    url=target_url,
                    captured_date_range=captured_date_range,
                )
            )

    entity_authority_summary = build_entity_authority_summary(entity_authority_data)
    if entity_authority_summary.get("mention_count"):
        items.append(
            build_evidence_item(
                evidence_type="entity_authority_summary",
                source_class="third_party_reference",
                observed_vs_inferred="observed",
                platform=None,
                query_theme="entity_authority",
                url_or_domain=target_url,
                raw_observation=entity_authority_summary,
                normalized_summary=(
                    f"Captured {entity_authority_summary.get('mention_count')} offsite entity mentions with "
                    f"{entity_authority_summary.get('gap_count')} authority gaps still open."
                ),
                confidence="medium",
            )
        )
    for row in _sequence(entity_authority_data.get("mentions")):
        if not isinstance(row, Mapping):
            continue
        items.append(_build_offsite_entity_signal(row))
        if _string(row.get("brand_match")) != "exact" or _string(row.get("profile_status")) != "complete":
            items.append(_build_offsite_authority_gap(row))

    prompt_query_proof = _mapping(client_sections.get("prompt_query_proof"))
    explicit_prompt_rows = [
        row
        for row in _sequence(prompt_query_proof.get("rows"))
        if isinstance(row, Mapping)
    ]
    prompt_rows = explicit_prompt_rows or build_sampled_query_prompt_rows(bridged_audit)
    for row in prompt_rows:
        if isinstance(row, Mapping):
            items.append(_build_prompt_proof_evidence(row, url=target_url))

    page_source_evidence = _mapping(client_sections.get("page_source_evidence"))
    for row in _sequence(page_source_evidence.get("priority_pages")):
        if isinstance(row, Mapping):
            items.append(_build_priority_page_evidence(row))
    for row in _sequence(page_source_evidence.get("source_domains")):
        if isinstance(row, Mapping):
            items.append(_build_source_domain_evidence(row))
    sitemap_pages = _sequence(readiness_inputs.get("sitemap_pages"))
    seen_sitemap_urls = {
        _normalized_url(_clean_text(item.get("url")) if isinstance(item, Mapping) else _clean_text(item))
        for item in items
        if _string(item.get("evidence_type")) == "linked_page"
    }
    if not any(_string(item.get("evidence_type")) == "linked_page" for item in items):
        for row in sitemap_pages[:5]:
            sitemap_url = _clean_text(row.get("url")) if isinstance(row, Mapping) else _clean_text(row)
            normalized = _normalized_url(sitemap_url)
            if (
                not normalized
                or normalized in seen_sitemap_urls
                or _same_page(sitemap_url, target_url)
                or not _is_high_signal_link(sitemap_url, _path_from_url(sitemap_url).split("/")[-1].replace("-", " "))
            ):
                continue
            seen_sitemap_urls.add(normalized)
            items.append(
                _build_linked_page_evidence(
                    sitemap_url,
                    source="sitemap",
                )
            )

    return {
        "items": items,
        "count": len(items),
        "target_url": target_url,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
