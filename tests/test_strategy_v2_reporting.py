from scripts.strategy_engine_v2.reporting import build_v2_report_sections
from scripts.strategy_engine_v2.evidence import build_v2_evidence_ledger
from scripts.strategy_engine_v2.adjudication import adjudicate_v2_sections
from tests.strategy_v2_samples import sample_v1_audit_payload


def test_v2_report_contains_expected_sections():
    sections = build_v2_report_sections({
        "manifest": {"mode": "script-only"},
        "evidence": {"items": [{"evidence_type": "run_manifest"}]},
        "adjudication": {
            "benchmark": {"status": "directional", "reason": "Benchmark is thin.", "warning": "Benchmark is directional because the sample is incomplete."},
            "prompt_proof": {"status": "omitted", "reason": "No useful prompt proof was captured.", "warning": "Prompt proof is omitted because exact prompts or winner URLs were not captured."},
            "platform_breakdown": {"status": "decision-grade", "reason": "Platform read is strong.", "warning": ""},
            "change_since_last_run": {"status": "omitted", "reason": "Comparison is not valid for this run.", "warning": "Change-since-last-run is omitted because the runs are not comparable."},
        },
    })
    assert list(sections.keys()) == [
        "leadership_summary",
        "score_explanations",
        "priority_findings",
        "competitive_benchmark",
        "platform_breakdown",
        "page_source_evidence",
        "action_plan",
        "proof_appendix",
    ]


def test_v2_report_surfaces_worst_reason_in_leadership_summary():
    sections = build_v2_report_sections({
        "manifest": {"mode": "script-only"},
        "evidence": {"items": [{"evidence_type": "run_manifest"}]},
        "adjudication": {
            "benchmark": {"status": "directional", "reason": "Benchmark is thin.", "warning": "Benchmark is directional because the sample is incomplete."},
            "prompt_proof": {"status": "omitted", "reason": "No useful prompt proof was captured.", "warning": "Prompt proof is omitted because exact prompts or winner URLs were not captured."},
            "platform_breakdown": {"status": "decision-grade", "reason": "Platform read is strong.", "warning": ""},
            "change_since_last_run": {"status": "omitted", "reason": "Comparison is not valid for this run.", "warning": "Change-since-last-run is omitted because the runs are not comparable."},
            "evidence_completeness": {"score": 50, "label": "Medium", "reason": "This run captured some direct evidence, but important proof layers are still partial."},
        },
        "audit_data": {"geo_score": 82},
    })

    summary = sections["leadership_summary"]
    assert summary["readiness_label"] == "Current GEO readiness"
    assert summary["readiness_value"] == "High"
    assert summary["completeness_label"] == "Evidence completeness for this run"
    assert summary["completeness_value"] == "Medium"
    assert summary["trust_label"] == "Evidence completeness for this run"
    assert summary["trust_value"] == "Medium"
    assert summary["visible_reason"] == "Prompt proof is omitted because exact prompts or winner URLs were not captured."
    assert "page-level site findings" in summary["trust_note"].lower()
    assert "prompt proof" in summary["trust_note"].lower()
    assert len(summary["summary"]) <= 3


def test_v2_report_surfaces_evidence_completeness_in_proof_appendix():
    sections = build_v2_report_sections(
        {
            "manifest": {"mode": "script-only"},
            "evidence": {"items": [{"evidence_type": "run_manifest"}]},
            "adjudication": {
                "benchmark": {"status": "directional", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "decision-grade", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
                "evidence_completeness": {
                    "score": 50,
                    "label": "Medium",
                    "reason": "This run captured some direct evidence, but important proof layers are still partial.",
                },
            },
            "audit_data": {"geo_score": 64},
        }
    )

    appendix = sections["proof_appendix"]
    assert appendix["evidence_completeness"]["score"] == 50
    assert appendix["evidence_completeness"]["label"] == "Medium"
    assert "proof layers" in appendix["evidence_completeness"]["reason"].lower()


def test_v2_report_surfaces_visible_reasons_for_downgraded_sections():
    sections = build_v2_report_sections({
        "manifest": {"mode": "script-only"},
        "evidence": {"items": [{"evidence_type": "run_manifest"}]},
        "adjudication": {
            "benchmark": {"status": "directional", "reason": "Benchmark is thin.", "warning": "Benchmark is directional because the sample is incomplete."},
            "prompt_proof": {"status": "omitted", "reason": "No useful prompt proof was captured.", "warning": "Prompt proof is omitted because exact prompts or winner URLs were not captured."},
            "platform_breakdown": {"status": "omitted", "reason": "Platform-level evidence was not captured.", "warning": "Platform breakdown is omitted because sampled platforms were not captured."},
            "change_since_last_run": {"status": "omitted", "reason": "Comparison is not valid for this run.", "warning": "Change-since-last-run is omitted because the runs are not comparable."},
        },
    })

    assert sections["competitive_benchmark"]["visible_reason"] == "Benchmark is directional because the sample is incomplete."
    assert sections["platform_breakdown"]["visible_reason"] == "Platform breakdown is omitted because sampled platforms were not captured."
    assert sections["proof_appendix"]["visible_reason"]


def test_v2_report_explains_prompt_proof_in_glossary():
    sections = build_v2_report_sections({
        "manifest": {"mode": "script-only"},
        "evidence": {"items": [{"evidence_type": "run_manifest"}]},
        "adjudication": {
            "benchmark": {"status": "directional", "reason": "Benchmark is thin.", "warning": "Benchmark is directional because the sample is incomplete."},
            "prompt_proof": {"status": "omitted", "reason": "No useful prompt proof was captured.", "warning": "Prompt proof is omitted because exact prompts or winner URLs were not captured."},
            "platform_breakdown": {"status": "decision-grade", "reason": "Platform read is strong.", "warning": ""},
            "change_since_last_run": {"status": "omitted", "reason": "Comparison is not valid for this run.", "warning": "Change-since-last-run is omitted because the runs are not comparable."},
        },
    })

    prompt_proof_term = next(
        item
        for item in sections["score_explanations"]["terms"]
        if item["label"] == "Prompt proof"
    )
    assert "exact prompts" in prompt_proof_term["plain_english"].lower()
    assert "cited urls" in prompt_proof_term["plain_english"].lower()


def test_v2_report_reuses_v1_sections_when_bridge_data_exists():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "mode": "script-only",
        "platforms": ["ChatGPT", "Perplexity"],
        "competitors": ["competitor.com"],
        "comparison_eligibility": {"requested": True, "eligible": True},
    }
    audit_data = sample_v1_audit_payload()
    evidence = build_v2_evidence_ledger(manifest=manifest, audit_data=audit_data)
    adjudication = adjudicate_v2_sections(
        manifest=manifest,
        evidence=evidence,
        audit_data=audit_data,
    )

    sections = build_v2_report_sections({
        "manifest": manifest,
        "evidence": evidence,
        "adjudication": adjudication,
        "audit_data": audit_data,
    })

    assert sections["competitive_benchmark"]["sample_scope"]["query_count"] == 6
    assert sections["competitive_benchmark"]["benchmark_rows"][0]["competitor_name"] == "Competitor Co"
    assert sections["platform_breakdown"]["platforms"][0]["platform"] == "ChatGPT"
    assert sections["platform_breakdown"]["platforms"][0]["official_sources"]
    assert sections["page_source_evidence"]["priority_pages"][0]["page_url"] == "https://www.transglobalus.com/"
    first_action = sections["action_plan"]["actions"][0]
    assert first_action["title"] == "Make priority pages answer-first and quote-ready"
    assert "https://www.transglobalus.com/" in first_action["exact_location"]
    assert "https://www.transglobalus.com/" in first_action["page_scope"]
    assert "Homepage" in first_action["template_scope"]
    assert "CMS" in first_action["repo_surface"]
    assert first_action["exact_change"]
    assert first_action["acceptance_criteria"]


