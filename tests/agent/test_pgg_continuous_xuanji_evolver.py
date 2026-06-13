from __future__ import annotations

from pathlib import Path

from agent import pgg_continuous_xuanji_evolver as xuanji


def _spec(step: int, gate: str) -> dict:
    return {"step": step, "gate": gate, "topic": f"topic-{step}", "repos": ["owner/repo"], "genes": []}


def test_next_maintenance_specs_rotates_when_all_gates_present(tmp_path, monkeypatch):
    monkeypatch.setattr(xuanji, "DATA_DIR", tmp_path)
    monkeypatch.setattr(xuanji, "MAINTENANCE_STATE", tmp_path / "maintenance_state.json")
    monkeypatch.setattr(xuanji, "STEP_SPECS", [_spec(7, "g7"), _spec(8, "g8")])

    first = xuanji.next_maintenance_specs(10)
    second = xuanji.next_maintenance_specs(10)
    third = xuanji.next_maintenance_specs(10)

    assert [s["step"] for s in first] == [7]
    assert [s["step"] for s in second] == [8]
    assert [s["step"] for s in third] == [7]
    assert (tmp_path / "maintenance_state.json").exists()


def test_evolve_uses_maintenance_refresh_instead_of_zero_rounds(tmp_path, monkeypatch):
    monkeypatch.setattr(xuanji, "DATA_DIR", tmp_path)
    monkeypatch.setattr(xuanji, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(xuanji, "LATEST", tmp_path / "latest.json")
    monkeypatch.setattr(xuanji, "MAINTENANCE_STATE", tmp_path / "maintenance_state.json")
    monkeypatch.setattr(xuanji, "READBACK_ROOT", tmp_path / "readback")
    monkeypatch.setattr(xuanji, "STEP_SPECS", [_spec(7, "g7")])
    monkeypatch.setattr(xuanji, "existing_gates", lambda: {"g7"})
    monkeypatch.setattr(
        xuanji,
        "gh_readme",
        lambda repo, out_dir: {"repo": repo, "ok": True, "path": str(Path(out_dir) / "README.md"), "bytes": 10, "snippet": "ok"},
    )
    monkeypatch.setattr(xuanji, "insert_verified_genes", lambda spec, cards: {"inserted": 0, "updated": 0, "gate_verified": 1, "total": 1, "verified": 1})
    monkeypatch.setattr(xuanji, "run_self_cycle", lambda: {"rc": 0})

    result = xuanji.evolve(max_rounds=10, refresh=False)

    assert result["status"] == "PASS_EFFECTIVE_ROUND"
    assert result["mode"] == "maintenance_refresh_all_configured_gates_present"
    assert result["rounds_done"] == 1
    assert result["rounds"][0]["status"] == "PASS_MAINTENANCE_REFRESH"
    assert (tmp_path / "latest.json").exists()
    assert (tmp_path / "ledger.jsonl").exists()
