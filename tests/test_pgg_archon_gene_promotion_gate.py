from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agent.pgg_archon_gene_promotion_gate import evaluate_gene_promotion_gate, main


def _db(tmp_path: Path) -> Path:
    path = tmp_path / "pgg_archon.db"
    con = sqlite3.connect(path)
    con.execute("create table gene_lifecycle(gene_id integer primary key, state text not null, quality_score real, promoted_at text, candidate_at text)")
    con.execute("insert into gene_lifecycle(gene_id,state,quality_score,promoted_at,candidate_at) values (347,'candidate',0.86,null,'2026-06-04T00:00:00Z')")
    con.commit(); con.close()
    return path


def test_promotion_gate_blocks_when_claude_not_visible(tmp_path: Path) -> None:
    evidence = tmp_path / "claude.json"
    evidence.write_text(json.dumps({"status": "http_error", "http_status": 403}), encoding="utf-8")
    result = evaluate_gene_promotion_gate(
        db_path=_db(tmp_path),
        gene_id=347,
        claude_evidence_path=evidence,
        required_tests_passed=True,
        manifest_updated=True,
    )
    data = result.to_json_dict()
    assert data["status"] == "BLOCKED_PROMOTION_REVIEW"
    assert "independent_visible_verification" in data["blockers"]
    assert data["lifecycle_state"] == "candidate"


def test_promotion_gate_ready_when_all_checks_pass(tmp_path: Path) -> None:
    evidence = tmp_path / "claude.json"
    evidence.write_text(json.dumps({"status": "ok_visible", "visible_output_chars": 100}), encoding="utf-8")
    result = evaluate_gene_promotion_gate(
        db_path=_db(tmp_path),
        gene_id=347,
        claude_evidence_path=evidence,
        required_tests_passed=True,
        manifest_updated=True,
    )
    assert result.status == "READY_FOR_PROMOTION_REVIEW"
    assert result.blockers == []


def test_promotion_gate_allows_alternate_visible_review_when_explicitly_enabled(tmp_path: Path) -> None:
    claude = tmp_path / "claude.json"
    alt = tmp_path / "minimax.json"
    claude.write_text(json.dumps({"status": "http_error", "http_status": 403}), encoding="utf-8")
    alt.write_text(json.dumps({"status": "ok_visible", "visible_output_chars": 5310}), encoding="utf-8")
    result = evaluate_gene_promotion_gate(
        db_path=_db(tmp_path),
        gene_id=347,
        claude_evidence_path=claude,
        alternate_evidence_path=alt,
        allow_alternate_when_claude_unavailable=True,
        required_tests_passed=True,
        manifest_updated=True,
    )
    assert result.status == "READY_FOR_PROMOTION_REVIEW"
    assert result.blockers == []
    assert "no promotion" in result.boundary.lower()


def test_main_writes_gate_result(tmp_path: Path, capsys) -> None:
    evidence = tmp_path / "claude.json"
    evidence.write_text(json.dumps({"status": "http_error", "http_status": 403}), encoding="utf-8")
    assert main([
        "--db", str(_db(tmp_path)),
        "--gene-id", "347",
        "--output-dir", str(tmp_path / "out"),
        "--claude-evidence", str(evidence),
        "--tests-passed",
        "--manifest-updated",
    ]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["status"] == "BLOCKED_PROMOTION_REVIEW"
    assert Path(printed["result"]).is_file()
