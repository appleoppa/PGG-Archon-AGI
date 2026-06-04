from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_review_bundle import evaluate_review_bundle, main


def _write(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _bundle_inputs(tmp_path: Path, *, quorum_status: str = "PASS_QUORUM", visible_pass_count: int = 2) -> tuple[Path, Path, Path]:
    readiness = _write(tmp_path / "readiness.json", {
        "schema": "PGGArchonPromotionReadinessPackage/v1",
        "status": "READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW",
        "blockers": [],
    })
    main_gate = _write(tmp_path / "main_patch_gate.json", {
        "schema": "PGGArchonMainPatchGateResult/v1",
        "status": "READY_FOR_DRY_RUN_MAIN_PATCH_REVIEW",
        "blockers": [],
        "target_files": ["tests/fixtures/pgg_archon_regressions.jsonl"],
    })
    quorum = _write(tmp_path / "llm_quorum.json", {
        "schema": "PGGArchonLLMQuorumGateResult/v1",
        "status": quorum_status,
        "required_pass_count": 2,
        "visible_pass_count": visible_pass_count,
        "blockers": [] if quorum_status == "PASS_QUORUM" else ["visible_pass_count_below_threshold"],
    })
    return readiness, main_gate, quorum


def test_review_bundle_ready_when_all_gates_pass(tmp_path: Path) -> None:
    readiness, main_gate, quorum = _bundle_inputs(tmp_path)
    result = evaluate_review_bundle(
        readiness_package=readiness,
        main_patch_gate_result=main_gate,
        llm_quorum_gate_result=quorum,
    )
    assert result.status == "READY_FOR_HUMAN_MAIN_PATCH_REVIEW"
    assert result.blockers == []
    assert result.target_files == ["tests/fixtures/pgg_archon_regressions.jsonl"]
    assert result.visible_pass_count == 2


def test_review_bundle_blocks_when_quorum_fails(tmp_path: Path) -> None:
    readiness, main_gate, quorum = _bundle_inputs(tmp_path, quorum_status="BLOCKED_QUORUM", visible_pass_count=1)
    result = evaluate_review_bundle(
        readiness_package=readiness,
        main_patch_gate_result=main_gate,
        llm_quorum_gate_result=quorum,
    )
    assert result.status == "BLOCKED_REVIEW_BUNDLE"
    assert "llm_quorum_pass" in result.blockers
    assert "llm_visible_pass_threshold" in result.blockers


def test_main_writes_review_bundle(tmp_path: Path, capsys) -> None:
    readiness, main_gate, quorum = _bundle_inputs(tmp_path)
    assert main([
        "--readiness-package", str(readiness),
        "--main-patch-gate", str(main_gate),
        "--llm-quorum-gate", str(quorum),
        "--output-dir", str(tmp_path / "out"),
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "READY_FOR_HUMAN_MAIN_PATCH_REVIEW"
    assert Path(printed["result"]).is_file()
