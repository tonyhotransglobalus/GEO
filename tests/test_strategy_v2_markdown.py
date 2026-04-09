from pathlib import Path

from scripts.strategy_engine_v2.markdown import render_v2_markdown_report
from scripts.strategy_engine_v2.workflow import run_strategy_report_v2
from tests.strategy_v2_samples import sample_v2_workflow_deps


def test_v2_markdown_renders_visible_warning_for_directional_benchmark():
    payload = {
        "manifest": {
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
        },
        "evidence": {
            "items": [],
        },
        "adjudication": {
            "benchmark": {
                "status": "directional",
                "reason": "Some competitor evidence exists, but the benchmark sample is still thin.",
                "warning": "Benchmark not decision-grade in this run.",
            },
            "prompt_proof": {
                "status": "omitted",
                "reason": "No useful prompt proof was captured.",
                "warning": "Prompt proof is omitted because exact prompts or winner URLs were not captured.",
            },
            "platform_breakdown": {
                "status": "omitted",
                "reason": "No platform-level evidence was captured.",
                "warning": "Platform breakdown is omitted because sampled platforms were not captured.",
            },
            "change_since_last_run": {
                "status": "omitted",
                "reason": "No comparison was requested.",
                "warning": "Change-since-last-run is omitted because comparison was not requested.",
            },
        },
        "report_sections": {
            "leadership_summary": {
                "title": "Leadership Summary",
                "status": "directional",
                "trust_label": "How much to trust this",
                "summary": [
                    "The V2 report keeps the top layer short and the proof visible.",
                    "Run mode: script-only.",
                ],
                "visible_reason": "Benchmark not decision-grade in this run.",
            },
            "score_explanations": {
                "title": "Score Explanations",
                "plain_english_note": "Scores are a guide, not proof.",
                "terms": [],
                "weighting": [],
                "run_context": {},
            },
            "priority_findings": {
                "title": "Priority Findings",
                "findings": [
                    {
                        "section": "benchmark",
                        "status": "directional",
                        "summary": "Some competitor evidence exists, but the benchmark sample is still thin.",
                        "visible_reason": "Benchmark not decision-grade in this run.",
                        "evidence_items": [],
                    }
                ],
            },
            "competitive_benchmark": {
                "title": "Competitive Benchmark",
                "status": "directional",
                "reason": "Some competitor evidence exists, but the benchmark sample is still thin.",
                "visible_reason": "Benchmark not decision-grade in this run.",
                "competitors": [],
                "sample_note": "This section stays conservative until named competitors, sampled queries, and winners are captured.",
            },
            "platform_breakdown": {
                "title": "Platform Breakdown",
                "status": "omitted",
                "reason": "No platform-level evidence was captured.",
                "visible_reason": "Platform breakdown is omitted because sampled platforms were not captured.",
                "platforms": [],
                "sample_note": "Platform-specific claims stay directional until direct captures are available.",
            },
            "page_source_evidence": {
                "title": "Page And Source Evidence",
                "evidence_items": [],
                "visible_reason": "The appendix lists the evidence ledger used to build the report.",
            },
            "action_plan": {
                "title": "Action Plan",
                "actions": [],
            },
            "proof_appendix": {
                "title": "Proof Appendix",
                "manifest": {},
                "evidence_count": 0,
                "adjudication": {},
                "bridge_warnings": [],
                "visible_reason": "This appendix preserves the run scope, evidence ledger, and section reasons.",
            },
        },
    }

    markdown = render_v2_markdown_report(payload)

    assert "Benchmark not decision-grade in this run." in markdown
    assert "## Leadership Summary" in markdown
    assert "## Proof Appendix" in markdown


