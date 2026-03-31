from pathlib import Path

import requests

from scripts.strategy_engine_v2 import workflow as workflow_module
from scripts.strategy_engine_v2.workflow import run_strategy_report_v2
from tests.strategy_v2_samples import sample_v1_audit_payload, sample_v2_workflow_deps


def _workflow_deps():
    calls = []

    def build_run_manifest_fn(**kwargs):
        calls.append(("build_run_manifest", kwargs["url"]))
        return {
            "target_url": kwargs["url"],
            "target_domain": "transglobalus.com",
            "mode": kwargs["mode"],
            "driver": kwargs["driver"],
            "shadow_run": kwargs["shadow_run"],
            "run_timestamp": "2026-03-30T10:00:00+00:00",
            "comparison_eligibility": {
                "requested": kwargs["compare_to_v1"],
                "eligible": kwargs["compare_to_v1"],
            },
        }

    def build_v2_evidence_ledger_fn(*, manifest, audit_data=None, **_kwargs):
        calls.append(("build_v2_evidence_ledger", manifest["target_url"]))
        assert audit_data["brand_name"] == "TransGlobal Holding Company"
        return {
            "items": [
                {
                    "evidence_type": "run_manifest",
                    "source_class": "internal_metadata",
                    "observed_vs_inferred": "observed",
                    "url_or_domain": manifest["target_url"],
                    "normalized_summary": "Run scope captured in the V2 manifest.",
                }
            ],
            "count": 1,
            "target_url": manifest["target_url"],
        }

    def run_v1_audit_fn(**kwargs):
        calls.append(("run_v1_audit", kwargs["url"]))
        return sample_v1_audit_payload()

    def adjudicate_v2_sections_fn(*, manifest, evidence, audit_data=None, comparison_context=None):
        calls.append(("adjudicate_v2_sections", evidence["count"]))
        assert audit_data["brand_name"] == "TransGlobal Holding Company"
        assert isinstance(comparison_context, dict)
        return {
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
        }

    def build_v2_report_sections_fn(report_input):
        calls.append(("build_v2_report_sections", report_input["manifest"]["target_url"]))
        assert report_input["audit_data"]["brand_name"] == "TransGlobal Holding Company"
        return {
            "leadership_summary": {
                "title": "Leadership Summary",
                "status": "directional",
                "trust_label": "How much to trust this",
                "summary": [
                    "The V2 report keeps the top layer short and the proof visible.",
                    "Run mode: script-only.",
                ],
                "visible_reason": "Benchmark is directional because the sample is incomplete.",
            },
            "score_explanations": {
                "title": "Score Explanations",
                "plain_english_note": "Scores are a guide, not proof.",
                "terms": [
                    {
                        "label": "Decision-grade",
                        "plain_english": "The evidence is strong enough to support a client-facing claim.",
                    }
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
                    "shadow_run": True,
                },
                "evidence_count": 1,
                "adjudication": {},
                "visible_reason": "This appendix preserves the run scope, evidence ledger, and section reasons.",
            },
        }

    def run_release_checks_fn(report_payload):
        calls.append(("run_release_checks", report_payload["manifest"]["target_url"]))
        return {
            "issues": ["benchmark_thinness"],
            "warnings": ["Benchmark is not decision-grade in this run because named competitor evidence is still thin."],
        }

    def publish_v2_artifacts_fn(*, brand_name, date_stamp, payload, base_dir=None, run_seed=None, write_compat_markdown=None):
        calls.append(
            (
                "publish_v2_artifacts",
                {
                    "brand_name": brand_name,
                    "date_stamp": date_stamp,
                    "payload": payload,
                    "base_dir": base_dir,
                    "run_seed": run_seed,
                    "write_compat_markdown": write_compat_markdown,
                },
            )
        )
        report_dir = (Path(base_dir) if base_dir else Path("output/reports")) / "transglobalus-com-2026-03-30"
        return {
            "report_dir": report_dir,
            "markdown_path": report_dir / "GEO-STRATEGY-REPORT-V2.md",
            "compat_markdown_path": report_dir / "GEO-STRATEGY-REPORT-V2.md",
            "manifest_path": report_dir / "GEO-STRATEGY-REPORT-V2.manifest.json",
            "evidence_path": report_dir / "GEO-STRATEGY-REPORT-V2.evidence.json",
            "comparison_metadata_path": report_dir / "GEO-STRATEGY-REPORT-V2.comparison-metadata.json",
        }

    class Deps:
        build_run_manifest = staticmethod(build_run_manifest_fn)
        run_v1_audit = staticmethod(run_v1_audit_fn)
        build_v2_evidence_ledger = staticmethod(build_v2_evidence_ledger_fn)
        adjudicate_v2_sections = staticmethod(adjudicate_v2_sections_fn)
        build_v2_report_sections = staticmethod(build_v2_report_sections_fn)
        run_release_checks = staticmethod(run_release_checks_fn)
        publish_v2_artifacts = staticmethod(publish_v2_artifacts_fn)

    return calls, Deps()


