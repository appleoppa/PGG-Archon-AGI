import json

from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli
from hermes_cli.commands import resolve_command


def test_apex_runtimeos_command_registered_with_alias():
    current = resolve_command("pgg-archon")
    legacy = resolve_command("apex-runtimeos")
    short = resolve_command("apex")
    archon = resolve_command("archon")
    assert current is not None and current.name == "pgg-archon"
    assert legacy is not None and legacy.name == "pgg-archon"
    assert short is not None and short.name == "pgg-archon"
    assert archon is not None and archon.name == "pgg-archon"


def test_apex_runtimeos_cli_summary_outputs_chinese_aggregate(tmp_path, monkeypatch):
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("APEX_RUNTIMEOS_AUDIT_PATH", str(audit_path))
    audit_path.write_text(
        json.dumps({
            "schema": "ApexRuntimeOSCheckpointAudit/v1",
            "stage": "pre_api_request",
            "session_id": "s1",
            "checkpoint": {
                "blocking": False,
                "results": {
                    "router": {"status": "PASS", "elapsed_ms": 2.0, "output": {"model": "m1"}}
                },
            },
        }) + "\nnot-json\n",
        encoding="utf-8",
    )
    output = run_apex_runtimeos_cli(["summary", "--limit", "10"])
    assert "PGG Archon AGI" in output
    assert "原 APEX RuntimeOS" not in output
    assert "| 有效记录 | 1 |" in output
    assert "| 坏行 | 1 |" in output
    assert "router" in output
    assert str(audit_path) not in output
    assert "prompt" not in output
    assert "messages" not in output


def test_apex_runtimeos_cli_json_outputs_machine_readable_summary(tmp_path, monkeypatch):
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("APEX_RUNTIMEOS_AUDIT_PATH", str(audit_path))
    audit_path.write_text("", encoding="utf-8")
    output = run_apex_runtimeos_cli(["--json"])
    data = json.loads(output)
    assert data["object"] == "hermes.apex_runtimeos.audit_summary"
    assert data["summary"]["records"] == 0
    assert "audit_path" not in data["summary"]


def test_apex_runtimeos_cli_feishu_outputs_safe_markdown(tmp_path, monkeypatch):
    audit_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("APEX_RUNTIMEOS_AUDIT_PATH", str(audit_path))
    audit_path.write_text(
        json.dumps({
            "schema": "ApexRuntimeOSCheckpointAudit/v1",
            "stage": "pre_completion",
            "session_id": "s1",
            "checkpoint": {
                "blocking": False,
                "results": {
                    "gene_selector": {"status": "PASS", "elapsed_ms": 4.0, "output": {"model": "m2"}}
                },
            },
        }) + "\n",
        encoding="utf-8",
    )
    output = run_apex_runtimeos_cli(["feishu", "--limit", "10"])
    assert "PGG Archon AGI" in output
    assert "原 APEX RuntimeOS" not in output
    assert "手动只读摘要" in output
    assert "gene_selector" in output
    assert "pre_completion" in output
    assert "本命令只生成文本，不自动发送飞书" in output
    assert str(audit_path) not in output
    assert "prompt" not in output
    assert "messages" not in output
    assert "token" not in output.lower()


def test_apex_runtimeos_autonomy_candidate_dry_run_does_not_write(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    monkeypatch.delenv("APEX_RUNTIMEOS_AUTO_WRITE_ENABLED", raising=False)
    output = run_apex_runtimeos_cli(["autonomy-candidate", "--json", "--limit", "10"])
    data = json.loads(output)
    assert data["object"] == "hermes.apex_runtimeos.autonomy_candidate"
    assert data["result"]["written"] is False
    assert data["result"]["reason"] == "disabled_or_not_enforce"
    assert not (tmp_path / "auto" / "candidates.jsonl").exists()


def test_apex_runtimeos_autonomy_candidate_execute_writes_sanitized_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    output = run_apex_runtimeos_cli(["autonomy-candidate", "--execute", "--json", "--limit", "10"])
    data = json.loads(output)
    assert data["result"]["written"] is True
    raw = (tmp_path / "auto" / "candidates.jsonl").read_text(encoding="utf-8")
    assert "ApexRuntimeOSAutoWriteCandidate/v1" in raw
    result_codes = {item.get("code") for item in data["result"]["recommendations"]["items"]}
    assert result_codes
    assert any(code in raw for code in result_codes)
    assert "/Users/" not in raw


def test_apex_runtimeos_autonomy_cli_shows_gep_safety_pipeline(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    output = run_apex_runtimeos_cli(["autonomy", "--limit", "10"])
    assert "字段：GEP安全流水线状态" in output
    assert "字段：GEP运行接入允许" in output
    assert "字段：GEP HOLD原因" in output
    assert "值：False" in output
    assert "runtime_execution" in output

def test_apex_runtimeos_cli_switch_cost_json_outputs_read_only_decision():
    output = run_apex_runtimeos_cli([
        "switch-cost",
        "--json",
        "--topic", "thrash guard",
        "--current-route", json.dumps({"id": "stable", "reward": 0.7, "evidence": 0.8, "confidence": 0.8, "features": ["a"]}),
        "--target-route", json.dumps({"id": "new", "reward": 0.75, "evidence": 0.8, "confidence": 0.8, "features": ["b"]}),
        "--switching-cost", "0.5",
    ])
    data = json.loads(output)
    assert data["object"] == "hermes.apex_runtimeos.switch_cost"
    report = data["result"]["report"]
    assert report["schema"] == "ApexSwitchCostReport/v1"
    assert report["decision"] == "HOLD"
    assert report["executed"] is False
    assert data["result"]["written"] is None


def test_apex_runtimeos_cli_switch_cost_text_outputs_chinese_fields():
    output = run_apex_runtimeos_cli([
        "switch-cost",
        "--topic", "upgrade",
        "--current-route", json.dumps({"id": "old", "reward": 0.2}),
        "--target-route", json.dumps({"id": "new", "reward": 1.0, "evidence": 1.0, "confidence": 1.0}),
        "--switching-cost", "0.05",
    ])
    assert "PGG Archon AGI 切换成本门禁" in output
    assert "APEX 切换成本门禁" not in output
    assert "字段：decision" in output
    assert "字段：executed" in output
    assert "值：False" in output