def test_v2_markdown_renders_bridge_warnings_in_proof_appendix():
    payload = {
        "manifest": {
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
        },
        "report_sections": {
            "leadership_summary": {
                "title": "Leadership Summary",
                "status": "directional",
                "trust_label": "How much to trust this",
                "summary": ["Bridge mode run."],
                "visible_reason": "Evidence is still partial.",
            },
            "score_explanations": {
                "title": "Score Explanations",
                "plain_english_note": "Scores are a guide, not proof.",
                "terms": [],
                "weighting": [],
                "run_context": {},
            },
            "priority_findings": {"title": "Priority Findings", "findings": []},
            "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
            "platform_breakdown": {"title": "Platform Breakdown", "status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
            "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": []},
            "action_plan": {"title": "Action Plan", "actions": []},
            "proof_appendix": {
                "title": "Proof Appendix",
                "manifest": {},
                "evidence_count": 0,
                "adjudication": {},
                "bridge_warnings": [
                    "DuckDuckGo keyword suggestions timed out for 'life insurance', so benchmark and query evidence stayed partial in this run."
                ],
                "visible_reason": "This appendix preserves the run scope, evidence ledger, and section reasons.",
            },
        },
    }

    markdown = render_v2_markdown_report(payload)

    assert "Bridge warnings:" in markdown
    assert "DuckDuckGo keyword suggestions timed out for 'life insurance'" in markdown


def test_v2_markdown_renders_official_source_links_in_proof_appendix():
    payload = {
        "manifest": {
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
        },
        "report_sections": {
            "leadership_summary": {
                "title": "Leadership Summary",
                "status": "directional",
                "trust_label": "How much to trust this",
                "summary": ["Bridge mode run."],
                "visible_reason": "Evidence is still partial.",
            },
            "score_explanations": {
                "title": "Score Explanations",
                "plain_english_note": "Scores are a guide, not proof.",
                "terms": [],
                "weighting": [],
                "run_context": {},
            },
            "priority_findings": {"title": "Priority Findings", "findings": []},
            "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
            "platform_breakdown": {"title": "Platform Breakdown", "status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
            "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": []},
            "action_plan": {"title": "Action Plan", "actions": []},
            "proof_appendix": {
                "title": "Proof Appendix",
                "manifest": {},
                "evidence_count": 0,
                "adjudication": {},
                "official_sources": [
                    {
                        "title": "OpenAI Publishers and Developers FAQ",
                        "url": "https://help.openai.com/en/articles/12627856-publishers-and-developers-faq",
                    }
                ],
                "visible_reason": "This appendix preserves the run scope, evidence ledger, and section reasons.",
            },
        },
    }

    markdown = render_v2_markdown_report(payload)

    assert "Official sources:" in markdown
    assert "OpenAI Publishers and Developers FAQ" in markdown
    assert "https://help.openai.com/en/articles/12627856-publishers-and-developers-faq" in markdown


def test_v2_markdown_renders_readiness_and_evidence_completeness():
    payload = {
        "manifest": {
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
        },
        "report_sections": {
            "leadership_summary": {
                "title": "Leadership Summary",
                "status": "directional",
                "readiness_label": "Current GEO readiness",
                "readiness_value": "High",
                "completeness_label": "Evidence completeness for this run",
                "completeness_value": "Medium",
                "trust_label": "Evidence completeness for this run",
                "trust_value": "Medium",
                "summary": ["Bridge mode run."],
                "visible_reason": "Evidence is still partial.",
                "trust_note": "Page-level site findings can still be stronger than this overall label.",
            },
            "score_explanations": {
                "title": "Score Explanations",
                "plain_english_note": "Scores are a guide, not proof.",
                "terms": [],
                "weighting": [],
                "run_context": {},
            },
            "priority_findings": {"title": "Priority Findings", "findings": []},
            "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
            "platform_breakdown": {"title": "Platform Breakdown", "status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
            "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": []},
            "action_plan": {"title": "Action Plan", "actions": []},
            "proof_appendix": {
                "title": "Proof Appendix",
                "manifest": {},
                "evidence_count": 0,
                "adjudication": {},
                "evidence_completeness": {
                    "score": 50,
                    "label": "Medium",
                    "reason": "This run captured some direct evidence, but important proof layers are still partial.",
                },
                "visible_reason": "This appendix preserves the run scope, evidence ledger, and section reasons.",
            },
        },
    }

    markdown = render_v2_markdown_report(payload)

    assert "Current GEO readiness: High" in markdown
    assert "Evidence completeness for this run: Medium" in markdown
    assert "Evidence completeness: Medium (50/100)" in markdown


