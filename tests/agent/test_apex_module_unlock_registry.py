from pathlib import Path

from agent.apex_module_unlock_registry import build_apex_module_unlock_registry


def test_apex_module_unlock_registry_finds_existing_module(tmp_path):
    repo = tmp_path
    agent = repo / "agent"
    agent.mkdir()
    (agent / "demo.py").write_text("def public_entry():\n    return 1\n\ndef _private():\n    return 2\n", encoding="utf-8")
    report = build_apex_module_unlock_registry(["demo.py"], repo_root=repo, write_report=True, report_dir=tmp_path / "reports")
    assert report["module_count"] == 1
    assert report["status_counts"] == {"UNLOCKABLE": 1}
    assert report["entries"][0]["public_entrypoints"] == ["public_entry"]
    assert Path(report["report_path"]).exists()
    assert report["agi_completion_claim"] is False


def test_apex_module_unlock_registry_marks_missing_module(tmp_path):
    (tmp_path / "agent").mkdir()
    report = build_apex_module_unlock_registry(["missing.py"], repo_root=tmp_path)
    assert report["status_counts"] == {"MISSING": 1}
    assert report["entries"][0]["unlock_state"] == "blocked_missing_file"
