"""PGG /goal unified status — MCP + CLI + GitHub + bounded gates.

Durable version of the hermes-goal status script. It is intentionally read-only:
no provider calls, no config writes, no scheduler/security mutation.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_ROOT_VENV_PYTHON = ROOT / "venv/bin/python"
VENV_PYTHON = _ROOT_VENV_PYTHON if _ROOT_VENV_PYTHON.exists() else Path(sys.executable)
HERMES_BIN = Path.home() / ".hermes/bin"


def status_class(status: Any) -> str:
    s = str(status or "")
    if s == "PASS" or s == "PASS_READY" or s.startswith("PASS_") or s.startswith("PASS-"):
        return "PASS"
    if s.startswith("WATCH") or s.startswith("PARTIAL") or s.startswith("HOLD"):
        return "WATCH"
    if s.startswith("BLOCK") or s.startswith("ERROR") or s.startswith("FAIL"):
        return "BLOCKED"
    return "WATCH" if s else "BLOCKED"


def run(cmd: list[str], timeout: int = 10) -> tuple[str, int]:
    try:
        env = os.environ.copy()
        env["PATH"] = f"{HERMES_BIN}:{env.get('PATH', '')}"
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.stdout.strip() or r.stderr.strip(), r.returncode
    except Exception as e:  # pragma: no cover - defensive status surface
        return str(e), -1


def load_json_or_error(out: str, name: str) -> dict[str, Any]:
    try:
        return json.loads(out)
    except Exception:
        return {"status": "ERROR", "detail": out[:300], "component": name}


def gate_json(cmd: list[str], name: str, timeout: int = 10) -> dict[str, Any]:
    out, rc = run(cmd, timeout)
    if rc != 0:
        return {"status": "ERROR", "detail": out[:300]}
    return load_json_or_error(out, name)


def summarize_gate(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    return {k: data.get(k) for k in fields if k in data}


def main() -> int:
    results: dict[str, dict[str, Any]] = {}

    # 1. Hermes CLI
    out, rc = run(["hermes", "--version"], 5)
    results["hermes_cli"] = {
        "status": "PASS" if rc == 0 else "ERROR",
        "version": out.split("\n")[0] if rc == 0 else out[:120],
    }

    # 2. GitHub CLI
    out, rc = run(["gh", "--version"], 5)
    results["github_cli"] = {
        "status": "PASS" if rc == 0 else "ERROR",
        "version": out.split("\n")[0] if rc == 0 else out[:120],
    }

    # 3. GitHub auth
    out, rc = run(["gh", "auth", "status"], 20)
    gh_auth_text = out
    results["github_auth"] = {
        "status": "PASS" if "Logged in" in gh_auth_text else "ERROR",
        "account": "appleoppa" if "appleoppa" in gh_auth_text else "unknown",
        "timeout_seconds": 20,
    }

    # 4. MCP servers
    out, rc = run(["hermes", "mcp", "list"], 10)
    mcp_servers: list[str] = []
    for line in out.split("\n"):
        l = line.strip()
        if "enabled" in l.lower() and not l.startswith("Name") and not l.startswith("─") and len(l) > 5:
            parts = l.split()
            if len(parts) >= 2:
                mcp_servers.append(parts[0])
    results["mcp_servers"] = {
        "status": "PASS" if len(mcp_servers) >= 2 else "WATCH",
        "count": len(mcp_servers),
        "servers": mcp_servers,
    }

    # 5. GitHub evolution pipeline — use absolute fallback to avoid PATH false WATCH.
    hermes_evolve = HERMES_BIN / "hermes-evolve"
    evolve_cmd = [str(hermes_evolve), "status"] if hermes_evolve.exists() else ["hermes-evolve", "status"]
    out, rc = run(evolve_cmd, 30)
    if rc != 0:
        results["evolution_pipeline"] = {"status": "ERROR", "detail": out[:300], "cmd": evolve_cmd, "timeout_seconds": 30}
    else:
        data = load_json_or_error(out, "evolution_pipeline")
        status = data.get("status", "UNKNOWN")
        # Preserve real pipeline WATCH; only fix the previous command-not-found false WATCH.
        results["evolution_pipeline"] = {
            "status": "PASS" if str(status).startswith("PASS") else "WATCH",
            "detail": status,
            "blockers": data.get("blockers", []),
            "cmd": evolve_cmd,
        }

    # 6. MCP endpoint smoke
    for s in mcp_servers:
        tout, trc = run(["hermes", "mcp", "test", s], 15)
        results["mcp_test_" + s] = {"status": "PASS" if "Connected" in tout else "ERROR"}

    # 7-13. Bounded gate CLIs/bridges
    apexagi = gate_json([str(VENV_PYTHON), "-m", "agent.pgg_archon_apexagi_runtime_gate"], "apexagi_gate")
    results["apexagi_gate"] = summarize_gate(apexagi, ["score", "status"])

    engineering = gate_json([str(VENV_PYTHON), "-m", "agent.pgg_archon_apex_engineering_formula"], "engineering_gate")
    results["engineering_gate"] = summarize_gate(engineering, ["score", "status"])

    evm = gate_json([str(VENV_PYTHON), "-m", "agent.pgg_archon_evm_runtime_gate"], "evm_gate")
    results["evm_gate"] = summarize_gate(evm, ["evm_gate", "status"])

    asi_cmd = [
        str(VENV_PYTHON),
        "-c",
        (
            f"import sys; sys.path.insert(0,{str(ROOT)!r}); "
            "from agent.pgg_archon_apex_asi_gate import PggApexAsiGate; "
            "import json; print(json.dumps(PggApexAsiGate().evaluate()))"
        ),
    ]
    asi = gate_json(asi_cmd, "asi_gate")
    results["asi_gate"] = summarize_gate(asi, ["score", "status"])

    apex_core = gate_json([str(VENV_PYTHON), "-m", "agent.pgg_archon_apex_core_gate"], "apex_core_gate")
    results["apex_core_gate"] = summarize_gate(apex_core, ["score", "status"])

    apex_v10 = gate_json([str(VENV_PYTHON), "-m", "agent.pgg_archon_apex_v10_gate"], "apex_v10_gate")
    results["apex_v10_gate"] = summarize_gate(apex_v10, ["score", "status"])

    sigma = gate_json([str(HERMES_BIN / "pgg_defect_reduction")], "sigma_delta_all")
    results["sigma_delta_all"] = summarize_gate(sigma, ["sigma_delta", "status"])

    pass_count = sum(1 for v in results.values() if isinstance(v, dict) and status_class(v.get("status")) == "PASS")
    total = len(results)
    all_no_error = all(isinstance(v, dict) and v.get("status") != "ERROR" for v in results.values())

    report = {
        "schema": "PGGGoalUnifiedStatus/v1",
        "generated_at": datetime.now().isoformat(),
        "overall_status": "PASS" if all_no_error else ("WATCH" if total and pass_count / total >= 0.7 else "BLOCKED"),
        "components": results,
        "summary": f"{pass_count}/{total} components PASS",
        "boundary": "Read-only status surface; not production enforcement, not full AGI/T5 proof.",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
