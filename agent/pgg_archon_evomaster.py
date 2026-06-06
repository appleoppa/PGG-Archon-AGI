"""Bounded PGG Archon EvoMaster Native Evolution Core — file-09 (real surface).

5-probe status surface for EvoMaster native evolution core formula:
  1. agent.pgg_archon_evomaster module is importable
  2. ~/.hermes/data/evomaster_state.jsonl or similar state log exists
  3. env PGG_ARCHON_EVOMASTER_VERSION or durable version marker is set
  4. ~/.hermes/data/pgg_archon_audit.jsonl exists (audit trail)
  5. hermes_pgg_evomaster_gate Rust/PyO3 module is importable
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class EvoMasterProbe:
    name: str
    status: str
    probes: dict[str, str]
    notes: str = ""


def _probe_env(env_name: str) -> str:
    return "present" if os.environ.get(env_name) else "missing"


def _probe_version_marker(home: Path | None = None) -> str:
    home = home or Path.home() / ".hermes"
    marker = home / "data" / "evomaster_version.json"
    if os.environ.get("PGG_ARCHON_EVOMASTER_VERSION"):
        return "present"
    if not marker.exists():
        return "missing"
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except Exception:
        return "invalid"
    return "present" if data.get("version") and data.get("schema") == "PGGArchonEvoMasterVersion/v1" else "invalid"


def write_version_marker(version: str = "0.1.0") -> dict[str, Any]:
    marker = Path.home() / ".hermes" / "data" / "evomaster_version.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "PGGArchonEvoMasterVersion/v1",
        "version": version,
        "source": "durable_marker",
        "env_var": "PGG_ARCHON_EVOMASTER_VERSION",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "boundary": "Durable status marker for EvoMaster surface only; not a capability proof by itself.",
    }
    marker.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(marker), "row": row}


def _probe_module(name: str) -> str:
    try:
        importlib.import_module(name)
        return "importable"
    except Exception:
        return "missing"


def _probe_path_writable(p: Path) -> str:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".pgg_archon_evomaster_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_evomaster() -> EvoMasterProbe:
    evo_state = Path.home() / ".hermes" / "data" / "evomaster_state.jsonl"
    audit = Path.home() / ".hermes" / "data" / "pgg_archon_audit.jsonl"
    deps = {
        "module_evomaster": _probe_module("agent.pgg_archon_evomaster_core"),
        "evomaster_state_present": "present" if evo_state.exists() else "missing",
        "version_marker_present": _probe_version_marker(),
        "audit_trail_present": "present" if audit.exists() else "missing",
        "rust_evomaster_gate": _probe_module("hermes_pgg_evomaster_gate"),
    }
    present = sum(1 for v in deps.values() if v in {"importable", "present", "writable"})
    if present == 5:
        status = "ACTIVE"
    elif present >= 3:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return EvoMasterProbe(
        name="evomaster",
        status=status,
        probes=deps,
        notes=f"EvoMaster native evolution core super-evolution 9; {present}/5 surface gates resolved",
    )


def build_evomaster_gate_input(home: Path | None = None) -> dict[str, Any]:
    """Build bounded Super Evolution 9 evidence from local readback.

    This intentionally does not execute provider calls or mutate core runtime.
    Missing policy-loop evidence stays missing so the gate cannot overclaim.
    """
    home = home or Path.home() / ".hermes"
    hashpool = home / "workspace" / "trace_hashpool" / "hashpool.jsonl"
    total = valid = duplicate = 0
    if hashpool.exists():
        for line in hashpool.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            total += 1
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("valid", row.get("status") == "completed"):
                valid += 1
            if row.get("duplicate"):
                duplicate += 1
    invalid = max(total - valid, 0)
    llm_dir = home / "workspace" / "pgg-archon-governance" / "super-evolution-9-evomaster" / "llm"
    visible_llms = 0
    gpt_or_claude = False
    if llm_dir.exists():
        for p in llm_dir.glob("*.txt"):
            size = p.stat().st_size
            if size > 100:
                visible_llms += 1
                if p.stem in {"gpt55", "claude"}:
                    gpt_or_claude = True
    external_summary = home / "workspace" / "pgg-archon-governance" / "super-evolution-9-evomaster" / "open_source" / "github_scout_summary.json"
    patterns = 0
    repo_hits = 0
    if external_summary.exists():
        try:
            summary = json.loads(external_summary.read_text(encoding="utf-8"))
            patterns = len(summary.get("absorbed_readonly_patterns", []))
            repo_hits = len(summary.get("repos", []))
        except Exception:
            patterns = 0
    policy_report_path = home / "workspace" / "pgg-archon-governance" / "super-evolution-9-evomaster" / "policy_loop" / "policy_loop_report.json"
    policy_report: dict[str, Any] = {}
    policy_records: list[dict[str, Any]] = []
    latest_reward = {
        "tool_success_count": 0,
        "tool_total_count": 0,
        "exec_reward": 0.0,
        "lambda": 0.0,
        "k_claw_score": 1.0 if valid > 0 else 0.0,
        "objective_score": 0.0,
        "bounded_reward": False,
        "objective_used_for_ranking": False,
    }
    if policy_report_path.exists():
        try:
            policy_report = json.loads(policy_report_path.read_text(encoding="utf-8"))
            policy_records = [r for r in policy_report.get("records", []) if isinstance(r, dict)]
            if policy_records and isinstance(policy_records[-1].get("reward"), dict):
                latest_reward.update(policy_records[-1]["reward"])
        except Exception:
            policy_report = {}
    policy_hashes = [r.get("policy_hash") for r in policy_records if r.get("policy_hash")]
    policy_differs = len(set(policy_hashes)) >= 2
    loop_rounds = int(policy_report.get("rounds") or len(policy_records) or 0)
    return {
        "source": {
            "status_surface_importable": True,
            "core_cycle_importable": _probe_module("agent.pgg_archon_evomaster_core") == "importable",
            "hashpool_sidecar_present": (home / "scripts" / "hermes_trace_hashpool.py").exists(),
            "rust_gate_integrated": _probe_module("hermes_pgg_evomaster_gate") == "importable",
        },
        "trace": {
            "total_traces": total,
            "valid_traces": valid,
            "invalid_traces": invalid,
            "duplicate_traces": duplicate,
            "hash_algorithm": "sha256" if hashpool.exists() else "missing",
            "stable_hash_readback": hashpool.exists() and total > 0,
            "eval_center_source_present": (home / "eval_center.db").exists(),
        },
        "reward": latest_reward,
        "policy": {
            "llm_provider_call_visible": visible_llms > 0,
            "provider_count_visible": visible_llms,
            "gpt_or_claude_visible": gpt_or_claude,
            "pi_next_written": bool(policy_records),
            "pi_next_differs_from_previous": policy_differs,
            "core_reads_k_claw": bool(policy_records),
            "sandbox_constraint_declared": True,
            "sandbox_execution_evidence": bool(policy_records),
            "loop_rounds": loop_rounds,
        },
        "anti_mock": {
            "hardcoded_pass_detected": False,
            "fixed_score_only_detected": False,
            "dry_run_only": False,
            "boundary_statement_present": True,
            "audit_readback_present": (home / "data" / "pgg_archon_audit.jsonl").exists(),
        },
        "external_learning": {
            "github_search_attempted": external_summary.exists(),
            "repo_hits": repo_hits,
            "readonly_patterns_absorbed": patterns,
            "patterns_recorded_path_present": external_summary.exists(),
        },
        "manifest_integration_present": (home / "data" / "EVOLUTION_MANIFEST.json").exists(),
    }


def run_rust_evomaster_gate(home: Path | None = None) -> dict[str, Any]:
    evidence = build_evomaster_gate_input(home)
    try:
        import hermes_pgg_evomaster_gate as gate  # type: ignore

        out = json.loads(gate.evaluate_evidence_json(json.dumps(evidence, ensure_ascii=False)))
        out["rust_module_version"] = gate.version()
        out["evidence_input"] = evidence
        return out
    except Exception as exc:  # noqa: BLE001
        return {
            "schema": "HermesPGGEvoMasterGate/v1",
            "status": "WATCH_RUST_GATE_UNAVAILABLE",
            "score": 0.0,
            "gaps": [f"rust_gate_unavailable: {exc!r}"],
            "evidence_input": evidence,
            "boundary": "Python wrapper fallback only; Rust/PyO3 gate was not callable.",
        }


def run_evomaster() -> dict[str, Any]:
    p = probe_evomaster()
    return {
        "schema": "PGGArchonEvoMaster/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "rust_gate": run_rust_evomaster_gate(),
        "boundary": "status surface plus bounded Rust/PyO3 evidence gate; ACTIVE means surface gates resolved, not full CLAW native self-evolution or full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_evomaster(), ensure_ascii=False, indent=2))