def test_run_strategy_report_v2_returns_manifest_evidence_and_sections(tmp_path):
    calls, deps = _workflow_deps()

    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        compare_to_v1=True,
        shadow_run=True,
        reports_dir=tmp_path,
        deps=deps,
    )

    assert "manifest" in result
    assert "evidence" in result
    assert "report_sections" in result
    assert "qa" in result
    assert "artifact_paths" in result
    assert "release_warnings" in result
    assert result["manifest"]["target_domain"] == "transglobalus.com"
    assert result["evidence"]["count"] == 1
    assert result["report_sections"]["leadership_summary"]["status"] == "directional"
    assert result["report_sections"]["leadership_summary"]["trust_label"] == "How much to trust this"
    assert result["report_sections"]["competitive_benchmark"]["status"] == "directional"
    assert result["report_sections"]["competitive_benchmark"]["visible_reason"] == "Benchmark is directional because the sample is incomplete."
    assert result["qa"]["warnings"] == [
        "Benchmark is not decision-grade in this run because named competitor evidence is still thin."
    ]
    assert result["release_warnings"] == result["qa"]["warnings"]
    assert "benchmark_thinness" in result["qa"]["issues"]
    assert result["rollout_metadata"] == {
        "shadow_run": True,
        "comparable_to_v1": True,
        "promotion_ready": False,
        "promotion_owner": "TBD",
        "checklist_status": "pending",
    }
    assert Path(result["artifact_paths"]["markdown_path"]).name == "GEO-STRATEGY-REPORT-V2.md"
    assert Path(result["artifact_paths"]["manifest_path"]).name == "GEO-STRATEGY-REPORT-V2.manifest.json"
    assert Path(result["artifact_paths"]["evidence_path"]).name == "GEO-STRATEGY-REPORT-V2.evidence.json"
    assert Path(result["artifact_paths"]["comparison_metadata_path"]).name == "GEO-STRATEGY-REPORT-V2.comparison-metadata.json"
    assert [call[0] for call in calls] == [
        "build_run_manifest",
        "run_v1_audit",
        "build_v2_evidence_ledger",
        "adjudicate_v2_sections",
        "build_v2_report_sections",
        "run_release_checks",
        "publish_v2_artifacts",
    ]
    publish_call = next(item for item in calls if item[0] == "publish_v2_artifacts")[1]
    assert publish_call["base_dir"] == tmp_path
    assert publish_call["run_seed"] == "2026-03-30T10:00:00+00:00|https://www.transglobalus.com/|script-only|script"
    assert publish_call["write_compat_markdown"] is False
    assert set(publish_call["payload"]) == {
        "manifest",
        "evidence",
        "adjudication",
        "qa",
        "report_sections",
        "rollout_metadata",
        "audit_data",
        "comparison_context",
    }