def test_v2_report_normalizes_client_action_plan_rows():
    payload = sample_v1_audit_payload()
    payload["client_report_sections"]["action_plan_30_60_90"] = {
        "actions": [
            {
                "time_horizon": "30_days",
                "action": "Rewrite key pages into answer-first blocks with facts, citations, and concise paragraphs.",
                "owner": "marketing",
                "expected_outcome": "Re-measure AI citability, cited passages, AI referral traffic, and assisted conversions after the content refresh.",
            },
            {
                "time_horizon": "30_days",
                "action": "Increase content self-containment; ensure 'Answer Blocks' remain accurate even when extracted from their surrounding context.",
                "owner": "marketing",
                "expected_outcome": "Track the before/after metric tied to this finding and confirm whether citations, referrals, or conversions improve.",
            },
            {
                "time_horizon": "30_days",
                "action": "Fact density is below GEO benchmarks. Target 1-2 specific entities or data points per 'Answer Block'.",
                "owner": "cross-functional",
                "expected_outcome": "Track the before/after metric tied to this finding and confirm whether citations, referrals, or conversions improve.",
            },
        ]
    }
    sections = build_v2_report_sections(
        {
            "manifest": {"mode": "script-only"},
            "evidence": {"items": [{"evidence_type": "run_manifest"}]},
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
            },
            "audit_data": payload,
        }
    )

    actions = sections["action_plan"]["actions"]
    assert len(actions) == 1
    assert actions[0]["exact_change"]
    assert actions[0]["acceptance_criteria"]
    assert actions[0]["verification_geo"]
    assert "quote-ready" in actions[0]["title"].lower()


def test_v2_report_uses_singleton_mode_when_one_website_fix_is_action_ready():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "mode": "script-only",
        "platforms": ["ChatGPT", "Perplexity"],
        "competitors": ["competitor.com"],
        "comparison_eligibility": {"requested": True, "eligible": True},
    }
    audit_data = sample_v1_audit_payload()
    evidence = build_v2_evidence_ledger(manifest=manifest, audit_data=audit_data)
    adjudication = adjudicate_v2_sections(
        manifest=manifest,
        evidence=evidence,
        audit_data=audit_data,
    )

    sections = build_v2_report_sections({
        "manifest": manifest,
        "evidence": evidence,
        "adjudication": adjudication,
        "audit_data": audit_data,
    })

    action_plan = sections["action_plan"]
    assert action_plan["mode"] == "singleton"
    primary_action = action_plan["primary_action"]
    assert primary_action["title"] == "Make priority pages answer-first and quote-ready"
    assert primary_action["why_this_is_the_lead_fix"]
    assert primary_action["proof_packet"]
    assert primary_action["rollout_sequence"]
    assert primary_action["success_metric"]
    assert action_plan["watchlist"]
    assert action_plan["watchlist"][0]["why_not_recommended_yet"]
    assert action_plan["watchlist"][0]["what_upgrades_this"]
    related_finding = next(
        item
        for item in sections["priority_findings"]["findings"]
        if item["section"] == "Key pages are not AI-citation ready"
    )
    assert related_finding["related_action_title"] == primary_action["title"]


