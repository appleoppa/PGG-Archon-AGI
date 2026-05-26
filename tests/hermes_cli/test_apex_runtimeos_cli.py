import json

from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli
from hermes_cli.commands import resolve_command


def test_apex_runtimeos_command_registered_with_alias():
    assert resolve_command("apex-runtimeos").name == "apex-runtimeos"
    assert resolve_command("apex").name == "apex-runtimeos"


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
    assert "APEX RuntimeOS 诊断摘要" in output
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
    assert "APEX RuntimeOS 体征摘要" in output
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
    assert "apex_sequence_evidence_incomplete" in raw
    assert "/Users/" not in raw
