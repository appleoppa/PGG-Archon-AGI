import json

from agent import pgg_goal_unified_status as goal
from agent.pgg_goal_unified_status import status_class


EXPECTED_COMPONENTS = {
    "hermes_cli",
    "github_cli",
    "github_auth",
    "mcp_servers",
    "evolution_pipeline",
    "mcp_test_hermes-studio",
    "mcp_test_github",
    "mcp_test_filesystem",
    "mcp_test_llm-audit",
    "apexagi_gate",
    "engineering_gate",
    "evm_gate",
    "asi_gate",
    "apex_core_gate",
    "apex_v10_gate",
    "sigma_delta_all",
}


def test_status_class_pass_family():
    assert status_class("PASS") == "PASS"
    assert status_class("PASS_READY") == "PASS"
    assert status_class("PASS_BOUNDED_EVM_RUNTIME_GATE") == "PASS"
    assert status_class("PASS-GITHUB") == "PASS"


def test_status_class_watch_blocked():
    assert status_class("WATCH_EVOLVING") == "WATCH"
    assert status_class("PARTIAL") == "WATCH"
    assert status_class("HOLD") == "WATCH"
    assert status_class("BLOCKED_IMMATURE") == "BLOCKED"
    assert status_class("ERROR") == "BLOCKED"
    assert status_class("") == "BLOCKED"


def test_hermes_goal_schema_fast_regression(monkeypatch, capsys):
    def fake_run(cmd, timeout=10):
        joined = " ".join(str(x) for x in cmd)
        if "hermes --version" in joined:
            return "Hermes Agent v0.16.0", 0
        if "gh --version" in joined:
            return "gh version 2.92.0", 0
        if "gh auth status" in joined:
            return "✓ Logged in to github.com account appleoppa", 0
        if "hermes mcp list" in joined:
            return "hermes-studio enabled\ngithub enabled\nfilesystem enabled\nllm-audit enabled", 0
        if "hermes-evolve status" in joined:
            return json.dumps({"status": "PASS_GITHUB_EVOLUTION_PIPELINE_BOUNDED", "blockers": []}), 0
        if "hermes mcp test" in joined:
            return "✓ Connected", 0
        return "", 0

    def fake_gate_json(cmd, name, timeout=10):
        if name == "evm_gate":
            return {"status": "PASS_BOUNDED_EVM_RUNTIME_GATE", "evm_gate": 0.9}
        if name == "sigma_delta_all":
            return {"status": "PASS", "sigma_delta": 10}
        return {"status": "PASS_READY", "score": 88.0}

    monkeypatch.setattr(goal, "run", fake_run)
    monkeypatch.setattr(goal, "gate_json", fake_gate_json)

    assert goal.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["schema"] == "PGGGoalUnifiedStatus/v2"
    assert data["overall_status"] == "PASS"
    assert data["summary"].startswith("16/16")
    assert set(data["components"]) == EXPECTED_COMPONENTS
    for name, component in data["components"].items():
        assert status_class(component.get("status")) == "PASS", (name, component)



def test_hermes_goal_watch_when_any_component_watch(monkeypatch, capsys):
    def fake_run(cmd, timeout=10):
        joined = " ".join(str(x) for x in cmd)
        if "hermes --version" in joined:
            return "Hermes Agent v0.16.0", 0
        if "gh --version" in joined:
            return "gh version 2.92.0", 0
        if "gh auth status" in joined:
            return "✓ Logged in to github.com account appleoppa", 0
        if "hermes mcp list" in joined:
            return "hermes-studio enabled\ngithub enabled\nfilesystem enabled\nllm-audit enabled", 0
        if "hermes-evolve status" in joined:
            return json.dumps({"status": "PASS_GITHUB_EVOLUTION_PIPELINE_BOUNDED", "blockers": []}), 0
        if "hermes mcp test" in joined:
            return "✓ Connected", 0
        return "", 0

    def fake_gate_json(cmd, name, timeout=10):
        if name == "apexagi_gate":
            return {"status": "WATCH_EVOLVING", "score": 71.43}
        if name == "evm_gate":
            return {"status": "PASS_BOUNDED_EVM_RUNTIME_GATE", "evm_gate": 0.9}
        if name == "sigma_delta_all":
            return {"status": "PASS", "sigma_delta": 10}
        return {"status": "PASS_READY", "score": 88.0}

    monkeypatch.setattr(goal, "run", fake_run)
    monkeypatch.setattr(goal, "gate_json", fake_gate_json)
    assert goal.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["overall_status"] == "WATCH"
    assert data["watch_count"] == 1
    assert data["summary"].startswith("15/16")


def test_hermes_goal_github_auth_missing_is_watch_not_error(monkeypatch, capsys):
    def fake_run(cmd, timeout=10):
        joined = " ".join(str(x) for x in cmd)
        if "hermes --version" in joined:
            return "Hermes Agent v0.16.0", 0
        if "gh --version" in joined:
            return "gh version 2.92.0", 0
        if "gh auth status" in joined:
            return "You are not logged into any GitHub hosts", 1
        if "hermes mcp list" in joined:
            return "hermes-studio enabled\ngithub enabled\nfilesystem enabled\nllm-audit enabled", 0
        if "hermes-evolve status" in joined:
            return json.dumps({"status": "WATCH_GITHUB_EVOLUTION_PIPELINE", "blockers": ["github_cli_authenticated"]}), 1
        if "hermes mcp test" in joined:
            return "✓ Connected", 0
        return "", 0

    def fake_gate_json(cmd, name, timeout=10):
        if name == "evm_gate":
            return {"status": "PASS_BOUNDED_EVM_RUNTIME_GATE", "evm_gate": 0.9}
        if name == "sigma_delta_all":
            return {"status": "PASS", "sigma_delta": 10}
        return {"status": "PASS_READY", "score": 88.0}

    monkeypatch.setattr(goal, "run", fake_run)
    monkeypatch.setattr(goal, "gate_json", fake_gate_json)
    assert goal.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["overall_status"] == "WATCH"
    assert data["blocked_count"] == 0
    assert data["watch_count"] == 2
    assert data["components"]["github_auth"]["status"] == "WATCH_GITHUB_AUTH_REQUIRED"
    assert data["components"]["evolution_pipeline"]["status"] == "WATCH"