def test_v2_report_merges_legacy_proof_with_bridge_warnings():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "mode": "script-only",
        "platforms": ["ChatGPT", "Perplexity"],
        "competitors": ["competitor.com"],
        "comparison_eligibility": {"requested": True, "eligible": True},
    }
    audit_data = sample_v1_audit_payload()
    audit_data["client_report_sections"]["technical_proof_appendix"] = {
        "bridge_warnings": [
            "DuckDuckGo keyword suggestions timed out for 'life insurance'."
        ]
    }
    audit_data["report_sections"] = {
        "technical_geo_gates": {
            "crawler_access": {
                "GPTBot": {
                    "platform": "OpenAI",
                    "status": "Allowed By Default",
                    "recommendation": "Keep accessible.",
                }
            }
        }
    }
    evidence = build_v2_evidence_ledger(manifest=manifest, audit_data=audit_data)
    adjudication = adjudicate_v2_sections(
        manifest=manifest,
        evidence=evidence,
        audit_data=audit_data,
    )

    sections = build_v2_report_sections({
        "manifest": manifest,
        "evidence": evidence,
        "adjudication": adjudication,
        "audit_data": audit_data,
    })

    proof_appendix = sections["proof_appendix"]
    assert proof_appendix["bridge_warnings"] == [
        "DuckDuckGo keyword suggestions timed out for 'life insurance'."
    ]
    assert proof_appendix["methodology"]["summary"]
    assert proof_appendix["robots_and_bot_access"]
    assert proof_appendix["official_sources"]
    assert any("openai" in item["title"].lower() for item in proof_appendix["official_sources"])


def test_v2_report_includes_curated_official_sources_for_platforms_and_appendix():
    sections = build_v2_report_sections(
        {
            "manifest": {
                "target_url": "https://www.transglobalus.com/",
                "mode": "script-only",
                "platforms": ["ChatGPT", "Perplexity", "Claude", "Google", "Bing"],
            },
            "evidence": {"items": [{"evidence_type": "run_manifest"}]},
            "adjudication": {
                "benchmark": {"status": "directional", "reason": "", "warning": ""},
                "prompt_proof": {"status": "directional", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "directional", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
            },
            "audit_data": sample_v1_audit_payload(),
        }
    )

    appendix_sources = sections["proof_appendix"]["official_sources"]
    assert any("Google Search AI features" == item["title"] for item in appendix_sources)
    assert any("OpenAI Publishers and Developers FAQ" == item["title"] for item in appendix_sources)
    assert any("Anthropic crawler guidance" == item["title"] for item in appendix_sources)
    assert any("Perplexity crawler guidance" == item["title"] for item in appendix_sources)
    assert any("Bing AI Performance" == item["title"] for item in appendix_sources)


def test_v2_report_surfaces_platform_control_matrix_by_surface():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "mode": "script-only",
        "platforms": ["ChatGPT", "Claude", "Perplexity", "Google"],
        "competitors": [],
        "comparison_eligibility": {"requested": False, "eligible": False},
    }
    audit_data = {
        "date": "2026-04-03",
        "geo_score": 64,
        "client_report_sections": {
            "platform_breakdown": {
                "platforms": [
                    {"platform": "ChatGPT", "observed_visibility_status": "Directional only in this run", "confidence": "low"},
                    {"platform": "Claude", "observed_visibility_status": "Directional only in this run", "confidence": "low"},
                    {"platform": "Perplexity", "observed_visibility_status": "Directional only in this run", "confidence": "low"},
                    {"platform": "Google", "observed_visibility_status": "Directional only in this run", "confidence": "medium"},
                ]
            }
        },
        "crawler_access": {
            "OAI-SearchBot": {"platform": "OpenAI", "status": "Allowed By Default", "recommendation": "Keep accessible."},
            "GPTBot": {"platform": "OpenAI", "status": "Blocked in robots.txt", "recommendation": "Keep blocked until training policy is defined."},
            "Claude-SearchBot": {"platform": "Anthropic", "status": "Allowed By Default", "recommendation": "Keep accessible."},
            "ClaudeBot": {"platform": "Anthropic", "status": "Blocked in robots.txt", "recommendation": "Allow only if training access is approved."},
            "Claude-User": {"platform": "Anthropic", "status": "Allowed By Default", "recommendation": "Review app fetch behavior separately."},
            "PerplexityBot": {"platform": "Perplexity", "status": "Allowed By Default", "recommendation": "Keep accessible."},
            "Perplexity-User": {"platform": "Perplexity", "status": "Review in WAF", "recommendation": "Allow app fetch traffic if users rely on Perplexity answers."},
            "Google-Extended": {"platform": "Google", "status": "Disallowed", "recommendation": "Keep blocked unless AI usage policy changes."},
        },
    }
    evidence = build_v2_evidence_ledger(manifest=manifest, audit_data=audit_data)

    sections = build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "directional", "reason": "Platform signals are partial.", "warning": "Platform breakdown is directional because platform coverage is limited."},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
                "evidence_completeness": {"score": 33, "label": "Low", "reason": "The run is still missing key direct captures."},
            },
            "audit_data": audit_data,
        }
    )

    chatgpt_row = next(
        item for item in sections["platform_breakdown"]["platforms"] if item["platform"] == "ChatGPT"
    )
    control_rows = chatgpt_row["control_rows"]

    assert {item["surface"] for item in control_rows} == {"search_bot", "training_bot", "user_fetch"}
    assert next(item for item in control_rows if item["bot_name"] == "OAI-SearchBot")["status"] == "Allowed"
    assert next(item for item in control_rows if item["bot_name"] == "GPTBot")["status"] == "Blocked"
    assert next(item for item in control_rows if item["surface"] == "user_fetch")["status"] == "Not observed"
    assert sections["platform_breakdown"]["control_matrix"]


