"""Tests for Hermes Agent 0.14 defect repair helpers."""
from __future__ import annotations

import importlib
import json


def _reload_for_home(monkeypatch, tmp_path):
    home = tmp_path / ".hermes"
    monkeypatch.setenv("HERMES_HOME", str(home))
    import hermes_constants
    import tools.hermes_agent_014_defect_tool as defect_tool
    importlib.reload(hermes_constants)
    return importlib.reload(defect_tool), home


def _write_skill(home, name, body="Useful reusable workflow content." * 20):
    skill_dir = home / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {name} description\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return skill_dir / "SKILL.md"


def test_record_subagent_artifact_writes_detail_and_index(monkeypatch, tmp_path):
    mod, home = _reload_for_home(monkeypatch, tmp_path)
    result = mod.record_subagent_artifact(
        task_index=1,
        goal="verify child work",
        status="completed",
        summary="done",
        api_calls=2,
        files_written=["/tmp/out.md"],
        output_tail=[{"tool": "terminal", "preview": "ok", "is_error": False}],
    )
    detail = json.loads(open(result["detail_path"], encoding="utf-8").read())
    assert detail["status"] == "completed"
    assert detail["evidence_level"] == "summary+trace"
    index = (home / "logs" / "subagents" / "index.jsonl").read_text(encoding="utf-8")
    assert result["artifact_id"] in index


def test_skill_quality_audit_marks_low_quality_without_delete(monkeypatch, tmp_path):
    mod, home = _reload_for_home(monkeypatch, tmp_path)
    _write_skill(home, "good-skill")
    _write_skill(home, "bad-skill", body="short")
    report = mod.skill_quality_audit(write=True)
    assert report["skill_count"] == 2
    bad = next(item for item in report["items"] if item["name"] == "bad-skill")
    assert bad["score"] <= 70
    assert bad["stale_candidate"] is True
    assert bad["delete_allowed"] is False
    assert (home / "skills" / ".quality_audit.json").exists()


def test_capability_audit_and_gene_evolve_write_sidecars(monkeypatch, tmp_path):
    mod, home = _reload_for_home(monkeypatch, tmp_path)
    _write_skill(home, "short-skill", body="short")
    cap = mod.self_capability_audit(write=True)
    genes = mod.dual_skill_gene_evolve(write=True)
    assert cap["skill_count"] == 1
    assert "rule" in cap
    assert genes["gene_count"] == 1
    assert genes["genes"][0]["issues"] == ["too_short"]
    assert genes["genes"][0]["mutation_allowed"] is False
    assert (home / "capability_map.json").exists()
    assert (home / "skills" / ".gene_evolution.json").exists()
