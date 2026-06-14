"""Bounded PGG Archon CMMI Industrial Standard — file-18 (real surface).

CMMI 工业化标准 (CMMI industrial standard) status surface.

Legacy 4 probes remain for compatibility, but Super Evolution 18 now also
checks the bounded Rust/PyO3 industrial evidence gate:
  1. agent.pgg_archon_cmmi_industrial module is importable
  2. ~/.hermes/data/cmmi_audit_log.jsonl exists
  3. env PGG_ARCHON_CMMI_VERSION is set
  4. ~/.hermes/data/pgg_archon_audit.jsonl has ≥3 lines
  5. hermes_pgg_cmmi_industrial_gate PyO3 module importable
  6. Rust gate sample decision is bounded PASS or explicit WATCH/HOLD
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CMMIProbe:
    name: str
    status: str
    probes: dict[str, str]
    notes: str = ""


def _probe_env(env_name: str) -> str:
    return "present" if os.environ.get(env_name) else "missing"


def _probe_module(name: str) -> str:
    try:
        importlib.import_module(name)
        return "importable"
    except Exception:
        return "missing"


def _probe_rust_gate() -> tuple[str, str]:
    try:
        import json
        gate = importlib.import_module("hermes_pgg_cmmi_industrial_gate")
        evidence = json.loads(gate.sample_input_json())
        decision = json.loads(gate.evaluate_evidence_json(json.dumps(evidence)))
        return "importable", str(decision.get("status", "UNKNOWN"))
    except Exception as exc:
        return "missing", f"error:{type(exc).__name__}"


def probe_cmmi() -> CMMIProbe:
    log = Path.home() / ".hermes" / "data" / "cmmi_audit_log.jsonl"
    audit = Path.home() / ".hermes" / "data" / "pgg_archon_audit.jsonl"
    audit_lines = sum(1 for _ in audit.open("r", encoding="utf-8")) if audit.exists() else 0
    rust_gate_import, rust_gate_status = _probe_rust_gate()
    deps = {
        "module_cmmi": _probe_module("agent.pgg_archon_cmmi_industrial"),
        "cmmi_audit_log_present": "present" if log.exists() else "missing",
        "env_PGG_ARCHON_CMMI_VERSION": _probe_env("PGG_ARCHON_CMMI_VERSION"),
        "audit_trail_lines": str(audit_lines),
        "rust_cmmi_gate": rust_gate_import,
        "rust_cmmi_gate_status": rust_gate_status,
    }
    present = 0
    if deps["module_cmmi"] == "importable":
        present += 1
    if deps["cmmi_audit_log_present"] == "present":
        present += 1
    if deps["env_PGG_ARCHON_CMMI_VERSION"] == "present":
        present += 1
    if audit_lines >= 3:
        present += 1
    if rust_gate_import == "importable":
        present += 1
    if rust_gate_status in {
        "PASS_BOUNDED_CMMI18_CORE_FUSION_LIVE_AUTOMATION_HOLD",
        "PASS_FULLY_VERIFIED_AUTHORIZED_INDUSTRIAL_LOOP",
        "WATCH_PARTIAL_CMMI18_GATE",
    }:
        present += 1
    if present >= 5:
        status = "ACTIVE"
    elif present >= 3:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return CMMIProbe(
        name="cmmi",
        status=status,
        probes=deps,
        notes=f"CMMI industrial standard super-evolution 18; {present}/6 legacy+Rust evidence gates resolved; live automation remains separately gated",
    )


def run_cmmi() -> dict[str, Any]:
    p = probe_cmmi()
    return {
        "schema": "PGGArchonCMMI/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means legacy+Rust evidence gates resolved; live Docker/GitHub/CI automation is separately gated and may remain HOLD; not formal CMMI certification or full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_cmmi(), ensure_ascii=False, indent=2))
