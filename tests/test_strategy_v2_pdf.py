from pathlib import Path

from pypdf import PdfReader

from scripts.strategy_engine_v2.pdf import generate_v2_pdf_report
from scripts.strategy_engine_v2.workflow import run_strategy_report_v2
from tests.strategy_v2_samples import sample_v2_workflow_deps


def test_v2_pdf_renders_core_sections(tmp_path):
    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        shadow_run=False,
        compare_to_v1=True,
        reports_dir=tmp_path,
        deps=sample_v2_workflow_deps(),
    )

    pdf_path = Path(result["artifact_paths"]["pdf_path"])
    assert pdf_path.exists()

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "GEO Strategy Report V2" in text
    assert "Leadership Summary" in text
    assert "Website Improvement Plan" in text
    assert "Priority Findings" in text
    assert "Key Pages Are Not Ai-Citation Ready" in text
    assert "Competitive Benchmark" in text
    assert "Proof Appendix" in text
    assert "Glossary" in text


def test_v2_pdf_omits_debug_style_copy_and_repetitive_bridge_rows(tmp_path):
    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        shadow_run=False,
        compare_to_v1=True,
        reports_dir=tmp_path,
        deps=sample_v2_workflow_deps(),
    )

    pdf_path = Path(result["artifact_paths"]["pdf_path"])
    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Evidence items captured" not in text
    assert "Bridge mode reuses this component from the V1 audit model." not in text
    assert "finding, internal_score" not in text
    assert "Recommended action" not in text


def test_v2_pdf_explains_prompt_proof_and_renders_richer_finding_proof(tmp_path):
    pdf_path = tmp_path / "custom-v2.pdf"
    generate_v2_pdf_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {
                    "trust_value": "Low",
                    "summary": ["Site findings are usable, but benchmark proof is still partial."],
                    "visible_reason": "Prompt proof is omitted because exact prompts or winner URLs were not captured.",
                    "trust_note": "This top-line trust label reflects benchmark, platform, and prompt-proof completeness. Page-level site findings can still be stronger than this overall label. Prompt proof means saved examples of the exact prompt, answer, and cited URL.",
                },
                "score_explanations": {
                    "plain_english_note": "Scores are a guide, not proof.",
                    "scorecard": [],
                    "terms": [
                        {
                            "label": "Prompt proof",
                            "plain_english": "Saved examples of the exact prompt, answer text, and cited URLs.",
                        }
                    ],
                },
                "priority_findings": {
                    "findings": [
                        {
                            "section": "heading_architecture",
                            "title": "Heading Architecture Is Diluted",
                            "status": "high",
                            "summary": "The homepage exposes 10 H1 tags instead of one clear primary heading.",
                            "visible_reason": "The homepage exposes 10 H1 tags instead of one clear primary heading.",
                            "leadership_impact": "This weakens topical focus for both users and AI systems.",
                            "marketing_action": "Clarify the homepage message hierarchy so one core message leads.",
                            "engineering_action": "Refactor the homepage markup to a single H1 and supporting H2/H3s.",
                            "confidence": "High",
                            "confidence_reason": "This comes from direct page-fetch and DOM evidence in the current run.",
                            "success_metric": "Reduce the homepage to one H1 and verify cleaner extracted snippets in the next audit.",
                            "limitations": "This is a point-in-time read of the audited page rather than every template on the site.",
                            "supporting_evidence": [
                                "live_site observed - https://example.com/: Observed H1 count: 10."
                            ],
                            "evidence_items": [
                                {
                                    "source_class": "live_site",
                                    "observed_vs_inferred": "observed",
                                    "url_or_domain": "https://example.com/",
                                    "normalized_summary": "Observed H1 count: 10.",
                                }
                            ],
                        }
                    ]
                },
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {"actions": []},
                "proof_appendix": {"manifest": {}, "evidence_count": 0, "adjudication": {}, "limitations": {}},
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Prompt proof means saved examples of the exact prompt" in text
    assert "Evidence from this run:" in text
    assert "What we saw:" not in text
    assert "Confidence:" in text
    assert "How we will know this improved:" in text


