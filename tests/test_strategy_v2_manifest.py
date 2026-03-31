from scripts.strategy_engine_v2.manifest import build_run_manifest
from scripts.strategy_engine_v2.workflow import run_strategy_report_v2
from tests.strategy_v2_samples import sample_v2_workflow_deps


def test_build_run_manifest_records_scope():
    manifest = build_run_manifest(
        url="https://www.transglobalus.com/",
        locale="en-us",
        platforms=["chatgpt", "gemini"],
        competitors=["example.com"],
        mode="script-only",
        driver="script",
    )
    assert manifest["target_url"] == "https://www.transglobalus.com/"
    assert manifest["locale"] == "en-us"
    assert manifest["platforms"] == ["chatgpt", "gemini"]


def test_build_run_manifest_keeps_shadow_comparison_eligible():
    manifest = build_run_manifest(
        url="https://www.transglobalus.com/",
        locale="en-us",
        platforms=["chatgpt"],
        competitors=["example.com"],
        mode="script-only",
        driver="script",
        compare_to_v1=True,
        shadow_run=True,
    )

    assert manifest["comparison_eligibility"]["requested"] is True
    assert manifest["comparison_eligibility"]["eligible"] is True


def test_run_strategy_report_v2_uses_manifest_as_authoritative_state():
    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        shadow_run=True,
        compare_to_v1=True,
        locale="en-us",
        platforms=["chatgpt"],
        competitors=["example.com"],
        mode="script-only",
        driver="script",
        deps=sample_v2_workflow_deps(),
    )

    assert result["version"] == "v2"
    assert result["status"] == "shadow"
    assert result["manifest"]["shadow_run"] is True
    assert result["manifest"]["comparison_eligibility"]["requested"] is True
    assert set(result) == {
        "adjudication",
        "artifact_paths",
        "evidence",
        "manifest",
        "qa",
        "release_warnings",
        "report_sections",
        "rollout_metadata",
        "status",
        "version",
    }
    assert result["rollout_metadata"] == {
        "shadow_run": True,
        "comparable_to_v1": True,
        "promotion_ready": False,
        "promotion_owner": "TBD",
        "checklist_status": "pending",
    }
    assert result["evidence"]["count"] >= 1
    assert any(item["evidence_type"] == "run_manifest" for item in result["evidence"]["items"])
    assert set(result["adjudication"]) == {
        "benchmark",
        "change_since_last_run",
        "platform_breakdown",
        "prompt_proof",
    }
    assert "issues" in result["qa"]
    assert "warnings" in result["qa"]
    assert result["artifact_paths"]["markdown_path"].endswith("GEO-STRATEGY-REPORT-V2.md")
    assert list(result["report_sections"].keys()) == [
        "leadership_summary",
        "score_explanations",
        "priority_findings",
        "competitive_benchmark",
        "platform_breakdown",
        "page_source_evidence",
        "action_plan",
        "proof_appendix",
    ]
