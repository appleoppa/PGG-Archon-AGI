"""Super Evolution 13 APEX ΔE unified read-only health report.

Boundary: aggregates existing gate/module/ledger/dashboard/formula/API status. It
performs no provider calls, no network calls, no crawling, no scheduler/security
mutation, and no automatic remediation.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


def _latest_jsonl(path: Path) -> dict[str, Any]:
    try:
        lines = [line for line in path.expanduser().read_text(encoding="utf-8").splitlines() if line.strip()]
        return json.loads(lines[-1]) if lines else {}
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc), "path": str(path)}


def _gate_smoke() -> dict[str, Any]:
    try:
        import hermes_pgg_apex_delta_e_gate as gate  # type: ignore

        result = json.loads(gate.evaluate_json(gate.sample_input_json()))
        return {
            "status": "PASS" if result.get("state") == "PASS_BOUNDED_APEX_DELTA_E_GATE" else "WATCH",
            "version": gate.version(),
            "state": result.get("state"),
            "score": result.get("score"),
            "audit_hash": result.get("audit_hash"),
            "boundary": result.get("boundary"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "WATCH", "error": repr(exc)}


def build_health_report(*, home: str | Path | None = None, task: str = "超级进化13 APEX ΔE runtime health") -> dict[str, Any]:
    h = Path(home).expanduser() if home else Path.home()
    gate = _gate_smoke()
    ledger = _latest_jsonl(h / ".hermes/data/pgg_apex_delta_e_autorun_ledger.jsonl")

    try:
        from agent.pgg_archon_autonomous_status import build_status

        dashboard = build_status(home=h).to_json_dict()
        dashboard_card = dashboard.get("apex_delta_e_gate") or {}
    except Exception as exc:  # noqa: BLE001
        dashboard = {"error": repr(exc)}
        dashboard_card = {"status": "WATCH", "error": repr(exc)}

    try:
        from agent.pgg_archon_formula_gate_status import build_formula_gate_status

        formula = build_formula_gate_status(task, manifest_path=h / ".hermes/data/EVOLUTION_MANIFEST.json")
        formula_apex = (formula.get("manifest_summary") or {}).get("apex_delta_e_gate") or {}
    except Exception as exc:  # noqa: BLE001
        formula = {"error": repr(exc)}
        formula_apex = {"status": "WATCH", "error": repr(exc)}

    checks = {
        "rust_gate_smoke": gate.get("status") == "PASS",
        "light_ledger_pass": ledger.get("status") == "PASS" and ledger.get("gate_state") == "PASS_BOUNDED_APEX_DELTA_E_GATE",
        "runtime_dashboard_card_pass": dashboard_card.get("status") == "PASS",
        "formula_panel_summary_pass": formula_apex.get("status") == "PASS",
    }
    overall = "PASS" if all(checks.values()) else "WATCH"
    return {
        "schema": "PGGApexDeltaEUnifiedHealth/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": overall,
        "checks": checks,
        "rust_gate": gate,
        "light_ledger": {
            "status": ledger.get("status"),
            "gate_state": ledger.get("gate_state"),
            "gate_score": ledger.get("gate_score"),
            "audit_hash": ledger.get("audit_hash"),
            "summary_sha256": ledger.get("summary_sha256"),
            "timestamp": ledger.get("timestamp"),
            "error": ledger.get("error"),
        },
        "runtime_dashboard": {
            "schema": dashboard.get("schema"),
            "card": dashboard_card,
            "known_gaps": dashboard.get("known_gaps", []),
        },
        "formula_panel": {
            "schema": formula.get("schema"),
            "status": formula.get("status"),
            "apex_delta_e_gate": formula_apex,
            "unresolved_gap_count": formula.get("unresolved_gap_count"),
            "missing_gates": formula.get("missing_gates"),
        },
        "boundary": "Read-only unified health report; no provider calls, no crawling, no code mutation, no scheduler/security mutation, no full AGI/self-awareness/official benchmark proof.",
    }


def render_health_report(report: dict[str, Any]) -> str:
    checks = report.get("checks") or {}
    return "\n".join(
        [
            "【Super Evolution 13 / APEX ΔE 统一健康检查】",
            f"状态：{report.get('status')}",
            f"Rust gate：{'PASS' if checks.get('rust_gate_smoke') else 'WATCH'}",
            f"LIGHT ledger：{'PASS' if checks.get('light_ledger_pass') else 'WATCH'}",
            f"Runtime dashboard：{'PASS' if checks.get('runtime_dashboard_card_pass') else 'WATCH'}",
            f"/goal 公式面板：{'PASS' if checks.get('formula_panel_summary_pass') else 'WATCH'}",
            f"边界：{report.get('boundary')}",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Super Evolution 13 APEX ΔE unified read-only health report")
    parser.add_argument("--home")
    parser.add_argument("--task", default="超级进化13 APEX ΔE runtime health")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = build_health_report(home=args.home, task=args.task)
    if args.output:
        out = Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render_health_report(report))
    return 0 if report.get("status") == "PASS" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