def test_v2_pdf_renders_official_source_links_in_proof_appendix(tmp_path):
    pdf_path = tmp_path / "sources-v2.pdf"
    generate_v2_pdf_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {"trust_value": "Medium", "summary": [], "visible_reason": ""},
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {"findings": []},
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {"actions": []},
                "proof_appendix": {
                    "manifest": {},
                    "evidence_count": 0,
                    "adjudication": {},
                    "official_sources": [
                        {
                            "title": "OpenAI Publishers and Developers FAQ",
                            "url": "https://help.openai.com/en/articles/12627856-publishers-and-developers-faq",
                        }
                    ],
                    "limitations": {},
                },
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Official Sources" in text
    assert "OpenAI Publishers and Developers FAQ" in text


def test_v2_pdf_renders_readiness_and_evidence_completeness(tmp_path):
    pdf_path = tmp_path / "completeness-v2.pdf"
    generate_v2_pdf_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {
                    "readiness_label": "Current GEO readiness",
                    "readiness_value": "High",
                    "completeness_label": "Evidence completeness for this run",
                    "completeness_value": "Medium",
                    "trust_label": "Evidence completeness for this run",
                    "trust_value": "Medium",
                    "summary": ["Site findings are usable, but benchmark proof is still partial."],
                    "visible_reason": "Prompt proof is omitted because exact prompts or winner URLs were not captured.",
                    "trust_note": "This top-line trust label reflects benchmark, platform, and prompt-proof completeness.",
                },
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {"findings": []},
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {"actions": []},
                "proof_appendix": {
                    "manifest": {},
                    "evidence_count": 0,
                    "adjudication": {},
                    "evidence_completeness": {
                        "score": 50,
                        "label": "Medium",
                        "reason": "This run captured some direct evidence, but important proof layers are still partial.",
                    },
                    "limitations": {},
                },
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Current GEO readiness: High" in text
    assert "Evidence completeness for this run: Medium" in text
    assert "Evidence Completeness" in text
    assert "Medium (50/100)" in text


def test_v2_pdf_renders_platform_control_matrix(tmp_path):
    pdf_path = tmp_path / "platform-controls-v2.pdf"
    generate_v2_pdf_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {"trust_value": "Medium", "summary": [], "visible_reason": ""},
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {"findings": []},
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {
                    "status": "directional",
                    "reason": "Platform signals are partial.",
                    "visible_reason": "",
                    "platforms": [
                        {
                            "platform": "ChatGPT",
                            "observed_visibility_status": "Directional only in this run",
                            "confidence": "low",
                            "control_rows": [
                                {"platform": "ChatGPT", "bot_name": "OAI-SearchBot", "surface": "search_bot", "surface_label": "Search bot", "status": "Allowed", "recommendation": "Keep accessible."},
                                {"platform": "ChatGPT", "bot_name": "GPTBot", "surface": "training_bot", "surface_label": "Training bot", "status": "Blocked", "recommendation": "Keep blocked until training policy is defined."},
                            ],
                        }
                    ],
                    "control_matrix": [
                        {"platform": "ChatGPT", "bot_name": "OAI-SearchBot", "surface": "search_bot", "surface_label": "Search bot", "status": "Allowed", "recommendation": "Keep accessible."},
                        {"platform": "ChatGPT", "bot_name": "GPTBot", "surface": "training_bot", "surface_label": "Training bot", "status": "Blocked", "recommendation": "Keep blocked until training policy is defined."},
                    ],
                },
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {"actions": []},
                "proof_appendix": {"manifest": {}, "evidence_count": 0, "adjudication": {}, "limitations": {}},
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Platform Control Matrix" in text
    assert "OAI-SearchBot" in text
    assert "GPTBot" in text


