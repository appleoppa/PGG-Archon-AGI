from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_mimo_micro_auditor import (
    MicroAuditClaim,
    BOUNDARY,
    deterministic_boundary_check,
    parse_json_candidate,
    run_micro_audits,
)


def test_parse_json_candidate_handles_fences_and_prefix() -> None:
    assert parse_json_candidate('```json\n{"audit_verdict":"PASS"}\n```') == {"audit_verdict": "PASS"}
    assert parse_json_candidate('prefix {"audit_verdict":"WATCH"} suffix') == {"audit_verdict": "WATCH"}


def test_deterministic_boundary_check_flags_obvious_overclaim() -> None:
    claim = MicroAuditClaim("agi", "可以宣称达到L2和full AGI", "不可称达到L2或full AGI")
    result = deterministic_boundary_check(claim)
    assert result["status"] == "WATCH"
    assert result["hits"]


def test_run_micro_audits_no_mimo_writes_summary(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.json"
    artifact.write_text(json.dumps({"ok": True}), encoding="utf-8")
    claim = MicroAuditClaim("boundary", "30题smoke真实运行", "不可称官方完整分数")
    summary = run_micro_audits(
        artifact_path=artifact,
        claims=[claim],
        output_dir=tmp_path / "audit",
        call_mimo=False,
    )
    assert summary.schema == "PGGArchonMiMoMicroAuditSummary/v1"
    assert summary.provider == "mimo_v25_pro_auditor"
    assert summary.role == "third_party_benchmark_judge_only"
    assert summary.judge_called is False
    assert summary.pass_count == 0
    assert summary.timeout_count == 0
    assert summary.results[0]["status"] == "LOCAL_PRECHECK_ONLY"
    assert summary.results[0]["audit_verdict"] is None
    assert summary.boundary == BOUNDARY
