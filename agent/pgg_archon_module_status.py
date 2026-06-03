"""PGG Archon module status compatibility surface.

Read-only replacement for the historical ``pgg_archon_module_status`` overlay.
It does not claim the old visual dashboard is restored; it reports the current
importability of known PGG/APEX modules with explicit evidence and boundaries.
"""
from __future__ import annotations

import importlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Iterable

SCHEMA = "PGGArchonModuleStatus/v2"
DEFAULT_MODULES = [
    "hermes_apex_evolution",
    "apex_god.health",
    "apex_god.fail_closed",
    "apex_god.middleware.convergence_check",
    "agent.case_orchestrator",
    "agent.pgg_archon_delta_gate",
    "agent.pgg_archon_codegenesis_scanner",
    "agent.pgg_archon_memory_trace",
    "agent.pgg_archon_schema_validator",
    "agent.pgg_archon_provenance",
    "agent.pgg_archon_debate",
    "agent.pgg_archon_ecc",
]


@dataclass(frozen=True)
class ModuleProbe:
    module: str
    ok: bool
    file: str | None = None
    error: str | None = None


def probe_module(module: str) -> ModuleProbe:
    try:
        mod = importlib.import_module(module)
        return ModuleProbe(module=module, ok=True, file=getattr(mod, "__file__", None))
    except Exception as exc:  # pragma: no cover - exact import errors are environment-specific
        return ModuleProbe(module=module, ok=False, error=f"{type(exc).__name__}: {exc}")


def build_module_status(modules: Iterable[str] | None = None) -> dict[str, Any]:
    """Return a read-only importability report for PGG/APEX modules."""
    names = list(modules or DEFAULT_MODULES)
    probes = [probe_module(name) for name in names]
    ok_count = sum(1 for p in probes if p.ok)
    failed = [p.module for p in probes if not p.ok]
    status = "PASS" if not failed else "WATCH"
    return {
        "schema": SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        "checked_count": len(probes),
        "ok_count": ok_count,
        "failed_count": len(failed),
        "failed_modules": failed,
        "modules": [asdict(p) for p in probes],
        "side_effects": "read_only_import_probe",
        "boundary": "Importability/status surface only; not proof of full AGI, external benchmark, or runtime participation.",
    }


def render_ascii_status(report: dict[str, Any] | None = None) -> str:
    """Render a compact terminal-friendly status table."""
    data = report or build_module_status()
    lines = [
        f"PGG Archon Module Status [{data.get('status')}] {data.get('ok_count')}/{data.get('checked_count')}",
        "-" * 72,
    ]
    for item in data.get("modules", []):
        flag = "PASS" if item.get("ok") else "WATCH"
        lines.append(f"{flag:5} {item.get('module')}")
    lines.append(f"boundary: {data.get('boundary')}")
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - CLI helper
    print(json.dumps(build_module_status(), ensure_ascii=False, indent=2))


__all__ = ["SCHEMA", "DEFAULT_MODULES", "ModuleProbe", "probe_module", "build_module_status", "render_ascii_status"]


if __name__ == "__main__":
    main()