def test_load_previous_comparison_context_reads_latest_compatible_run(tmp_path):
    previous_report_dir = tmp_path / "transglobalus-com-2026-03-30-run-a"
    previous_report_dir.mkdir(parents=True)
    (previous_report_dir / "GEO-STRATEGY-REPORT-V2.manifest.json").write_text(
        """{
  "target_url": "https://www.transglobalus.com/",
  "target_domain": "transglobalus.com",
  "locale": "en-us",
  "platforms": [],
  "run_timestamp": "2026-03-30T10:00:00+00:00"
}""",
        encoding="utf-8",
    )
    (previous_report_dir / "GEO-STRATEGY-REPORT-V2.evidence.json").write_text(
        """{
  "items": [
    {"evidence_type": "run_manifest", "url_or_domain": "https://www.transglobalus.com/"},
    {"evidence_type": "linked_page", "url_or_domain": "https://www.transglobalus.com/life-insurance-annuity/"}
  ],
  "count": 2
}""",
        encoding="utf-8",
    )

    context = workflow_module._load_previous_comparison_context(
        manifest={
            "target_url": "https://www.transglobalus.com/",
            "target_domain": "transglobalus.com",
            "locale": "en-us",
            "platforms": [],
            "run_timestamp": "2026-03-31T10:00:00+00:00",
            "comparison_eligibility": {"requested": True, "eligible": True},
        },
        evidence={
            "items": [
                {"evidence_type": "run_manifest", "url_or_domain": "https://www.transglobalus.com/"},
                {"evidence_type": "linked_page", "url_or_domain": "https://www.transglobalus.com/life-insurance-annuity/"},
                {"evidence_type": "linked_page", "url_or_domain": "https://www.transglobalus.com/wealth-management/"},
            ],
            "count": 3,
        },
        reports_dir=tmp_path,
    )

    assert context["previous_manifest"]["run_timestamp"] == "2026-03-30T10:00:00+00:00"
    assert context["previous_snapshot"]["non_primary_page_count"] == 1
    assert context["current_snapshot"]["non_primary_page_count"] == 2
    assert context["change_points"] >= 1


def test_run_v1_audit_tolerates_opportunity_timeouts(monkeypatch):
    def fake_orchestrate_audit(*args, **kwargs):
        keyword_suggestions = workflow_module.opportunity_plugin.fetch_keyword_suggestions(
            "life insurance"
        )
        serp_snapshot = workflow_module.opportunity_plugin.fetch_serp_snapshot(
            "life insurance"
        )
        payload = sample_v1_audit_payload()
        payload["bridge_probe"] = {
            "keyword_suggestions": keyword_suggestions,
            "serp_snapshot": serp_snapshot,
        }
        return payload

    def raising_fetch(*args, **kwargs):
        raise requests.ConnectTimeout("timed out")

    monkeypatch.setattr(workflow_module, "orchestrate_audit", fake_orchestrate_audit)
    monkeypatch.setattr(
        workflow_module.opportunity_plugin,
        "fetch_keyword_suggestions",
        raising_fetch,
    )
    monkeypatch.setattr(
        workflow_module.opportunity_plugin,
        "fetch_serp_snapshot",
        raising_fetch,
    )

    result = workflow_module._run_v1_audit(url="https://www.transglobalus.com/")

    assert result["bridge_probe"]["keyword_suggestions"] == []
    assert result["bridge_probe"]["serp_snapshot"] == []
    assert len(result["v2_bridge_metadata"]["network_fallbacks"]) == 2
    assert all(
        item["component"] == "opportunity"
        for item in result["v2_bridge_metadata"]["network_fallbacks"]
    )
    assert len(
        result["client_report_sections"]["technical_proof_appendix"]["bridge_warnings"]
    ) == 2


def test_run_strategy_report_v2_clears_prompt_proof_thinness_when_sampled_query_evidence_is_explained():
    deps = sample_v2_workflow_deps()
    audit_data = sample_v1_audit_payload()
    audit_data["client_report_sections"]["prompt_query_proof"] = {
        "sampling_note": "Exact platform captures were not retained in this sample.",
        "rows": [],
    }
    deps.run_v1_audit = lambda **_kwargs: audit_data

    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        shadow_run=True,
        compare_to_v1=False,
        deps=deps,
    )

    assert result["adjudication"]["prompt_proof"]["status"] == "directional"
    assert "prompt_proof_thinness" not in result["qa"]["issues"]
