from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agent import pgg_archon_autonomous_status as status_mod
from agent.pgg_archon_autonomous_status import build_status, main, write_status


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    manifest = {
        "last_updated": "2026-06-04T00:00:00Z",
        "capabilities": {
            "autonomous_evolution_loop": {
                "status": "PASS_WITH_BOUNDARY",
                "cron_job_id": "c0fad245e325",
                "pipeline": "queue→proposal→targeted_regression→patch_candidate→sandbox_readiness→temp_worktree_patch→promotion_readiness_package",
            }
        },
    }
    _write(home / ".hermes/data/EVOLUTION_MANIFEST.json", manifest)
    ledger = home / ".hermes/data/pgg-background-evolution/autonomous_loop_cycles.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps({"status": "PASS", "started_at": "s", "finished_at": "f", "generated_count": 1, "error_count": 0, "boundary": "b"}) + "\n", encoding="utf-8")
    _write(home / ".hermes/cron/jobs.json", {"jobs": [{"id": "c0fad245e325", "name": "loop", "enabled": True, "last_status": "ok", "script": "pgg_autonomous_evolution_loop.py"}]})
    readiness = home / ".hermes/workspace/evolution/autonomous_loop/x/promotion_readiness_package.json"
    _write(readiness, {"status": "READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW", "blockers": [], "generated_at": "g"})
    db = home / ".hermes/data/pgg_archon.db"
    con = sqlite3.connect(db)
    con.execute("create table genes(id integer primary key, name text, pattern_type text, quality_score real, extracted_at text)")
    con.execute("create table gene_lifecycle(gene_id integer primary key, state text, quality_score real, candidate_at text, promoted_at text)")
    con.execute("create table promotion_chain(id integer primary key, gene_id integer, from_state text, to_state text, transitioned_at text, trigger_phase text)")
    con.execute("insert into genes values (347,'g','verified_patch_gate',0.86,'t')")
    con.execute("insert into gene_lifecycle values (347,'promoted',0.86,'c','p')")
    con.execute("insert into promotion_chain values (2,347,'candidate','promoted','p','phase')")
    con.commit(); con.close()
    return home


def test_build_status_aggregates_core_state(tmp_path: Path, monkeypatch) -> None:
    home = _home(tmp_path)
    monkeypatch.setattr(status_mod, "_rust_watcher_status", lambda: {"active": True, "label": "ai.hermes.evol-watcher"})
    status = build_status(home=home).to_json_dict()
    assert status["schema"] == "PGGAutonomousEvolutionStatus/v1"
    assert status["latest_loop_cycle"]["status"] == "PASS"
    assert status["genedb_gene_347"]["lifecycle"][1] == "promoted"
    assert status["latest_readiness_package"]["status"] == "READY_FOR_MAIN_PATCH_OR_GENE_CANDIDATE_REVIEW"
    assert "latest promotion readiness package is not READY" not in status["known_gaps"]


def test_write_status_writes_json(tmp_path: Path, monkeypatch) -> None:
    home = _home(tmp_path)
    monkeypatch.setattr(status_mod, "_rust_watcher_status", lambda: {"active": True})
    result = write_status(output_path=tmp_path / "status.json", home=home)
    assert Path(result["status_path"]).is_file()
    assert result["latest_loop_status"] == "PASS"


def test_main_prints_status(capsys, monkeypatch, tmp_path: Path) -> None:
    home = _home(tmp_path)
    monkeypatch.setattr(status_mod.Path, "home", lambda: home)
    monkeypatch.setattr(status_mod, "_rust_watcher_status", lambda: {"active": True})
    assert main([]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["manifest_last_updated"] == "2026-06-04T00:00:00Z"
