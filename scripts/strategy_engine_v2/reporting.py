from __future__ import annotations

from typing import Any, Mapping

from scripts.strategy_engine_v2.business_profiles import resolve_business_profile
from scripts.strategy_engine_v2.platform_sources import (
    default_official_sources,
    sources_for_platform,
)


REPORT_SECTION_ORDER = (
    "leadership_summary",
    "score_explanations",
    "priority_findings",
    "competitive_benchmark",
    "platform_breakdown",
    "page_source_evidence",
    "action_plan",
    "proof_appendix",
)

WEBSITE_ACTION_THEMES = {
    "content_citability",
    "content_extractability",
    "content_proof_density",
    "content_question_coverage",
    "heading_structure",
    "author_trust",
    "entity_authority",
    "accessibility_parity",
    "technical_hardening",
    "llms_guidance",
}

SECTION_EVIDENCE_TYPES = {
    "benchmark": ("run_manifest", "plugin_results"),
    "prompt_proof": ("plugin_results",),
    "platform_breakdown": ("run_manifest", "plugin_results"),
    "change_since_last_run": ("run_manifest",),
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


def _normalized_text(value: Any) -> str:
    return " ".join(_string(value).lower().split())


def _title_case_status(value: Any) -> str:
    return _string(value).replace("-", " ").replace("_", " ").title()


def _label_text(value: Any) -> str:
    text = _string(value).replace("_", " ")
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _clean_legacy_language(value: Any) -> str:
    text = _string(value)
    replacements = {
        "ReScience optimization pass": "Optimization pass",
        "ReScience recommendations": "optimization recommendations",
        "rescience optimization pass": "optimization pass",
        "rescience recommendations": "optimization recommendations",
        "geo-seo-claude audit model": "bridged live-audit model",
        "directly limits": "can limit",
        "directly limit": "can limit",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split()).strip()


def _status_rank(status: str) -> int:
    ranks = {
        "decision-grade": 0,
        "directional": 1,
        "omitted": 2,
    }
    return ranks.get(status, 3)


def _worst_status(statuses: list[str]) -> str:
    cleaned = [status for status in statuses if status]
    if not cleaned:
        return "omitted"
    return sorted(cleaned, key=_status_rank)[-1]


def _trust_value(statuses: list[str]) -> str:
    worst = _worst_status(statuses)
    values = {
        "decision-grade": "High",
        "directional": "Medium",
        "omitted": "Low",
    }
    return values.get(worst, "Low")


def _evidence_grade_from_status(status: str) -> str:
    normalized = _normalized_text(status)
    if normalized == "decision-grade":
        return "decision-grade"
    if normalized == "directional":
        return "directional"
    if normalized == "omitted":
        return "thin"
    return "strong"


def _readiness_value(audit_data: Mapping[str, Any]) -> str:
    geo_score = audit_data.get("geo_score")
    try:
        score = int(geo_score)
    except (TypeError, ValueError):
        return "Unavailable"
    if score >= 75:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def _visible_reason(section: Mapping[str, Any]) -> str:
    warning = _string(section.get("warning"))
    if warning:
        return warning
    reason = _string(section.get("reason"))
    if reason:
        return reason
    return "No evidence was captured for this section yet."


def _section_status(section: Mapping[str, Any]) -> str:
    return _string(section.get("status")) or "omitted"


def _most_severe_visible_reason(adjudication: Mapping[str, Any], section_names: tuple[str, ...]) -> str:
    best_section: Mapping[str, Any] | None = None
    best_rank = -1
    for section_name in section_names:
        section = _mapping(adjudication.get(section_name))
        rank = _status_rank(_section_status(section))
        if rank > best_rank:
            best_rank = rank
            best_section = section
    if best_section is None:
        return "No evidence has been captured yet."
    return _visible_reason(best_section)


def _evidence_items(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    evidence = _mapping(report_input.get("evidence"))
    items: list[dict[str, Any]] = []
    for item in _sequence(evidence.get("items")):
        if isinstance(item, Mapping):
            items.append(dict(item))
    return items


def _audit_data(report_input: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(report_input.get("audit_data"))


def _client_sections(report_input: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(_audit_data(report_input).get("client_report_sections"))


def _legacy_sections(report_input: Mapping[str, Any]) -> dict[str, Any]:
    return _mapping(_audit_data(report_input).get("report_sections"))


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        text = _clean_legacy_language(_string(value))
        if not text:
            continue
        marker = _normalized_text(text)
        if marker in seen:
            continue
        seen.add(marker)
        items.append(text)
    return items


def _dedupe_evidence_items(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    items: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, Mapping):
            continue
        key = (
            _string(item.get("evidence_type")),
            _string(item.get("url_or_domain")),
            _string(item.get("normalized_summary")),
            _string(_mapping(item.get("raw_observation")).get("title")),
        )
        if key in seen:
            continue
        seen.add(key)
        items.append(dict(item))
    return items


def _business_profile(report_input: Mapping[str, Any]) -> dict[str, str]:
    audit_data = _audit_data(report_input)
    explicit_profile = _string(report_input.get("business_profile")) or _string(audit_data.get("business_profile"))
    return resolve_business_profile(explicit_profile, audit_data)


def _finding_theme(finding: Mapping[str, Any]) -> str:
    blob = " ".join(
        part
        for part in (
            _string(finding.get("title")),
            _string(finding.get("summary")),
            _string(finding.get("description")),
            _string(finding.get("leadership_impact")),
            _string(finding.get("marketing_action")),
            _string(finding.get("developer_action")),
        )
        if part
    )
    normalized_blob = _normalized_text(blob)
    if any(
        token in normalized_blob
        for token in (
            "ai-citation",
            "citation ready",
            "citability",
            "answer-first",
            "quote-ready",
            "citation share",
            "measured platform visibility",
        )
    ):
        return "content_citability"
    if "llms" in normalized_blob:
        return "llms_guidance"
    if "heading" in normalized_blob or "h1" in normalized_blob:
        return "heading_structure"
    if any(
        token in normalized_blob
        for token in ("accessibility", "landmark", "aria", "rendered", "hydration", "parity")
    ):
        return "accessibility_parity"
    if any(token in normalized_blob for token in ("entity", "authority", "wikidata", "profile")):
        return "entity_authority"
    if any(
        token in normalized_blob
        for token in ("author", "authorship", "byline", "credential", "freshness", "datepublished", "datemodified")
    ):
        return "author_trust"
    return _legacy_action_theme({"action": blob})


def _related_finding_evidence(theme: str, evidence_by_type: Mapping[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    theme_map = {
        "author_trust": ("authorship_signal", "freshness_signal"),
        "accessibility_parity": ("accessibility_signal",),
        "content_citability": ("citation_share_signal", "platform_measurement", "referral_signal"),
        "entity_authority": ("offsite_entity_signal", "offsite_authority_gap", "entity_authority_summary"),
    }
    items: list[dict[str, Any]] = []
    for evidence_type in theme_map.get(theme, ()):
        items.extend(evidence_by_type.get(evidence_type, []))
    return _dedupe_evidence_items(items)


def _supporting_evidence_sort_key(item: Mapping[str, Any]) -> tuple[int, str]:
    evidence_type = _string(item.get("evidence_type"))
    order = {
        "platform_measurement": 0,
        "citation_share_signal": 1,
        "referral_signal": 2,
        "entity_authority_summary": 0,
        "offsite_entity_signal": 1,
        "offsite_authority_gap": 2,
        "authorship_signal": 0,
        "freshness_signal": 1,
        "accessibility_signal": 0,
        "page_fetch": 2,
        "page_citability": 2,
        "brand_entity": 2,
        "priority_page": 3,
        "source_domain": 3,
        "finding": 9,
    }
    return (order.get(evidence_type, 5), _string(item.get("normalized_summary")))


def _supporting_evidence_line(item: Mapping[str, Any]) -> str:
    evidence_type = _string(item.get("evidence_type"))
    if evidence_type == "finding":
        return ""
    summary = _string(item.get("normalized_summary"))
    if not summary:
        return ""
    source = _string(item.get("url_or_domain"))
    observed_vs_inferred = _string(item.get("observed_vs_inferred")).lower()
    if observed_vs_inferred == "observed":
        prefix = "Observed"
    elif observed_vs_inferred == "inferred":
        prefix = "Inferred"
    else:
        prefix = "Captured"
    if source:
        return f"{prefix} on {source}: {summary}"
    source_class = _string(item.get("source_class")).replace("_", " ")
    if source_class:
        return f"{prefix} from {source_class}: {summary}"
    return f"{prefix}: {summary}"


def _finding_supporting_evidence(
    report_input: Mapping[str, Any],
    finding: Mapping[str, Any],
    matching_evidence: list[dict[str, Any]],
) -> list[str]:
    theme = _finding_theme(finding)
    page_source_section = _mapping(_client_sections(report_input).get("page_source_evidence"))
    lines: list[str] = []

    for page in _sequence(page_source_section.get("priority_pages"))[:2]:
        if not isinstance(page, Mapping):
            continue
        page_url = _string(page.get("page_url"))
        page_type = _string(page.get("page_type")) or "page"
        if theme == "content_citability":
            citability = _string(page.get("citability_score"))
            if page_url and citability:
                lines.append(
                    f"Priority page {page_type} {page_url} scored {citability}/100 for citability in this run."
                )
            for note in _sequence(page.get("content_observations"))[:1]:
                lines.append(_string(note))
        if theme == "heading_structure":
            for note in _sequence(page.get("technical_observations"))[:2]:
                lines.append(_string(note))
        if theme == "entity_authority":
            for note in _sequence(page.get("trust_observations"))[:2]:
                lines.append(_string(note))

    if theme == "content_citability":
        for item in _sequence(_audit_data(report_input).get("citation_failures"))[:2]:
            if not isinstance(item, Mapping):
                continue
            query = _string(item.get("query"))
            target_url = _string(item.get("target_url"))
            if query and target_url:
                lines.append(
                    f"Sampled query '{query}' did not surface {target_url} in the captured visibility run."
                )

    preferred_evidence = [
        item for item in matching_evidence if _string(item.get("evidence_type")) != "finding"
    ] or matching_evidence
    for item in preferred_evidence[:3]:
        if not isinstance(item, Mapping):
            continue
        line = _supporting_evidence_line(item)
        if line:
            lines.append(line)

    fallback = _string(finding.get("observed_evidence")) or _string(finding.get("leadership_impact"))
    if fallback:
        lines.append(fallback)

    return _dedupe_strings(lines)


def _finding_confidence(theme: str, supporting_evidence: list[str], status: str) -> str:
    normalized_status = _normalized_text(status)
    if normalized_status in {"omitted", "directional"}:
        return "low"
    if supporting_evidence and theme in {
        "content_citability",
        "heading_structure",
        "llms_guidance",
        "content_extractability",
        "content_proof_density",
    }:
        return "high"
    if supporting_evidence:
        return "medium"
    return "low"


def _finding_confidence_reason(theme: str, confidence: str) -> str:
    if theme == "content_citability":
        return "This finding is grounded in priority page scoring and measured citation or referral evidence from the current run."
    if theme == "heading_structure":
        return "This finding comes from direct page-level structure checks in the current run."
    if theme == "llms_guidance":
        return "This finding comes from a direct root-file fetch, but the file itself is optional guidance."
    if theme == "entity_authority":
        return "This finding is based on the current entity and trust signals captured in this run."
    if theme == "author_trust":
        return "This finding comes from direct byline, author-page, and freshness signals captured on the audited page."
    if theme == "accessibility_parity":
        return "This finding comes from direct landmark and rendered-state parity checks in the current run."
    if confidence == "low":
        return "This read is still directional because the supporting evidence is partial."
    return "This read combines live observations from the current run with bridged audit context."


def _finding_success_metric(theme: str, profile_key: str) -> str:
    if theme == "content_citability":
        surfaces = {
            "local": "location or service-area pages",
            "ecommerce": "product or category pages",
            "publisher": "editorial or explainer pages",
        }
        target_surface = surfaces.get(profile_key, "priority pages")
        return f"Raise citability on {target_surface} and see more sampled answers cite or summarize those pages accurately."
    if theme == "heading_structure":
        return "Reduce priority pages to one clear H1 and verify cleaner extracted snippets in the next audit."
    if theme == "llms_guidance":
        return "Publish the file at the root, keep it updated, and confirm whether supported bots request it in logs."
    if theme == "entity_authority":
        return "Increase durable third-party entity signals and improve authority reads in the next comparable audit."
    if theme == "author_trust":
        return "Expose aligned bylines, author pages, and publish or update dates on priority pages and confirm they remain visible in the next run."
    if theme == "accessibility_parity":
        return "Keep critical content present in the primary rendered state and confirm landmarks and rendered parity improve on the next run."
    if theme == "content_extractability":
        return "Improve passage extraction quality so key answers stay accurate when quoted out of context."
    return "Re-run the same audit scope and confirm the cited weakness improved on the affected pages."


def _profile_tuned_action(row: Mapping[str, Any], profile: Mapping[str, Any]) -> dict[str, Any]:
    tuned = dict(row)
    profile_key = _string(profile.get("key"))
    content_surface = _string(profile.get("content_surface")) or "priority pages"
    owner_overrides = {
        "local": "local_marketing",
        "ecommerce": "merchandising",
        "publisher": "editorial",
    }
    current_owner = _normalized_text(tuned.get("owner"))
    if profile_key in owner_overrides and current_owner in {"", "marketing", "strategy", "cross-functional"}:
        tuned["owner"] = owner_overrides[profile_key]
    action_text = _normalized_text(tuned.get("action"))
    if profile_key in {"local", "ecommerce", "publisher"} and (
        "quote-ready" in action_text or "priority pages" in action_text
    ):
        tuned["expected_outcome"] = (
            f"Increase citations, referrals, and assisted conversions from {content_surface}."
        )
    return tuned


def _finding_time_horizon(status: Any) -> str:
    normalized = _normalized_text(status)
    if normalized in {"critical", "high"}:
        return "30 days"
    if normalized == "medium":
        return "60 days"
    return "90 days"


def _priority_label(status: Any) -> str:
    normalized = _normalized_text(status)
    if normalized == "critical":
        return "Critical"
    if normalized == "high":
        return "High"
    if normalized == "medium":
        return "Medium"
    if normalized == "low":
        return "Low"
    return _title_case_status(status) or "Medium"


def _surface_group(theme: str) -> str:
    if theme in {"content_citability", "content_extractability", "content_proof_density", "heading_structure"}:
        return "Priority Pages And Templates"
    if theme in {"author_trust", "entity_authority"}:
        return "Trust And Entity Surfaces"
    if theme in {"llms_guidance", "accessibility_parity", "technical_hardening"}:
        return "Template, Schema, And Crawl Surfaces"
    return "Website Improvements"


def _primary_priority_pages(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(page)
        for page in _sequence(_mapping(_client_sections(report_input).get("page_source_evidence")).get("priority_pages"))
        if isinstance(page, Mapping)
    ]


def _formatted_priority_page_locations(report_input: Mapping[str, Any]) -> list[str]:
    locations: list[str] = []
    for page in _primary_priority_pages(report_input)[:2]:
        page_url = _string(page.get("page_url"))
        page_type = _string(page.get("page_type"))
        if page_url and page_type:
            locations.append(f"{page_type}: {page_url}")
        elif page_url:
            locations.append(page_url)
    return locations


def _website_fix_owner(theme: str, profile: Mapping[str, Any]) -> str:
    profile_key = _string(profile.get("key"))
    if theme in {"heading_structure", "accessibility_parity", "technical_hardening", "llms_guidance"}:
        return "Engineering"
    if theme == "author_trust":
        return "Editorial + SEO" if profile_key == "publisher" else "Content + SEO"
    if theme == "entity_authority":
        return "Brand + SEO"
    if theme == "content_citability":
        if profile_key == "local":
            return "Local Marketing"
        if profile_key == "ecommerce":
            return "Merchandising"
        if profile_key == "publisher":
            return "Editorial"
        return "Content"
    return "SEO + Content"


def _website_fix_roles(theme: str) -> list[str]:
    role_map = {
        "content_citability": ["Content", "SEO", "Engineering"],
        "content_extractability": ["Content", "SEO"],
        "content_proof_density": ["Content", "SEO"],
        "content_question_coverage": ["Content", "SEO"],
        "heading_structure": ["SEO", "Engineering"],
        "author_trust": ["Content", "SEO"],
        "entity_authority": ["Brand", "SEO"],
        "accessibility_parity": ["Engineering", "SEO"],
        "technical_hardening": ["Engineering", "SEO"],
        "llms_guidance": ["SEO", "Engineering"],
    }
    return role_map.get(theme, ["SEO", "Content"])


def _website_fix_title(theme: str, finding: Mapping[str, Any]) -> str:
    titles = {
        "content_citability": "Make priority pages answer-first and quote-ready",
        "content_extractability": "Make key answers stand on their own",
        "content_proof_density": "Add specific proof points to answer sections",
        "content_question_coverage": "Add direct coverage for high-intent questions",
        "heading_structure": "Fix heading hierarchy on the homepage and core templates",
        "author_trust": "Add visible bylines, author pages, and update dates",
        "entity_authority": "Strengthen on-site entity and trust signals",
        "accessibility_parity": "Keep primary content and landmarks consistent after render",
        "technical_hardening": "Reduce HTML weight and keep core signals early",
        "llms_guidance": "Publish root-level AI guidance files correctly",
    }
    return titles.get(theme, _string(finding.get("marketing_action")) or _string(finding.get("engineering_action")) or _string(finding.get("section")))


def _website_fix_location(theme: str, report_input: Mapping[str, Any]) -> str:
    page_locations = _formatted_priority_page_locations(report_input)
    if theme in {"content_citability", "content_extractability", "content_proof_density", "content_question_coverage"} and page_locations:
        return "; ".join(page_locations)
    if theme == "heading_structure":
        if page_locations:
            return "; ".join(page_locations)
        return "Homepage hero and shared heading template"
    if theme == "author_trust":
        if page_locations:
            return "; ".join(page_locations) + "; linked author pages"
        return "Priority article or expert templates and linked author pages"
    if theme == "entity_authority":
        return "Homepage, About page, organization schema, and linked profile surfaces"
    if theme == "accessibility_parity":
        return "Primary page template, global layout, and rendered page state"
    if theme == "technical_hardening":
        return "Global head markup and primary page template"
    if theme == "llms_guidance":
        return "Root files: /llms.txt, /llms-full.txt, and robots.txt"
    return page_locations[0] if page_locations else "Priority website surfaces captured in this run"


def _website_fix_page_scope(theme: str, report_input: Mapping[str, Any]) -> list[str]:
    return [
        _string(page.get("page_url"))
        for page in _primary_priority_pages(report_input)
        if _string(page.get("page_url"))
    ]


def _website_fix_template_scope(theme: str, report_input: Mapping[str, Any]) -> list[str]:
    types = [
        _string(page.get("page_type")).replace("_", " ").title()
        for page in _primary_priority_pages(report_input)
        if _string(page.get("page_type"))
    ]
    if theme == "heading_structure":
        return _dedupe_strings(types + ["Shared heading template"])
    if theme == "author_trust":
        return _dedupe_strings(types + ["Author profile template"])
    if theme == "accessibility_parity":
        return ["Primary page template", "Global layout"]
    if theme == "technical_hardening":
        return ["Document head", "Primary page template"]
    if theme == "llms_guidance":
        return ["Root text files"]
    if theme == "entity_authority":
        return ["Organization schema", "About page", "Homepage"]
    return _dedupe_strings(types)


def _website_fix_repo_surface(theme: str) -> str:
    surfaces = {
        "content_citability": "CMS / Content Editor",
        "content_extractability": "CMS / Content Editor",
        "content_proof_density": "CMS / Content Editor",
        "content_question_coverage": "CMS / Content Editor",
        "heading_structure": "Frontend / Templates",
        "author_trust": "CMS / Author Profiles",
        "entity_authority": "Frontend / Schema",
        "accessibility_parity": "Frontend / Layout",
        "technical_hardening": "Frontend / Document Head",
        "llms_guidance": "Static Assets / Root",
    }
    return surfaces.get(theme, "Frontend")


def _website_fix_change_steps(theme: str, finding: Mapping[str, Any]) -> list[str]:
    steps = _dedupe_strings(
        [
            _string(finding.get("marketing_action")),
            _string(finding.get("engineering_action")),
        ]
    )
    if steps:
        return steps[:3]
    defaults = {
        "content_citability": [
            "Open each target page with a direct answer block that resolves the main user question quickly.",
            "Support the answer with named facts, service details, or sourceable proof instead of generic marketing copy.",
        ],
        "heading_structure": [
            "Keep one primary H1 for the page promise and move section labels under semantic H2 and H3 headings.",
            "Remove layout-driven heading misuse from cards, accordions, and repeated sections.",
        ],
        "author_trust": [
            "Add a visible byline, linked author page, and publish or update date on each expert page.",
            "Keep visible author and date details aligned with schema markup.",
        ],
        "entity_authority": [
            "Strengthen About and brand pages with consistent organization details, services, and profile links.",
            "Keep organization and profile schema aligned with visible brand information.",
        ],
        "accessibility_parity": [
            "Keep the main answer content present in the primary rendered state instead of hiding it behind JS-only interactions.",
            "Use a clean landmark structure with one main content region.",
        ],
        "technical_hardening": [
            "Reduce bulky HTML and repeated template markup so core content appears earlier in the fetched document.",
            "Keep title, canonical, description, schema, and key answer content early in the page source.",
        ],
        "llms_guidance": [
            "Publish llms.txt and llms-full.txt at the root with current guidance for supported bots.",
            "Keep the files aligned with actual site sections and maintenance ownership.",
        ],
    }
    return defaults.get(theme, ["Apply the fix described by this finding on the affected website surfaces."])


def _website_fix_example(theme: str, report_input: Mapping[str, Any]) -> str:
    sample_url = _string((_primary_priority_pages(report_input)[:1] or [{}])[0].get("page_url"))
    examples = {
        "content_citability": "Example: add a 2-4 sentence answer summary near the top of the page, followed by specific facts, coverage details, or constraints that can be quoted accurately.",
        "heading_structure": "Example: use one H1 for the page promise, then H2s for major sections such as coverage, pricing, FAQs, and next steps.",
        "author_trust": "Example: show 'By Jane Doe, CFP' with a linked bio page and a visible updated date that matches Article schema.",
        "entity_authority": "Example: add consistent organization details, sameAs links, and service descriptions on About and profile surfaces.",
        "accessibility_parity": "Example: keep the primary answer copy visible without requiring hydration, and expose one main landmark for the page body.",
        "technical_hardening": "Example: move bulky inline assets out of the initial document and keep the answer-first copy near the top of the HTML.",
        "llms_guidance": "Example: publish /llms.txt with a short site map of important sections and keep the file accessible at the root.",
    }
    example = examples.get(theme, "")
    if sample_url and theme == "content_citability":
        return f"{example} Start with {sample_url}."
    return example


def _website_fix_acceptance(theme: str) -> str:
    criteria = {
        "content_citability": "Each target page opens with a direct answer section, contains specific proof points, and remains understandable when quoted out of context.",
        "content_extractability": "Each key answer can stand alone without relying on surrounding page copy to stay accurate.",
        "content_proof_density": "Each answer section includes concrete entities, data points, or named details instead of vague claims.",
        "content_question_coverage": "Each high-intent question has a direct answer section on a live target page.",
        "heading_structure": "Each target page uses one H1 and semantic H2 or H3 structure for supporting sections.",
        "author_trust": "Each target page shows a visible byline, linked author page, visible date, and matching schema details.",
        "entity_authority": "Brand and organization pages expose consistent entity details, profile links, and matching organization markup.",
        "accessibility_parity": "Primary content remains visible after render, and the template exposes a clean landmark structure with one main region.",
        "technical_hardening": "Critical SEO and GEO signals appear early in the HTML, and document weight is reduced on the affected template.",
        "llms_guidance": "Root guidance files are published, reachable, and aligned with the current site structure.",
    }
    return criteria.get(theme, "The affected website surface reflects the intended change clearly and consistently.")


def _website_fix_expected_effect(theme: str) -> tuple[str, str, str]:
    effects = {
        "content_citability": (
            "Higher likelihood that priority pages are cited, summarized accurately, and surfaced in AI answers.",
            "High",
            "1-2 comparable runs",
        ),
        "content_extractability": (
            "Cleaner answer extraction when platforms quote passages out of surrounding context.",
            "Medium",
            "1-2 comparable runs",
        ),
        "content_proof_density": (
            "Stronger support for platform citations because pages carry more quotable proof.",
            "Medium",
            "1-2 comparable runs",
        ),
        "heading_structure": (
            "Clearer topic parsing and better snippet extraction on affected templates.",
            "High",
            "Next run",
        ),
        "author_trust": (
            "Stronger trust interpretation on expert content and better alignment for quoted answers.",
            "Medium",
            "1-2 comparable runs",
        ),
        "entity_authority": (
            "Stronger brand-entity association and more defensible authority signals over time.",
            "Medium",
            "Multiple runs",
        ),
        "accessibility_parity": (
            "More reliable machine access to the same core content users see.",
            "High",
            "Next run",
        ),
        "technical_hardening": (
            "Lower risk that critical GEO signals are missed or weakened during fetch and render.",
            "Medium",
            "Next run",
        ),
        "llms_guidance": (
            "Clearer optional guidance for supported bots without treating the file as the main ranking lever.",
            "Low",
            "Multiple runs",
        ),
    }
    return effects.get(theme, ("Better website clarity for search and answer engines.", "Medium", "Next run"))


def _website_fix_verification(theme: str) -> tuple[str, str, str]:
    checks = {
        "content_citability": (
            "QA: confirm the answer-first summary and proof-rich sections are published on the target page.",
            "Next run: confirm citability and answer extraction improve on the affected pages.",
            "Watch citation share, referral visits, or answer quality on the updated URLs.",
        ),
        "content_extractability": (
            "QA: confirm the key answer block reads clearly on its own without surrounding copy.",
            "Next run: confirm answer extraction and passage quality improve on the affected pages.",
            "Watch whether sampled answers quote the updated passages more accurately.",
        ),
        "content_proof_density": (
            "QA: confirm each answer section includes named facts, entities, or concrete proof.",
            "Next run: confirm proof-density findings improve on the affected pages.",
            "Watch whether platforms cite or summarize the updated details more directly.",
        ),
        "content_question_coverage": (
            "QA: confirm each target question has a live answer section on the intended page.",
            "Next run: confirm the updated pages appear stronger for the sampled question set.",
            "Watch whether sampled answers surface the new coverage more often.",
        ),
        "heading_structure": (
            "QA: confirm the target page uses one H1 and semantic H2 or H3 structure.",
            "Next run: confirm H1 count and heading-structure findings improve on affected templates.",
            "Watch snippet quality and answer extraction on those pages.",
        ),
        "author_trust": (
            "QA: confirm bylines, author pages, and visible dates are published and aligned with schema.",
            "Next run: confirm authorship and freshness signals are captured across the updated pages.",
            "Watch trust-signal findings and citation quality on expert content.",
        ),
        "entity_authority": (
            "QA: confirm organization details and profile links are visible on the intended pages.",
            "Next run: confirm entity and authority reads improve in the comparable audit.",
            "Watch brand-entity findings rather than expecting an immediate citation jump.",
        ),
        "accessibility_parity": (
            "QA: confirm the rendered page keeps the same core content and landmark structure users see.",
            "Next run: confirm landmark and rendered-parity findings improve on the affected template.",
            "Watch whether machine-readable access issues stop recurring in later runs.",
        ),
        "technical_hardening": (
            "QA: confirm the target template ships lighter HTML and keeps critical signals early in source.",
            "Next run: confirm fetch-risk signals improve on the affected template.",
            "Watch whether crawl and rendering notes stop flagging the page.",
        ),
        "llms_guidance": (
            "QA: confirm /llms.txt and related root guidance files are published and reachable.",
            "Next run: confirm the file is fetched cleanly and no guidance-file gaps remain.",
            "Watch logs or later bot-access evidence rather than expecting direct performance movement alone.",
        ),
    }
    return checks.get(theme, ("QA: confirm the change is published on the intended page or template.", "Next run: confirm the related finding improves.", "Watch the related outcome in the next comparable run."))


def _singleton_rollout_sequence(action: Mapping[str, Any], report_input: Mapping[str, Any]) -> list[str]:
    locations = _formatted_priority_page_locations(report_input)
    pilot_surface = locations[0] if locations else (_string(action.get("exact_location")) or "the highest-priority affected page")
    rollout_steps = [f"Pilot this fix on {pilot_surface}."]
    if len(locations) > 1:
        rollout_steps.append(
            "Extend the same change to the remaining priority pages once the pilot passes QA and the next audit confirms improvement."
        )
    else:
        rollout_steps.append(
            "Apply the same pattern to the shared template or the next highest-priority surface after the pilot passes QA."
        )
    rollout_steps.append(
        "Re-run the audit on the updated surface before expanding further so the next rollout is backed by direct evidence."
    )
    return rollout_steps


def _singleton_primary_action(
    action: Mapping[str, Any],
    finding: Mapping[str, Any],
    report_input: Mapping[str, Any],
) -> dict[str, Any]:
    primary = dict(action)
    proof_packet = _dedupe_strings(
        [_string(item) for item in _sequence(action.get("supporting_evidence")) if _string(item)]
    )[:3]
    if not proof_packet:
        proof_packet = _dedupe_strings(
            [
                _string(action.get("observed_evidence")),
                _string(finding.get("visible_reason")),
                _string(finding.get("summary")),
            ]
        )[:3]
    primary["why_this_is_the_lead_fix"] = (
        "This is the only website fix in this run with strong enough evidence and a clear implementation path."
    )
    primary["confidence_reason"] = _string(finding.get("confidence_reason"))
    primary["success_metric"] = _string(finding.get("success_metric"))
    primary["proof_packet"] = proof_packet
    primary["pilot_surface"] = (_formatted_priority_page_locations(report_input)[:1] or [_string(action.get("exact_location"))])[0]
    primary["rollout_scope"] = _string(action.get("exact_location")) or "Priority website surfaces captured in this run"
    primary["rollout_sequence"] = _singleton_rollout_sequence(action, report_input)
    return primary


def _watchlist_title(finding: Mapping[str, Any]) -> str:
    title = _string(finding.get("title"))
    if title:
        return title
    section = _normalized_text(finding.get("section"))
    if section == "prompt_proof":
        return "Prompt proof is still partial"
    return _string(finding.get("section")).replace("_", " ").capitalize() or "Observation needs more proof"


def _watchlist_items(
    findings: list[dict[str, Any]],
    primary_theme: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, Mapping):
            continue
        if _string(finding.get("theme")) == primary_theme:
            continue
        strongest_evidence = _dedupe_strings(
            [*_sequence(finding.get("supporting_evidence")), _string(finding.get("visible_reason")), _string(finding.get("summary"))]
        )
        evidence_grade = _label_text(finding.get("evidence_grade")) or _title_case_status(finding.get("status")) or "Directional"
        items.append(
            {
                "observation_id": _normalized_text(_string(finding.get("section")) or _watchlist_title(finding)).replace(" ", "-"),
                "title": _watchlist_title(finding),
                "theme": _string(finding.get("theme")),
                "evidence_grade": evidence_grade,
                "why_not_recommended_yet": (
                    _string(finding.get("limitations"))
                    or f"This signal is still {evidence_grade.lower()} rather than recommendation-grade in this run."
                ),
                "what_upgrades_this": _string(finding.get("what_upgrades_this")) or _string(finding.get("success_metric")),
                "strongest_evidence": strongest_evidence[0] if strongest_evidence else "",
            }
        )
    return items[:4]


def _finding_to_website_action(
    report_input: Mapping[str, Any],
    finding: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    theme = _string(finding.get("theme")) or _finding_theme(finding)
    effect, effect_confidence, effect_timeframe = _website_fix_expected_effect(theme)
    verify_qa, verify_geo, verify_outcome = _website_fix_verification(theme)
    support_line = _dedupe_strings(
        [*_sequence(finding.get("supporting_evidence")), _string(finding.get("visible_reason")), _string(finding.get("summary"))]
    )
    return {
        "action_id": _normalized_text(_string(finding.get("section")) or theme).replace(" ", "-"),
        "title": _website_fix_title(theme, finding),
        "action": _website_fix_title(theme, finding),
        "time_horizon": _finding_time_horizon(finding.get("status")),
        "priority": _priority_label(finding.get("status")),
        "owner": _website_fix_owner(theme, profile),
        "role_tags": _website_fix_roles(theme),
        "surface_group": _surface_group(theme),
        "exact_location": _website_fix_location(theme, report_input),
        "page_scope": _website_fix_page_scope(theme, report_input),
        "template_scope": _website_fix_template_scope(theme, report_input),
        "repo_surface": _website_fix_repo_surface(theme),
        "observed_evidence": support_line[0] if support_line else _string(finding.get("visible_reason")) or _string(finding.get("summary")),
        "exact_change": _website_fix_change_steps(theme, finding),
        "example_implementation": _website_fix_example(theme, report_input),
        "acceptance_criteria": _website_fix_acceptance(theme),
        "verification_qa": verify_qa,
        "verification_geo": verify_geo,
        "verification_outcome": verify_outcome,
        "expected_geo_effect": effect,
        "expected_effect_confidence": effect_confidence,
        "expected_effect_timeframe": effect_timeframe,
        "confidence": _title_case_status(_string(finding.get("confidence")) or effect_confidence),
        "supporting_evidence": _sequence(finding.get("supporting_evidence")),
        "theme": theme,
    }


def _finding_claim_source_class(theme: str, evidence_items: list[dict[str, Any]]) -> str:
    if theme == "entity_authority":
        return "heuristic_inference"
    source_classes = {
        _string(item.get("source_class"))
        for item in evidence_items
        if isinstance(item, Mapping) and _string(item.get("source_class"))
    }
    if "live_platform_measurement" in source_classes:
        return "live_platform_measurement"
    if "third_party_reference" in source_classes:
        return "heuristic_inference"
    if "live_site" in source_classes:
        return "live_site_observation"
    if "internal_score" in source_classes:
        return "internal_score"
    if theme == "llms_guidance":
        return "official_guidance"
    return "heuristic_inference"


def _finding_evidence_grade(
    claim_source_class: str,
    confidence: str,
    evidence_items: list[dict[str, Any]],
) -> str:
    if claim_source_class == "live_platform_measurement" and any(
        _string(item.get("evidence_type")) in {"platform_measurement", "citation_share_signal"}
        for item in evidence_items
        if isinstance(item, Mapping)
    ):
        return "decision-grade"
    normalized_confidence = _normalized_text(confidence)
    if normalized_confidence == "high":
        return "strong"
    if normalized_confidence == "medium":
        return "directional"
    return "thin"


def _finding_what_upgrades_this(theme: str, claim_source_class: str) -> str:
    if claim_source_class == "live_platform_measurement":
        return "Add more measured platform coverage across more pages and a longer date range."
    if theme == "entity_authority":
        return "Add more durable third-party profiles and references with exact entity matches."
    if theme == "author_trust":
        return "Capture aligned visible bylines, author pages, and dates across more priority pages."
    if theme == "accessibility_parity":
        return "Capture cleaner rendered-state parity across additional templates and user-agent checks."
    if theme == "heading_structure":
        return "Verify the fix across more templates and confirm extracted snippets improve in the next run."
    return "Add more direct proof from the affected pages or platforms in the next comparable run."


def _section_claim_source_class(section_name: str, report_input: Mapping[str, Any]) -> str:
    if section_name in {"leadership_summary", "score_explanations"}:
        return "internal_score"
    if section_name == "competitive_benchmark":
        return "heuristic_inference"
    if section_name == "platform_breakdown":
        if _platform_measurement_summary_by_platform(report_input):
            return "live_platform_measurement"
        if _platform_control_matrix(report_input):
            return "official_guidance"
        return "heuristic_inference"
    if section_name == "page_source_evidence":
        return "live_site_observation"
    if section_name == "proof_appendix":
        return "official_guidance"
    if section_name == "action_plan":
        return "heuristic_inference"
    return "heuristic_inference"


def _section_what_upgrades_this(section_name: str, claim_source_class: str) -> str:
    if section_name == "platform_breakdown":
        if claim_source_class == "live_platform_measurement":
            return "Extend the measured date range, add more platforms, and cover more priority page URLs."
        return "Add direct platform measurements or saved answer captures instead of relying on guidance-only reads."
    if section_name == "competitive_benchmark":
        return "Capture named competitor winners, cited URLs, and fixed query samples."
    if section_name == "page_source_evidence":
        return "Expand the priority page sample and keep direct page observations attached to each finding."
    if section_name == "action_plan":
        return "Tie each action to direct proof gaps so the roadmap is less inferential."
    if section_name == "proof_appendix":
        return "Attach more direct prompt, platform, and benchmark captures to the appendix."
    return "Add more direct evidence in the next comparable run."


def _finding_limitations(theme: str) -> str:
    if theme == "llms_guidance":
        return "This is optional machine-readable guidance for some platforms, not a universal ranking requirement."
    if theme == "entity_authority":
        return "Entity and authority work compounds over time, so this will move more slowly than on-page structural fixes."
    if theme == "author_trust":
        return "These cues support machine interpretation and trust, but they do not prove authority or freshness on their own."
    if theme == "accessibility_parity":
        return "These are accessibility and agent-compatibility support signals, not a standalone ranking guarantee."
    return "This is a point-in-time read of the audited pages in this run rather than every template, query, or platform surface."


def _scorecard_rows(audit_data: Mapping[str, Any]) -> list[dict[str, Any]]:
    geo_score = audit_data.get("geo_score")
    if geo_score is None:
        geo_score = _mapping(_mapping(audit_data.get("report_sections")).get("technical_geo_gates")).get("summary", {}).get("geo_score")
    component_scores = _mapping(audit_data.get("scores"))
    if geo_score is None and not component_scores:
        return []
    rows: list[dict[str, Any]] = []
    if geo_score is not None:
        rows.append(
            {
                "label": "GEO Score",
                "score": geo_score,
                "plain_english": "The rolled-up readiness signal from the bridged live audit.",
            }
        )
    labels = {
        "ai_citability": "AI Citability",
        "brand_authority": "Brand Authority",
        "content_eeat": "Content E-E-A-T",
        "technical": "Technical Foundation",
        "schema": "Schema",
        "platform_optimization": "Platform Optimization",
    }
    explanations = {
        "ai_citability": "How easily priority pages can be quoted, summarized, and attributed in AI answers.",
        "brand_authority": "How strongly the brand is reinforced by entity signals, references, and trust cues.",
        "content_eeat": "How clearly the content demonstrates experience, expertise, authority, and trust.",
        "technical": "How reliably the site can be crawled, rendered, and understood by search systems.",
        "schema": "How well structured data helps machines interpret key entities and page meaning.",
        "platform_optimization": "How prepared the site is for platform-specific AI search behaviors and surfaces.",
    }
    for key, label in labels.items():
        if key in component_scores:
            rows.append(
                {
                    "label": label,
                    "score": component_scores[key],
                    "plain_english": explanations.get(key, ""),
                }
            )
    return rows


def _bridge_action_visible_reason(action: Mapping[str, Any], adjudication: Mapping[str, Any]) -> str:
    action_text = _normalized_text(action.get("action"))
    evidence_basis = _string(action.get("evidence_basis")).lower()
    source = _string(action.get("source")).lower()
    if "llms" in action_text:
        return "The live audit flagged llms.txt as missing, but V2 still treats it as secondary to stronger content and crawl evidence."
    if "heading" in action_text:
        return "The live audit found a diluted heading structure, so this remains a near-term structural cleanup item."
    if "security" in action_text:
        return "Technical hardening is not the top blocker, but it remains a medium-term support task in the bridged backlog."
    if any(token in action_text for token in ("entity", "profile", "wikidata", "authority")):
        return "Entity and trust signals remain thin, so this action supports stronger attribution and brand reinforcement."
    if "fact density" in action_text or "data points" in action_text or "entities" in action_text:
        return "The current pages do not carry enough proof-rich detail, so this action strengthens the evidence AI systems can lift into answers."
    if "answer block" in action_text or "self-containment" in action_text or "extracted" in action_text:
        return "Important answers still depend too much on surrounding page context, so this action makes key passages more self-contained."
    if "high-intent user questions" in action_text or "questions directly" in action_text:
        return "The audit surfaced clear question demand, so this action expands coverage for the service questions users are already asking."
    if any(token in action_text for token in ("answer-first", "citations", "citability", "content")):
        return "Citability is weak on priority pages, so this action supports clearer answer-first content and proof."
    if "quick" in evidence_basis or "benchmark" in evidence_basis:
        return _visible_reason(_mapping(adjudication.get("benchmark")))
    if "prompt" in evidence_basis or "platform" in evidence_basis:
        return _visible_reason(_mapping(adjudication.get("prompt_proof")))
    if "change" in evidence_basis or "delta" in evidence_basis:
        return _visible_reason(_mapping(adjudication.get("change_since_last_run")))
    if "medium_term" in source or "strategic" in source:
        return "This action comes from the bridged V1 roadmap and stays directional until stronger comparison evidence is captured."
    return "This action is reused from the bridged V1 action plan and stays subject to V2 evidence review."


def _legacy_action_owner(action: Mapping[str, Any]) -> str:
    owner = _string(action.get("owner"))
    action_text = _normalized_text(action.get("action"))
    if any(token in action_text for token in ("content-security-policy", "security headers", "heading hierarchy", "single h1", "llms.txt", "llms-full.txt")):
        return "developers"
    if any(token in action_text for token in ("answer-first", "content", "questions directly", "recurring ai-native")):
        return "marketing"
    if any(token in action_text for token in ("entity trust", "entity authority", "wikidata", "profile governance")):
        return "leadership"
    return owner or "strategy"


def _legacy_action_expected_outcome(action: Mapping[str, Any]) -> str:
    action_text = _normalized_text(action.get("action"))
    if "llms" in action_text:
        return "Confirm the file is published, maintained, and monitored without treating it as the primary visibility lever."
    if "heading" in action_text:
        return "Make the homepage and service pages easier for users and answer engines to parse in the next audit."
    if "fact density" in action_text or "data points" in action_text or "entities" in action_text:
        return "Increase the number of specific proof points AI systems can cite instead of forcing them to summarize vague marketing copy."
    if "answer block" in action_text or "self-containment" in action_text or "extracted" in action_text:
        return "Make priority answers easier to quote correctly even when an AI system pulls them out of surrounding page context."
    if any(token in action_text for token in ("entity", "profile", "wikidata", "authority")):
        return "Strengthen the brand's authority signals so answer engines can connect the company to its services more confidently."
    if any(token in action_text for token in ("answer-first", "citations", "citability")):
        return "Improve quote-ready passages and raise citation readiness on the highest-value pages."
    if "security" in action_text:
        return "Reduce avoidable technical risk while preserving crawl and rendering stability."
    if any(token in action_text for token in ("high-intent user questions", "recurring ai-native content")):
        return "Build a repeatable publishing motion around the service questions the audit surfaced most often."
    if "track ai visibility" in action_text or "kpis" in action_text:
        return "Create a repeatable measurement loop for citations, referral traffic, and assisted conversion impact."
    return "Track the before/after metric tied to this action in the next comparable run."


def _legacy_action_theme(action: Mapping[str, Any]) -> str:
    action_text = _normalized_text(action.get("action"))
    if "llms" in action_text:
        return "llms_guidance"
    if "heading" in action_text or "single h1" in action_text:
        return "heading_structure"
    if any(token in action_text for token in ("entity", "profile", "wikidata", "authority")):
        return "entity_authority"
    if "fact density" in action_text or "data points" in action_text or "entities" in action_text:
        return "content_proof_density"
    if "answer block" in action_text or "self-containment" in action_text or "extracted" in action_text:
        return "content_extractability"
    if any(token in action_text for token in ("questions directly", "recurring ai-native content")):
        return "content_question_coverage"
    if any(token in action_text for token in ("answer-first", "citations", "citability")):
        return "content_citability"
    if "content-security-policy" in action_text or "security headers" in action_text:
        return "technical_hardening"
    if "track ai visibility" in action_text or "kpis" in action_text:
        return "measurement_loop"
    return action_text or "action"


def _is_generic_expected_outcome(value: Any) -> bool:
    text = _normalized_text(value)
    if not text:
        return True
    generic_markers = (
        "track the before/after metric tied to this action",
        "track the before/after metric tied to this finding",
        "re-measure ai citability, cited passages, ai referral traffic, and assisted conversions after the content refresh.",
        "if published, monitor crawler access logs and any downstream citation or referral changes rather than expecting ranking movement by itself.",
        "verify one h1 per priority page, then track changes in engagement, excerpt quality, and citation pickup.",
    )
    return any(marker in text for marker in generic_markers)


def _normalize_action_row(action: Mapping[str, Any], adjudication: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    row = dict(action)
    row["time_horizon"] = label
    row["owner"] = _legacy_action_owner(row)
    if _is_generic_expected_outcome(row.get("expected_outcome")):
        row["expected_outcome"] = _legacy_action_expected_outcome(row)
    row["visible_reason"] = _bridge_action_visible_reason(row, adjudication)
    return row


def _has_finding_section(findings: list[dict[str, Any]], section_name: str) -> bool:
    normalized_section = _normalized_text(section_name)
    return any(_normalized_text(item.get("section")) == normalized_section for item in findings)


def _page_fetch_risk(report_input: Mapping[str, Any]) -> dict[str, Any]:
    page_data = _mapping(_audit_data(report_input).get("page_data"))
    evidence_item: dict[str, Any] = {}
    if not page_data:
        for item in _evidence_items(report_input):
            if _normalized_text(item.get("evidence_type")) == "page_fetch":
                page_data = _mapping(item.get("raw_observation"))
                if page_data:
                    evidence_item = dict(item)
                    break
    else:
        for item in _evidence_items(report_input):
            if _normalized_text(item.get("evidence_type")) == "page_fetch":
                evidence_item = dict(item)
                break
    html_bytes_raw = page_data.get("html_bytes")
    try:
        html_bytes = int(html_bytes_raw)
    except (TypeError, ValueError):
        html_bytes = 0
    if html_bytes <= 0:
        return {}

    html_kb = round(html_bytes / 1024)
    html_mb = html_bytes / (1024 * 1024)
    meta_tags = _mapping(page_data.get("meta_tags"))
    h1_tags = _sequence(page_data.get("h1_tags"))
    structured_data = _sequence(page_data.get("structured_data"))
    risk_flags: list[str] = []
    if not _string(page_data.get("canonical")):
        risk_flags.append("canonical")
    if not _string(page_data.get("title")):
        risk_flags.append("title")
    if not _string(meta_tags.get("description")):
        risk_flags.append("description")
    if not structured_data:
        risk_flags.append("structured data")
    if len(h1_tags) != 1:
        risk_flags.append("heading structure")

    if html_bytes >= 1_500_000:
        note = (
            f"Homepage HTML is about {html_kb:,} KB ({html_mb:.2f} MB) and approaches the documented 2 MB HTML fetch limit "
            "Google describes for Googlebot. Keep critical elements such as the title, canonical, description, "
            "structured data, and answer-first content early in the document."
        )
        visible_reason = (
            f"The homepage HTML approaches Google's documented HTML fetch cutoff at about {html_kb:,} KB "
            f"({html_mb:.2f} MB)."
        )
        if risk_flags:
            visible_reason += (
                " The current page also shows weaker coverage for "
                + ", ".join(risk_flags)
                + "."
            )
        return {
            "status": "high",
            "note": note,
            "visible_reason": visible_reason,
            "marketing_action": (
                "Keep critical elements and answer-first copy near the top of the document so important signals are not pushed "
                "toward Google's fetch cutoff."
            ),
            "engineering_action": (
                "Reduce inline HTML weight, simplify repeated template markup, and move bulky CSS or JavaScript out of the initial "
                "document where practical."
            ),
            "evidence_items": [evidence_item] if evidence_item else [],
        }

    note = (
        f"Homepage HTML is about {html_kb:,} KB ({html_mb:.2f} MB), which stays well below the documented 2 MB HTML fetch limit "
        "Google describes for Googlebot. This is a supporting technical check rather than a core GEO score factor."
    )
    return {
        "status": "low",
        "note": note,
        "evidence_items": [evidence_item] if evidence_item else [],
    }


def _prompt_proof_finding(
    adjudication: Mapping[str, Any],
    evidence_by_type: Mapping[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    prompt_section = _mapping(adjudication.get("prompt_proof"))
    status = _string(prompt_section.get("status")) or "omitted"
    if status == "decision-grade":
        return None
    prompt_items = list(evidence_by_type.get("prompt_proof", []))
    sampled_query_items = [
        item
        for item in prompt_items
        if _normalized_text(_mapping(item.get("raw_observation")).get("capture_mode"))
        == "sampled_query_bridge"
    ]
    summary = _string(prompt_section.get("reason")) or "Prompt proof was not captured."
    if sampled_query_items:
        summary = (
            f"Sampled query evidence exists for {len(sampled_query_items)} query theme(s), "
            "but exact prompt and answer capture is still partial."
        )
    supporting_evidence: list[str] = []
    for item in prompt_items[:3]:
        raw = _mapping(item.get("raw_observation"))
        query = _string(raw.get("query_or_prompt")) or _string(item.get("query_theme"))
        platform = _string(raw.get("platform")) or _string(item.get("platform"))
        winning_urls = ", ".join(_sequence(raw.get("winning_urls"))[:2])
        if query or platform:
            line = " | ".join(
                part for part in (
                    f"Platform: {platform}" if platform else "",
                    f"Prompt/query: {query}" if query else "",
                    f"Winning URLs: {winning_urls}" if winning_urls else "",
                )
                if part
            )
            if line:
                supporting_evidence.append(line)
    return {
        "section": "prompt_proof",
        "status": status,
        "summary": summary,
        "visible_reason": _visible_reason(prompt_section),
        "leadership_impact": (
            "This gives the team a directional read on visibility gaps, but it is still weaker than direct platform captures."
            if sampled_query_items
            else "Direct prompt and answer capture is still missing, so this section should stay cautious."
        ),
        "marketing_action": (
            "Capture exact prompts, answer snippets, and cited URLs for the highest-value themes."
            if sampled_query_items
            else "Capture exact prompts, answer snippets, and cited URLs before treating this as proof-grade."
        ),
        "engineering_action": "",
        "confidence": "low",
        "confidence_reason": (
            "This section still relies on sampled query evidence instead of direct platform captures."
            if sampled_query_items
            else "This section has no direct platform captures yet, so it should stay low-confidence."
        ),
        "success_metric": "Capture exact prompts, answer text, and cited URLs for priority themes so this section can move to decision-grade.",
        "limitations": (
            "This is still based on sampled query evidence rather than exact prompt and answer captures."
            if sampled_query_items
            else "This section is missing exact prompt, answer, and cited-URL captures in this run."
        ),
        "supporting_evidence": _dedupe_strings(supporting_evidence),
        "evidence_items": prompt_items[:3],
    }


def _score_explanations(report_input: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping(report_input.get("manifest"))
    adjudication = _mapping(report_input.get("adjudication"))
    evidence = _mapping(report_input.get("evidence"))
    audit_data = _audit_data(report_input)
    return {
        "title": "Score Explanations",
        "plain_english_note": (
            "Scores are a guide, not proof. Sections are labeled decision-grade, directional, or omitted so weak samples stay visible."
        ),
        "terms": [
            {
                "label": "How much to trust this",
                "plain_english": "A short read on how confident we should be in the current run.",
            },
            {
                "label": "Prompt proof",
                "plain_english": "Saved examples of the exact prompts, answer text, and cited URLs used to validate an AI visibility claim.",
            },
            {
                "label": "Decision-grade",
                "plain_english": "The evidence is strong enough to support a client-facing claim.",
            },
            {
                "label": "Directional",
                "plain_english": "The signal is useful, but the sample is still partial.",
            },
            {
                "label": "Omitted",
                "plain_english": "There was not enough proof to make the section look stronger than it is.",
            },
            {
                "label": "Evidence class",
                "plain_english": "The source type behind a claim, such as live site checks or internal scoring.",
            },
            {
                "label": "Citability",
                "plain_english": "How easy a page is for an AI system to quote, summarize, and attribute accurately.",
            },
            {
                "label": "E-E-A-T",
                "plain_english": "Experience, expertise, authoritativeness, and trustworthiness in the content and brand presentation.",
            },
            {
                "label": "llms.txt",
                "plain_english": "An optional machine-readable file some platforms may consult, but not a substitute for strong pages and crawl access.",
            },
        ],
        "weighting": [
            {
                "label": "Evidence completeness",
                "why_it_matters": "Weak samples should stay directional or omitted instead of being overstated.",
            },
            {
                "label": "Visible reasons",
                "why_it_matters": "Every downgraded section should explain itself in plain English.",
            },
            {
                "label": "Bridge mode",
                "why_it_matters": "This V2 run reuses V1 scoring outputs as inputs, then applies stricter evidence gating on top.",
            },
        ],
        "scorecard": _scorecard_rows(audit_data),
        "score_provenance": "Bridge mode reuses the V1 live-audit score outputs and labels them as explanatory inputs inside V2.",
        "run_context": {
            "mode": _string(manifest.get("mode")) or "script-only",
            "evidence_items": len(_sequence(evidence.get("items"))),
            "adjudicated_sections": list(adjudication.keys()),
            "score_provenance": "v1-bridge",
        },
    }


def _priority_findings(report_input: Mapping[str, Any]) -> dict[str, Any]:
    adjudication = _mapping(report_input.get("adjudication"))
    evidence_items = _evidence_items(report_input)
    audit_data = _audit_data(report_input)
    business_profile = _business_profile(report_input)
    evidence_by_type: dict[str, list[dict[str, Any]]] = {}
    for item in evidence_items:
        evidence_type = _string(item.get("evidence_type")) or "unknown"
        evidence_by_type.setdefault(evidence_type, []).append(item)

    findings: list[dict[str, Any]] = []
    for finding in _sequence(audit_data.get("findings")):
        if not isinstance(finding, Mapping):
            continue
        title = _string(finding.get("title")) or "Finding"
        matching_evidence = [
            item
            for item in evidence_by_type.get("finding", [])
            if _normalized_text(_mapping(item.get("raw_observation")).get("title")) == _normalized_text(title)
        ]
        theme = _finding_theme(finding)
        matching_evidence = _dedupe_evidence_items(
            matching_evidence + _related_finding_evidence(theme, evidence_by_type)
        )
        matching_evidence = sorted(matching_evidence, key=_supporting_evidence_sort_key)
        supporting_evidence = _finding_supporting_evidence(report_input, finding, matching_evidence)
        confidence = _finding_confidence(theme, supporting_evidence, _string(finding.get("severity")))
        claim_source_class = _finding_claim_source_class(theme, matching_evidence)
        evidence_grade = _finding_evidence_grade(claim_source_class, confidence, matching_evidence)
        findings.append(
            {
                "section": title,
                "theme": theme,
                "status": _string(finding.get("severity")) or "medium",
                "summary": _clean_legacy_language(_string(finding.get("summary")) or _string(finding.get("description"))),
                "visible_reason": _clean_legacy_language(_string(finding.get("observed_evidence")) or _string(finding.get("leadership_impact"))),
                "leadership_impact": _clean_legacy_language(_string(finding.get("leadership_impact"))),
                "marketing_action": _clean_legacy_language(_string(finding.get("marketing_action"))),
                "engineering_action": _clean_legacy_language(_string(finding.get("developer_action"))),
                "claim_source_class": claim_source_class,
                "evidence_grade": evidence_grade,
                "what_upgrades_this": _finding_what_upgrades_this(theme, claim_source_class),
                "confidence": confidence,
                "confidence_reason": _finding_confidence_reason(theme, confidence),
                "success_metric": _finding_success_metric(theme, _string(business_profile.get("key"))),
                "limitations": _finding_limitations(theme),
                "supporting_evidence": supporting_evidence,
                "evidence_items": matching_evidence,
            }
        )

    prompt_proof_finding = _prompt_proof_finding(adjudication, evidence_by_type)
    if prompt_proof_finding and not _has_finding_section(findings, "prompt_proof"):
        findings.append(prompt_proof_finding)

    fetch_risk = _page_fetch_risk(report_input)
    if (
        fetch_risk
        and _normalized_text(fetch_risk.get("status")) == "high"
        and not _has_finding_section(findings, "fetch_render_risk")
    ):
        findings.append(
            {
                "section": "fetch_render_risk",
                "status": "medium",
                "summary": (
                    "The homepage HTML is large enough that Google-specific fetch limits become a practical technical risk."
                ),
                "visible_reason": _string(fetch_risk.get("visible_reason")),
                "leadership_impact": (
                    "This is not a headline GEO factor, but it can weaken crawl visibility if critical signals land too late in the HTML."
                ),
                "marketing_action": _string(fetch_risk.get("marketing_action")),
                "engineering_action": _string(fetch_risk.get("engineering_action")),
                "confidence": "high",
                "confidence_reason": "This finding comes from direct page-fetch evidence in the current run.",
                "success_metric": "Reduce initial HTML weight and confirm critical signals stay early in the fetched HTML.",
                "limitations": _finding_limitations("technical_hardening"),
                "supporting_evidence": _dedupe_strings(
                    [
                        _string(fetch_risk.get("visible_reason")),
                        _string(fetch_risk.get("note")),
                    ]
                ),
                "evidence_items": _sequence(fetch_risk.get("evidence_items")),
            }
        )

    if not findings:
        for section_name in ("benchmark", "prompt_proof", "platform_breakdown", "change_since_last_run"):
            section = _mapping(adjudication.get(section_name))
            status = _string(section.get("status")) or "omitted"
            reason = _string(section.get("reason")) or "No reason recorded."
            warning = _string(section.get("warning"))
            evidence_types = SECTION_EVIDENCE_TYPES.get(section_name, ())
            section_evidence: list[dict[str, Any]] = []
            for evidence_type in evidence_types:
                section_evidence.extend(evidence_by_type.get(evidence_type, []))
            findings.append(
                {
                    "section": section_name,
                    "status": status,
                    "summary": reason,
                    "visible_reason": warning or reason,
                    "confidence": "low",
                    "confidence_reason": "This fallback section exists to make missing evidence visible rather than overstate certainty.",
                    "success_metric": "Capture direct evidence for this section in the next comparable run.",
                    "limitations": "This section is shown as a placeholder because stronger evidence was not available in this run.",
                    "supporting_evidence": _dedupe_strings(
                        [item.get("normalized_summary") for item in section_evidence]
                    ),
                    "evidence_items": section_evidence,
                }
            )

    return {
        "title": "Priority Findings",
        "findings": findings,
    }


def _competitive_benchmark(report_input: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping(report_input.get("manifest"))
    adjudication = _mapping(report_input.get("adjudication")).get("benchmark", {})
    benchmark_section = _mapping(_client_sections(report_input).get("competitive_benchmark"))
    legacy_benchmark = _mapping(_legacy_sections(report_input).get("competitor_visibility"))
    if not isinstance(adjudication, Mapping):
        adjudication = {}
    if benchmark_section:
        status = _string(adjudication.get("status")) or "omitted"
        return {
            "title": "Competitive Benchmark",
            "status": status,
            "reason": _string(benchmark_section.get("summary")) or _string(adjudication.get("reason")) or "No benchmark reason was recorded.",
            "visible_reason": _visible_reason(adjudication),
            "competitors": [] if status == "omitted" else (_sequence(benchmark_section.get("competitor_set")) or _sequence(manifest.get("competitors"))),
            "sample_scope": {} if status == "omitted" else _mapping(benchmark_section.get("sample_scope")),
            "benchmark_rows": [] if status == "omitted" else _sequence(benchmark_section.get("benchmark_rows")),
            "sample_note": (
                "This is a partial crawl sample only; no competitor winners were captured."
                if status == "omitted"
                else _string(benchmark_section.get("summary"))
                or "This section stays conservative until named competitors, sampled queries, and winners are captured."
            ),
        }
    if legacy_benchmark:
        summary = _mapping(legacy_benchmark.get("summary"))
        status = _string(adjudication.get("status")) or "omitted"
        return {
            "title": "Competitive Benchmark",
            "status": status,
            "reason": _string(summary.get("discovery_note")) or _string(adjudication.get("reason")) or "No benchmark reason was recorded.",
            "visible_reason": _visible_reason(adjudication),
            "competitors": [] if status == "omitted" else (_sequence(legacy_benchmark.get("competitors")) or _sequence(manifest.get("competitors"))),
            "sample_scope": (
                {}
                if status == "omitted"
                else {
                    "query_count": len(_sequence(_audit_data(report_input).get("query_clusters"))),
                    "date_range": _string(_audit_data(report_input).get("date")),
                    "locale": _string(manifest.get("locale")),
                    "sample_completeness": "partial",
                }
            ),
            "benchmark_rows": [] if status == "omitted" else _sequence(legacy_benchmark.get("competitors")),
            "sample_note": (
                "This is a partial crawl sample only; no competitor winners were captured."
                if status == "omitted"
                else _string(summary.get("discovery_note"))
                or "The competitive picture is still incomplete in this sample."
            ),
        }
    return {
        "title": "Competitive Benchmark",
        "status": _string(adjudication.get("status")) or "omitted",
        "reason": _string(adjudication.get("reason")) or "No benchmark reason was recorded.",
        "visible_reason": _visible_reason(adjudication),
        "competitors": _sequence(manifest.get("competitors")),
        "sample_note": (
            "This section stays conservative until named competitors, sampled queries, and winners are captured."
        ),
    }


def _platform_breakdown(report_input: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping(report_input.get("manifest"))
    adjudication = _mapping(report_input.get("adjudication")).get("platform_breakdown", {})
    platform_section = _mapping(_client_sections(report_input).get("platform_breakdown"))
    legacy_technical = _mapping(_legacy_sections(report_input).get("technical_geo_gates"))
    control_matrix = _platform_control_matrix(report_input)
    measurement_summary = _platform_measurement_summary_by_platform(report_input)
    if not isinstance(adjudication, Mapping):
        adjudication = {}
    if platform_section:
        platforms = _attach_platform_measurement(
            _attach_platform_controls(
                _with_curated_platform_sources(
                    _sequence(platform_section.get("platforms")),
                    _sequence(manifest.get("platforms")),
                ),
                control_matrix,
            ),
            measurement_summary,
        )
        return {
            "title": "Platform Breakdown",
            "status": _string(adjudication.get("status")) or "omitted",
            "reason": _string(adjudication.get("reason")) or "No platform reason was recorded.",
            "visible_reason": _visible_reason(adjudication),
            "platforms": platforms,
            "control_matrix": control_matrix or _sequence(platform_section.get("control_matrix")),
            "sample_note": "Platform-specific claims stay directional until direct captures are available.",
        }
    legacy_summary = _mapping(legacy_technical.get("summary"))
    legacy_platforms = _sequence(legacy_summary.get("platforms"))
    if legacy_platforms:
        platform_rows: list[dict[str, Any]] = []
        for row in legacy_platforms:
            if not isinstance(row, Mapping):
                continue
            platform_name = _string(row.get("platform"))
            platform_rows.append(
                {
                    "platform": platform_name,
                    "documented_behavior": "Bridge mode reused legacy platform readiness output from V1.",
                    "observed_site_status": f"Legacy readiness score: {_string(row.get('score'))}.",
                    "observed_visibility_status": _string(row.get("status")) or "directional",
                    "cautious_inference": "This section is directional until direct prompt or answer captures are attached.",
                    "recommended_actions": [
                        "Review search, training, and user-fetch controls separately before changing access for this platform."
                    ],
                    "official_sources": sources_for_platform(platform_name),
                    "last_verified_at": _string(_audit_data(report_input).get("date")),
                    "confidence": "medium" if _string(row.get("status")) else "low",
                }
            )
        derived_control_matrix = control_matrix or [
            dict(control)
            for row in platform_rows
            for control in _sequence(row.get("control_rows"))
            if isinstance(control, Mapping)
        ]
        return {
            "title": "Platform Breakdown",
            "status": _string(adjudication.get("status")) or "omitted",
            "reason": _string(adjudication.get("reason")) or "Legacy platform readiness was captured from V1.",
            "visible_reason": _visible_reason(adjudication),
            "platforms": _attach_platform_measurement(
                _attach_platform_controls(platform_rows, derived_control_matrix),
                measurement_summary,
            ),
            "control_matrix": derived_control_matrix,
            "sample_note": "Platform-specific claims stay directional until direct captures are available.",
        }
    return {
        "title": "Platform Breakdown",
        "status": _string(adjudication.get("status")) or "omitted",
        "reason": _string(adjudication.get("reason")) or "No platform reason was recorded.",
        "visible_reason": _visible_reason(adjudication),
        "platforms": _attach_platform_measurement(
            _attach_platform_controls(
                _with_curated_platform_sources([], _sequence(manifest.get("platforms"))),
                control_matrix,
            ),
            measurement_summary,
        ),
        "control_matrix": control_matrix,
        "sample_note": "Platform-specific claims stay directional until direct captures are available.",
    }


def _page_source_evidence(report_input: Mapping[str, Any]) -> dict[str, Any]:
    page_source_section = _mapping(_client_sections(report_input).get("page_source_evidence"))
    evidence_items = []
    for item in _evidence_items(report_input):
        evidence_items.append(
            {
                "evidence_type": _string(item.get("evidence_type")),
                "source_class": _string(item.get("source_class")),
                "observed_vs_inferred": _string(item.get("observed_vs_inferred")),
                "summary": _string(item.get("normalized_summary")),
                "confidence": _string(item.get("confidence")),
            }
        )
    if page_source_section:
        return {
            "title": "Page And Source Evidence",
            "priority_pages": _sequence(page_source_section.get("priority_pages")),
            "source_domains": _sequence(page_source_section.get("source_domains")),
            "entity_signal_review": _mapping(page_source_section.get("entity_signal_review")),
            "evidence_items": evidence_items,
            "visible_reason": "The appendix lists the evidence ledger used to build the report.",
        }
    return {
        "title": "Page And Source Evidence",
        "evidence_items": evidence_items,
        "visible_reason": "The appendix lists the evidence ledger used to build the report.",
    }


def _platform_measurement_summary_by_platform(report_input: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for item in _evidence_items(report_input):
        if _string(item.get("evidence_type")) != "platform_measurement":
            continue
        raw = _mapping(item.get("raw_observation"))
        platform = _normalized_text(raw.get("platform") or item.get("platform"))
        if not platform:
            continue
        rows[platform] = raw
    return rows


def _attach_platform_measurement(
    platforms: list[Any],
    measurement_by_platform: Mapping[str, dict[str, Any]],
) -> list[Any]:
    enriched: list[Any] = []
    seen_platforms: set[str] = set()
    for item in platforms:
        if not isinstance(item, Mapping):
            enriched.append(item)
            continue
        row = dict(item)
        platform_key = _normalized_text(row.get("platform"))
        if platform_key:
            seen_platforms.add(platform_key)
        measurement_summary = dict(measurement_by_platform.get(platform_key, {}))
        if measurement_summary:
            row["measurement_summary"] = measurement_summary
            if not _string(row.get("observed_visibility_status")):
                parts: list[str] = []
                citation_count = _string(measurement_summary.get("citation_count"))
                grounding_query_count = _string(measurement_summary.get("grounding_query_count"))
                referral_visits = _string(measurement_summary.get("referral_visits"))
                if citation_count:
                    parts.append(f"{citation_count} citations")
                if grounding_query_count:
                    parts.append(f"{grounding_query_count} grounding queries")
                if referral_visits:
                    parts.append(f"{referral_visits} referral visits")
                if parts:
                    row["observed_visibility_status"] = "Measured " + ", ".join(parts) + "."
            if not _string(row.get("confidence")):
                row["confidence"] = "high"
        enriched.append(row)
    for platform_key, measurement_summary in measurement_by_platform.items():
        if platform_key in seen_platforms:
            continue
        enriched.append(
            {
                "platform": _string(measurement_summary.get("platform")),
                "observed_visibility_status": "Direct measurement captured in this run.",
                "confidence": "high",
                "measurement_summary": dict(measurement_summary),
                "official_sources": sources_for_platform(measurement_summary.get("platform")),
            }
        )
    return enriched


def _with_curated_platform_sources(platform_rows: list[Any], fallback_platforms: list[Any]) -> list[Any]:
    enriched: list[Any] = []
    for item in platform_rows:
        if isinstance(item, Mapping):
            row = dict(item)
            official_sources = _sequence(row.get("official_sources"))
            if not official_sources:
                row["official_sources"] = sources_for_platform(row.get("platform"))
            enriched.append(row)
            continue
        if _string(item):
            enriched.append(
                {
                    "platform": _string(item),
                    "official_sources": sources_for_platform(item),
                }
            )
    if enriched:
        return enriched
    return [
        {
            "platform": _string(item),
            "official_sources": sources_for_platform(item),
        }
        for item in fallback_platforms
        if _string(item)
    ]


def _platform_control_matrix(report_input: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _evidence_items(report_input):
        if _string(item.get("evidence_type")) != "platform_control":
            continue
        raw = _mapping(item.get("raw_observation"))
        if raw:
            rows.append(raw)
    if rows:
        return rows
    platform_section = _mapping(_client_sections(report_input).get("platform_breakdown"))
    return [
        dict(row)
        for row in _sequence(platform_section.get("control_matrix"))
        if isinstance(row, Mapping)
    ]


def _attach_platform_controls(platforms: list[Any], control_matrix: list[dict[str, Any]]) -> list[Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in control_matrix:
        grouped.setdefault(_normalized_text(row.get("platform")), []).append(dict(row))

    enriched: list[Any] = []
    for item in platforms:
        if not isinstance(item, Mapping):
            enriched.append(item)
            continue
        row = dict(item)
        existing_controls = [
            dict(control)
            for control in _sequence(row.get("control_rows"))
            if isinstance(control, Mapping)
        ]
        control_rows = existing_controls or grouped.get(_normalized_text(row.get("platform")), [])
        if control_rows:
            row["control_rows"] = control_rows
        if control_rows and not _string(row.get("observed_site_status")):
            row["observed_site_status"] = "; ".join(
                f"{_string(control.get('surface_label'))}: {_string(control.get('status'))}"
                for control in control_rows[:3]
                if _string(control.get("surface_label")) and _string(control.get("status"))
            )
        if control_rows and not _sequence(row.get("recommended_actions")):
            row["recommended_actions"] = _dedupe_strings(
                [
                    _string(control.get("recommendation"))
                    for control in control_rows
                    if _string(control.get("recommendation"))
                ]
            )[:2]
        enriched.append(row)
    return enriched


def _action_plan(report_input: Mapping[str, Any]) -> dict[str, Any]:
    adjudication = _mapping(report_input.get("adjudication"))
    action_plan_section = _mapping(_client_sections(report_input).get("action_plan_30_60_90"))
    legacy_execution = _mapping(_legacy_sections(report_input).get("execution_ledger"))
    business_profile = _business_profile(report_input)
    priority_findings = _sequence(_priority_findings(report_input).get("findings"))
    benchmark = _mapping(adjudication.get("benchmark"))
    prompt_proof = _mapping(adjudication.get("prompt_proof"))
    platform_breakdown = _mapping(adjudication.get("platform_breakdown"))
    change = _mapping(adjudication.get("change_since_last_run"))
    supplemental_actions: list[dict[str, Any]] = []
    seen_themes: set[str] = set()
    for horizon_key, label in (
        ("thirty_day", "30_days"),
        ("sixty_day", "60_days"),
        ("ninety_day", "90_days"),
    ):
        for item in _sequence(legacy_execution.get(horizon_key)):
            if not isinstance(item, Mapping):
                continue
            theme = _legacy_action_theme(item)
            if theme in seen_themes:
                continue
            seen_themes.add(theme)
            row = _normalize_action_row(item, adjudication, label=label)
            row = _profile_tuned_action(row, business_profile)
            row["action"] = _string(item.get("action"))
            supplemental_actions.append(row)
    website_actions = [
        _finding_to_website_action(report_input, finding, business_profile)
        for finding in priority_findings
        if isinstance(finding, Mapping)
        and _string(finding.get("theme")) in WEBSITE_ACTION_THEMES
        and (
            _string(finding.get("marketing_action"))
            or _string(finding.get("engineering_action"))
            or _sequence(finding.get("supporting_evidence"))
        )
    ]
    if website_actions:
        if len(website_actions) == 1:
            primary_finding = next(
                (
                    finding
                    for finding in priority_findings
                    if _string(_mapping(finding).get("theme")) == _string(website_actions[0].get("theme"))
                ),
                website_actions[0],
            )
            primary_action = _singleton_primary_action(website_actions[0], _mapping(primary_finding), report_input)
            return {
                "title": "Website Improvement Plan",
                "mode": "singleton",
                "primary_action": primary_action,
                "top_actions": [primary_action],
                "actions": [primary_action, *supplemental_actions],
                "supplemental_actions": supplemental_actions,
                "watchlist": _watchlist_items(priority_findings, _string(primary_action.get("theme"))),
            }
        groups: list[dict[str, Any]] = []
        seen_groups: set[str] = set()
        for action in website_actions:
            group_label = _string(action.get("surface_group")) or "Website Improvements"
            if group_label in seen_groups:
                continue
            seen_groups.add(group_label)
            groups.append(
                {
                    "label": group_label,
                    "actions": [
                        item
                        for item in website_actions
                        if _string(item.get("surface_group")) == group_label
                    ],
                }
            )
        result = {
            "title": "Website Improvement Plan",
            "mode": "multi_action",
            "top_actions": website_actions[:3],
            "groups": groups,
            "actions": website_actions,
        }
        if supplemental_actions:
            result["actions"] = website_actions + supplemental_actions
            result["supplemental_actions"] = supplemental_actions
        return result
    if _sequence(action_plan_section.get("actions")):
        actions: list[dict[str, Any]] = []
        seen_themes: set[tuple[str, str]] = set()
        for item in _sequence(action_plan_section.get("actions")):
            if not isinstance(item, Mapping):
                continue
            label = _string(item.get("time_horizon")) or "30_days"
            row = _normalize_action_row(item, adjudication, label=label)
            row = _profile_tuned_action(row, business_profile)
            theme = _legacy_action_theme(row)
            marker = (label, theme)
            if marker in seen_themes:
                continue
            seen_themes.add(marker)
            actions.append(row)
        return {
            "title": "Website Improvement Plan",
            "mode": "legacy",
            "actions": actions,
            "top_actions": actions[:3],
        }
    if legacy_execution:
        if supplemental_actions:
            return {
                "title": "Website Improvement Plan",
                "mode": "legacy",
                "actions": supplemental_actions,
                "top_actions": supplemental_actions[:3],
            }
    actions = [
        {
            "time_horizon": "30 days",
            "action": "Capture named competitor queries and exact answer snippets before upgrading benchmark claims.",
            "owner": "strategy",
            "expected_outcome": "Benchmark reporting becomes decision-grade instead of directional.",
            "visible_reason": _visible_reason(benchmark),
        },
        {
            "time_horizon": "60 days",
            "action": "Collect real prompt and platform captures so proof and platform sections can move beyond placeholders.",
            "owner": "marketing",
            "expected_outcome": "Prompt proof and platform breakdowns become more defensible.",
            "visible_reason": _visible_reason(prompt_proof) or _visible_reason(platform_breakdown),
        },
        {
            "time_horizon": "90 days",
            "action": "Define a repeatable comparison baseline so change-since-last-run can show real deltas.",
            "owner": "strategy",
            "expected_outcome": "Comparisons move from omitted to directional or decision-grade.",
            "visible_reason": _visible_reason(change),
        },
    ]
    actions = [_profile_tuned_action(action, business_profile) for action in actions]
    return {
        "title": "Website Improvement Plan",
        "mode": "legacy",
        "actions": actions,
        "top_actions": actions[:3],
    }


def _proof_appendix(report_input: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping(report_input.get("manifest"))
    evidence = _mapping(report_input.get("evidence"))
    adjudication = _mapping(report_input.get("adjudication"))
    comparison_context = _mapping(report_input.get("comparison_context"))
    technical_proof = _mapping(_client_sections(report_input).get("technical_proof_appendix"))
    legacy_methodology = _mapping(_client_sections(report_input).get("methodology"))
    legacy_technical = _mapping(_legacy_sections(report_input).get("technical_geo_gates"))
    crawler_access = _mapping(legacy_technical.get("crawler_access"))
    fallback_proof = {
        "methodology": {
            "summary": _string(legacy_methodology.get("summary"))
            or "Bridge mode reused the legacy V1 methodology and technical readiness outputs.",
        },
        "robots_and_bot_access": [
            f"{crawler} ({_string(info.get('platform'))}): {_string(info.get('status'))}. Recommendation: {_string(info.get('recommendation'))}"
            for crawler, info in crawler_access.items()
            if isinstance(info, Mapping)
        ],
        "limitations": {
            "limitations_note": _string(legacy_methodology.get("limitations"))
            or "Legacy V1 sections were bridged into V2, so direct prompt-proof remains limited in this run.",
        },
    }

    methodology = _mapping(technical_proof.get("methodology")) or _mapping(fallback_proof.get("methodology"))
    crawl_and_fetch_evidence = _sequence(technical_proof.get("crawl_and_fetch_evidence")) or _sequence(fallback_proof.get("crawl_and_fetch_evidence"))
    robots_and_bot_access = _sequence(technical_proof.get("robots_and_bot_access")) or _sequence(fallback_proof.get("robots_and_bot_access"))
    dom_and_heading_proof = _sequence(technical_proof.get("dom_and_heading_proof")) or _sequence(fallback_proof.get("dom_and_heading_proof"))
    schema_proof = _sequence(technical_proof.get("schema_proof")) or _sequence(fallback_proof.get("schema_proof"))
    source_inventory = _sequence(technical_proof.get("source_inventory")) or _sequence(fallback_proof.get("source_inventory"))
    limitations = _mapping(technical_proof.get("limitations")) or _mapping(fallback_proof.get("limitations"))
    fetch_risk = _page_fetch_risk(report_input)
    if fetch_risk:
        crawl_and_fetch_evidence = list(crawl_and_fetch_evidence)
        crawl_and_fetch_evidence.append(_string(fetch_risk.get("note")))
    official_sources = _sequence(technical_proof.get("official_sources")) or default_official_sources()
    evidence_completeness = _mapping(adjudication.get("evidence_completeness"))
    delta_summary = _mapping(comparison_context.get("delta_summary"))
    return {
        "title": "Proof Appendix",
        "manifest": manifest,
        "evidence_count": len(_sequence(evidence.get("items"))),
        "adjudication": adjudication,
        "evidence_completeness": evidence_completeness,
        "delta_summary": delta_summary,
        "change_since_last_run": delta_summary,
        "methodology": methodology,
        "crawl_and_fetch_evidence": crawl_and_fetch_evidence,
        "robots_and_bot_access": robots_and_bot_access,
        "dom_and_heading_proof": dom_and_heading_proof,
        "schema_proof": schema_proof,
        "source_inventory": source_inventory,
        "official_sources": official_sources,
        "bridge_warnings": _sequence(technical_proof.get("bridge_warnings")),
        "limitations": limitations,
        "visible_reason": "This appendix preserves the run scope, evidence ledger, and section reasons.",
    }


def _attach_action_references(
    priority_findings: Mapping[str, Any],
    action_plan: Mapping[str, Any],
) -> dict[str, Any]:
    findings = [dict(item) for item in _sequence(priority_findings.get("findings")) if isinstance(item, Mapping)]
    actions = [dict(item) for item in _sequence(action_plan.get("actions")) if isinstance(item, Mapping)]
    if not findings or not actions:
        return dict(priority_findings)
    by_theme: dict[str, dict[str, Any]] = {}
    for action in actions:
        theme = _string(action.get("theme"))
        if theme and theme not in by_theme:
            by_theme[theme] = action
    linked_findings: list[dict[str, Any]] = []
    for finding in findings:
        linked = dict(finding)
        related_action = by_theme.get(_string(finding.get("theme")))
        if related_action:
            linked["related_action_id"] = _string(related_action.get("action_id"))
            linked["related_action_title"] = _string(related_action.get("title"))
        linked_findings.append(linked)
    merged = dict(priority_findings)
    merged["findings"] = linked_findings
    return merged


def build_v2_report_sections(report_input: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(report_input)
    evidence = _mapping(payload.get("evidence"))
    adjudication = _mapping(payload.get("adjudication"))
    manifest = _mapping(payload.get("manifest"))
    audit_data = _audit_data(payload)
    evidence_count = len(_sequence(evidence.get("items")))
    section_statuses = [
        _section_status(_mapping(adjudication.get(section_name)))
        for section_name in ("benchmark", "prompt_proof", "platform_breakdown", "change_since_last_run")
    ]
    evidence_completeness = _mapping(adjudication.get("evidence_completeness"))
    completeness_value = _string(evidence_completeness.get("label")) or _trust_value(section_statuses)
    readiness_value = _readiness_value(audit_data)
    leadership_summary = [
        "The V2 report keeps the top layer short and the proof visible.",
    ]
    executive_summary = _string(audit_data.get("executive_summary"))
    if executive_summary:
        leadership_summary[0] = _clean_legacy_language(executive_summary.split(". ")[0].rstrip(".")) + "."
    geo_score = audit_data.get("geo_score")
    if geo_score is not None and "geo score" not in _normalized_text(executive_summary):
        leadership_summary.append(f"Bridged GEO score from the live audit: {geo_score}/100.")
    leadership_summary.append(
        "This version keeps the leadership layer short while pushing lower-confidence proof into later sections."
    )

    action_plan = _action_plan(payload)
    priority_findings = _attach_action_references(_priority_findings(payload), action_plan)
    sections = {
        "leadership_summary": {
            "title": "Leadership Summary",
            "status": _worst_status(section_statuses),
            "readiness_label": "Current GEO readiness",
            "readiness_value": readiness_value,
            "completeness_label": "Evidence completeness for this run",
            "completeness_value": completeness_value,
            "trust_label": "Evidence completeness for this run",
            "trust_value": completeness_value,
            "trust_note": (
                "This top-line trust label reflects benchmark, platform, prompt-proof, and change-comparison completeness. "
                "Page-level site findings can still be stronger than this overall label. Prompt proof means saved examples "
                "of the exact prompt, answer, and cited URL."
            ),
            "summary": leadership_summary[:3],
            "visible_reason": _most_severe_visible_reason(
                adjudication,
                ("benchmark", "prompt_proof", "platform_breakdown", "change_since_last_run"),
            ),
        },
        "score_explanations": _score_explanations(payload),
        "priority_findings": priority_findings,
        "competitive_benchmark": _competitive_benchmark(payload),
        "platform_breakdown": _platform_breakdown(payload),
        "page_source_evidence": _page_source_evidence(payload),
        "action_plan": action_plan,
        "proof_appendix": _proof_appendix(payload),
    }
    for section_name, section in sections.items():
        if not isinstance(section, dict):
            continue
        claim_source_class = _section_claim_source_class(section_name, payload)
        section["claim_source_class"] = claim_source_class
        section["evidence_grade"] = _evidence_grade_from_status(_string(section.get("status")))
        section["what_upgrades_this"] = _section_what_upgrades_this(section_name, claim_source_class)
    return {key: sections[key] for key in REPORT_SECTION_ORDER}
