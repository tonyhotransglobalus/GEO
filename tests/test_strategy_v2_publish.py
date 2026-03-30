from __future__ import annotations

import json
from pathlib import Path

from scripts.strategy_engine_v2.publish import (
    DEFAULT_REPORTS_DIR,
    build_v2_output_paths,
    publish_v2_artifacts,
)
from scripts.strategy_engine_v2.workflow import run_strategy_report_v2


def _payload(*, compare_to_v1: bool = False, shadow_run: bool = True) -> dict:
    return {
        "manifest": {
            "target_url": "https://www.transglobalus.com/",
            "target_domain": "transglobalus.com",
            "mode": "script-only",
            "driver": "script",
            "shadow_run": shadow_run,
            "comparison_eligibility": {
                "requested": compare_to_v1,
                "eligible": compare_to_v1,
            },
        },
        "evidence": {
            "items": [
                {
                    "evidence_type": "run_manifest",
                    "url_or_domain": "https://www.transglobalus.com/",
                    "source_class": "internal_metadata",
                    "normalized_summary": "Run scope captured in the V2 manifest.",
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
        "qa": {
            "issues": ["benchmark_thinness"],
            "warnings": ["Benchmark is not decision-grade in this run because named competitor evidence is still thin."],
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
                "visible_reason": "Benchmark is directional because the sample is incomplete.",
            },
            "score_explanations": {
                "title": "Score Explanations",
                "plain_english_note": "Scores are a guide, not proof.",
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
        },
    }


def test_v2_shadow_run_writes_versioned_outputs(tmp_path):
    paths = build_v2_output_paths(
        "TransGlobal Holding Company",
        "2026-03-30",
        base_dir=tmp_path,
    )

    assert paths["markdown_path"].name == "GEO-STRATEGY-REPORT-V2.md"
    assert paths["manifest_path"].name == "GEO-STRATEGY-REPORT-V2.manifest.json"
    assert paths["evidence_path"].name == "GEO-STRATEGY-REPORT-V2.evidence.json"
    assert paths["comparison_metadata_path"].name == "GEO-STRATEGY-REPORT-V2.comparison-metadata.json"


def test_v2_default_reports_dir_is_repo_root_relative():
    expected = Path(__file__).resolve().parents[1] / "output" / "reports"

    assert DEFAULT_REPORTS_DIR.is_absolute()
    assert DEFAULT_REPORTS_DIR == expected


def test_v2_shadow_run_preserves_compatibility_markdown(tmp_path):
    first_paths = publish_v2_artifacts(
        brand_name="TransGlobal Holding Company",
        date_stamp="2026-03-30",
        payload=_payload(compare_to_v1=False, shadow_run=False),
        base_dir=tmp_path,
    )
    first_compat = first_paths["compat_markdown_path"].read_text(encoding="utf-8")

    shadow_payload = _payload(compare_to_v1=False)
    shadow_payload["manifest"]["shadow_run"] = True
    shadow_payload["report_sections"]["leadership_summary"]["summary"] = [
        "The shadow run should not replace the compatibility copy.",
    ]

    publish_v2_artifacts(
        brand_name="TransGlobal Holding Company",
        date_stamp="2026-03-30",
        payload=shadow_payload,
        base_dir=tmp_path,
    )

    assert first_paths["compat_markdown_path"].read_text(encoding="utf-8") == first_compat


def test_v2_preserves_comparison_metadata_when_follow_up_run_skips_comparison(tmp_path):
    first_paths = publish_v2_artifacts(
        brand_name="TransGlobal Holding Company",
        date_stamp="2026-03-30",
        payload=_payload(compare_to_v1=True),
        base_dir=tmp_path,
    )
    first_metadata = first_paths["comparison_metadata_path"].read_text(encoding="utf-8")

    publish_v2_artifacts(
        brand_name="TransGlobal Holding Company",
        date_stamp="2026-03-30",
        payload=_payload(compare_to_v1=False),
        base_dir=tmp_path,
    )

    assert first_paths["comparison_metadata_path"].read_text(encoding="utf-8") == first_metadata


def test_v2_slugify_uses_run_seed_when_brand_name_is_missing(tmp_path):
    paths = build_v2_output_paths(
        "",
        "2026-03-30",
        base_dir=tmp_path,
        run_seed="https://www.transglobalus.com/",
    )

    assert paths["report_dir"].name.startswith("transglobalus-com-2026-03-30-")
    assert "site" not in paths["report_dir"].name


def test_v2_output_paths_use_run_seed_to_separate_same_day_runs(tmp_path):
    first = build_v2_output_paths(
        "TransGlobal Holding Company",
        "2026-03-30",
        base_dir=tmp_path,
        run_seed="2026-03-30T10:00:00Z|https://www.transglobalus.com/",
    )
    second = build_v2_output_paths(
        "TransGlobal Holding Company",
        "2026-03-30",
        base_dir=tmp_path,
        run_seed="2026-03-30T11:00:00Z|https://www.transglobalus.com/",
    )

    assert first["report_dir"] != second["report_dir"]
    assert first["report_dir"].name != second["report_dir"].name


def test_publish_v2_artifacts_writes_manifest_evidence_and_comparison_metadata(tmp_path):
    paths = publish_v2_artifacts(
        brand_name="TransGlobal Holding Company",
        date_stamp="2026-03-30",
        payload=_payload(compare_to_v1=True, shadow_run=False),
        base_dir=tmp_path,
    )

    assert paths["markdown_path"].exists()
    assert paths["compat_markdown_path"].exists()
    assert paths["manifest_path"].exists()
    assert paths["evidence_path"].exists()
    assert paths["comparison_metadata_path"].exists()

    comparison_metadata = json.loads(paths["comparison_metadata_path"].read_text(encoding="utf-8"))
    assert comparison_metadata["compare_to_v1"] is True
    assert comparison_metadata["comparison_eligible"] is True


def test_run_strategy_report_v2_uses_publisher_and_returns_artifact_paths(tmp_path):
    result = run_strategy_report_v2(
        "https://www.transglobalus.com/",
        compare_to_v1=True,
        shadow_run=True,
        reports_dir=tmp_path,
    )

    assert result["status"] == "stub"
    assert "artifact_paths" in result
    assert Path(result["artifact_paths"]["markdown_path"]).name == "GEO-STRATEGY-REPORT-V2.md"
    assert Path(result["artifact_paths"]["compat_markdown_path"]).name == "GEO-STRATEGY-REPORT-V2.md"
    assert Path(result["artifact_paths"]["manifest_path"]).exists()
    assert Path(result["artifact_paths"]["evidence_path"]).exists()
    assert Path(result["artifact_paths"]["comparison_metadata_path"]).exists()
