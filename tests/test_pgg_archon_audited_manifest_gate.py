from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_audited_manifest_gate import (
    default_promptfoo_30_claims,
    decide_manifest_status,
    write_audited_manifest_entry,
)


def test_decide_manifest_status_requires_all_audits_pass() -> None:
    final, reasons = decide_manifest_status(
        requested_status="PASS",
        audit_summary={"judge_called": True, "pass_count": 2, "timeout_count": 0, "results": [{}, {}, {}]},
    )
    assert final == "WATCH"
    assert "reported_pass_count_mismatch=2_vs_eligible_0" in reasons
    assert "eligible_audit_pass_count=0_of_3" in reasons

    final, reasons = decide_manifest_status(
        requested_status="PASS",
        audit_summary={"judge_called": True, "pass_count": 3, "timeout_count": 0, "results": [{"status":"OK_PARSED","audit_verdict":"PASS"}, {"status":"OK_PARSED","audit_verdict":"PASS"}, {"status":"OK_PARSED","audit_verdict":"PASS"}]}
    )
    assert final == "PASS"
    assert reasons == []

    final, reasons = decide_manifest_status(
        requested_status="WATCH",
        audit_summary={"judge_called": True, "pass_count": 3, "timeout_count": 0, "results": [{"status":"OK_PARSED","audit_verdict":"PASS"}, {"status":"OK_PARSED","audit_verdict":"PASS"}, {"status":"OK_PARSED","audit_verdict":"PASS"}]}
    )
    assert final == "WATCH"
    assert "requested_status_is_WATCH" in reasons


def test_decide_manifest_status_recomputes_eligible_passes_from_results() -> None:
    final, reasons = decide_manifest_status(
        requested_status="PASS",
        audit_summary={
            "judge_called": True,
            "pass_count": 3,
            "timeout_count": 0,
            "results": [{}, {}, {}],
        },
    )
    assert final == "WATCH"
    assert "reported_pass_count_mismatch=3_vs_eligible_0" in reasons
    assert "eligible_audit_pass_count=0_of_3" in reasons

    final, reasons = decide_manifest_status(
        requested_status="PASS",
        audit_summary={
            "judge_called": True,
            "pass_count": 1,
            "timeout_count": 0,
            "results": [{"status": "LOCAL_PRECHECK_ONLY", "audit_verdict": "PASS"}],
        },
    )
    assert final == "WATCH"
    assert "reported_pass_count_mismatch=1_vs_eligible_0" in reasons

    final, reasons = decide_manifest_status(
        requested_status="PASS",
        audit_summary={
            "judge_called": True,
            "pass_count": 1,
            "timeout_count": 0,
            "results": [{"status": "OK_UNPARSED", "audit_verdict": "PASS"}],
        },
    )
    assert final == "WATCH"
    assert "eligible_audit_pass_count=0_of_1" in reasons


def test_decide_manifest_status_accepts_only_ok_parsed_pass() -> None:
    final, reasons = decide_manifest_status(
        requested_status="PASS",
        audit_summary={
            "judge_called": True,
            "pass_count": 2,
            "timeout_count": 0,
            "results": [
                {"status": "OK_PARSED", "audit_verdict": "PASS"},
                {"status": "OK_PARSED", "audit_verdict": "PASS"},
            ],
        },
    )
    assert final == "PASS"
    assert reasons == []


def test_write_audited_manifest_entry_no_mimo_downgrades_to_watch(tmp_path: Path) -> None:
    manifest = tmp_path / "EVOLUTION_MANIFEST.json"
    artifact = tmp_path / "artifact.json"
    artifact.write_text(json.dumps({"sample_count": 30}), encoding="utf-8")
    result = write_audited_manifest_entry(
        manifest_path=manifest,
        manifest_key="latest_test_gate",
        artifact_path=artifact,
        title="test gate",
        requested_status="PASS",
        claims=default_promptfoo_30_claims(),
        audit_output_dir=tmp_path / "audit",
        call_mimo=False,
        run_legal_boundary_precheck=True,
    )
    assert result.final_status == "WATCH"
    assert "mimo_judge_not_called" in result.downgrade_reasons
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["latest_test_gate"]["status"] == "WATCH"
    assert data["latest_test_gate"]["audit_gate"]["pass_count"] == 0
    assert data["latest_test_gate"]["audit_gate"]["timeout_count"] == 0
    assert "mimo_judge_not_called" in data["latest_test_gate"]["audit_gate"]["downgrade_reasons"]
    assert data["latest_test_gate"]["legal_boundary_gate"]["status"] == "WATCH"
    assert "not MiMo audit PASS" in data["latest_test_gate"]["legal_boundary_gate"]["note"]
