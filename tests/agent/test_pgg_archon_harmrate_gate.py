"""Tests for PGG internal HarmRate gate."""

from __future__ import annotations

from pathlib import Path

from agent.pgg_archon_harmrate_gate import compute_harmrate, write_harmrate_report


def test_low_risk_allows() -> None:
    out = compute_harmrate({"risk": 0.05, "uncertainty": 0.05, "source_confidence": 0.95, "regression_risk": 0.0, "overclaim_risk": 0.0})
    assert out["decision"] == "ALLOW"
    assert out["APEX_MOSS_VERIFIED"] is False
    assert out["zero_risk_claim"] is False


def test_high_harmrate_blocks() -> None:
    out = compute_harmrate({"risk": 0.9, "uncertainty": 0.8, "source_confidence": 0.2, "regression_risk": 0.7, "overclaim_risk": 0.8})
    assert out["decision"] == "BLOCK"
    assert out["harmrate"] >= out["thresholds"]["block"]


def test_low_source_confidence_watches() -> None:
    out = compute_harmrate({"risk": 0.05, "uncertainty": 0.05, "source_confidence": 0.6})
    assert out["decision"] == "WATCH"
    assert "low_source_confidence" not in out["reasons"] or out["inputs"]["source_confidence"] < 0.75


def test_apex_moss_verified_claim_blocks_until_source() -> None:
    out = compute_harmrate({"risk": 0.01, "uncertainty": 0.01, "source_confidence": 1.0, "apex_moss_verified_claim": True})
    assert out["decision"] == "BLOCK"
    assert "apex_moss_verified_claim_blocked_until_independent_source" in out["reasons"]


def test_sensitive_task_is_stricter() -> None:
    out = compute_harmrate({"risk": 0.2, "uncertainty": 0.2, "source_confidence": 0.7, "task_type": "legal"})
    assert out["decision"] in {"WATCH", "BLOCK"}
    assert "sensitive_task_stricter_threshold" in out["reasons"]


def test_write_report(tmp_path: Path) -> None:
    report = compute_harmrate({"risk": 0.1, "source_confidence": 0.9})
    path = write_harmrate_report(report, tmp_path)
    assert Path(path).exists()