def test_v2_markdown_renders_website_fix_blocks():
    full_action = {
        "title": "Make priority pages answer-first and quote-ready",
        "priority": "High",
        "owner": "Content",
        "role_tags": ["Content", "SEO", "Engineering"],
        "exact_location": "homepage: https://www.transglobalus.com/",
        "observed_evidence": "Priority page homepage https://www.transglobalus.com/ scored 28/100 for citability in this run.",
        "exact_change": ["Open the page with a direct answer block."],
        "example_implementation": "Lead with a concise answer summary, then follow with proof bullets.",
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
    payload = {
        "manifest": {
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
        },
        "report_sections": {
            "leadership_summary": {"title": "Leadership Summary", "status": "directional", "summary": [], "visible_reason": ""},
            "score_explanations": {"title": "Score Explanations", "plain_english_note": "Scores are a guide, not proof.", "terms": [], "weighting": [], "run_context": {}},
            "priority_findings": {"title": "Priority Findings", "findings": []},
            "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
            "platform_breakdown": {"title": "Platform Breakdown", "status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
            "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": []},
            "action_plan": {
                "title": "Website Improvement Plan",
                "top_actions": [full_action, second_action],
                "groups": [{"label": "Priority Pages And Templates", "actions": [full_action, second_action]}],
                "actions": [],
            },
            "proof_appendix": {"title": "Proof Appendix", "manifest": {}, "evidence_count": 0, "adjudication": {}, "visible_reason": ""},
        },
    }

    markdown = render_v2_markdown_report(payload)

    assert "## Website Improvement Plan" in markdown
    assert "### Top Website Fixes" in markdown
    assert "Exact location: homepage: https://www.transglobalus.com/" in markdown
    assert "QA: Confirm the answer block is published." in markdown
    assert "Example implementation: Lead with a concise answer summary" in markdown
    assert "Outcome tracking: citation rate on the updated URL." in markdown
    assert "QA: QA:" not in markdown
    assert "Next run: Next run:" not in markdown


def test_v2_markdown_renders_singleton_mode_sections():
    primary_action = {
        "title": "Make priority pages answer-first and quote-ready",
        "priority": "High",
        "owner": "Content",
        "role_tags": ["Content", "SEO", "Engineering"],
        "exact_location": "homepage: https://www.transglobalus.com/",
        "observed_evidence": "Priority page homepage https://www.transglobalus.com/ scored 28/100 for citability in this run.",
        "exact_change": ["Open the page with a direct answer block.", "Support the answer with specific proof points."],
        "example_implementation": "Lead with a concise answer summary, then follow with proof bullets.",
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
            "Extend the same pattern to other priority templates after QA passes.",
        ],
        "proof_packet": [
            "Priority page homepage https://www.transglobalus.com/ scored 28/100 for citability in this run.",
            "Observed word count: 100.",
        ],
    }
    payload = {
        "manifest": {
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
        },
        "report_sections": {
            "leadership_summary": {"title": "Leadership Summary", "status": "directional", "summary": [], "visible_reason": ""},
            "score_explanations": {"title": "Score Explanations", "plain_english_note": "Scores are a guide, not proof.", "terms": [], "weighting": [], "run_context": {}},
            "priority_findings": {"title": "Priority Findings", "findings": []},
            "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
            "platform_breakdown": {"title": "Platform Breakdown", "status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
            "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": []},
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
            "proof_appendix": {"title": "Proof Appendix", "manifest": {}, "evidence_count": 0, "adjudication": {}, "visible_reason": ""},
        },
    }

    markdown = render_v2_markdown_report(payload)

    assert "## Primary Website Fix This Run" in markdown
    assert "## Rollout Map" in markdown
    assert "## Not Recommending Yet" in markdown
    assert "Top Website Fixes" not in markdown
    assert "Why this is the lead fix" in markdown
    assert "Prompt proof is still partial" in markdown


