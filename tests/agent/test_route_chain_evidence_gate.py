from pathlib import Path

from agent.route_chain_evidence_gate import classify_task, select_chain, run_gate, validate_record_hash


def test_classify_agi_and_select_dual_strong_review():
    classified = classify_task("PGG Archon AGI 进化硬门禁", "auto")
    assert classified["task_class"] == "evolution_agi"
    chain = select_chain(classified["task_class"], classified["risk_level"])
    assert chain["selected_chain"] == "dual_strong_review"
    assert chain["model_roles"]["GPT主脑统筹"]["provider"] == "gpt55_5yuantoken"
    assert chain["model_roles"]["Claude反证审错"]["provider"] == "claude_opus47_5yuantoken"


def test_run_gate_planning_writes_progress_record(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.route_chain_evidence_gate.run_cmd", lambda *a, **k: {"ok": True, "data": []})
    progress = tmp_path / "progress.json"
    record = run_gate("日常摘要", "daily", execute=False, out_path=progress)
    assert progress.exists()
    assert record["schema"] == "route_chain_evidence_gate/v4"
    assert record["final_decision"] == "allow_planning_only"
    assert validate_record_hash(record) is True


def test_conversation_loop_uses_repo_controlled_route_chain_script():
    src = Path("agent/conversation_loop.py").read_text(encoding="utf-8")
    assert "/Users/appleoppa/.hermes/hermes-agent/agent/route_chain_evidence_gate.py" in src
