from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_audited_manifest_gate import default_promptfoo_claims
from agent.pgg_archon_promptfoo_finalize import (
    build_promptfoo_report,
    finalize_promptfoo_suite,
    parse_promptfoo_counts,
)


def test_parse_promptfoo_counts() -> None:
    log = """
Results:
  ✓ 30 passed (100%)
  0 failed (0%)
  0 errors (0%)
Duration: 7m 42s
"""
    assert parse_promptfoo_counts(log) == {"passed_count": 30, "failed_count": 0, "error_count": 0}
    failed_log = """
Results:
  ✓ 45 passed (90.00%)
  ✗ 5 failed (10.00%)
  0 errors (0%)
"""
    assert parse_promptfoo_counts(failed_log) == {"passed_count": 45, "failed_count": 5, "error_count": 0}


def test_build_promptfoo_report_validates_domain_total(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    log = tmp_path / "run.log"
    cfg = tmp_path / "config.yaml"
    raw.write_text(json.dumps({"results": []}), encoding="utf-8")
    log.write_text("Results:\n  ✓ 2 passed (100%)\n  0 failed (0%)\n  0 errors (0%)\n", encoding="utf-8")
    cfg.write_text("tests: []", encoding="utf-8")
    with pytest.raises(ValueError, match="domains total"):
        build_promptfoo_report(
            raw_result=raw,
            run_log=log,
            config=cfg,
            prompt=None,
            provider=None,
            output_dir=tmp_path / "out",
            suite_id="suite",
            source_type="official_harness_smoke",
            domains={"x": 1},
        )


def test_promptfoo_claims_use_real_sample_count() -> None:
    claims = default_promptfoo_claims(sample_count=50, suite_label="自建promptfoo CLI smoke（使用promptfoo官方CLI工具执行）")
    assert "50题" in claims[0].claim
    assert "50/50" in claims[0].claim
    assert "30/30" not in claims[0].claim
    assert "50题smoke不是L2/full AGI证明" in claims[2].claim


def test_finalize_promptfoo_suite_no_mimo_writes_manifest(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    log = tmp_path / "run.log"
    cfg = tmp_path / "config.yaml"
    manifest = tmp_path / "EVOLUTION_MANIFEST.json"
    raw.write_text(json.dumps({"results": []}), encoding="utf-8")
    log.write_text("Results:\n  ✓ 3 passed (100%)\n  0 failed (0%)\n  0 errors (0%)\n", encoding="utf-8")
    cfg.write_text("tests: []", encoding="utf-8")
    result = finalize_promptfoo_suite(
        raw_result=raw,
        run_log=log,
        config=cfg,
        prompt=None,
        provider=None,
        output_dir=tmp_path / "out",
        suite_id="suite3",
        source_type="official_harness_smoke_test",
        domains={"a": 1, "b": 1, "legal_case": 1},
        manifest_key="latest_suite3",
        title="suite3",
        manifest_path=manifest,
        call_mimo=False,
        legal_boundary_precheck=True,
    )
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["latest_suite3"]["status"] == "WATCH"
    assert data["latest_suite3"]["extra"]["sample_count"] == 3
    assert data["latest_suite3"]["legal_boundary_gate"]["status"] == "PASS"
    report_path = Path(data["latest_suite3"]["artifact_path"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["legal_boundary_statements"]
    assert "mimo_judge_not_called" in data["latest_suite3"]["audit_gate"]["downgrade_reasons"]
    assert result["gate"].final_status == "WATCH"
