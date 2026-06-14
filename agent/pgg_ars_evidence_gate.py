"""PGG ARS Evidence Gate — read-only minimal E2E proof packet collector.

This module does not mutate GeneDB, provider config, scheduler, security, or
Hermes native core. It collects evidence for a single ARS task_id and returns
an honest PASS/WATCH/BLOCKED verdict.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERMES_AGENT_ROOT = Path("/Users/appleoppa/.hermes/hermes-agent")
GENE_DB = Path("/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3")
DEFAULT_PROOF_ROOT = Path("/Users/appleoppa/.hermes/workspace/pgg-archon-governance/ars-minimal-e2e-proof")

CORE_FILES = [
    "run_agent.py",
    "model_tools.py",
    "toolsets.py",
    "agent/chat_completion_helpers.py",
    "agent/agent_runtime_helpers.py",
    "agent/pgg_bridge_processor.py",
    "agent/pgg_archon_ultimate_evolution_ars_cycle.py",
    "agent/pgg_self_evolution_loop.py",
    "agent/pgg_execution_bridge.py",
    "agent/pgg_recovery_guard.py",
]

STATE_REQUIRED = ["INTAKE", "CORE_READBACK", "MODEL_REVIEW", "DECIDED", "SETTLED"]
PROVIDERS = ["gpt55", "claude46", "deepseek_v4", "ark"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _run(cmd: list[str], cwd: Path = HERMES_AGENT_ROOT, timeout: int = 60) -> dict[str, Any]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return {"cmd": cmd, "exit_code": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
    except Exception as e:
        return {"cmd": cmd, "exit_code": 999, "stdout": "", "stderr": repr(e)}


def _task_dir(task_id: str, proof_root: Path = DEFAULT_PROOF_ROOT) -> Path:
    if not task_id or any(ch in task_id for ch in "/\\.."):
        raise ValueError("unsafe task_id")
    return proof_root / task_id


def init_task(task_id: str, proof_root: Path = DEFAULT_PROOF_ROOT, summary: str = "") -> dict[str, Any]:
    td = _task_dir(task_id, proof_root)
    (td / "receipts").mkdir(parents=True, exist_ok=True)
    (td / "core_readback").mkdir(parents=True, exist_ok=True)
    intake = {
        "schema": "pgg_ars_task_intake/v1",
        "task_id": task_id,
        "created_at": _now(),
        "summary": summary or "bounded minimal ARS proof task",
        "boundary": "read-only proof packet; no native-core mutation; no AGI/T5/full-AGI claim",
        "payload_sha256": _sha256_text(task_id + "|" + (summary or "")),
    }
    (td / "task_intake.json").write_text(json.dumps(intake, ensure_ascii=False, indent=2))
    transitions = [
        {"ts": _now(), "task_id": task_id, "state": "INTAKE", "actor": "pgg_ars_evidence_gate", "source": "init_task"}
    ]
    (td / "state_transition.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in transitions) + "\n")
    return intake


def collect_core_inventory(task_id: str, proof_root: Path = DEFAULT_PROOF_ROOT) -> dict[str, Any]:
    td = _task_dir(task_id, proof_root)
    (td / "core_readback").mkdir(parents=True, exist_ok=True)
    items: list[dict[str, Any]] = []
    for rel in CORE_FILES:
        p = HERMES_AGENT_ROOT / rel
        if not p.exists():
            items.append({"path": rel, "exists": False})
            continue
        txt = p.read_text(errors="ignore")
        classes: list[str] = []
        funcs: list[str] = []
        try:
            tree = ast.parse(txt)
            classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)][:20]
            funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))][:50]
        except Exception as e:
            funcs = ["AST_ERROR:" + str(e)]
        items.append({
            "path": rel,
            "exists": True,
            "lines": txt.count("\n") + 1,
            "sha256": _sha256_text(txt),
            "classes": classes,
            "functions": funcs,
            "signals": {k: (k.lower() in txt.lower()) for k in [
                "gpt55", "claude", "deepseek", "ark", "ARS", "Agent_Evolve",
                "Authorization: Bearer", "responses", "tool_call", "handle_function_call",
            ]},
        })
    out = {"schema": "pgg_ars_core_inventory/v1", "task_id": task_id, "created_at": _now(), "root": str(HERMES_AGENT_ROOT), "items": items}
    (td / "core_readback" / "core_file_inventory.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def import_smoke(task_id: str, proof_root: Path = DEFAULT_PROOF_ROOT) -> dict[str, Any]:
    td = _task_dir(task_id, proof_root)
    cmd = [
        ".venv/bin/python", "-c",
        "from agent import pgg_bridge_processor as b; "
        "from agent import pgg_archon_ultimate_evolution_ars_cycle as a; "
        "import json; "
        "print(json.dumps({'bridge_schema':b.bridge_processor_summary()['schema'],"
        "'ars_import':a.__name__,'phase3_callable':callable(a.build_phase3_ars_cycle)}, ensure_ascii=False))",
    ]
    out = _run(cmd, timeout=90)
    (td / "core_readback" / "runtime_import_smoke.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def bridge_summary() -> dict[str, Any]:
    out = _run([".venv/bin/python", "-m", "agent.pgg_bridge_processor", "--summary"], timeout=90)
    parsed = _read_json_from_stdout(out.get("stdout", ""))
    return {"run": out, "parsed": parsed}


def _read_json_from_stdout(stdout: str) -> Any:
    stdout = stdout.strip()
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except Exception:
        start = stdout.find("{")
        end = stdout.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(stdout[start:end + 1])
            except Exception:
                return None
    return None


def gene_db_stats() -> dict[str, Any]:
    if not GENE_DB.exists():
        return {"exists": False, "path": str(GENE_DB)}
    con = sqlite3.connect(GENE_DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    status = {r[0]: r[1] for r in cur.execute("SELECT status, COUNT(*) FROM evolution_genes GROUP BY status")}
    buckets = {r[0]: r[1] for r in cur.execute("""
        SELECT CASE
          WHEN fitness >= 700 THEN 'fitness_ge_700'
          WHEN fitness >= 600 THEN 'fitness_600_699'
          WHEN fitness >= 300 THEN 'fitness_300_599'
          ELSE 'fitness_lt_300'
        END AS bucket, COUNT(*)
        FROM evolution_genes WHERE status='candidate' GROUP BY bucket
    """)}
    sample = [dict(r) for r in cur.execute("""
        SELECT gene_id, gene_name, fitness, evidence_grade, gate_type, verification_status
        FROM evolution_genes WHERE status='candidate' AND fitness >= 600
        ORDER BY fitness DESC LIMIT 10
    """)]
    con.close()
    return {"exists": True, "path": str(GENE_DB), "status_counts": status, "candidate_fitness_buckets": buckets, "candidate_ge600_sample": sample}


def header_ast_check() -> dict[str, Any]:
    p = HERMES_AGENT_ROOT / "agent/pgg_bridge_processor.py"
    txt = p.read_text(errors="ignore")
    tree = ast.parse(txt)
    joined: list[dict[str, Any]] = []
    binop: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            try:
                s = ast.unparse(node)
            except Exception:
                s = ""
            if "Authorization: Bearer" in s:
                vars_ = []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.FormattedValue):
                        vars_.append(ast.unparse(sub.value))
                joined.append({"lineno": node.lineno, "vars": vars_})
        if isinstance(node, ast.BinOp):
            try:
                s = ast.unparse(node)
            except Exception:
                s = ""
            if "Authorization: Bearer" in s:
                binop.append({"lineno": getattr(node, "lineno", None), "expr": s})
    return {"joinedstr_headers": joined, "binop_headers": binop, "pass": bool(joined) and not binop and all("api_key" in x.get("vars", []) for x in joined)}


def provider_receipts(task_id: str, proof_root: Path = DEFAULT_PROOF_ROOT) -> dict[str, Any]:
    td = _task_dir(task_id, proof_root)
    receipts_dir = td / "receipts"
    statuses: dict[str, Any] = {}
    for provider in PROVIDERS:
        candidates = list(receipts_dir.glob(provider + "*.json")) + list(receipts_dir.glob(provider + "*.txt")) + list(receipts_dir.glob(provider + "*.md"))
        parsed: list[Any] = []
        success = False
        failure_reasons: list[str] = []
        for p in candidates:
            if p.suffix == ".json":
                obj = _read_json(p)
                parsed.append(obj)
                status_blob = json.dumps(obj, ensure_ascii=False).lower() if obj is not None else ""
                if any(x in status_blob for x in ["timeout", "error", "failed", "503", "401"]):
                    failure_reasons.append(p.name)
                if any(x in status_blob for x in ["success", "pass", "http_200", "http 200", '"http": 200', "result"]):
                    success = True
            elif p.stat().st_size > 0:
                success = True
        statuses[provider] = {
            "found": bool(candidates),
            "success": success,
            "files": [str(p) for p in candidates],
            "bytes": sum(p.stat().st_size for p in candidates if p.exists()),
            "failure_reasons": failure_reasons,
            "parsed_preview": parsed[:2],
        }
    return statuses


def state_chain(task_id: str, proof_root: Path = DEFAULT_PROOF_ROOT) -> dict[str, Any]:
    td = _task_dir(task_id, proof_root)
    path = td / "state_transition.jsonl"
    states: list[str] = []
    rows: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                rows.append(obj)
                if obj.get("state"):
                    states.append(obj["state"])
            except Exception:
                pass
    missing = [s for s in STATE_REQUIRED if s not in states]
    return {"path": str(path), "states": states, "missing": missing, "rows": rows[-20:]}


def evaluate_packet(task_id: str, proof_root: Path = DEFAULT_PROOF_ROOT) -> dict[str, Any]:
    td = _task_dir(task_id, proof_root)
    intake = _read_json(td / "task_intake.json")
    core = _read_json(td / "core_readback" / "core_file_inventory.json") or collect_core_inventory(task_id, proof_root)
    smoke = _read_json(td / "core_readback" / "runtime_import_smoke.json") or import_smoke(task_id, proof_root)
    bridge = bridge_summary()
    stats = gene_db_stats()
    headers = header_ast_check()
    receipts = provider_receipts(task_id, proof_root)
    chain = state_chain(task_id, proof_root)

    missing_artifacts = []
    if not intake:
        missing_artifacts.append("task_intake.json")
    if not core:
        missing_artifacts.append("core_file_inventory.json")
    if not smoke or smoke.get("exit_code") != 0:
        missing_artifacts.append("runtime_import_smoke_pass")
    if chain["missing"]:
        missing_artifacts.append("state_chain:" + ",".join(chain["missing"]))
    for provider, meta in receipts.items():
        if not meta["found"]:
            missing_artifacts.append("provider_receipt:" + provider)
        elif not meta.get("success"):
            missing_artifacts.append("provider_success:" + provider)

    all_provider_success = all(v.get("success") for v in receipts.values())
    smoke_pass = bool(smoke and smoke.get("exit_code") == 0)
    structural_pass = bool(intake) and smoke_pass and headers.get("pass") and bool(bridge.get("parsed"))
    if structural_pass and all_provider_success and not chain["missing"]:
        verdict = "PASS_MINIMAL_BOUNDED_ARS_PROOF"
    elif structural_pass:
        verdict = "WATCH_STRUCTURAL_ONLY_OR_PARTIAL_RECEIPTS"
    else:
        verdict = "BLOCKED_NO_MINIMAL_STRUCTURE"

    packet = {
        "schema": "pgg_ars_evidence_gate/v1",
        "task_id": task_id,
        "created_at": _now(),
        "verdict": verdict,
        "boundary": "bounded evidence gate only; not full AGI/T5/native-core fusion/production autonomy proof",
        "task_dir": str(td),
        "missing_artifacts": missing_artifacts,
        "core_inventory": {"item_count": len(core.get("items", [])) if isinstance(core, dict) else 0},
        "runtime_import_smoke": smoke,
        "bridge_summary": bridge.get("parsed"),
        "gene_db_stats": stats,
        "header_ast_check": headers,
        "provider_receipts": receipts,
        "state_chain": chain,
    }
    td.mkdir(parents=True, exist_ok=True)
    (td / "proof_packet.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2))
    return packet


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="PGG ARS read-only evidence gate")
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--proof-root", default=str(DEFAULT_PROOF_ROOT))
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--summary", default="")
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    proof_root = Path(args.proof_root)
    if args.init:
        init_task(args.task_id, proof_root, args.summary)
    if args.collect or args.init:
        collect_core_inventory(args.task_id, proof_root)
        import_smoke(args.task_id, proof_root)
    packet = evaluate_packet(args.task_id, proof_root)
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print(f"{packet['verdict']} task_id={args.task_id} missing={len(packet['missing_artifacts'])} path={packet['task_dir']}")
    return 0 if not packet["verdict"].startswith("BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
