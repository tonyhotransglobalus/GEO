from scripts.strategy_engine_v2.manifest import build_run_manifest
from scripts.strategy_engine_v2.workflow import run_strategy_report_v2


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
    )

    assert result["version"] == "v2"
    assert result["status"] == "stub"
    assert result["manifest"]["shadow_run"] is True
    assert result["manifest"]["comparison_eligibility"]["requested"] is True
    assert set(result) == {"evidence", "manifest", "status", "version"}
    assert result["evidence"]["count"] == 1
    assert result["evidence"]["items"][0]["evidence_type"] == "run_manifest"
