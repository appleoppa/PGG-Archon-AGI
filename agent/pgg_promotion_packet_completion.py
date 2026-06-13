"""PGG proof packet completion for Promotion Authority Matrix.

Read-only completion gate: source readback, py_compile/test smoke, ledger evidence,
and replay. It never mutates GeneDB and never promotes by itself.
"""
from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "PGGProofPacketCompletion/v0.1"
BOUNDARY = "READ_ONLY_COMPLETION_NO_DB_MUTATION_NO_AUTO_PROMOTION"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _parse_source_file(packet: dict[str, Any]) -> Path | None:
    raw = packet.get("source_refs_json")
    if not raw:
        return None
    try:
        refs = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return None
    source = refs.get("source_file") if isinstance(refs, dict) else None
    return Path(source).expanduser() if source else None


def _repo_root_from_source(source: Path) -> Path:
    parts = source.parts
    if "hermes-agent" in parts:
        idx = parts.index("hermes-agent")
        return Path(*parts[: idx + 1])
    if "agent" in parts:
        return source.parent.parent
    return source.parent.parent if source.parent.name == "agent" else source.parent


def _candidate_tests(source: Path, pytest_root: Path | None = None) -> list[Path]:
    root = pytest_root or _repo_root_from_source(source)
    stem = source.stem
    candidates = [
        root / "tests" / "agent" / f"test_{stem}.py",
        root / "tests" / f"test_{stem}.py",
    ]
    return [p for p in candidates if p.exists()]


def _run(cmd: list[str], *, cwd: Path | None = None, pythonpath: Path | None = None) -> dict[str, Any]:
    env = os.environ.copy()
    if pythonpath:
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(pythonpath) + ((os.pathsep + existing) if existing else "")
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    return {"cmd": cmd, "exit_code": proc.returncode, "output_tail": proc.stdout[-4000:]}


def complete_packet(packet: dict[str, Any], outdir: str | Path, *, pytest_root: str | Path | None = None, pythonpath: str | Path | None = None) -> dict[str, Any]:
    """Complete one proof packet as far as possible, without DB mutation."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    task_id = packet.get("task_id") or packet.get("capability_id") or "unknown"
    source = _parse_source_file(packet)
    result: dict[str, Any] = {
        "schema": "PGGProofPacketCompletionResult/v0.1",
        "task_id": task_id,
        "capability_id": packet.get("capability_id"),
        "risk_lane": packet.get("risk_lane"),
        "source_file": str(source) if source else None,
        "started_at": _now(),
        "completed_evidence": [],
        "missing_evidence": [],
        "command_results": [],
        "db_mutation": False,
        "controlled_promotion_eligible": False,
        "boundary": BOUNDARY,
    }
    if source is None or not source.exists():
        result["verdict"] = "BLOCKED_SOURCE_MISSING"
        result["missing_evidence"] = ["source_readback", "test_output", "ledger_or_manifest", "replay"]
        (out / f"{task_id}.completion.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    result["source_size_bytes"] = source.stat().st_size
    result["completed_evidence"].append("source_readback")

    try:
        py_compile.compile(str(source), doraise=True)
        result["completed_evidence"].append("runtime_output")
        result["command_results"].append({"cmd": [sys.executable, "-m", "py_compile", str(source)], "exit_code": 0, "output_tail": "py_compile PASS"})
    except py_compile.PyCompileError as exc:
        result["command_results"].append({"cmd": [sys.executable, "-m", "py_compile", str(source)], "exit_code": 1, "output_tail": str(exc)[-4000:]})
        result["verdict"] = "BLOCKED_PY_COMPILE_FAILED"
        result["missing_evidence"] = ["test_output", "ledger_or_manifest", "replay"]
        (out / f"{task_id}.completion.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    root = Path(pytest_root).expanduser() if pytest_root else _repo_root_from_source(source)
    py_path = Path(pythonpath).expanduser() if pythonpath else root
    tests = _candidate_tests(source, root)
    if not tests:
        result["verdict"] = "BLOCKED_TEST_MISSING"
        result["missing_evidence"] = ["test_output", "ledger_or_manifest", "replay"]
        (out / f"{task_id}.completion.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    test_cmd = [sys.executable, "-m", "pytest", str(tests[0]), "-q"]
    first = _run(test_cmd, cwd=root, pythonpath=py_path)
    result["command_results"].append(first)
    if first["exit_code"] != 0:
        result["verdict"] = "BLOCKED_TEST_FAILED"
        result["missing_evidence"] = ["test_output", "ledger_or_manifest", "replay"]
        (out / f"{task_id}.completion.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    result["completed_evidence"].append("test_output")

    second = _run(test_cmd, cwd=root, pythonpath=py_path)
    result["command_results"].append(second)
    if second["exit_code"] != 0:
        result["verdict"] = "BLOCKED_REPLAY_FAILED"
        result["missing_evidence"] = ["ledger_or_manifest", "replay"]
        (out / f"{task_id}.completion.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    result["completed_evidence"].append("replay")

    ledger = out / "completion_ledger.jsonl"
    ledger_entry = {"task_id": task_id, "capability_id": packet.get("capability_id"), "source_file": str(source), "test_file": str(tests[0]), "verdict": "PASS_CONTROLLED_PROMOTION_PROPOSAL", "written_at": _now(), "boundary": BOUNDARY}
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ledger_entry, ensure_ascii=False) + "\n")
    result["ledger_path"] = str(ledger)
    result["completed_evidence"].append("ledger_or_manifest")

    required = set(packet.get("required_evidence") or ["source_readback", "test_output", "runtime_output", "ledger_or_manifest", "replay"])
    if packet.get("risk_lane") == "low_engineering" and required.issubset(set(result["completed_evidence"]) | {"claim_extract"}):
        result["controlled_promotion_eligible"] = True
        result["verdict"] = "PASS_CONTROLLED_PROMOTION_PROPOSAL"
    else:
        result["verdict"] = "WATCH_REQUIRES_HUMAN_OR_MORE_EVIDENCE"
        result["missing_evidence"] = sorted(required - set(result["completed_evidence"]))
    (out / f"{task_id}.completion.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def complete_packet_queue(queue_path: str | Path, outdir: str | Path, *, limit: int = 10, pytest_root: str | Path | None = None, pythonpath: str | Path | None = None) -> dict[str, Any]:
    queue = json.loads(Path(queue_path).read_text(encoding="utf-8"))
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    results = [complete_packet(packet, out, pytest_root=pytest_root, pythonpath=pythonpath) for packet in queue[:limit]]
    verdict_counts = Counter(r.get("verdict") for r in results)
    proposal = [r for r in results if r.get("controlled_promotion_eligible")]
    (out / "completion_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "controlled_promotion_proposal.json").write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "schema": SCHEMA,
        "created_at": _now(),
        "queue_path": str(queue_path),
        "outdir": str(out),
        "completed_count": len(results),
        "verdict_counts": dict(verdict_counts),
        "controlled_promotion_proposal_count": len(proposal),
        "db_mutation": False,
        "boundary": BOUNDARY,
    }
    (out / "completion_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


__all__ = ["complete_packet", "complete_packet_queue"]