def test_v2_report_surfaces_freshness_authorship_and_accessibility_in_page_evidence_and_findings():
    manifest = {
        "target_url": "https://www.transglobalus.com/insights/retirement-income/",
        "mode": "script-only",
        "platforms": [],
        "competitors": [],
        "comparison_eligibility": {"requested": False, "eligible": False},
    }
    audit_data = {
        "findings": [
            {
                "severity": "medium",
                "title": "Author Trust Signals Are Thin",
                "summary": "Priority pages do not clearly expose author credentials and freshness signals.",
                "leadership_impact": "Thin authorship and freshness cues can weaken trust in quoted answers.",
                "marketing_action": "Add visible bylines, bios, and update dates to expert pages.",
                "developer_action": "Keep author and date markup aligned with visible content.",
                "observed_evidence": "Author and freshness signals were partial on the audited page.",
            },
            {
                "severity": "medium",
                "title": "Rendered Accessibility Signals Are Partial",
                "summary": "Landmarks and rendered-state parity still look inconsistent on the audited page.",
                "leadership_impact": "This can make machine extraction and assistive interpretation less reliable.",
                "marketing_action": "Preserve critical content and CTA copy in the primary rendered state.",
                "developer_action": "Add landmarks and reduce hydration-only content gaps.",
                "observed_evidence": "Rendered accessibility signals were partial on the audited page.",
            },
        ],
    }
    evidence = build_v2_evidence_ledger(
        manifest=manifest,
        audit_data=audit_data,
        page_data={
            "title": "Retirement Income Planning",
            "byline": "Jane Doe, CFP",
            "author_pages": ["https://www.transglobalus.com/authors/jane-doe/"],
            "structured_data": [
                {
                    "@type": "Article",
                    "datePublished": "2026-03-01",
                    "dateModified": "2026-03-20",
                    "author": {"name": "Jane Doe, CFP"},
                }
            ],
            "aria_landmarks": ["banner", "navigation", "main", "contentinfo"],
            "rendered_state_parity": {
                "status": "partial",
                "summary": "Primary CTA only appears after hydration.",
            },
        },
    )

    sections = build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
                "evidence_completeness": {"score": 40, "label": "Medium", "reason": "This run captured some direct page evidence."},
            },
            "audit_data": audit_data,
        }
    )

    page_evidence_types = {
        item["evidence_type"] for item in sections["page_source_evidence"]["evidence_items"]
    }
    assert {"freshness_signal", "authorship_signal", "accessibility_signal"} <= page_evidence_types

    authorship_finding = next(
        item for item in sections["priority_findings"]["findings"] if item["section"] == "Author Trust Signals Are Thin"
    )
    accessibility_finding = next(
        item for item in sections["priority_findings"]["findings"] if item["section"] == "Rendered Accessibility Signals Are Partial"
    )

    assert any("Jane Doe" in line for line in authorship_finding["supporting_evidence"])
    assert any("2026-03-20" in line for line in authorship_finding["supporting_evidence"])
    assert any(line.startswith("Observed on ") for line in authorship_finding["supporting_evidence"])
    assert not any("internal score - inferred" in line.lower() for line in authorship_finding["supporting_evidence"])
    assert any("hydration" in line.lower() or "landmarks" in line.lower() for line in accessibility_finding["supporting_evidence"])
    assert any(line.startswith("Observed on ") for line in accessibility_finding["supporting_evidence"])


def test_v2_report_prefers_contract_hardened_observed_support_for_author_trust():
    manifest = {
        "target_url": "https://www.transglobalus.com/insights/retirement-income/",
        "mode": "script-only",
        "platforms": [],
        "competitors": [],
        "comparison_eligibility": {"requested": False, "eligible": False},
    }
    audit_data = {
        "date": "2026-04-08",
        "findings": [
            {
                "severity": "medium",
                "title": "Author Trust Signals Are Thin",
                "summary": "Priority pages do not clearly expose author credentials and freshness signals.",
                "leadership_impact": "Thin authorship and freshness cues can weaken trust in quoted answers.",
                "marketing_action": "Add visible bylines, bios, and update dates to expert pages.",
                "developer_action": "Keep author and date markup aligned with visible content.",
                "observed_evidence": "Author and freshness signals were partial on the audited page.",
            }
        ],
    }
    evidence = build_v2_evidence_ledger(
        manifest=manifest,
        audit_data=audit_data,
        page_data={
            "title": "Retirement Income Planning",
            "byline": "Jane Doe, CFP",
            "author_pages": ["https://www.transglobalus.com/authors/jane-doe/"],
            "visible_dates": [
                {"text": "Updated March 20, 2026", "source": "page_header"}
            ],
            "structured_data": [
                {
                    "@type": "Article",
                    "datePublished": "2026-03-01",
                    "dateModified": "2026-03-20",
                    "author": {"name": "Jane Doe, CFP"},
                }
            ],
        },
    )

    sections = build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
                "evidence_completeness": {
                    "score": 40,
                    "label": "Medium",
                    "reason": "This run captured some direct page evidence.",
                },
            },
            "audit_data": audit_data,
        }
    )

    authorship_finding = next(
        item for item in sections["priority_findings"]["findings"] if item["section"] == "Author Trust Signals Are Thin"
    )

    assert authorship_finding["evidence_items"][0]["evidence_type"] == "authorship_signal"
    assert authorship_finding["evidence_items"][1]["evidence_type"] == "freshness_signal"
    assert any("Observed on https://www.transglobalus.com/insights/retirement-income/" in line for line in authorship_finding["supporting_evidence"])
    assert any("Updated March 20, 2026" in line for line in authorship_finding["supporting_evidence"])
    assert any("aligned" in line.lower() for line in authorship_finding["supporting_evidence"])