def test_v2_markdown_renders_platform_control_matrix():
    payload = {
        "manifest": {
            "target_url": "https://www.transglobalus.com/",
            "mode": "script-only",
        },
        "report_sections": {
            "leadership_summary": {
                "title": "Leadership Summary",
                "status": "directional",
                "trust_label": "Evidence completeness for this run",
                "trust_value": "Medium",
                "summary": ["Bridge mode run."],
                "visible_reason": "Evidence is still partial.",
            },
            "score_explanations": {
                "title": "Score Explanations",
                "plain_english_note": "Scores are a guide, not proof.",
                "terms": [],
                "weighting": [],
                "run_context": {},
            },
            "priority_findings": {"title": "Priority Findings", "findings": []},
            "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
            "platform_breakdown": {
                "title": "Platform Breakdown",
                "status": "directional",
                "reason": "Platform signals are partial.",
                "visible_reason": "Platform breakdown is directional because platform coverage is limited.",
                "platforms": [
                    {
                        "platform": "ChatGPT",
                        "observed_visibility_status": "Directional only in this run",
                        "confidence": "low",
                        "control_rows": [
                            {"bot_name": "OAI-SearchBot", "surface": "search_bot", "surface_label": "Search bot", "status": "Allowed", "recommendation": "Keep accessible."},
                            {"bot_name": "GPTBot", "surface": "training_bot", "surface_label": "Training bot", "status": "Blocked", "recommendation": "Keep blocked until training policy is defined."},
                        ],
                    }
                ],
            },
            "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": []},
            "action_plan": {"title": "Action Plan", "actions": []},
            "proof_appendix": {"title": "Proof Appendix", "manifest": {}, "evidence_count": 0, "adjudication": {}, "visible_reason": ""},
        },
    }

    markdown = render_v2_markdown_report(payload)

    assert "Control matrix:" in markdown
    assert "OAI-SearchBot (Search bot): Allowed." in markdown
    assert "GPTBot (Training bot): Blocked." in markdown


def test_v2_workflow_includes_markdown_artifact(tmp_path):
    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        reports_dir=tmp_path,
        deps=sample_v2_workflow_deps(),
    )

    markdown_path = Path(result["artifact_paths"]["compat_markdown_path"])
    assert markdown_path.exists()
    assert markdown_path.read_text(encoding="utf-8").startswith("# GEO Strategy Report V2")
    assert "## Leadership Summary" in render_v2_markdown_report(result)


def test_v2_markdown_renders_user_friendly_finding_evidence_lines():
    payload = {
        "manifest": {
            "target_url": "https://example.com/insights/retirement-income/",
            "mode": "script-only",
        },
        "report_sections": {
            "leadership_summary": {
                "title": "Leadership Summary",
                "status": "directional",
                "trust_label": "Evidence completeness for this run",
                "trust_value": "Medium",
                "summary": ["Bridge mode run."],
                "visible_reason": "Evidence is still partial.",
            },
            "score_explanations": {
                "title": "Score Explanations",
                "plain_english_note": "Scores are a guide, not proof.",
                "terms": [],
                "weighting": [],
                "run_context": {},
            },
            "priority_findings": {
                "title": "Priority Findings",
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
                ],
            },
            "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
            "platform_breakdown": {"title": "Platform Breakdown", "status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
            "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": []},
            "action_plan": {"title": "Action Plan", "actions": []},
            "proof_appendix": {"title": "Proof Appendix", "manifest": {}, "evidence_count": 0, "adjudication": {}, "visible_reason": ""},
        },
    }

    markdown = render_v2_markdown_report(payload)

    assert "Observed on https://example.com/insights/retirement-income/" in markdown
    assert "Updated March 20, 2026" in markdown
    assert "live_site observed -" not in markdown


def test_v2_markdown_prefers_supporting_evidence_over_raw_fallback_rows():
    payload = {
        "manifest": {
            "target_url": "https://example.com/insights/retirement-income/",
            "mode": "script-only",
        },
        "report_sections": {
            "leadership_summary": {
                "title": "Leadership Summary",
                "status": "directional",
                "trust_label": "Evidence completeness for this run",
                "trust_value": "Medium",
                "summary": ["Bridge mode run."],
                "visible_reason": "Evidence is still partial.",
            },
            "score_explanations": {
                "title": "Score Explanations",
                "plain_english_note": "Scores are a guide, not proof.",
                "terms": [],
                "weighting": [],
                "run_context": {},
            },
            "priority_findings": {
                "title": "Priority Findings",
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
                ],
            },
            "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
            "platform_breakdown": {"title": "Platform Breakdown", "status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
            "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": []},
            "action_plan": {"title": "Action Plan", "actions": []},
            "proof_appendix": {"title": "Proof Appendix", "manifest": {}, "evidence_count": 0, "adjudication": {}, "visible_reason": ""},
        },
    }

    markdown = render_v2_markdown_report(payload)

    assert markdown.count("Authorship signals captured") == 1


