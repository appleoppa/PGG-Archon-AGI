from pathlib import Path
import json
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]

from agent.pgg_archon_formula_gate_status import (
    GOAL_FORMULA_RULE,
    TRUTHFUL_BOUNDARY,
    build_formula_gate_status,
    classify_task_type,
    render_formula_gate_status,
)


def test_classify_task_type_prioritizes_agi_goal() -> None:
    assert classify_task_type("继续推进 AGI 总纲 T5 进化") == "agi"
    assert classify_task_type("法律办案 管辖核验") == "legal"
    assert classify_task_type("Hermes router web runtime") == "system"


def test_formula_gate_status_has_six_dimensions_and_no_t5_claim(tmp_path: Path) -> None:
    manifest = tmp_path / "EVOLUTION_MANIFEST.json"
    manifest.write_text(json.dumps({"latest_demo": {"status": "PASS"}}, ensure_ascii=False), encoding="utf-8")
    panel = build_formula_gate_status("AGI 进化任务", manifest_path=manifest)
    assert panel["schema"] == "PGGArchonFormulaGateStatus/v1"
    assert panel["status"] == "PASS"
    assert len(panel["six_dimensions"]) == 6
    assert all(d["active"] for d in panel["six_dimensions"])
    assert "not T5 proof" in panel["target_tier"]
    assert panel["goal_formula_rule"] == GOAL_FORMULA_RULE
    assert panel["goal_formula_rule"]["source"] == "/goal"
    assert "Agent_Evolve" in panel["goal_formula_rule"]["execution_chain"]
    assert "not full AGI" in panel["boundary"]
    assert panel["manifest_summary"]["latest_pass_count"] == 1


def test_formula_gate_status_watch_when_task_empty(tmp_path: Path) -> None:
    manifest = tmp_path / "EVOLUTION_MANIFEST.json"
    manifest.write_text("{}", encoding="utf-8")
    panel = build_formula_gate_status("", manifest_path=manifest)
    assert panel["status"] == "WATCH"
    assert "task_description" in panel["missing_gates"]


def test_formula_gate_status_watch_when_explicit_false(tmp_path: Path) -> None:
    manifest = tmp_path / "EVOLUTION_MANIFEST.json"
    manifest.write_text(json.dumps({"latest_demo": {"status": "PASS"}}), encoding="utf-8")
    panel = build_formula_gate_status("AGI 进化任务", manifest_path=manifest, explicit=False)
    assert panel["status"] == "WATCH"
    assert "explicit_formula_gate" in panel["missing_gates"]


def test_formula_gate_manifest_missing_or_malformed_is_watch(tmp_path: Path) -> None:
    missing_panel = build_formula_gate_status("AGI 进化任务", manifest_path=tmp_path / "missing.json")
    assert missing_panel["status"] == "WATCH"
    assert "manifest_present" in missing_panel["missing_gates"]
    bad = tmp_path / "bad.json"
    bad.write_text("{not-json", encoding="utf-8")
    bad_panel = build_formula_gate_status("AGI 进化任务", manifest_path=bad)
    assert bad_panel["status"] == "WATCH"
    assert bad_panel["manifest_summary"]["latest_pass_keys"] == []


def test_formula_gate_manifest_latest_uses_timestamp_sort(tmp_path: Path) -> None:
    manifest = tmp_path / "EVOLUTION_MANIFEST.json"
    manifest.write_text(
        json.dumps(
            {
                "latest_zzz_old": {"status": "PASS", "created_at": "2026-01-01 00:00:00"},
                "latest_aaa_new": {"status": "PASS", "created_at": "2026-06-06 12:00:00"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    panel = build_formula_gate_status("AGI 进化任务", manifest_path=manifest)
    assert panel["manifest_summary"]["latest_keys"][-1] == "latest_aaa_new"
    assert panel["manifest_summary"]["sort"] == "created_at/generated_at/timestamp fallback key"


def test_render_formula_gate_status_is_human_readable(tmp_path: Path) -> None:
    manifest = tmp_path / "EVOLUTION_MANIFEST.json"
    manifest.write_text(json.dumps({"latest_demo": {"status": "PASS"}}, ensure_ascii=False), encoding="utf-8")
    panel = build_formula_gate_status("法律办案流程门禁", manifest_path=manifest)
    text = render_formula_gate_status(panel)
    assert "【公式门禁状态】" in text
    assert "/goal" in text
    assert "AGI L0-L5" in text
    assert "Agent_Evolve" in text
    assert "总纲1六维" in text
    assert "总纲2闭环" in text
    assert TRUTHFUL_BOUNDARY in text


def test_module_is_read_only_no_provider_network_or_config_writes() -> None:
    src = (REPO_ROOT / "agent" / "pgg_archon_formula_gate_status.py").read_text(encoding="utf-8")
    forbidden = ["call_provider", "urllib", "requests", "subprocess", "write_text", "open(\"w", "launchctl", "scheduler.", "get_db().execute"]
    assert [token for token in forbidden if token in src] == []


def test_cli_json_smoke() -> None:
    cp = subprocess.run(
        [sys.executable, "-m", "agent.pgg_archon_formula_gate_status", "AGI", "进化", "--json"],
        text=True,
        capture_output=True,
        timeout=20,
        cwd=REPO_ROOT,
    )
    assert cp.returncode == 0
    data = json.loads(cp.stdout)
    assert data["schema"] == "PGGArchonFormulaGateStatus/v1"
    assert data["task_type"] == "agi"
    assert data["boundary"] == TRUTHFUL_BOUNDARY
