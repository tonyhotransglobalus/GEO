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