def test_v2_markdown_renders_claim_source_and_evidence_grade_labels():
    markdown = render_v2_markdown_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "report_sections": {
                "leadership_summary": {"title": "Leadership Summary", "summary": [], "visible_reason": ""},
                "score_explanations": {"title": "Score Explanations", "terms": [], "weighting": [], "scorecard": []},
                "priority_findings": {
                    "title": "Priority Findings",
                    "findings": [
                        {
                            "section": "AI Citation Share Is Still Thin",
                            "status": "medium",
                            "summary": "Measured platform visibility is still concentrated on too few pages.",
                            "visible_reason": "Measured citations were concentrated in a narrow page set.",
                            "claim_source_class": "live_platform_measurement",
                            "evidence_grade": "decision-grade",
                            "what_upgrades_this": "Add more measured platform coverage across more pages and a longer date range.",
                            "supporting_evidence": ["Measured 7 citations and 2 grounding queries for the retirement income page."],
                        }
                    ],
                },
                "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {
                    "title": "Platform Breakdown",
                    "status": "directional",
                    "reason": "Platform signals are partial.",
                    "visible_reason": "Platform coverage is still limited.",
                    "claim_source_class": "live_platform_measurement",
                    "evidence_grade": "directional",
                    "what_upgrades_this": "Extend the measured date range and add more platforms.",
                    "platforms": [],
                },
                "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": []},
                "action_plan": {"title": "Action Plan", "actions": []},
                "proof_appendix": {"title": "Proof Appendix", "manifest": {}, "evidence_count": 0, "adjudication": {}, "visible_reason": ""},
            },
        }
    )

    assert "- Claim source: Live platform measurement" in markdown
    assert "- Evidence grade: Decision-grade" in markdown
    assert "- What upgrades this: Add more measured platform coverage across more pages and a longer date range." in markdown


def test_v2_markdown_renders_change_since_last_run_subsection():
    markdown = render_v2_markdown_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "report_sections": {
                "leadership_summary": {"title": "Leadership Summary", "summary": [], "visible_reason": ""},
                "score_explanations": {"title": "Score Explanations", "terms": [], "weighting": [], "scorecard": []},
                "priority_findings": {"title": "Priority Findings", "findings": []},
                "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"title": "Platform Breakdown", "status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": []},
                "action_plan": {"title": "Action Plan", "actions": []},
                "proof_appendix": {
                    "title": "Proof Appendix",
                    "manifest": {},
                    "evidence_count": 0,
                    "adjudication": {},
                    "visible_reason": "",
                    "delta_summary": {
                        "comparable": True,
                        "summary": "Comparable prior run found.",
                        "what_changed": [
                            {"metric": "citation_count", "current": 10, "previous": 7, "delta": 3},
                            {"metric": "referral_visits", "current": 30, "previous": 20, "delta": 10},
                        ],
                        "what_upgrades_this": "Keep the same query, competitor, and prompt sets in the next run.",
                    },
                },
            },
        }
    )

    assert "### Change Since Last Run" in markdown
    assert "- Citation count: 7 -> 10 (+3)" in markdown
    assert "- What upgrades this: Keep the same query, competitor, and prompt sets in the next run." in markdown


def test_v2_markdown_renders_change_since_last_run_summary():
    markdown = render_v2_markdown_report(
        {
            "manifest": {"target_url": "https://example.com/", "mode": "script-only"},
            "report_sections": {
                "leadership_summary": {"title": "Leadership Summary", "summary": [], "visible_reason": ""},
                "score_explanations": {"title": "Score Explanations", "terms": [], "weighting": [], "scorecard": []},
                "priority_findings": {"title": "Priority Findings", "findings": []},
                "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "", "visible_reason": "", "competitors": []},
                "platform_breakdown": {"title": "Platform Breakdown", "status": "omitted", "reason": "", "visible_reason": "", "platforms": []},
                "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": []},
                "action_plan": {"title": "Action Plan", "actions": []},
                "proof_appendix": {
                    "title": "Proof Appendix",
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
                    "visible_reason": "",
                },
            },
        }
    )

    assert "### Change Since Last Run" in markdown
    assert "GEO score improved by 6 points" in markdown
    assert "GEO score: up 6" in markdown
