from scripts.strategy_engine_v2.qa import run_release_checks
from scripts.strategy_engine_v2.workflow import run_strategy_report_v2


def _base_payload():
    return {
        "manifest": {
            "target_url": "https://www.transglobalus.com/",
            "target_domain": "transglobalus.com",
            "platforms": ["chatgpt"],
            "competitors": ["example.com"],
            "comparison_eligibility": {"requested": True, "eligible": True},
        },
        "evidence": {
            "items": [
                {
                    "evidence_type": "run_manifest",
                    "url_or_domain": "https://www.transglobalus.com/",
                    "source_class": "internal_metadata",
                    "normalized_summary": "Run scope captured in the V2 manifest.",
                },
                {
                    "evidence_type": "page_fetch",
                    "source_class": "live_site",
                    "normalized_summary": "Homepage fetch completed.",
                }
            ]
        },
        "adjudication": {
            "benchmark": {
                "status": "directional",
                "reason": "Benchmark is thin.",
                "warning": "Benchmark is directional because the sample is incomplete.",
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
                "reason": "Comparison is not valid for this run.",
                "warning": "Change-since-last-run is omitted because the runs are not comparable.",
            },
        },
        "report_sections": {
            "leadership_summary": {
                "title": "Leadership Summary",
                "status": "directional",
                "trust_label": "How much to trust this",
                "summary": [
                    "The V2 report keeps the top layer short and the proof visible.",
                    "The V2 report keeps the top layer short and the proof visible.",
                    "The V2 report keeps the top layer short and the proof visible.",
                    "Run mode: script-only.",
                ],
                "visible_reason": "Benchmark is directional because the sample is incomplete.",
            },
            "score_explanations": {
                "title": "Score Explanations",
                "plain_english_note": "Scores are a guide, not proof.",
                "score_provenance": "internal scoring model v2",
                "terms": [
                    {
                        "label": "Decision-grade",
                        "plain_english": "The evidence is strong enough to support a client-facing claim.",
                    },
                    {
                        "label": "Directional",
                        "plain_english": "The signal is useful, but the sample is still partial.",
                    },
                ],
                "weighting": [],
                "run_context": {"mode": "script-only", "evidence_items": 1, "adjudicated_sections": []},
            },
            "priority_findings": {
                "title": "Priority Findings",
                "findings": [
                    {
                        "section": "benchmark",
                        "status": "directional",
                        "summary": "Some competitor evidence exists, but the benchmark sample is still thin.",
                        "visible_reason": "Benchmark is directional because the sample is incomplete.",
                        "evidence_items": [],
                    },
                    {
                        "section": "prompt_proof",
                        "status": "omitted",
                        "summary": "No useful prompt proof was captured.",
                        "visible_reason": "",
                        "evidence_items": [],
                    }
                ],
            },
            "competitive_benchmark": {
                "title": "Competitive Benchmark",
                "status": "directional",
                "reason": "Some competitor evidence exists, but the benchmark sample is still thin.",
                "visible_reason": "Benchmark is directional because the sample is incomplete.",
                "competitors": ["example.com"],
                "sample_note": "This section stays conservative until named competitors, sampled queries, and winners are captured.",
            },
            "platform_breakdown": {
                "title": "Platform Breakdown",
                "status": "omitted",
                "reason": "No platform-level evidence was captured.",
                "visible_reason": "Platform breakdown is omitted because sampled platforms were not captured.",
                "platforms": ["chatgpt"],
                "sample_note": "Platform-specific claims stay directional until direct captures are available.",
            },
            "page_source_evidence": {
                "title": "Page And Source Evidence",
                "evidence_items": [
                    {
                        "evidence_type": "run_manifest",
                        "summary": "Run scope captured in the V2 manifest.",
                    }
                ],
                "visible_reason": "The appendix lists the evidence ledger used to build the report.",
            },
            "action_plan": {
                "title": "Action Plan",
                "actions": [],
            },
            "proof_appendix": {
                "title": "Proof Appendix",
                "manifest": {
                    "target_url": "https://www.transglobalus.com/",
                    "mode": "script-only",
                    "shadow_run": False,
                },
                "evidence_count": 1,
                "adjudication": {},
                "visible_reason": "This appendix preserves the run scope, evidence ledger, and section reasons.",
            },
        },
    }


