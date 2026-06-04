from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_main_patch_gate import evaluate_main_patch_gate, main


def _package(tmp_path: Path, *, target: str = "tests/fixtures/pgg_archon_regressions.jsonl", status: str = "READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW") -> Path:
    diff = tmp_path / "candidate.diff"
    diff.write_text(f"diff --git a/{target} b/{target}\n--- a/{target}\n+++ b/{target}\n", encoding="utf-8")
    pkg = tmp_path / "promotion_readiness_package.json"
    pkg.write_text(json.dumps({
        "schema": "PGGArchonPromotionReadinessPackage/v1",
        "status": status,
        "blockers": [],
        "patch_diff": str(diff),
        "readiness_checks": {
            "patch_apply_passed": True,
            "regression_tasks_exists": True,
        },
    }), encoding="utf-8")
    return pkg


def test_main_patch_gate_ready_for_allowed_test_fixture(tmp_path: Path) -> None:
    result = evaluate_main_patch_gate(_package(tmp_path))
    assert result.status == "READY_FOR_DRY_RUN_MAIN_PATCH_REVIEW"
    assert result.blockers == []
    assert result.target_files == ["tests/fixtures/pgg_archon_regressions.jsonl"]


def test_main_patch_gate_blocks_disallowed_agent_target(tmp_path: Path) -> None:
    result = evaluate_main_patch_gate(_package(tmp_path, target="agent/core_security.py"))
    assert result.status == "BLOCKED_MAIN_PATCH_GATE"
    assert "targets_allowed" in result.blockers


def test_main_patch_gate_blocks_non_ready_package(tmp_path: Path) -> None:
    result = evaluate_main_patch_gate(_package(tmp_path, status="BLOCKED_READINESS_PACKAGE"))
    assert result.status == "BLOCKED_MAIN_PATCH_GATE"
    assert "package_ready" in result.blockers


def test_main_cli_writes_gate_result(tmp_path: Path, capsys) -> None:
    assert main(["--readiness-package", str(_package(tmp_path)), "--output-dir", str(tmp_path / "out")]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "READY_FOR_DRY_RUN_MAIN_PATCH_REVIEW"
    assert Path(printed["result"]).is_file()