def test_v2_report_turns_conflicts_and_missing_author_pages_into_short_proof_lines():
    manifest = {
        "target_url": "https://www.transglobalus.com/insights/retirement-income/",
        "mode": "script-only",
        "platforms": [],
        "competitors": [],
        "comparison_eligibility": {"requested": False, "eligible": False},
    }
    audit_data = {
        "date": "2026-04-08",
        "findings": [
            {
                "severity": "medium",
                "title": "Author Trust Signals Are Thin",
                "summary": "Priority pages do not clearly expose author credentials and freshness signals.",
                "leadership_impact": "Thin authorship and freshness cues can weaken trust in quoted answers.",
                "marketing_action": "Add visible bylines, bios, and update dates to expert pages.",
                "developer_action": "Keep author and date markup aligned with visible content.",
                "observed_evidence": "Author and freshness signals were partial on the audited page.",
            }
        ],
    }
    evidence = build_v2_evidence_ledger(
        manifest=manifest,
        audit_data=audit_data,
        page_data={
            "title": "Retirement Income Planning",
            "byline": "John Smith",
            "author_pages": [],
            "visible_dates": [
                {"text": "Updated March 20, 2026", "source": "page_header"}
            ],
            "structured_data": [
                {
                    "@type": "Article",
                    "datePublished": "2025-01-01",
                    "dateModified": "2025-01-05",
                    "author": {"name": "Jane Doe, CFP"},
                }
            ],
        },
    )

    sections = build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
                "evidence_completeness": {
                    "score": 40,
                    "label": "Medium",
                    "reason": "This run captured some direct page evidence.",
                },
            },
            "audit_data": audit_data,
        }
    )

    authorship_finding = next(
        item for item in sections["priority_findings"]["findings"] if item["section"] == "Author Trust Signals Are Thin"
    )

    assert any("do not align" in line.lower() for line in authorship_finding["supporting_evidence"])
    assert any("author page is missing" in line.lower() for line in authorship_finding["supporting_evidence"])


def test_v2_report_surfaces_measurement_grade_platform_ingestion():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "mode": "script-only",
        "platforms": ["Bing", "ChatGPT"],
        "competitors": [],
        "comparison_eligibility": {"requested": False, "eligible": False},
    }
    audit_data = {
        "date": "2026-04-08",
        "measurement_data": {
            "platforms": [
                {
                    "platform": "Bing",
                    "source": "bing_ai_performance",
                    "date_range": {"start": "2026-03-01", "end": "2026-03-31"},
                    "page_metrics": [
                        {
                            "page_url": "https://www.transglobalus.com/retirement-income/",
                            "cited_count": 7,
                            "grounding_queries": ["best retirement income strategy", "retirement income planning"],
                        }
                    ],
                },
                {
                    "platform": "ChatGPT",
                    "source": "chatgpt_referrals",
                    "date_range": {"start": "2026-03-01", "end": "2026-03-31"},
                    "referrals": {"visits": 42, "change_pct": 18.5, "utm_source": "chatgpt.com"},
                },
            ]
        },
        "findings": [
            {
                "severity": "medium",
                "title": "AI Citation Share Is Still Thin",
                "summary": "Measured platform visibility is still concentrated on too few pages.",
                "leadership_impact": "Thin citation share limits how often the brand appears in grounded AI answers.",
                "marketing_action": "Expand high-citation page patterns to the next priority pages.",
                "developer_action": "Preserve quote-ready passages and stable URLs on cited pages.",
                "observed_evidence": "Measured citations were concentrated in a narrow page set.",
            }
        ],
    }

    evidence = build_v2_evidence_ledger(manifest=manifest, audit_data=audit_data)
    sections = build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "directional", "reason": "Platform signals are partial.", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
                "evidence_completeness": {"score": 55, "label": "Medium", "reason": "This run captured partial direct platform evidence."},
            },
            "audit_data": audit_data,
        }
    )

    bing_platform = next(item for item in sections["platform_breakdown"]["platforms"] if item["platform"] == "Bing")
    page_evidence_types = {item["evidence_type"] for item in sections["page_source_evidence"]["evidence_items"]}
    citation_finding = next(
        item for item in sections["priority_findings"]["findings"] if item["section"] == "AI Citation Share Is Still Thin"
    )

    assert "measurement_summary" in bing_platform
    assert bing_platform["measurement_summary"]["citation_count"] == 7
    assert bing_platform["measurement_summary"]["grounding_query_count"] == 2
    assert "measured" in bing_platform["observed_visibility_status"].lower()
    assert bing_platform["confidence"] == "high"
    assert "platform_measurement" in page_evidence_types
    assert "citation_share_signal" in page_evidence_types
    assert any("measured" in line.lower() or "citation" in line.lower() for line in citation_finding["supporting_evidence"])


def test_v2_report_tags_claim_source_class_and_evidence_grade():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "mode": "script-only",
        "platforms": ["Bing", "ChatGPT"],
        "competitors": [],
        "comparison_eligibility": {"requested": False, "eligible": False},
    }
    audit_data = {
        "date": "2026-04-08",
        "measurement_data": {
            "platforms": [
                {
                    "platform": "Bing",
                    "source": "bing_ai_performance",
                    "date_range": {"start": "2026-03-01", "end": "2026-03-31"},
                    "page_metrics": [
                        {
                            "page_url": "https://www.transglobalus.com/retirement-income/",
                            "cited_count": 7,
                            "grounding_queries": ["best retirement income strategy", "retirement income planning"],
                        }
                    ],
                }
            ]
        },
        "findings": [
            {
                "severity": "medium",
                "title": "AI Citation Share Is Still Thin",
                "summary": "Measured platform visibility is still concentrated on too few pages.",
                "leadership_impact": "Thin citation share limits how often the brand appears in grounded AI answers.",
                "marketing_action": "Expand high-citation page patterns to the next priority pages.",
                "developer_action": "Preserve quote-ready passages and stable URLs on cited pages.",
                "observed_evidence": "Measured citations were concentrated in a narrow page set.",
            }
        ],
    }

    evidence = build_v2_evidence_ledger(manifest=manifest, audit_data=audit_data)
    sections = build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "directional", "reason": "Platform signals are partial.", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
                "evidence_completeness": {"score": 55, "label": "Medium", "reason": "This run captured partial direct platform evidence."},
            },
            "audit_data": audit_data,
        }
    )

    platform_section = sections["platform_breakdown"]
    citation_finding = next(
        item for item in sections["priority_findings"]["findings"] if item["section"] == "AI Citation Share Is Still Thin"
    )

    assert platform_section["claim_source_class"] == "live_platform_measurement"
    assert platform_section["evidence_grade"] == "directional"
    assert "date range" in platform_section["what_upgrades_this"].lower()
    assert citation_finding["claim_source_class"] == "live_platform_measurement"
    assert citation_finding["evidence_grade"] == "decision-grade"
    assert "more measured platform coverage" in citation_finding["what_upgrades_this"].lower()


