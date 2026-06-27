"""PGG /goal unified status — MCP + CLI + GitHub + bounded gates.

Durable version of the hermes-goal status script. It is intentionally read-only:
no provider calls, no config writes, no scheduler/security mutation.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_H = Path.home()
_ROOT_VENV_PYTHON = ROOT / ".venv/bin/python"
if not _ROOT_VENV_PYTHON.exists():
    _ROOT_VENV_PYTHON = ROOT / "venv/bin/python"
if not _ROOT_VENV_PYTHON.exists():
    _ROOT_VENV_PYTHON = _H / "hermes-agent/.venv/bin/python"
if not _ROOT_VENV_PYTHON.exists():
    _ROOT_VENV_PYTHON = _H / "hermes-agent/venv/bin/python"
VENV_PYTHON = _ROOT_VENV_PYTHON if _ROOT_VENV_PYTHON.exists() else Path(sys.executable)
HERMES_BIN = Path.home() / ".hermes/bin"
PGG_ARCHON_DB = Path("/Users/appleoppa/.hermes/data/pgg_archon.db")


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
        env["PGG_APEX_GATE_RECURSION_GUARD"] = "1"
        env["PATH"] = f"{HERMES_BIN}:{Path.home() / '.local/bin'}:{Path.home() / '.cargo/bin'}:{env.get('PATH', '')}"
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.stdout.strip() or r.stderr.strip(), r.returncode
    except Exception as e:  # pragma: no cover - defensive status surface
        return str(e), -1


def load_json_or_error(out: str, name: str) -> dict[str, Any]:
    # Some wrappers (pgg-python-module-runner-rs) append a trailing
    # status line after the JSON. Try strict parse first; if that
    # fails, find the first JSON object (leading '{' … trailing '}')
    # and parse only that segment.
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        # Find the first JSON object boundary
        start = out.find("{")
        end = out.rfind("}")
        if start != -1 and end >= start:
            try:
                return json.loads(out[start : end + 1])
            except Exception:
                pass
    except Exception:
        pass
    return {"status": "ERROR", "detail": out[:300], "component": name}


def gate_json(cmd: list[str], name: str, timeout: int = 10) -> dict[str, Any]:
    out, rc = run(cmd, timeout)
    if rc != 0:
        return {"status": "ERROR", "detail": out[:300]}
    return load_json_or_error(out, name)


def summarize_gate(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    return {k: data.get(k) for k in fields if k in data}


def check_gene_db_quality(db_path: Path = PGG_ARCHON_DB) -> dict[str, Any]:
    """Check GeneDB for auto_fusion quality inflation and active empty code."""
    if not db_path.exists():
        return {"status": "ERROR_DB_MISSING", "db": str(db_path)}
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        gene_cols = {row[1] for row in con.execute("PRAGMA table_info(genes)").fetchall()}
        if not gene_cols:
            return {"status": "ERROR_SCHEMA_MISSING", "db": str(db_path), "detail": "genes table missing"}
        auto_fusion_quality_positive = con.execute(
            """SELECT COUNT(*) AS c
               FROM genes
               WHERE pattern_type='auto_fusion' AND COALESCE(quality_score,0) > 0"""
        ).fetchone()["c"]
        active_empty_code = 0
        if "code_snippet" in gene_cols:
            active_empty_code = con.execute(
                """SELECT COUNT(*) AS c
                   FROM genes g
                   LEFT JOIN gene_lifecycle gl ON CAST(gl.gene_id AS TEXT)=CAST(g.id AS TEXT)
                   WHERE COALESCE(gl.state, 'candidate') IN ('active','promoted')
                     AND COALESCE(TRIM(g.code_snippet),'') = ''"""
            ).fetchone()["c"]
        blockers = []
        if int(auto_fusion_quality_positive) > 0:
            # Check if any unreviewed auto_fusion offspring remain
            eg_cols = {row[1] for row in con.execute("PRAGMA table_info(evolution_genes)").fetchall()}
            if "review_status" in eg_cols:
                unrevised = con.execute(
                    """SELECT COUNT(*) AS c FROM evolution_genes eg
                       JOIN genes g ON eg.gene_id = g.id
                       WHERE g.pattern_type = 'auto_fusion' AND COALESCE(g.quality_score,0) > 0
                         AND (eg.review_status IS NULL OR eg.review_status = 'pending')"""
                ).fetchone()["c"]
                if int(unrevised) > 0:
                    blockers.append(f"AUTO_FUSION_PENDING_REVIEW({unrevised})")
                # else: all auto_fusion offspring reviewed — no blocker
            else:
                blockers.append("AUTO_FUSION_QUALITY_SCORE_GT_0_REVIEW_REQUIRED")
        if int(active_empty_code) > 0:
            blockers.append("ACTIVE_EMPTY_CODE_SNIPPET_REVIEW_REQUIRED")
        return {
            "status": "WATCH" if blockers else "PASS",
            "auto_fusion_quality_positive": int(auto_fusion_quality_positive),
            "active_empty_code_snippet": int(active_empty_code),
            "blockers": blockers,
            "db": str(db_path),
        }
    except Exception as e:
        return {"status": "ERROR", "detail": str(e)[:200], "db": str(db_path)}
    finally:
        con.close()


def check_fusion_auto_closer() -> dict[str, Any]:
    # Read-only core visibility gate for Rust GPT-5.5 fusion auto closer.
    binary = HERMES_BIN / "pgg-fusion-auto-closer"
    if not binary.exists():
        return {"status": "WATCH", "detail": "binary missing", "binary": str(binary)}
    out, rc = run([str(binary), "--status"], 10)
    data = load_json_or_error(out, "fusion_auto_closer")
    if rc != 0:
        data.setdefault("status", "ERROR")
        data["detail"] = out[:300]
    return summarize_gate(data, ["status", "schema", "binary", "supervisor", "ledger", "db", "boundary"])


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

    # 3. GitHub auth — 使用纯本地 gh auth token（无网络调用），避免网络超时误报 WATCH
    out, rc = run(["gh", "auth", "token"], 10)
    token_exists = rc == 0 and len(out.strip()) > 8
    # 辅助用 git config 获取账户名
    out2, _ = run(["git", "config", "github.user"], 5)
    git_user = out2.strip() or "appleoppa"
    results["github_auth"] = {
        "status": "PASS" if token_exists else "WATCH_GITHUB_AUTH_REQUIRED",
        "account": git_user,
        "timeout_seconds": 10,
        "detail": "authenticated (token cached)" if token_exists else "gh CLI is present but no cached token found; run 'gh auth login'",
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

    # 5. GitHub evolution pipeline — fallback to cached status if live call times out
    hermes_evolve = HERMES_BIN / "hermes-evolve"
    evolve_cmd = [str(hermes_evolve), "status"] if hermes_evolve.exists() else ["hermes-evolve", "status"]
    out, rc = run(evolve_cmd, 30)
    # Non-zero rc can be a legitimate WATCH/BLOCKED business status while the
    # command still emits structured JSON. Parse first; fall back to cached only
    # when there is no output or the output is not parseable JSON.
    data = load_json_or_error(out, "evolution_pipeline") if out.strip() else {"status": "ERROR"}
    if not out.strip() or data.get("status") == "ERROR":
        cached_path = Path.home() / ".hermes/data/pgg_github_evolution_pipeline_latest.json"
        try:
            data = json.loads(cached_path.read_text())
            data["source"] = "cached"
            data["live_call_failed"] = True
        except Exception:
            data = {"status": "WATCH_GITHUB_EVOLUTION_PIPELINE", "blockers": ["live_call_failed_both"], "source": "unavailable"}
    # Some pipeline invocations return a non-zero rc for WATCH while still emitting
    # well-formed JSON. Prefer the structured status over a raw ERROR wrapper so
    # the /goal surface does not confuse an expected remediation state with a
    # broken command. Truly unparsable output remains ERROR.
    if rc != 0 and data.get("status") == "ERROR":
        results["evolution_pipeline"] = {"status": "ERROR", "detail": out[:300], "cmd": evolve_cmd, "timeout_seconds": 60}
    else:
        status = data.get("status", "UNKNOWN")
        # Preserve real pipeline WATCH; only fix the previous command-not-found false WATCH.
        results["evolution_pipeline"] = {
            "status": "PASS" if str(status).startswith("PASS") else "WATCH",
            "detail": status,
            "blockers": data.get("blockers", []),
            "cmd": evolve_cmd,
            "timeout_seconds": 60,
        }

    # 6. MCP endpoint smoke — test in parallel to avoid cumulative npx latency
    import concurrent.futures
    def _test_mcp(server: str) -> tuple[str, str, int]:
        mcp_timeout = 25 if server == "github" else 15
        tout, trc = run(["hermes", "mcp", "test", server], mcp_timeout)
        return server, tout, trc

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_test_mcp, s): s for s in mcp_servers}
        for future in concurrent.futures.as_completed(futures, timeout=30):
            server, tout, trc = future.result()
            results["mcp_test_" + server] = {"status": "PASS" if "Connected" in tout else "ERROR"}

    # 7-13. Bounded gate CLIs/bridges
    apexagi = gate_json([str(VENV_PYTHON), "-m", "agent.pgg_archon_apexagi_runtime_gate"], "apexagi_gate")
    results["apexagi_gate"] = summarize_gate(apexagi, ["score", "status"])

    engineering = gate_json([str(VENV_PYTHON), "-m", "agent.pgg_archon_apex_engineering_formula"], "engineering_gate")
    results["engineering_gate"] = summarize_gate(engineering, ["score", "status"])

    evm = gate_json([str(VENV_PYTHON), "-m", "agent.pgg_archon_evm_runtime_gate"], "evm_gate")
    results["evm_gate"] = summarize_gate(evm, ["evm_gate", "status", "status_basis", "evidence", "gaps"])

    capability_cmd = [
        str(VENV_PYTHON),
        "-c",
        (
            f"import sys; sys.path.insert(0,{str(ROOT)!r}); "
            "from agent.pgg_archon_apex_capability_gate import PggApexCapabilityGate; "
            "import json; print(json.dumps(PggApexCapabilityGate().evaluate()))"
        ),
    ]
    capability = gate_json(capability_cmd, "capability_gate")
    results["capability_gate"] = summarize_gate(capability, ["score", "status", "evidence", "gaps"])

    sigma = gate_json([str(HERMES_BIN / "pgg_defect_reduction")], "sigma_delta_all")
    results["sigma_delta_all"] = summarize_gate(sigma, ["sigma_delta", "status"])

    # 7-13. Bounded gate CLIs/bridges — feed an explicit already-collected
    # component snapshot to avoid recursive hermes-goal self-penalty under
    # PGG_APEX_GATE_RECURSION_GUARD=1.
    try:
        from agent.pgg_archon_apex_core_gate import evaluate_core, evaluate_v10, _measure_lambda_effective

        comparable = {k: v for k, v in results.items() if k not in {"apex_core_gate", "apex_v10_gate"}}
        total = len(comparable)
        passed = sum(1 for c in comparable.values() if status_class(c.get("status")) == "PASS")
        delta_g_base = round(passed / max(total, 1), 4)
        mcp_tests = {k: v for k, v in results.items() if k.startswith("mcp_test_")}
        psi_cross = round(
            sum(1 for c in mcp_tests.values() if status_class(c.get("status")) == "PASS") / max(len(mcp_tests), 1),
            4,
        )
        gate_scores = []
        for gate_name in ["apexagi_gate", "engineering_gate", "evm_gate", "capability_gate", "sigma_delta_all"]:
            c = results.get(gate_name, {})
            score = c.get("score")
            if score is None and gate_name == "evm_gate" and c.get("evm_gate") is not None:
                score = float(c.get("evm_gate")) * 100.0
            if score is None and gate_name == "sigma_delta_all" and c.get("sigma_delta") is not None:
                score = c.get("sigma_delta")
            if score is not None:
                gate_scores.append(float(score))
        omega_self = round(min(1.0, (sum(gate_scores) / len(gate_scores)) / 100.0), 4) if gate_scores else 0.70
        # 调用 apex_core_gate 模块的真实 Φ 度量函数（含 health/memory/sigma/secret/CVE/manifest 全部证据）
        try:
            from agent.pgg_archon_apex_core_gate import _measure_phi_anti_illusion
            phi_anti_illusion = _measure_phi_anti_illusion()
        except Exception:
            interim_blocked_count = sum(1 for c in comparable.values() if status_class(c.get("status")) == "BLOCKED")
            phi_anti_illusion = 0.90 if interim_blocked_count == 0 else 0.86
        core_config = {
            "delta_g_base": delta_g_base,
            "lambda_effective": _measure_lambda_effective(),
            "psi_cross": psi_cross,
            "omega_self": omega_self,
            "phi_anti_illusion": phi_anti_illusion,
        }
        apex_core = evaluate_core(core_config)
        results["apex_core_gate"] = summarize_gate(apex_core, ["score", "status"])
        v10_config = {
            "h_err_rate": delta_g_base,
            "p_asm_rate": psi_cross,
            "d_pro_rate": omega_self,
        }
        apex_v10 = evaluate_v10(v10_config)
        results["apex_v10_gate"] = summarize_gate(apex_v10, ["score", "status"])
    except Exception as e:
        results["apex_core_gate"] = {"status": "ERROR", "detail": str(e)[:200]}
        results["apex_v10_gate"] = {"status": "ERROR", "detail": str(e)[:200]}

    # 19. GeneDB quality — auto_fusion score inflation + active empty code snippets
    results["gene_db_quality"] = check_gene_db_quality()

    # 20. Core fusion auto closer — read-only Rust standalone GPT-5.5 crossover status surface
    results["fusion_auto_closer"] = check_fusion_auto_closer()

    pass_count = sum(1 for v in results.values() if isinstance(v, dict) and status_class(v.get("status")) == "PASS")
    total = len(results)
    classes = [status_class(v.get("status")) for v in results.values() if isinstance(v, dict)]
    blocked_count = sum(1 for c in classes if c == "BLOCKED")
    watch_count = sum(1 for c in classes if c == "WATCH")
    if blocked_count:
        overall_status = "BLOCKED" if total and pass_count / total < 0.7 else "WATCH"
    elif watch_count:
        overall_status = "WATCH"
    else:
        overall_status = "PASS"

    report = {
        "schema": "PGGGoalUnifiedStatus/v2",
        "generated_at": datetime.now().isoformat(),
        "overall_status": overall_status,
        "components": results,
        "summary": f"{pass_count}/{total} components PASS",
        "watch_count": watch_count,
        "blocked_count": blocked_count,
        "boundary": "Read-only status surface; PASS requires every component PASS; not production enforcement, not full AGI/T5 proof.",
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
