from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_llm_quorum_gate import evaluate_llm_quorum_gate, main


def _ev(tmp_path: Path, name: str, *, status: str = "ok_visible", verdict: str = "PASS", chars: int = 100) -> Path:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({
        "label": name,
        "provider": name,
        "model": name,
        "status": status,
        "visible_output_chars": chars,
        "classified_verdict": verdict,
    }), encoding="utf-8")
    return path


def test_llm_quorum_gate_passes_two_of_three(tmp_path: Path) -> None:
    result = evaluate_llm_quorum_gate([
        _ev(tmp_path, "gpt", verdict="PASS"),
        _ev(tmp_path, "deepseek", verdict="PASS"),
        _ev(tmp_path, "minimax", verdict="BLOCKED"),
    ], required_pass_count=2)
    assert result.status == "PASS_QUORUM"
    assert result.visible_pass_count == 2
    assert result.blockers == []


def test_llm_quorum_gate_blocks_below_threshold(tmp_path: Path) -> None:
    result = evaluate_llm_quorum_gate([
        _ev(tmp_path, "gpt", verdict="PASS"),
        _ev(tmp_path, "deepseek", verdict="BLOCKED"),
        _ev(tmp_path, "minimax", status="http_error", verdict="ERROR", chars=0),
    ], required_pass_count=2)
    assert result.status == "BLOCKED_QUORUM"
    assert result.visible_pass_count == 1
    assert "visible_pass_count_below_threshold" in result.blockers


def test_llm_quorum_classifies_top_level_pass_despite_nested_candidate_blocked(tmp_path: Path) -> None:
    path = tmp_path / "mimo.json"
    path.write_text(json.dumps({
        "label": "mimo",
        "provider": "mimo_v25_pro_auditor",
        "model": "mimo-v2.5-pro",
        "status": "ok_visible",
        "visible_output_chars": 300,
        "text_preview": "```json\n{\"model_verdict\":\"PASS\",\"feasibility_ok\":true,\"selected_gene_id\":114,\"candidate_decisions\":[{\"gene_id\":112,\"decision\":\"BLOCKED\"}]}\n```",
    }), encoding="utf-8")
    result = evaluate_llm_quorum_gate([path], required_pass_count=1)
    assert result.status == "PASS_QUORUM"
    assert result.visible_pass_count == 1
    assert result.model_results[0]["classified_verdict"] == "PASS"


def test_main_writes_quorum_result(tmp_path: Path, capsys) -> None:
    assert main([
        "--evidence", str(_ev(tmp_path, "gpt", verdict="PASS")),
        "--evidence", str(_ev(tmp_path, "deepseek", verdict="PASS")),
        "--required-pass-count", "2",
        "--output-dir", str(tmp_path / "out"),
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "PASS_QUORUM"
    assert Path(printed["result"]).is_file()
