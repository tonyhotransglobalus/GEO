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
