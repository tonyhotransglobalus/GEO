from pathlib import Path

from scripts.strategy_engine_v2.workflow import build_rollout_metadata, run_strategy_report_v2


def test_v2_payload_exposes_shadow_mode_metadata():
    result = build_rollout_metadata(shadow_run=True, comparable_to_v1=True)

    assert result["shadow_run"] is True
    assert result["comparable_to_v1"] is True
    assert result["promotion_ready"] is False
    assert result["promotion_owner"] == "TBD"
    assert result["checklist_status"] == "pending"


def test_v2_run_payload_threads_rollout_metadata(tmp_path):
    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        shadow_run=True,
        compare_to_v1=True,
        reports_dir=tmp_path,
    )

    assert result["rollout_metadata"] == {
        "shadow_run": True,
        "comparable_to_v1": True,
        "promotion_ready": False,
        "promotion_owner": "TBD",
        "checklist_status": "pending",
    }


def test_v2_run_payload_uses_comparison_eligibility_not_request_flag(tmp_path):
    def build_run_manifest_fn(**kwargs):
        return {
            "target_url": kwargs["url"],
            "target_domain": "transglobalus.com",
            "mode": kwargs["mode"],
            "driver": kwargs["driver"],
            "shadow_run": kwargs["shadow_run"],
            "run_timestamp": "2026-03-30T10:00:00+00:00",
            "comparison_eligibility": {
                "requested": kwargs["compare_to_v1"],
                "eligible": False,
            },
        }

    deps = type(
        "Deps",
        (),
        {
            "build_run_manifest": staticmethod(build_run_manifest_fn),
            "build_v2_evidence_ledger": staticmethod(lambda *, manifest: {"items": [], "count": 0}),
            "adjudicate_v2_sections": staticmethod(lambda *, manifest, evidence: {
                "benchmark": {"status": "omitted", "reason": "Benchmark is thin.", "warning": "Benchmark is omitted because named competitors or winner domains were not captured."},
                "prompt_proof": {"status": "omitted", "reason": "No useful prompt proof was captured.", "warning": "Prompt proof is omitted because exact prompts or winner URLs were not captured."},
                "platform_breakdown": {"status": "omitted", "reason": "No platform-level evidence was captured.", "warning": "Platform breakdown is omitted because sampled platforms were not captured."},
                "change_since_last_run": {"status": "omitted", "reason": "Comparison is not valid for this run.", "warning": "Change-since-last-run is omitted because the runs are not comparable."},
            }),
            "build_v2_report_sections": staticmethod(lambda report_input: {
                "leadership_summary": {"title": "Leadership Summary", "status": "omitted", "trust_label": "How much to trust this", "summary": ["The run is intentionally sparse."], "visible_reason": "Comparison is not valid for this run."},
                "score_explanations": {"title": "Score Explanations", "plain_english_note": "Scores are a guide, not proof.", "terms": [], "weighting": [], "run_context": {}},
                "priority_findings": {"title": "Priority Findings", "findings": []},
                "competitive_benchmark": {"title": "Competitive Benchmark", "status": "omitted", "reason": "Benchmark is thin.", "visible_reason": "Benchmark is omitted because named competitors or winner domains were not captured.", "competitors": [], "sample_note": ""},
                "platform_breakdown": {"title": "Platform Breakdown", "status": "omitted", "reason": "No platform-level evidence was captured.", "visible_reason": "Platform breakdown is omitted because sampled platforms were not captured.", "platforms": [], "sample_note": ""},
                "page_source_evidence": {"title": "Page And Source Evidence", "evidence_items": [], "visible_reason": "The appendix lists the evidence ledger used to build the report."},
                "action_plan": {"title": "Action Plan", "actions": []},
                "proof_appendix": {"title": "Proof Appendix", "manifest": report_input["manifest"], "evidence_count": 0, "adjudication": report_input["adjudication"], "visible_reason": "This appendix preserves the run scope, evidence ledger, and section reasons."},
            }),
            "run_release_checks": staticmethod(lambda report_payload: {"issues": [], "warnings": []}),
            "publish_v2_artifacts": staticmethod(lambda *, brand_name, date_stamp, payload, base_dir=None, run_seed=None, write_compat_markdown=None: {
                "report_dir": (Path(base_dir) if base_dir else Path("output/reports")) / "transglobalus-com-2026-03-30",
                "markdown_path": (Path(base_dir) if base_dir else Path("output/reports")) / "transglobalus-com-2026-03-30" / "GEO-STRATEGY-REPORT-V2.md",
                "compat_markdown_path": (Path(base_dir) if base_dir else Path("output/reports")) / "GEO-STRATEGY-REPORT-V2.md",
                "manifest_path": (Path(base_dir) if base_dir else Path("output/reports")) / "transglobalus-com-2026-03-30" / "GEO-STRATEGY-REPORT-V2.manifest.json",
                "evidence_path": (Path(base_dir) if base_dir else Path("output/reports")) / "transglobalus-com-2026-03-30" / "GEO-STRATEGY-REPORT-V2.evidence.json",
                "comparison_metadata_path": (Path(base_dir) if base_dir else Path("output/reports")) / "transglobalus-com-2026-03-30" / "GEO-STRATEGY-REPORT-V2.comparison-metadata.json",
            }),
        },
    )()

    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        shadow_run=True,
        compare_to_v1=True,
        reports_dir=tmp_path,
        deps=deps,
    )

    assert result["rollout_metadata"]["comparable_to_v1"] is False