def test_v2_pdf_renders_user_friendly_finding_evidence_lines(tmp_path):
    pdf_path = tmp_path / "task5-proof-quality.pdf"
    generate_v2_pdf_report(
        {
            "manifest": {
                "target_url": "https://example.com/insights/retirement-income/",
                "mode": "script-only",
            },
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {"trust_value": "Medium", "summary": [], "visible_reason": ""},
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {
                    "findings": [
                        {
                            "section": "Author Trust Signals Are Thin",
                            "status": "medium",
                            "summary": "Priority pages do not clearly expose author credentials and freshness signals.",
                            "visible_reason": "Author and freshness signals were partial on the audited page.",
                            "leadership_impact": "Thin authorship and freshness cues can weaken trust in quoted answers.",
                            "marketing_action": "Add visible bylines, bios, and update dates to expert pages.",
                            "engineering_action": "Keep author and date markup aligned with visible content.",
                            "confidence": "medium",
                            "confidence_reason": "This finding comes from direct byline, author-page, and freshness signals captured on the audited page.",
                            "success_metric": "Expose aligned bylines, author pages, and publish or update dates on priority pages and confirm they remain visible in the next run.",
                            "limitations": "These cues support machine interpretation and trust, but they do not prove authority or freshness on their own.",
                            "supporting_evidence": [
                                "Observed on https://example.com/insights/retirement-income/: Authorship signals captured: visible byline 'Jane Doe, CFP', 1 linked author page.",
                                "Observed on https://example.com/insights/retirement-income/: Freshness signals captured: visible date text 'Updated March 20, 2026'; published 2026-03-01 and updated 2026-03-20 in Article schema; visible and schema dates are aligned.",
                            ],
                            "evidence_items": [],
                        }
                    ]
                },
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {"actions": []},
                "proof_appendix": {"manifest": {}, "evidence_count": 0, "adjudication": {}, "limitations": {}},
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Observed on https://example.com/insights/retirement-income/" in text
    assert "Updated March 20, 2026" in text
    assert "live_site observed -" not in text


def test_v2_pdf_prefers_supporting_evidence_over_raw_fallback_rows(tmp_path):
    pdf_path = tmp_path / "task5-no-dup.pdf"
    generate_v2_pdf_report(
        {
            "manifest": {
                "target_url": "https://example.com/insights/retirement-income/",
                "mode": "script-only",
            },
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {"trust_value": "Medium", "summary": [], "visible_reason": ""},
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {
                    "findings": [
                        {
                            "section": "Author Trust Signals Are Thin",
                            "status": "medium",
                            "summary": "Priority pages do not clearly expose author credentials and freshness signals.",
                            "visible_reason": "Author and freshness signals were partial on the audited page.",
                            "supporting_evidence": [
                                "Observed on https://example.com/insights/retirement-income/: Authorship signals captured: visible byline 'Jane Doe, CFP', 1 linked author page."
                            ],
                            "evidence_items": [
                                {
                                    "evidence_type": "authorship_signal",
                                    "source_class": "live_site",
                                    "normalized_summary": "Authorship signals captured: visible byline 'Jane Doe, CFP', 1 linked author page.",
                                }
                            ],
                        }
                    ]
                },
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {"actions": []},
                "proof_appendix": {"manifest": {}, "evidence_count": 0, "adjudication": {}, "limitations": {}},
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert text.count("Authorship signals captured") == 1


def test_v2_pdf_renders_claim_source_and_evidence_grade_labels(tmp_path):
    pdf_path = tmp_path / "claim-labels-v2.pdf"
    generate_v2_pdf_report(
        {
            "manifest": {
                "target_url": "https://example.com/",
                "mode": "script-only",
            },
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {"trust_value": "Medium", "summary": [], "visible_reason": ""},
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {
                    "findings": [
                        {
                            "section": "AI Citation Share Is Still Thin",
                            "status": "medium",
                            "summary": "Measured platform visibility is still concentrated on too few pages.",
                            "visible_reason": "Measured citations were concentrated in a narrow page set.",
                            "claim_source_class": "live_platform_measurement",
                            "evidence_grade": "decision-grade",
                            "what_upgrades_this": "Add more measured platform coverage across more pages and a longer date range.",
                            "supporting_evidence": [
                                "Measured 7 citations and 2 grounding queries for the retirement income page."
                            ],
                            "evidence_items": [],
                        }
                    ]
                },
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {
                    "status": "directional",
                    "reason": "Platform signals are partial.",
                    "visible_reason": "Platform coverage is still limited.",
                    "claim_source_class": "live_platform_measurement",
                    "evidence_grade": "directional",
                    "what_upgrades_this": "Extend the measured date range and add more platforms.",
                    "platforms": [],
                },
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {"actions": []},
                "proof_appendix": {"manifest": {}, "evidence_count": 0, "adjudication": {}, "limitations": {}},
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Claim source:" in text
    assert "Live platform measurement" in text
    assert "Evidence grade:" in text
    assert "What upgrades this:" in text


def test_v2_pdf_renders_page_source_reason_and_evidence_ledger_highlights(tmp_path):
    pdf_path = tmp_path / "page-source-v2.pdf"
    generate_v2_pdf_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {"trust_value": "Medium", "summary": [], "visible_reason": ""},
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {"findings": []},
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {
                    "title": "Page And Source Evidence",
                    "visible_reason": "The appendix lists the evidence ledger used to build the report.",
                    "priority_pages": [],
                    "source_domains": [],
                    "evidence_items": [
                        {
                            "evidence_type": "authorship_signal",
                            "summary": "Visible byline Jane Doe, CFP, with one linked author page.",
                        }
                    ],
                },
                "action_plan": {"actions": []},
                "proof_appendix": {"manifest": {}, "evidence_count": 0, "adjudication": {}, "limitations": {}},
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "The appendix lists the evidence ledger used to build the report." in text
    assert "Evidence Ledger Highlights" in text
    assert "Authorship signal: Visible byline Jane Doe, CFP, with one linked author page." in text


def test_v2_pdf_renders_action_plan_context_lines(tmp_path):
    pdf_path = tmp_path / "action-plan-v2.pdf"
    generate_v2_pdf_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {"trust_value": "Medium", "summary": [], "visible_reason": ""},
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {"findings": []},
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {
                    "actions": [
                        {
                            "time_horizon": "30 days",
                            "action": "Capture named competitor prompts and saved answers.",
                            "owner": "strategy",
                            "visible_reason": "Benchmark evidence is still too thin to support winner claims.",
                            "expected_outcome": "Benchmark reporting becomes decision-grade instead of directional.",
                        }
                    ]
                },
                "proof_appendix": {"manifest": {}, "evidence_count": 0, "adjudication": {}, "limitations": {}},
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Capture named competitor prompts and saved answers." in text
    assert "Owner:" in text
    assert "QA:" in text or "Why now:" in text


def test_v2_pdf_renders_website_fix_cards(tmp_path):
    pdf_path = tmp_path / "website-fixes-v2.pdf"
    full_action = {
        "title": "Make priority pages answer-first and quote-ready",
        "priority": "High",
        "owner": "Content",
        "role_tags": ["Content", "SEO", "Engineering"],
        "exact_location": "homepage: https://example.com/",
        "observed_evidence": "Priority page homepage https://example.com/ scored 28/100 for citability in this run.",
        "exact_change": [
            "Open the page with a direct answer block.",
            "Support the answer with specific proof points.",
        ],
        "example_implementation": "Start with a short answer summary, then add proof bullets with exact facts.",
        "acceptance_criteria": "The page opens with a direct answer section and remains understandable when quoted out of context.",
        "expected_geo_effect": "Higher likelihood that the page is cited and summarized accurately.",
        "confidence": "High",
        "verification_qa": "QA: Confirm the answer block is published.",
        "verification_geo": "Next run: Confirm citability improves in the next run.",
        "verification_outcome": "Watch citation rate on the updated URL.",
    }
    second_action = dict(full_action)
    second_action["title"] = "Fix heading hierarchy on the homepage and core templates"
    second_action["exact_location"] = "homepage template"
    second_action["observed_evidence"] = "The homepage exposes multiple H1 tags in this run."
    generate_v2_pdf_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {"trust_value": "Medium", "summary": [], "visible_reason": ""},
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {"findings": []},
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {
                    "title": "Website Improvement Plan",
                    "top_actions": [full_action, second_action],
                    "groups": [{"label": "Priority Pages And Templates", "actions": [full_action, second_action]}],
                    "actions": [],
                },
                "proof_appendix": {"manifest": {}, "evidence_count": 0, "adjudication": {}, "limitations": {}},
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Top Website Fixes" in text
    assert "Exact location:" in text
    assert "Acceptance criteria:" in text
    assert "Next run:" in text
    assert "Example implementation:" in text
    assert "Outcome tracking:" in text
    assert "QA: QA:" not in text
    assert "Next run: Next run:" not in text


def test_v2_pdf_renders_singleton_mode_sections(tmp_path):
    pdf_path = tmp_path / "singleton-v2.pdf"
    primary_action = {
        "title": "Make priority pages answer-first and quote-ready",
        "priority": "High",
        "owner": "Content",
        "role_tags": ["Content", "SEO", "Engineering"],
        "exact_location": "homepage: https://example.com/",
        "observed_evidence": "Priority page homepage https://example.com/ scored 28/100 for citability in this run.",
        "exact_change": [
            "Open the page with a direct answer block.",
            "Support the answer with specific proof points.",
        ],
        "example_implementation": "Start with a short answer summary, then add proof bullets with exact facts.",
        "acceptance_criteria": "The page opens with a direct answer section and remains understandable when quoted out of context.",
        "expected_geo_effect": "Higher likelihood that the page is cited and summarized accurately.",
        "confidence": "High",
        "confidence_reason": "This is grounded in direct priority-page scoring.",
        "success_metric": "Raise citability on priority pages and see more sampled answers cite or summarize those pages accurately.",
        "why_this_is_the_lead_fix": "This is the only website fix in this run with strong enough evidence and immediate execution value.",
        "verification_qa": "QA: Confirm the answer block is published.",
        "verification_geo": "Next run: Confirm citability improves in the next run.",
        "verification_outcome": "Watch citation rate on the updated URL.",
        "rollout_sequence": [
            "Pilot the answer-first structure on the homepage.",
            "Extend the same pattern to the service page template after QA passes.",
        ],
        "proof_packet": [
            "Priority page homepage https://example.com/ scored 28/100 for citability in this run.",
            "Observed word count: 100.",
        ],
    }
    generate_v2_pdf_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {"trust_value": "Medium", "summary": [], "visible_reason": ""},
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {"findings": []},
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {
                    "title": "Website Improvement Plan",
                    "mode": "singleton",
                    "primary_action": primary_action,
                    "watchlist": [
                        {
                            "title": "Prompt proof is still partial",
                            "evidence_grade": "Directional",
                            "why_not_recommended_yet": "This signal is still directional rather than recommendation-grade in this run.",
                            "what_upgrades_this": "Capture exact prompts, answer text, and cited URLs.",
                            "strongest_evidence": "Platform: ChatGPT | Prompt/query: best life insurance company | Winning URLs: https://competitor.com/life",
                        }
                    ],
                },
                "proof_appendix": {"manifest": {}, "evidence_count": 0, "adjudication": {}, "limitations": {}},
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Primary Website Fix This Run" in text
    assert "Why this is the lead fix:" in text
    assert "Rollout Map" in text
    assert "Not Recommending Yet" in text
    assert "Top Website Fixes" not in text
    assert "Prompt proof is still partial" in text


def test_v2_pdf_renders_change_since_last_run_subsection(tmp_path):
    pdf_path = tmp_path / "delta-v2.pdf"
    generate_v2_pdf_report(
        {
            "manifest": {
                "target_url": "https://example.com/",
                "mode": "script-only",
            },
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {"trust_value": "Medium", "summary": [], "visible_reason": ""},
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {"findings": []},
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {"actions": []},
                "proof_appendix": {
                    "manifest": {},
                    "evidence_count": 0,
                    "adjudication": {},
                    "delta_summary": {
                        "comparable": True,
                        "summary": "Comparable prior run found.",
                        "what_changed": [
                            {"metric": "citation_count", "current": 10, "previous": 7, "delta": 3},
                            {"metric": "referral_visits", "current": 30, "previous": 20, "delta": 10},
                        ],
                        "what_upgrades_this": "Keep the same query, competitor, and prompt sets in the next run.",
                    },
                    "limitations": {},
                },
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Change Since Last Run" in text
    assert "Citation count: 7 -> 10 (+3)" in text
    assert "What upgrades this:" in text


def test_v2_pdf_renders_change_since_last_run_summary(tmp_path):
    pdf_path = tmp_path / "delta-v2.pdf"
    generate_v2_pdf_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "audit_data": {"brand_name": "Example Co"},
            "report_sections": {
                "leadership_summary": {"trust_value": "Medium", "summary": [], "visible_reason": ""},
                "score_explanations": {"plain_english_note": "Scores are a guide, not proof.", "scorecard": [], "terms": []},
                "priority_findings": {"findings": []},
                "competitive_benchmark": {"status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"priority_pages": [], "source_domains": [], "evidence_items": []},
                "action_plan": {"actions": []},
                "proof_appendix": {
                    "manifest": {},
                    "evidence_count": 0,
                    "adjudication": {},
                    "change_since_last_run": {
                        "comparable": True,
                        "summary": "GEO score improved by 6 points and citations improved by 2.",
                        "delta_items": [
                            {"label": "GEO score", "delta": 6, "direction": "up"},
                            {"label": "Citations", "delta": 2, "direction": "up"},
                        ],
                    },
                    "limitations": {},
                },
            },
        },
        output_path=pdf_path,
    )

    reader = PdfReader(str(pdf_path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)

    assert "Change Since Last Run" in text
    assert "GEO score improved by 6 points" in text
    assert "GEO score: up 6" in text