def test_v2_report_surfaces_offsite_entity_authority_evidence():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "mode": "script-only",
        "platforms": [],
        "competitors": [],
        "comparison_eligibility": {"requested": False, "eligible": False},
    }
    audit_data = {
        "entity_authority_data": {
            "mentions": [
                {
                    "platform": "Reddit",
                    "mention_type": "discussion",
                    "mention_url": "https://reddit.com/r/retirement/comments/example",
                    "entity_name": "TransGlobal",
                    "brand_match": "exact",
                    "source_quality_tier": "community",
                    "profile_status": "present",
                },
                {
                    "platform": "Wikipedia",
                    "mention_type": "entity_profile",
                    "mention_url": "https://wikipedia.org/wiki/TransGlobal",
                    "entity_name": "TransGlobal",
                    "brand_match": "partial",
                    "source_quality_tier": "reference",
                    "profile_status": "thin",
                },
            ]
        },
        "findings": [
            {
                "severity": "medium",
                "title": "Entity Authority Signals Are Thin",
                "summary": "Offsite entity coverage is incomplete across durable profile and reference surfaces.",
                "leadership_impact": "Thin offsite authority makes it harder for AI systems to reinforce the brand confidently.",
                "marketing_action": "Expand durable brand profiles and reinforce them with trusted references.",
                "developer_action": "Keep entity names, URLs, and profile markup consistent across those surfaces.",
                "observed_evidence": "Offsite authority is present in some places but still incomplete.",
            }
        ],
    }

    evidence = build_v2_evidence_ledger(manifest=manifest, audit_data=audit_data)
    sections = build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
                "evidence_completeness": {"score": 50, "label": "Medium", "reason": "This run captured partial direct authority evidence."},
            },
            "audit_data": audit_data,
        }
    )

    finding = next(
        item for item in sections["priority_findings"]["findings"] if item["section"] == "Entity Authority Signals Are Thin"
    )
    evidence_types = {item["evidence_type"] for item in sections["page_source_evidence"]["evidence_items"]}

    assert finding["claim_source_class"] == "heuristic_inference"
    assert any("reddit" in line.lower() or "wikipedia" in line.lower() for line in finding["supporting_evidence"])
    assert "offsite_entity_signal" in evidence_types
    assert "offsite_authority_gap" in evidence_types


def test_v2_report_surfaces_change_since_last_run_summary_in_proof_appendix():
    sections = build_v2_report_sections(
        {
            "manifest": {
                "target_url": "https://www.transglobalus.com/",
                "mode": "script-only",
                "comparison_eligibility": {"requested": True, "eligible": True},
            },
            "evidence": {"items": [{"evidence_type": "run_manifest"}]},
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {
                    "status": "directional",
                    "reason": "Comparable run exists with a limited but usable delta set.",
                    "warning": "",
                },
                "evidence_completeness": {"score": 60, "label": "Medium", "reason": "This run captured partial direct evidence."},
            },
            "audit_data": {"geo_score": 74},
            "comparison_context": {
                "delta_summary": {
                    "comparable": True,
                    "summary": "GEO score improved by 6 points and citations improved by 2.",
                    "delta_items": [
                        {"metric": "geo_score", "label": "GEO score", "delta": 6, "direction": "up"},
                        {"metric": "citation_count", "label": "Citations", "delta": 2, "direction": "up"},
                    ],
                }
            },
        }
    )

    delta_summary = sections["proof_appendix"]["change_since_last_run"]
    assert delta_summary["comparable"] is True
    assert "improved by 6" in delta_summary["summary"].lower()
    assert delta_summary["delta_items"][0]["metric"] == "geo_score"


def test_v2_report_tunes_actions_and_success_metrics_by_business_profile():
    base_payload = {
        "findings": [
            {
                "severity": "medium",
                "title": "AI Citation Share Is Still Thin",
                "summary": "Measured platform visibility is still concentrated on too few pages.",
                "leadership_impact": "Thin citation share limits how often the brand appears in grounded AI answers.",
                "marketing_action": "Expand high-citation page patterns to the next priority pages.",
                "developer_action": "Preserve quote-ready passages and stable URLs on cited pages.",
                "observed_evidence": "Measured citations were concentrated in a narrow page set.",
            }
        ],
        "client_report_sections": {
            "action_plan_30_60_90": {
                "actions": [
                    {
                        "time_horizon": "30_days",
                        "action": "Expand priority pages into quote-ready answer blocks.",
                        "owner": "marketing",
                        "expected_outcome": "Track the before/after metric tied to this finding and confirm whether citations, referrals, or conversions improve.",
                    }
                ]
            }
        },
    }

    local_sections = build_v2_report_sections(
        {
            "manifest": {"mode": "script-only"},
            "evidence": {"items": [{"evidence_type": "run_manifest"}]},
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
            },
            "audit_data": {**base_payload, "business_profile": "local"},
        }
    )
    ecommerce_sections = build_v2_report_sections(
        {
            "manifest": {"mode": "script-only"},
            "evidence": {"items": [{"evidence_type": "run_manifest"}]},
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
            },
            "audit_data": {**base_payload, "business_profile": "ecommerce"},
        }
    )

    local_action = local_sections["action_plan"]["actions"][0]
    ecommerce_action = ecommerce_sections["action_plan"]["actions"][0]
    local_finding = local_sections["priority_findings"]["findings"][0]
    ecommerce_finding = ecommerce_sections["priority_findings"]["findings"][0]

    assert local_action["owner"] == "Local Marketing"
    assert "priority pages" in local_action["expected_geo_effect"].lower()
    assert ecommerce_action["owner"] == "Merchandising"
    assert "priority pages" in ecommerce_action["expected_geo_effect"].lower()
    assert "location or service-area pages" in local_finding["success_metric"].lower()
    assert "product or category pages" in ecommerce_finding["success_metric"].lower()


