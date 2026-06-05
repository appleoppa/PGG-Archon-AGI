from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_external_benchmark_bridge import (
    BOUNDARY,
    CrossDomainTask,
    EvolutionGainItem,
    build_bridge_report,
    compute_evolution_gain,
    default_external_benchmark_sources,
    write_json_report,
)


def test_default_external_benchmark_sources_separate_official_adapted_internal() -> None:
    sources = default_external_benchmark_sources()
    by_id = {s.source_id: s for s in sources}
    assert by_id["lm_eval_harness"].source_type == "official_harness"
    assert by_id["openai_evals"].source_type == "official_harness"
    assert by_id["promptfoo"].source_type == "adapted_external"
    assert by_id["pgg_internal_100"].source_type == "internal_frozen_smoke"
    assert "never label as official" in by_id["pgg_internal_100"].license_note.lower()
    assert all(s.boundary == BOUNDARY for s in sources)


def test_bridge_report_marks_agnes_as_third_party_judge_only_and_case_0006_watch(tmp_path: Path) -> None:
    case_root = tmp_path / "0006-PGGMS-20260605-demo"
    (case_root / "正式文书").mkdir(parents=True)
    (case_root / "总结报告").mkdir()
    (case_root / "审计记录").mkdir()
    (case_root / "正式文书" / "PGG-MS-20260605-0006-民事起诉状_FINAL_v2.md").write_text("FINAL v2", encoding="utf-8")
    (case_root / "总结报告" / "PGG-MS-20260605-0006-案件台账.md").write_text("CMS BLOCKED", encoding="utf-8")
    (case_root / "审计记录" / "PGG-MS-20260605-0006-cms_case_guard_validate.json").write_text('{"status":"BLOCKED"}', encoding="utf-8")

    report = build_bridge_report(case_root=case_root)
    assert report.schema == "PGGArchonExternalBenchmarkBridge/v1"
    assert report.evidence_summary["cross_domain_task_count"] == 1
    assert report.evidence_summary["task_status_counts"] == {"WATCH": 1}
    assert report.agnes_policy["role"] == "third_party_benchmark_judge_only"
    assert "daily task handling" in report.agnes_policy["forbidden"]
    assert report.case_0006_review["status"] == "WATCH"
    assert "CMS guard recorded BLOCKED" in report.case_0006_review["open_gaps"]


def test_compute_evolution_gain_reports_pass_delta_without_hiding_regressions() -> None:
    report = compute_evolution_gain(
        baseline_label="before",
        evolved_label="after",
        items=[
            EvolutionGainItem("task-a", "WATCH", "PASS", 0.5, 1.0, "/tmp/a.json"),
            EvolutionGainItem("task-b", "PASS", "WATCH", 1.0, 0.8, "/tmp/b.json", "minor regression"),
        ],
    )
    assert report.schema == "PGGArchonEvolutionGainReport/v1"
    assert report.status == "WATCH"
    assert report.aggregate["pass_delta"] == 0
    assert report.aggregate["regression_count"] == 1
    assert report.aggregate["score_delta_mean"] == 0.15


def test_write_json_report_round_trips(tmp_path: Path) -> None:
    task = CrossDomainTask(
        task_id="research-open-source-evals",
        domain="research",
        title="Open-source eval framework scan",
        real_or_synthetic="real",
        source_of_truth="GitHub API metadata",
        input_artifacts=[],
        output_artifacts=[],
        acceptance_criteria=["records source URLs"],
        verifier="read report JSON",
        status="PASS",
        evidence_paths=["/tmp/source.json"],
    )
    report = build_bridge_report(extra_tasks=[task])
    out = Path(write_json_report(report, tmp_path / "bridge.json"))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "PGGArchonExternalBenchmarkBridge/v1"
    assert data["cross_domain_tasks"][0]["task_id"] == "research-open-source-evals"
    assert data["boundary"] == BOUNDARY
