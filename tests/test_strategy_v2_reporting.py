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
        },
    })

    summary = sections["leadership_summary"]
    assert summary["trust_label"] == "How much to trust this"
    assert summary["trust_value"] == "Low"
    assert summary["visible_reason"] == "Prompt proof is omitted because exact prompts or winner URLs were not captured."
    assert len(summary["summary"]) <= 3


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
    assert sections["page_source_evidence"]["priority_pages"][0]["page_url"] == "https://www.transglobalus.com/"
    assert sections["action_plan"]["actions"][0]["action"] == "Rewrite key pages into answer-first blocks with facts and citations."


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
    assert len(actions) == 3
    assert any("quote-ready passages" in item["expected_outcome"].lower() for item in actions)
    assert any("out of surrounding page context" in item["expected_outcome"].lower() for item in actions)
    assert any("specific proof points" in item["expected_outcome"].lower() for item in actions)


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