def test_v2_report_surfaces_delta_summary_in_proof_appendix():
    sections = build_v2_report_sections(
        {
            "manifest": {"mode": "script-only"},
            "evidence": {"items": [{"evidence_type": "run_manifest"}]},
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "decision-grade", "reason": "Comparable prior run found.", "warning": ""},
                "evidence_completeness": {"score": 60, "label": "Medium", "reason": "Comparison proof is now available."},
            },
            "comparison_context": {
                "delta_summary": {
                    "comparable": True,
                    "summary": "Comparable prior run found.",
                    "what_changed": [
                        {"metric": "citation_count", "current": 10, "previous": 7, "delta": 3},
                        {"metric": "referral_visits", "current": 30, "previous": 20, "delta": 10},
                    ],
                    "what_upgrades_this": "Keep the same query, competitor, and prompt sets in the next run.",
                }
            },
        }
    )

    delta_summary = sections["proof_appendix"]["delta_summary"]

    assert delta_summary["comparable"] is True
    assert delta_summary["what_changed"][0]["metric"] == "citation_count"
    assert "same query" in delta_summary["what_upgrades_this"].lower()


def test_v2_report_cleans_legacy_wording_and_action_heuristics():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "mode": "script-only",
        "platforms": ["ChatGPT", "Perplexity"],
        "competitors": ["competitor.com"],
        "comparison_eligibility": {"requested": True, "eligible": True},
    }
    audit_data = sample_v1_audit_payload()
    audit_data["findings"].append(
        {
            "severity": "medium",
            "title": "Optimization opportunities remain after the base audit",
            "summary": "Optimization pass keeps the roadmap moving.",
            "marketing_action": "Turn the ReScience recommendations into a clearer optimization backlog.",
            "developer_action": "Package the structural fixes into a cleaner rollout plan.",
            "observed_evidence": "The advisory pass still found improvement room after the base audit.",
        }
    )
    audit_data["client_report_sections"]["action_plan_30_60_90"] = {}
    audit_data["report_sections"] = {
        "execution_ledger": {
            "sixty_day": [
                {
                    "action": "Add stronger security headers, starting with Content-Security-Policy.",
                    "owner": "marketing",
                },
                {
                    "action": "Strengthen entity trust with consistent profiles, citations, and a future Wikidata path if eligible.",
                    "owner": "leadership",
                },
            ],
            "ninety_day": [
                {
                    "action": "Develop stronger entity authority through third-party citations and consistent profile governance.",
                    "owner": "leadership",
                }
            ],
        }
    }
    evidence = build_v2_evidence_ledger(manifest=manifest, audit_data=audit_data)
    adjudication = adjudicate_v2_sections(
        manifest=manifest,
        evidence=evidence,
        audit_data=audit_data,
    )

    sections = build_v2_report_sections({
        "manifest": manifest,
        "evidence": evidence,
        "adjudication": adjudication,
        "audit_data": audit_data,
    })

    finding = next(
        item
        for item in sections["priority_findings"]["findings"]
        if item["section"] == "Optimization opportunities remain after the base audit"
    )
    assert "ReScience" not in finding["marketing_action"]

    security_action = next(
        item for item in sections["action_plan"]["actions"] if "Content-Security-Policy" in item["action"]
    )
    assert security_action["owner"] == "developers"

    entity_action = next(
        item for item in sections["action_plan"]["actions"] if "future Wikidata path" in item["action"]
    )
    assert "quote-ready passages" not in entity_action["expected_outcome"]


def test_v2_report_adds_prompt_proof_finding_when_only_sampled_query_evidence_exists():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "mode": "script-only",
        "platforms": ["ChatGPT", "Perplexity"],
        "competitors": ["competitor.com"],
        "comparison_eligibility": {"requested": True, "eligible": True},
    }
    audit_data = sample_v1_audit_payload()
    audit_data["client_report_sections"]["prompt_query_proof"] = {
        "sampling_note": "Exact platform captures were not retained in this sample.",
        "rows": [],
    }
    evidence = build_v2_evidence_ledger(manifest=manifest, audit_data=audit_data)
    adjudication = adjudicate_v2_sections(
        manifest=manifest,
        evidence=evidence,
        audit_data=audit_data,
    )

    sections = build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": evidence,
            "adjudication": adjudication,
            "audit_data": audit_data,
        }
    )

    prompt_finding = next(
        item
        for item in sections["priority_findings"]["findings"]
        if item["section"] == "prompt_proof"
    )
    assert "sampled query evidence" in prompt_finding["summary"].lower()
    assert "exact prompt" in prompt_finding["visible_reason"].lower()
    assert prompt_finding["confidence"] == "low"
    assert "direct platform capture" in prompt_finding["confidence_reason"].lower()
    assert "exact prompts" in prompt_finding["success_metric"].lower()
    assert "sampled query evidence" in prompt_finding["limitations"].lower()


