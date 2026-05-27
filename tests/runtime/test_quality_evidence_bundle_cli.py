from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli
from runtime.quality.evidence_bundle import (
    build_quality_evidence_bundle,
    run_test_command_for_evidence,
)


def test_quality_evidence_bundle_builder_sanitizes_aggregate_fields():
    bundle = build_quality_evidence_bundle(
        test_exit_code=0,
        test_summary="tests passed\nsecret output should be folded",
        audit_present=True,
        audit_summary="git commit verified",
        documentation_present=True,
        documentation_summary="report sent",
    )
    assert bundle["schema"] == "ApexRuntimeOSQualityEvidenceBundle/v1"
    assert bundle["evidence"]["test_report"]["present"] is True
    assert "\n" not in bundle["evidence"]["test_report"]["summary"]
    assert bundle["evidence"]["audit_log"]["present"] is True
    assert bundle["evidence"]["documentation"]["present"] is True


@patch("runtime.quality.evidence_bundle.subprocess.run")
def test_run_test_command_for_evidence_uses_exit_code_only(mock_run):
    mock_run.return_value = Mock(returncode=0)
    result = run_test_command_for_evidence(["python", "-m", "pytest"], cwd=None)
    assert result["schema"] == "ApexRuntimeOSTestEvidence/v1"
    assert result["exit_code"] == 0
    assert result["passed"] is True
    assert result["side_effects"] == "runs_requested_test_command_only"
    kwargs = mock_run.call_args.kwargs
    assert kwargs["shell"] is False
    assert kwargs["stdout"] is not None
    assert kwargs["stderr"] is not None


@patch("runtime.quality.evidence_bundle.subprocess.run")
def test_cli_quality_evidence_generates_json_bundle(mock_run, tmp_path):
    mock_run.return_value = Mock(returncode=0)
    out = tmp_path / "quality_evidence.json"
    payload = json.loads(run_apex_runtimeos_cli([
        "quality-evidence",
        "--execute",
        "--test-cmd", "python -m pytest tests/runtime/test_cmmi_gate.py",
        "--audit",
        "--documentation",
        "--output", str(out),
        "--json",
    ]))
    bundle = payload["result"]["bundle"]
    assert payload["object"] == "hermes.apex_runtimeos.quality_evidence"
    assert bundle["schema"] == "ApexRuntimeOSQualityEvidenceBundle/v1"
    assert bundle["evidence"]["test_report"]["present"] is True
    assert bundle["evidence"]["audit_log"]["present"] is True
    assert bundle["evidence"]["documentation"]["present"] is True
    assert out.exists()
    raw = out.read_text(encoding="utf-8")
    assert "pytest" not in raw
    assert "secret" not in raw.lower()


@patch("runtime.quality.evidence_bundle.subprocess.run")
def test_cli_quality_evidence_failed_test_stays_not_present(mock_run):
    mock_run.return_value = Mock(returncode=1)
    payload = json.loads(run_apex_runtimeos_cli([
        "quality-evidence",
        "--execute",
        "--test-cmd", "python -m pytest tests/runtime/test_cmmi_gate.py",
        "--json",
    ]))
    bundle = payload["result"]["bundle"]
    assert bundle["evidence"]["test_report"]["present"] is False
    assert bundle["evidence"]["audit_log"]["present"] is False
