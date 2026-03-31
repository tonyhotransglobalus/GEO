from __future__ import annotations

from typing import Any, Mapping


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
    for key, label in labels.items():
        if key in component_scores:
            rows.append(
                {
                    "label": label,
                    "score": component_scores[key],
                    "plain_english": "Bridge mode reuses this component from the V1 audit model.",
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
    if any(token in action_text for token in ("answer-first", "citations", "citability", "questions directly", "recurring ai-native content")):
        return "content_citability"
    if "content-security-policy" in action_text or "security headers" in action_text:
        return "technical_hardening"
    if "track ai visibility" in action_text or "kpis" in action_text:
        return "measurement_loop"
    return action_text or "action"


def _has_finding_section(findings: list[dict[str, Any]], section_name: str) -> bool:
    normalized_section = _normalized_text(section_name)
    return any(_normalized_text(item.get("section")) == normalized_section for item in findings)


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
        findings.append(
            {
                "section": title,
                "status": _string(finding.get("severity")) or "medium",
                "summary": _clean_legacy_language(_string(finding.get("summary")) or _string(finding.get("description"))),
                "visible_reason": _clean_legacy_language(_string(finding.get("observed_evidence")) or _string(finding.get("leadership_impact"))),
                "leadership_impact": _clean_legacy_language(_string(finding.get("leadership_impact"))),
                "marketing_action": _clean_legacy_language(_string(finding.get("marketing_action"))),
                "engineering_action": _clean_legacy_language(_string(finding.get("developer_action"))),
                "evidence_items": matching_evidence,
            }
        )

    prompt_proof_finding = _prompt_proof_finding(adjudication, evidence_by_type)
    if prompt_proof_finding and not _has_finding_section(findings, "prompt_proof"):
        findings.append(prompt_proof_finding)

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
    if not isinstance(adjudication, Mapping):
        adjudication = {}
    if platform_section:
        return {
            "title": "Platform Breakdown",
            "status": _string(adjudication.get("status")) or "omitted",
            "reason": _string(adjudication.get("reason")) or "No platform reason was recorded.",
            "visible_reason": _visible_reason(adjudication),
            "platforms": _sequence(platform_section.get("platforms")) or _sequence(manifest.get("platforms")),
            "sample_note": "Platform-specific claims stay directional until direct captures are available.",
        }
    legacy_summary = _mapping(legacy_technical.get("summary"))
    legacy_platforms = _sequence(legacy_summary.get("platforms"))
    if legacy_platforms:
        platform_rows: list[dict[str, Any]] = []
        crawler_access = _mapping(legacy_technical.get("crawler_access"))
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
                        _string(
                            next(
                                (
                                    info.get("recommendation")
                                    for crawler, info in crawler_access.items()
                                    if isinstance(info, Mapping)
                                    and _string(info.get("platform")).lower() in platform_name.lower()
                                ),
                                "",
                            )
                        )
                        or "Add direct platform captures before treating this section as decision-grade."
                    ],
                    "official_sources": [],
                    "last_verified_at": _string(_audit_data(report_input).get("date")),
                    "confidence": "medium" if _string(row.get("status")) else "low",
                }
            )
        return {
            "title": "Platform Breakdown",
            "status": _string(adjudication.get("status")) or "omitted",
            "reason": _string(adjudication.get("reason")) or "Legacy platform readiness was captured from V1.",
            "visible_reason": _visible_reason(adjudication),
            "platforms": platform_rows,
            "sample_note": "Platform-specific claims stay directional until direct captures are available.",
        }
    return {
        "title": "Platform Breakdown",
        "status": _string(adjudication.get("status")) or "omitted",
        "reason": _string(adjudication.get("reason")) or "No platform reason was recorded.",
        "visible_reason": _visible_reason(adjudication),
        "platforms": _sequence(manifest.get("platforms")),
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


def _action_plan(report_input: Mapping[str, Any]) -> dict[str, Any]:
    adjudication = _mapping(report_input.get("adjudication"))
    action_plan_section = _mapping(_client_sections(report_input).get("action_plan_30_60_90"))
    legacy_execution = _mapping(_legacy_sections(report_input).get("execution_ledger"))
    benchmark = _mapping(adjudication.get("benchmark"))
    prompt_proof = _mapping(adjudication.get("prompt_proof"))
    platform_breakdown = _mapping(adjudication.get("platform_breakdown"))
    change = _mapping(adjudication.get("change_since_last_run"))
    if _sequence(action_plan_section.get("actions")):
        actions: list[dict[str, Any]] = []
        for item in _sequence(action_plan_section.get("actions")):
            if not isinstance(item, Mapping):
                continue
            row = dict(item)
            row["visible_reason"] = _bridge_action_visible_reason(row, adjudication)
            actions.append(row)
        return {
            "title": "Action Plan",
            "actions": actions,
        }
    if legacy_execution:
        actions: list[dict[str, Any]] = []
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
                row = {
                    "time_horizon": label,
                    "action": _string(item.get("action")),
                    "owner": _legacy_action_owner(item),
                    "expected_outcome": _legacy_action_expected_outcome(item),
                    "visible_reason": _bridge_action_visible_reason(item, adjudication),
                }
                actions.append(row)
        if actions:
            return {
                "title": "Action Plan",
                "actions": actions,
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
    return {
        "title": "Action Plan",
        "actions": actions,
    }


def _proof_appendix(report_input: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping(report_input.get("manifest"))
    evidence = _mapping(report_input.get("evidence"))
    adjudication = _mapping(report_input.get("adjudication"))
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
    return {
        "title": "Proof Appendix",
        "manifest": manifest,
        "evidence_count": len(_sequence(evidence.get("items"))),
        "adjudication": adjudication,
        "methodology": methodology,
        "crawl_and_fetch_evidence": crawl_and_fetch_evidence,
        "robots_and_bot_access": robots_and_bot_access,
        "dom_and_heading_proof": dom_and_heading_proof,
        "schema_proof": schema_proof,
        "source_inventory": source_inventory,
        "bridge_warnings": _sequence(technical_proof.get("bridge_warnings")),
        "limitations": limitations,
        "visible_reason": "This appendix preserves the run scope, evidence ledger, and section reasons.",
    }


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
    leadership_summary = [
        "The V2 report keeps the top layer short and the proof visible.",
    ]
    executive_summary = _string(audit_data.get("executive_summary"))
    if executive_summary:
        leadership_summary[0] = _clean_legacy_language(executive_summary.split(". ")[0].rstrip(".")) + "."
    geo_score = audit_data.get("geo_score")
    if geo_score is not None and "geo score" not in _normalized_text(executive_summary):
        leadership_summary.append(f"Bridged GEO score from the live audit: {geo_score}/100.")
    else:
        leadership_summary.append(f"Run mode: {_string(manifest.get('mode')) or 'script-only'}.")
    leadership_summary.append(f"Evidence items captured: {evidence_count}.")

    sections = {
        "leadership_summary": {
            "title": "Leadership Summary",
            "status": _worst_status(section_statuses),
            "trust_label": "How much to trust this",
            "trust_value": _trust_value(section_statuses),
            "summary": leadership_summary[:3],
            "visible_reason": _most_severe_visible_reason(
                adjudication,
                ("benchmark", "prompt_proof", "platform_breakdown", "change_since_last_run"),
            ),
        },
        "score_explanations": _score_explanations(payload),
        "priority_findings": _priority_findings(payload),
        "competitive_benchmark": _competitive_benchmark(payload),
        "platform_breakdown": _platform_breakdown(payload),
        "page_source_evidence": _page_source_evidence(payload),
        "action_plan": _action_plan(payload),
        "proof_appendix": _proof_appendix(payload),
    }
    return {key: sections[key] for key in REPORT_SECTION_ORDER}