def test_v2_report_enriches_priority_findings_with_proof_and_measurement():
    sections = build_v2_report_sections(
        {
            "manifest": {"mode": "script-only"},
            "evidence": {"items": [{"evidence_type": "run_manifest"}]},
            "adjudication": {
                "benchmark": {"status": "directional", "reason": "Benchmark is thin.", "warning": "Benchmark is directional because the sample is incomplete."},
                "prompt_proof": {"status": "directional", "reason": "Prompt evidence is partial.", "warning": "Prompt proof is directional because exact prompts are incomplete."},
                "platform_breakdown": {"status": "decision-grade", "reason": "Platform read is strong.", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "Comparison is not valid for this run.", "warning": "Change-since-last-run is omitted because the runs are not comparable."},
            },
            "audit_data": sample_v1_audit_payload(),
        }
    )

    finding = next(
        item
        for item in sections["priority_findings"]["findings"]
        if item["section"] == "Key pages are not AI-citation ready"
    )
    assert finding["confidence"] == "high"
    assert "priority page" in finding["confidence_reason"].lower()
    assert finding["success_metric"]
    assert "citability" in finding["success_metric"].lower()
    assert finding["limitations"]
    assert "point-in-time" in finding["limitations"].lower()
    assert finding["supporting_evidence"]


def test_v2_report_adds_low_risk_fetch_note_without_creating_new_finding():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "mode": "script-only",
        "comparison_eligibility": {"requested": False, "eligible": False},
    }
    audit_data = sample_v1_audit_payload()
    audit_data["page_data"] = {
        "url": "https://www.transglobalus.com/",
        "title": "TransGlobal",
        "html_bytes": 185000,
        "h1_tags": ["Services We Provide"],
        "meta_tags": {"description": "Services We Provide"},
        "canonical": "https://www.transglobalus.com/",
        "structured_data": [{"@type": "Organization"}],
    }

    sections = build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": {"items": [{"evidence_type": "run_manifest"}]},
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
            },
            "audit_data": audit_data,
        }
    )

    appendix = sections["proof_appendix"]
    assert any("well below the documented 2 mb html fetch limit" in item.lower() for item in appendix["crawl_and_fetch_evidence"])
    assert not any(
        item["section"] == "fetch_render_risk"
        for item in sections["priority_findings"]["findings"]
    )


def test_v2_report_adds_fetch_render_risk_finding_when_html_is_bloated():
    manifest = {
        "target_url": "https://www.transglobalus.com/",
        "mode": "script-only",
        "comparison_eligibility": {"requested": False, "eligible": False},
    }
    audit_data = sample_v1_audit_payload()
    audit_data["page_data"] = {
        "url": "https://www.transglobalus.com/",
        "title": "TransGlobal",
        "html_bytes": 1750000,
        "h1_tags": [
            "Services We Provide",
            "WHO WE ARE | ABOUT US",
            "MEET OUR STAFF",
        ],
        "meta_tags": {"description": "Services We Provide"},
        "canonical": "https://www.transglobalus.com/",
        "structured_data": [],
    }

    sections = build_v2_report_sections(
        {
            "manifest": manifest,
            "evidence": {"items": [{"evidence_type": "run_manifest"}]},
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
            },
            "audit_data": audit_data,
        }
    )

    finding = next(
        item
        for item in sections["priority_findings"]["findings"]
        if item["section"] == "fetch_render_risk"
    )
    assert "google's documented html fetch cutoff" in finding["visible_reason"].lower()
    assert "critical elements" in finding["marketing_action"].lower()
    assert any("approaches the documented 2 mb html fetch limit" in item.lower() for item in sections["proof_appendix"]["crawl_and_fetch_evidence"])


def test_v2_fetch_render_risk_finding_keeps_page_fetch_evidence():
    sections = build_v2_report_sections(
        {
            "manifest": {
                "target_url": "https://www.transglobalus.com/",
                "mode": "script-only",
                "comparison_eligibility": {"requested": False, "eligible": False},
            },
            "evidence": {
                "items": [
                    {"evidence_type": "run_manifest"},
                    {
                        "evidence_type": "page_fetch",
                        "raw_observation": {
                            "url": "https://www.transglobalus.com/",
                            "title": "TransGlobal",
                            "html_bytes": 1750000,
                            "h1_tags": ["One", "Two"],
                            "meta_tags": {"description": "Services We Provide"},
                            "canonical": "https://www.transglobalus.com/",
                            "structured_data": [],
                        },
                    },
                ]
            },
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
            },
            "audit_data": sample_v1_audit_payload(),
        }
    )

    finding = next(
        item
        for item in sections["priority_findings"]["findings"]
        if item["section"] == "fetch_render_risk"
    )
    assert finding["evidence_items"]
    assert finding["evidence_items"][0]["evidence_type"] == "page_fetch"


def test_v2_report_uses_page_fetch_evidence_when_page_data_is_missing():
    sections = build_v2_report_sections(
        {
            "manifest": {
                "target_url": "https://www.transglobalus.com/",
                "mode": "script-only",
                "comparison_eligibility": {"requested": False, "eligible": False},
            },
            "evidence": {
                "items": [
                    {"evidence_type": "run_manifest"},
                    {
                        "evidence_type": "page_fetch",
                        "raw_observation": {
                            "url": "https://www.transglobalus.com/",
                            "title": "TransGlobal",
                            "html_bytes": 1650000,
                            "h1_tags": ["One", "Two"],
                            "meta_tags": {"description": "Services We Provide"},
                            "canonical": "https://www.transglobalus.com/",
                            "structured_data": [],
                        },
                    },
                ]
            },
            "adjudication": {
                "benchmark": {"status": "omitted", "reason": "", "warning": ""},
                "prompt_proof": {"status": "omitted", "reason": "", "warning": ""},
                "platform_breakdown": {"status": "omitted", "reason": "", "warning": ""},
                "change_since_last_run": {"status": "omitted", "reason": "", "warning": ""},
            },
            "audit_data": sample_v1_audit_payload(),
        }
    )

    assert any(
        "approaches the documented 2 mb html fetch limit" in item.lower()
        for item in sections["proof_appendix"]["crawl_and_fetch_evidence"]
    )
    assert any(
        item["section"] == "fetch_render_risk"
        for item in sections["priority_findings"]["findings"]
    )
