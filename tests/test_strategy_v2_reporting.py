from scripts.strategy_engine_v2.reporting import build_v2_report_sections


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
