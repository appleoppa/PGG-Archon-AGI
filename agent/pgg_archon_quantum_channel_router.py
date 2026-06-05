"""Bounded PGG Archon Quantum Channel Router — file-01 (real surface).

4-probe status surface for 河图洛书 LLM routing:
  1. agent.pgg_archon_quantum_channel_router module is importable
  2. ~/.hermes/data/quantum_router_cache has at least 1 file
  3. env PGG_ARCHON_ROUTER_VERSION is set
  4. ~/.hermes/data/router_health.jsonl or similar router log exists
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HOME = Path.home()
OMNIROUTE_CRATE = HOME / ".hermes" / "hermes-agent" / "rust_modules" / "hermes_pgg_omniroute"
OMNIROUTE_BIN = OMNIROUTE_CRATE / "target" / "debug" / "pgg-omniroute-smoke"
OMNIROUTE_DASHBOARD = HOME / ".hermes" / "workspace" / "github_absorption" / "9router" / "analysis" / "pgg-omniroute-dashboard-20260605.json"
OMNIROUTE_EVM_REPORT = HOME / ".hermes" / "workspace" / "github_absorption" / "9router" / "analysis" / "pgg-omniroute-evm-report-20260605.json"
OMNIROUTE_PROVIDER_HEALTH = HOME / ".hermes" / "workspace" / "github_absorption" / "9router" / "analysis" / "pgg-omniroute-provider-health-20260605.json"
OMNIROUTE_CONTROL = HOME / ".hermes" / "data" / "omniroute_control.json"
OMNIROUTE_ROUTE_CALL_EVENTS = HOME / ".hermes" / "data" / "omniroute_route_call_events.jsonl"
OMNIROUTE_PROVIDER_CALL_EVENTS = HOME / ".hermes" / "data" / "omniroute_provider_call_events.jsonl"


@dataclass
class OmniRouteDecision:
    schema: str
    decided_at: str
    task_type: str
    requested_provider: str
    selected_provider: str
    selected_source: str
    dashboard_selected_provider: str
    manual_override_provider: str
    manual_override_applied: bool
    available_providers: list[str]
    blocked_reasons: list[str]
    generation_id: str
    boundary: str


@dataclass
class QuantumChannelRouterProbe:
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


def _probe_path_writable(p: Path) -> str:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".pgg_archon_router_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def _write_live_evm_report() -> dict[str, Any]:
    """Run the live Python EvomasterEngine and persist its report for Rust.

    This is a real local EVM computation, not an LLM/provider call.
    """
    try:
        from agent.evm_engine import EvomasterEngine

        report = EvomasterEngine(strategy="score").run(iterations=1, seed=42)
        OMNIROUTE_EVM_REPORT.parent.mkdir(parents=True, exist_ok=True)
        OMNIROUTE_EVM_REPORT.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        first = (report.get("results") or [{}])[0]
        return {
            "status": "present",
            "path": str(OMNIROUTE_EVM_REPORT),
            "schema": str(report.get("schema", "")),
            "final_score": str(report.get("final_score", "")),
            "ancient_product": str(first.get("ancient_product", "")),
            "defect_rate": str(first.get("defect_rate", "")),
        }
    except Exception as exc:
        return {"status": "error", "error": repr(exc), "path": str(OMNIROUTE_EVM_REPORT)}


def _write_live_provider_health() -> dict[str, Any]:
    """Run live provider probes and persist provider health for Rust.

    Real lightweight upstream probes are performed by
    agent.pgg_archon_provider_health_snapshot. Single-provider failure is
    recorded as unhealthy and must not be converted into a fake pass.
    """
    try:
        from agent.pgg_archon_provider_health_snapshot import run_provider_health_snapshot

        snap = run_provider_health_snapshot(OMNIROUTE_PROVIDER_HEALTH, timeout=18.0)
        summary = snap.get("summary", {})
        return {
            "status": "present",
            "path": str(OMNIROUTE_PROVIDER_HEALTH),
            "schema": str(snap.get("schema", "")),
            "healthy_count": str(summary.get("healthy_count", "")),
            "unhealthy_count": str(summary.get("unhealthy_count", "")),
            "providers": ",".join(summary.get("providers", [])),
            "cache_status": str(snap.get("cache_status", "")),
            "age_sec": str(snap.get("age_sec", "")),
            "ttl_sec": str(snap.get("ttl_sec", "")),
        }
    except Exception as exc:
        return {"status": "error", "error": repr(exc), "path": str(OMNIROUTE_PROVIDER_HEALTH)}


def _run_omniroute_dashboard() -> dict[str, Any]:
    """Return Rust OmniRoute dashboard JSON if the local binary is available.

    Bounded bridge: this exposes status/dashboard data only. It does not call
    upstream LLM providers and is not proof of provider participation.
    """
    if not OMNIROUTE_BIN.exists():
        return {"status": "missing_binary", "path": str(OMNIROUTE_BIN)}
    evm = _write_live_evm_report()
    health = _write_live_provider_health()
    cmd = [str(OMNIROUTE_BIN), "dashboard"]
    if evm.get("status") == "present" and health.get("status") == "present":
        cmd = [str(OMNIROUTE_BIN), "dashboard-from-live", str(OMNIROUTE_EVM_REPORT), str(OMNIROUTE_PROVIDER_HEALTH)]
    elif evm.get("status") == "present":
        cmd = [str(OMNIROUTE_BIN), "dashboard-from-evm", str(OMNIROUTE_EVM_REPORT)]
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        return {"status": "error", "error": repr(exc), "path": str(OMNIROUTE_BIN)}
    if proc.returncode != 0:
        return {
            "status": "error",
            "returncode": proc.returncode,
            "stderr": proc.stderr[-500:],
            "path": str(OMNIROUTE_BIN),
        }
    try:
        payload = json.loads(proc.stdout)
    except Exception as exc:
        return {"status": "invalid_json", "error": repr(exc), "stdout_head": proc.stdout[:500]}
    try:
        OMNIROUTE_DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
        OMNIROUTE_DASHBOARD.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return {
        "status": "present",
        "schema": str(payload.get("schema", "")),
        "selected_provider": str(payload.get("summary", {}).get("selected_provider", "")),
        "provider_cards": str(len(payload.get("provider_cards", []))),
        "blocked_count": str(payload.get("summary", {}).get("blocked_count", "")),
        "order_source": str(payload.get("order_source", "")),
        "evm_report_path": str(OMNIROUTE_EVM_REPORT),
        "provider_health_path": str(OMNIROUTE_PROVIDER_HEALTH),
        "provider_healthy_count": str(payload.get("provider_health_snapshot", {}).get("summary", {}).get("healthy_count", "")),
        "provider_unhealthy_count": str(payload.get("provider_health_snapshot", {}).get("summary", {}).get("unhealthy_count", "")),
        "provider_health_cache_status": str(payload.get("provider_health_snapshot", {}).get("cache_status", health.get("cache_status", ""))),
        "provider_health_age_sec": str(payload.get("provider_health_snapshot", {}).get("age_sec", health.get("age_sec", ""))),
        "provider_health_ttl_sec": str(payload.get("provider_health_snapshot", {}).get("ttl_sec", health.get("ttl_sec", ""))),
        "evm_final_score": str(payload.get("evm_report", {}).get("final_score", "")),
        "order_status": str(payload.get("order_influence", {}).get("status", "")),
        "order_strength": str(payload.get("order_influence", {}).get("order_strength", "")),
        "dashboard_path": str(OMNIROUTE_DASHBOARD),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _append_route_call_event(event: dict[str, Any]) -> None:
    try:
        OMNIROUTE_ROUTE_CALL_EVENTS.parent.mkdir(parents=True, exist_ok=True)
        with OMNIROUTE_ROUTE_CALL_EVENTS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _route_generation_id(dashboard: dict[str, Any], control: dict[str, Any]) -> str:
    try:
        import hashlib

        facts = {
            "dashboard_generated_at_epoch_ms": dashboard.get("generated_at_epoch_ms"),
            "dashboard_selected_provider": (dashboard.get("summary") or {}).get("selected_provider"),
            "control_mode": control.get("mode"),
            "control_provider": control.get("selected_provider_override"),
            "control_updated_at": control.get("updated_at"),
        }
        return hashlib.sha256(json.dumps(facts, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    except Exception:
        return "unknown"


def decide_omniroute_provider(task_type: str = "general", requested_provider: str = "") -> dict[str, Any]:
    """Return a bounded OmniRoute decision and persist route-call evidence.

    This function is the first real bridge from the WebUI manual/auto control
    surface into local quantum-router decisions. It does not call an upstream
    provider by itself; it records the provider that should be used by a later
    task execution layer.
    """
    dashboard = _read_json(OMNIROUTE_DASHBOARD)
    control = _read_json(OMNIROUTE_CONTROL)
    summary = dashboard.get("summary") or {}
    cards = dashboard.get("provider_cards") or []
    available = []
    blocked = []
    for card in cards if isinstance(cards, list) else []:
        if not isinstance(card, dict):
            continue
        provider = str(card.get("provider") or card.get("id") or card.get("name") or "").strip()
        if not provider:
            continue
        available.append(provider)
        if card.get("blocked") or card.get("blocked_reasons"):
            blocked.append(f"{provider}: {card.get('blocked_reasons') or card.get('reasons') or 'blocked'}")
    dashboard_selected = str(summary.get("selected_provider") or dashboard.get("selected_provider") or "").strip()
    manual_provider = str(control.get("selected_provider_override") or "").strip()
    mode = str(control.get("mode") or "auto")
    requested_provider = (requested_provider or "").strip()
    selected_source = "dashboard_auto"
    selected = dashboard_selected
    manual_applied = False
    if requested_provider:
        selected = requested_provider
        selected_source = "request_override"
    elif mode == "manual" and manual_provider:
        selected = manual_provider
        selected_source = "manual_control"
        manual_applied = True
    if not selected and available:
        selected = available[0]
        selected_source = "first_available_fallback"
    decision = OmniRouteDecision(
        schema="PGGArchonOmniRouteDecision/v1",
        decided_at=_now_iso(),
        task_type=task_type,
        requested_provider=requested_provider,
        selected_provider=selected,
        selected_source=selected_source,
        dashboard_selected_provider=dashboard_selected,
        manual_override_provider=manual_provider,
        manual_override_applied=manual_applied,
        available_providers=available,
        blocked_reasons=blocked,
        generation_id=_route_generation_id(dashboard, control),
        boundary="Route decision evidence only. Provider participation requires a subsequent real provider/API call tied to this decision.",
    )
    payload = asdict(decision)
    _append_route_call_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "route_decision", "payload": payload})
    return payload


def _append_provider_call_event(event: dict[str, Any]) -> None:
    try:
        OMNIROUTE_PROVIDER_CALL_EVENTS.parent.mkdir(parents=True, exist_ok=True)
        with OMNIROUTE_PROVIDER_CALL_EVENTS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _read_jsonl_tail(path: Path, limit: int = 20) -> list[dict[str, Any]]:
    try:
        if not path.exists():
            return []
        rows = path.read_text(encoding="utf-8").splitlines()[-limit:]
        out = []
        for row in rows:
            try:
                item = json.loads(row)
                if isinstance(item, dict):
                    out.append(item)
            except Exception:
                continue
        return out
    except Exception:
        return []


def recent_omniroute_route_events(limit: int = 20) -> list[dict[str, Any]]:
    return _read_jsonl_tail(OMNIROUTE_ROUTE_CALL_EVENTS, limit)


def recent_omniroute_provider_call_events(limit: int = 20) -> list[dict[str, Any]]:
    return _read_jsonl_tail(OMNIROUTE_PROVIDER_CALL_EVENTS, limit)


def execute_omniroute_provider_call(
    prompt: str = "Reply exactly: PGG_ROUTE_OK",
    *,
    task_type: str = "participation_probe",
    requested_provider: str = "",
    timeout: float = 45.0,
) -> dict[str, Any]:
    """Make a real provider API call tied to an OmniRoute decision.

    This is provider participation proof for a bounded probe. It is not a
    benchmark, not legal correctness evidence, and not proof of participation in
    unrelated user tasks.
    """
    from agent.pgg_archon_external_benchmark_provider_run import PROVIDERS, _load_env, call_provider

    decision = decide_omniroute_provider(task_type=task_type, requested_provider=requested_provider)
    selected = str(decision.get("selected_provider") or "").strip()
    _load_env(HOME / ".hermes" / ".env")
    spec = next((s for s in PROVIDERS if s.name == selected), None)
    started = datetime.now(timezone.utc)
    if spec is None:
        result = {
            "schema": "PGGArchonOmniRouteProviderParticipation/v1",
            "called_at": started.isoformat(),
            "decision": decision,
            "provider": selected,
            "participated": False,
            "http_status": 0,
            "visible_chars": 0,
            "elapsed_sec": 0.0,
            "error": f"selected provider {selected!r} not in callable PROVIDERS registry",
            "boundary": "No provider participation; selected provider is not callable by this local registry.",
        }
    else:
        call = call_provider(spec, prompt, timeout)
        text = call.get("parsed_text") or ""
        http_status = int(call.get("http_status") or 0)
        visible_chars = len(text)
        participated = http_status == 200 and visible_chars > 0
        result = {
            "schema": "PGGArchonOmniRouteProviderParticipation/v1",
            "called_at": started.isoformat(),
            "decision": decision,
            "provider": spec.name,
            "model": spec.model,
            "api_mode": spec.api_mode,
            "prompt_sha256": __import__("hashlib").sha256(prompt.encode("utf-8")).hexdigest(),
            "prompt_preview": prompt[:120],
            "participated": participated,
            "http_status": http_status,
            "visible_chars": visible_chars,
            "elapsed_sec": call.get("elapsed_sec", 0.0),
            "parsed_preview": text[:300],
            "error": call.get("error", "") if not participated else "",
            "boundary": "Provider participation proof for this bounded probe only; not benchmark/legal correctness/unrelated-task proof.",
        }
    _append_provider_call_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "provider_participation", "payload": result})
    return result


def probe_quantum_channel_router() -> QuantumChannelRouterProbe:
    cache_dir = HOME / ".hermes" / "data" / "quantum_router_cache"
    health_log = HOME / ".hermes" / "data" / "router_health.jsonl"
    cache_files = list(cache_dir.glob("*")) if cache_dir.exists() else []
    omniroute_dashboard = _run_omniroute_dashboard()
    deps = {
        "module_quantum_channel_router": _probe_module("agent.pgg_archon_quantum_channel_router"),
        "router_cache_files": str(len(cache_files)),
        "env_PGG_ARCHON_ROUTER_VERSION": _probe_env("PGG_ARCHON_ROUTER_VERSION"),
        "router_health_log": "present" if health_log.exists() else "missing",
        "rust_omniroute_crate": "present" if OMNIROUTE_CRATE.exists() else "missing",
        "rust_omniroute_binary": "present" if OMNIROUTE_BIN.exists() else "missing",
        "rust_omniroute_dashboard": str(omniroute_dashboard.get("status", "unknown")),
        "rust_omniroute_selected_provider": str(omniroute_dashboard.get("selected_provider", "")),
        "rust_omniroute_provider_cards": str(omniroute_dashboard.get("provider_cards", "")),
        "rust_omniroute_order_source": str(omniroute_dashboard.get("order_source", "")),
        "rust_omniroute_evm_report": "present" if OMNIROUTE_EVM_REPORT.exists() else "missing",
        "rust_omniroute_provider_health": "present" if OMNIROUTE_PROVIDER_HEALTH.exists() else "missing",
        "rust_omniroute_provider_healthy_count": str(omniroute_dashboard.get("provider_healthy_count", "")),
        "rust_omniroute_provider_unhealthy_count": str(omniroute_dashboard.get("provider_unhealthy_count", "")),
        "rust_omniroute_provider_cache_status": str(omniroute_dashboard.get("provider_health_cache_status", "")),
        "rust_omniroute_provider_cache_age_sec": str(omniroute_dashboard.get("provider_health_age_sec", "")),
        "rust_omniroute_provider_cache_ttl_sec": str(omniroute_dashboard.get("provider_health_ttl_sec", "")),
        "rust_omniroute_order_status": str(omniroute_dashboard.get("order_status", "")),
    }
    present = (
        (1 if deps["module_quantum_channel_router"] == "importable" else 0)
        + (1 if len(cache_files) >= 1 else 0)
        + (1 if deps["env_PGG_ARCHON_ROUTER_VERSION"] == "present" else 0)
        + (1 if deps["router_health_log"] == "present" else 0)
        + (1 if deps["rust_omniroute_crate"] == "present" else 0)
        + (1 if deps["rust_omniroute_binary"] == "present" else 0)
        + (1 if deps["rust_omniroute_dashboard"] == "present" else 0)
        + (1 if deps["rust_omniroute_order_source"] in {"python_evm_engine", "python_evm_engine+live_provider_health"} else 0)
        + (1 if deps["rust_omniroute_evm_report"] == "present" else 0)
        + (1 if deps["rust_omniroute_provider_health"] == "present" else 0)
    )
    if present >= 9:
        status = "ACTIVE"
    elif present >= 4:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return QuantumChannelRouterProbe(
        name="quantum_channel_router",
        status=status,
        probes=deps,
        notes=f"Quantum channel router + Rust OmniRoute dashboard bridge; {present}/10 surface gates resolved",
    )


def run_quantum_channel_router() -> dict[str, Any]:
    p = probe_quantum_channel_router()
    return {
        "schema": "PGGArchonQuantumChannelRouter/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "dashboard": _run_omniroute_dashboard(),
        "boundary": "status + dashboard data surface; ACTIVE does not prove upstream provider participation or full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_quantum_channel_router(), ensure_ascii=False, indent=2))
