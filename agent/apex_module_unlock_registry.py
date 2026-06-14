"""APEX module unlock registry.

Discovers selected APEX/PGG modules and records whether their public entrypoints
are present. This is an audit registry, not a dynamic importer/executor.
"""
from __future__ import annotations

import ast
import json
import time
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/apex-module-unlocks")
DEFAULT_MODULES = (
    "apex_formula.py",
    "apex_runtimeos_evm_gate.py",
    "apex_gep.py",
    "apex_gene_lifecycle.py",
    "apex_flow_reward.py",
    "apex_switch_cost.py",
    "apex_real_capability_metrics.py",
    "apex_sequence_loop_runner.py",
    "workspace_evidence_governor.py",
    "route_chain_stage_retry_replay.py",
    "case_flow_orchestrator_ledger.py",
    "capability_metric_driver.py",
)


def _public_defs(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            names.append(node.name)
    return names


def build_apex_module_unlock_registry(
    modules: Iterable[str] = DEFAULT_MODULES,
    *,
    repo_root: str | Path = REPO_ROOT,
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    root = Path(repo_root)
    entries = []
    for name in modules:
        path = root / "agent" / name
        if not path.exists():
            entries.append({"module": name, "status": "MISSING", "public_entrypoints": [], "unlock_state": "blocked_missing_file"})
            continue
        try:
            defs = _public_defs(path)
            status = "UNLOCKABLE" if defs else "PRESENT_NO_PUBLIC_ENTRYPOINT"
            unlock_state = "audit_ready" if defs else "manual_review"
        except Exception as exc:  # noqa: BLE001
            defs = []
            status = "PARSE_ERROR"
            unlock_state = f"blocked_parse_error:{type(exc).__name__}"
        entries.append({"module": name, "status": status, "public_entrypoints": defs[:20], "unlock_state": unlock_state})
    counts: dict[str, int] = {}
    for item in entries:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    report = {
        "schema": "ApexModuleUnlockRegistry/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "module_count": len(entries),
        "status_counts": dict(sorted(counts.items())),
        "entries": entries,
        "side_effects": "report_write" if write_report else "read_only_registry",
        "agi_completion_claim": False,
    }
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_apex_module_unlock_registry.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report_path"] = str(out)
    return report


__all__ = ["build_apex_module_unlock_registry"]