def _improved_payload():
    payload = _base_payload()
    payload["manifest"]["comparison_eligibility"]["requested"] = False
    payload["evidence"]["items"] = [
        {
            "evidence_type": "run_manifest",
            "url_or_domain": "https://www.transglobalus.com/",
            "source_class": "internal_metadata",
            "normalized_summary": "Run scope captured in the V2 manifest.",
        },
        {
            "evidence_type": "page_fetch",
            "url_or_domain": "https://www.transglobalus.com/about",
            "source_class": "live_site",
            "normalized_summary": "About page fetch completed.",
        },
    ]
    payload["adjudication"]["benchmark"]["status"] = "directional"
    payload["adjudication"]["benchmark"]["warning"] = "Benchmark is directional because the sample is incomplete."
    payload["adjudication"]["prompt_proof"]["status"] = "directional"
    payload["adjudication"]["prompt_proof"]["reason"] = "Prompt capture is partial but explained."
    payload["adjudication"]["prompt_proof"]["warning"] = "Prompt proof is directional because the sample is partial."
    payload["adjudication"]["change_since_last_run"]["status"] = "omitted"
    payload["adjudication"]["change_since_last_run"]["warning"] = "Change-since-last-run is omitted because comparison was not requested."
    payload["report_sections"]["leadership_summary"]["summary"] = [
        "The V2 report keeps the top layer short and the proof visible.",
        "Run mode: script-only.",
        "Evidence items captured: 2.",
    ]
    payload["report_sections"]["leadership_summary"]["visible_reason"] = "Benchmark is directional because the sample is incomplete."
    payload["report_sections"]["score_explanations"]["score_provenance"] = "internal scoring model v2"
    payload["report_sections"]["score_explanations"]["terms"] = [
        {
            "label": "Decision-grade",
            "plain_english": "The evidence is strong enough to support a client-facing claim.",
        },
        {
            "label": "Directional",
            "plain_english": "The signal is useful, but the sample is still partial.",
        },
        {
            "label": "Citability",
            "plain_english": "How easy a page is for AI systems to quote accurately.",
        },
    ]
    payload["report_sections"]["priority_findings"]["findings"] = [
        {
            "section": "benchmark",
            "status": "directional",
            "summary": "Some competitor evidence exists, but the benchmark sample is still thin.",
            "visible_reason": "Benchmark is directional because the sample is incomplete.",
            "evidence_items": [],
        },
        {
            "section": "prompt_proof",
            "status": "directional",
            "summary": "Prompt proof is partial but the evidence is clear.",
            "visible_reason": "Prompt proof is directional because the sample is partial.",
            "evidence_items": [],
        }
    ]
    payload["report_sections"]["page_source_evidence"]["evidence_items"] = [
        {"evidence_type": "run_manifest", "summary": "Run scope captured in the V2 manifest."},
        {"evidence_type": "page_fetch", "summary": "About page fetch completed."},
    ]
    return payload


def test_qa_flags_repeated_phrasing_and_missing_provenance():
    payload = _base_payload()
    payload["report_sections"]["score_explanations"].pop("score_provenance", None)
    payload["report_sections"]["leadership_summary"]["summary"] = [
        "Repeat repeat repeat repeat repeat repeat repeat.",
        "Repeat repeat repeat repeat repeat repeat repeat.",
        "Repeat repeat repeat repeat repeat repeat repeat.",
        "Run mode: script-only.",
    ]

    result = run_release_checks(payload)

    assert "missing_score_provenance" in result["issues"]
    assert "repeated_phrasing" in result["issues"]
    assert result["warnings"]


def test_qa_flags_unsupported_comparison_and_homepage_only_evidence():
    payload = _base_payload()

    result = run_release_checks(payload)

    assert "unsupported_change_since_last_run" in result["issues"]
    assert "homepage_only_evidence" in result["issues"]


def test_qa_flags_thin_benchmark_prompt_proof_and_unexplained_jargon_when_reasons_are_unclear():
    payload = _base_payload()
    payload["report_sections"]["leadership_summary"]["summary"] = [
        "The V2 report keeps the top layer short and the proof visible.",
        "The V2 report keeps the top layer short and the proof visible.",
        "The V2 report keeps the top layer short and the proof visible.",
    ]
    payload["report_sections"]["score_explanations"]["terms"] = []
    payload["report_sections"]["competitive_benchmark"]["visible_reason"] = ""
    payload["report_sections"]["competitive_benchmark"]["reason"] = "Needs work."
    payload["report_sections"]["priority_findings"]["findings"][1]["visible_reason"] = ""
    payload["report_sections"]["priority_findings"]["findings"][1]["summary"] = "Needs work."

    result = run_release_checks(payload)

    assert "benchmark_thinness" in result["issues"]
    assert "prompt_proof_thinness" in result["issues"]
    assert "unexplained_jargon" in result["issues"]


def test_qa_clears_warnings_when_payload_improves():
    result = run_release_checks(_improved_payload())

    assert result["issues"] == []
    assert result["warnings"] == []


def test_qa_uses_page_level_language_for_non_root_targets():
    payload = _improved_payload()
    payload["manifest"]["target_url"] = "https://www.transglobalus.com/about"
    payload["manifest"]["target_domain"] = "transglobalus.com"
    payload["evidence"]["items"] = [
        {
            "evidence_type": "run_manifest",
            "url_or_domain": "https://www.transglobalus.com/about",
            "source_class": "internal_metadata",
            "normalized_summary": "Run scope captured in the V2 manifest.",
        },
        {
            "evidence_type": "page_fetch",
            "url_or_domain": "https://www.transglobalus.com/about",
            "source_class": "live_site",
            "normalized_summary": "About page fetch completed.",
        },
    ]

    result = run_release_checks(payload)

    assert "homepage_only_evidence" in result["issues"]
    assert any("primary analyzed page" in warning for warning in result["warnings"])


def test_qa_accepts_plain_english_clear_reasons_without_section_keywords():
    payload = _improved_payload()
    clear_reason = (
        "The section is cautious because the sampled evidence is still limited and the report explains what was captured."
    )
    payload["report_sections"]["competitive_benchmark"]["visible_reason"] = clear_reason
    payload["report_sections"]["competitive_benchmark"]["reason"] = clear_reason
    payload["report_sections"]["priority_findings"]["findings"][0]["visible_reason"] = clear_reason
    payload["report_sections"]["priority_findings"]["findings"][0]["summary"] = clear_reason
    payload["report_sections"]["priority_findings"]["findings"][1]["visible_reason"] = clear_reason
    payload["report_sections"]["priority_findings"]["findings"][1]["summary"] = clear_reason

    result = run_release_checks(payload)

    assert "benchmark_thinness" not in result["issues"]
    assert "prompt_proof_thinness" not in result["issues"]


def test_v2_workflow_exposes_qa_warnings():
    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        compare_to_v1=True,
    )

    assert "qa" in result
    assert "issues" in result["qa"]
    assert "warnings" in result["qa"]
