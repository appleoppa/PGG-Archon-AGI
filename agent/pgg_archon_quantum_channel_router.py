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
import re
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
OMNIROUTE_TASK_EXECUTION_EVENTS = HOME / ".hermes" / "data" / "omniroute_task_execution_events.jsonl"
OMNIROUTE_MULTI_TASK_EVENTS = HOME / ".hermes" / "data" / "omniroute_multi_task_events.jsonl"
OMNIROUTE_MIRROR_EVENTS = HOME / ".hermes" / "data" / "omniroute_core_mirror_events.jsonl"
OMNIROUTE_PROVIDER_COOLDOWN = HOME / ".hermes" / "data" / "omniroute_provider_cooldown.json"
OMNIROUTE_ENFORCE_CONFIG = HOME / ".hermes" / "data" / "omniroute_route_enforce_canary.json"
OMNIROUTE_ENFORCE_EVENTS = HOME / ".hermes" / "data" / "omniroute_route_enforce_events.jsonl"
OMNIROUTE_SUBSTITUTION_EVENTS = HOME / ".hermes" / "data" / "omniroute_provider_substitution_events.jsonl"
OMNIROUTE_EVIDENCE_DIR = HOME / ".hermes" / "workspace" / "github_absorption" / "9router" / "analysis" / "evidence"
OMNIROUTE_ROUTE_POLICY_VERSION = "v2.6-fresh-calibrated-window-20260606"
OMNIROUTE_THIRD_PARTY_JUDGE_ALIASES = {"mimo", "mimo_v25_pro_auditor", "custom:mimo_v25_pro_auditor"}
OMNIROUTE_HARD_DENIED_ENFORCE_INTENTS = {"chinese_legal", "audit_judge", "agi_architecture_coding"}


def _is_third_party_judge_provider(name: str | None) -> bool:
    raw = str(name or "").strip()
    key = raw.split(":", 1)[1] if raw.startswith("custom:") else raw
    return raw in OMNIROUTE_THIRD_PARTY_JUDGE_ALIASES or key in OMNIROUTE_THIRD_PARTY_JUDGE_ALIASES


def _ordinary_callable_provider_names(providers: list[Any]) -> list[str]:
    return [str(p.name) for p in providers if not _is_third_party_judge_provider(getattr(p, "name", ""))]


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


def _append_route_enforce_event(event: dict[str, Any]) -> None:
    try:
        OMNIROUTE_ENFORCE_EVENTS.parent.mkdir(parents=True, exist_ok=True)
        with OMNIROUTE_ENFORCE_EVENTS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _default_route_enforce_config() -> dict[str, Any]:
    return {
        "schema": "PGGArchonOmniRouteEnforceCanaryConfig/v1",
        "enabled": False,
        "mode": "observe_only",
        "allowed_intents": ["bounded_exact_or_math", "general"],
        "denied_intents": sorted(OMNIROUTE_HARD_DENIED_ENFORCE_INTENTS),
        "require_route_class_match_actual": True,
        "require_policy_version": OMNIROUTE_ROUTE_POLICY_VERSION,
        "rollback": "Set enabled=false or delete this file. Default is fail-open observe_only.",
        "boundary": "Guarded canary scaffold only. Default-off; legal/audit/AGI denied.",
    }


def _sanitize_route_enforce_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Preserve hard safety invariants even if config/API tries to weaken them."""
    cfg = dict(cfg or {})
    if cfg.get("mode") not in {"observe_only", "canary"}:
        cfg["mode"] = "observe_only"
    allowed = [str(x) for x in (cfg.get("allowed_intents") or []) if str(x) not in OMNIROUTE_HARD_DENIED_ENFORCE_INTENTS]
    cfg["allowed_intents"] = sorted(set(allowed))
    denied = set(str(x) for x in (cfg.get("denied_intents") or [])) | OMNIROUTE_HARD_DENIED_ENFORCE_INTENTS
    cfg["denied_intents"] = sorted(denied)
    cfg["hard_denied_intents"] = sorted(OMNIROUTE_HARD_DENIED_ENFORCE_INTENTS)
    return cfg


def read_route_enforce_canary_config() -> dict[str, Any]:
    cfg = _default_route_enforce_config()
    data = _read_json(OMNIROUTE_ENFORCE_CONFIG)
    if isinstance(data, dict):
        cfg.update(data)
    return _sanitize_route_enforce_config(cfg)


def write_route_enforce_canary_config(update: dict[str, Any]) -> dict[str, Any]:
    cfg = read_route_enforce_canary_config()
    if isinstance(update, dict):
        for key in ["enabled", "mode", "allowed_intents", "denied_intents", "require_route_class_match_actual", "require_policy_version"]:
            if key in update:
                cfg[key] = update[key]
    cfg = _sanitize_route_enforce_config(cfg)
    cfg["updated_at"] = _now_iso()
    OMNIROUTE_ENFORCE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    tmp = OMNIROUTE_ENFORCE_CONFIG.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(OMNIROUTE_ENFORCE_CONFIG)
    return cfg


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


def _classify_route_intent(task_type: str = "", prompt: str = "") -> dict[str, Any]:
    text = f"{task_type}\n{prompt}".lower()
    if any(k in text for k in ["法律", "法条", "案例", "合同", "诉讼", "办案", "刑事", "民事", "公司法", "破产", "执行", "legal", "law", "litigation", "contract"]):
        return {"intent": "chinese_legal", "preferred": ["deepseek", "gpt55", "claude", "mimo"], "reason": "Chinese legal work prefers DeepSeek, with GPT/Claude as review; MiMo is not primary."}
    if any(k in text for k in ["审计", "judge", "benchmark", "评测", "验证", "verdict", "pass", "fail", "打分", "复核", "audit", "evaluator", "evaluation"]):
        return {"intent": "audit_judge", "preferred": ["mimo", "claude", "gpt55", "deepseek"], "reason": "Audit/judge tasks may prefer MiMo as judge."}
    if any(k in text for k in ["math", "gsm8k", "计算", "算", "answer exactly", "reply exactly", "只回答"]):
        return {"intent": "bounded_exact_or_math", "preferred": ["gpt55", "deepseek", "mimo", "claude"], "reason": "Bounded exact/math tasks keep GPT/DeepSeek ahead of judge-only MiMo."}
    if any(k in text for k in ["agi", "pgg", "archon", "进化", "架构", "route", "router", "omniroute", "apex", "系统", "代码", "编译", "rust", "优化"]):
        return {"intent": "agi_architecture_coding", "preferred": ["gpt55", "claude", "deepseek", "mimo"], "reason": "AGI/architecture/coding tasks prefer GPT/Claude per user policy; MiMo is not primary."}
    return {"intent": "general", "preferred": ["gpt55", "deepseek", "claude", "mimo"], "reason": "General tasks prefer current strong GPT/DeepSeek before MiMo judge."}


def _provider_available_aliases(available: list[str]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for p in available:
        low = p.lower()
        aliases[p] = p
        if "gpt" in low:
            aliases.setdefault("gpt55", p)
        if "claude" in low or "opus" in low:
            aliases.setdefault("claude", p)
        if "deepseek" in low:
            aliases.setdefault("deepseek", p)
        if "mimo" in low:
            aliases.setdefault("mimo", p)
    return aliases


def decide_omniroute_provider(task_type: str = "general", requested_provider: str = "", prompt_preview: str = "") -> dict[str, Any]:
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
    route_policy = _classify_route_intent(task_type, prompt_preview)
    aliases = _provider_available_aliases(available)
    selected_source = "policy_auto"
    selected = ""
    manual_applied = False
    if requested_provider:
        selected = requested_provider
        selected_source = "request_override"
    elif mode == "manual" and manual_provider:
        selected = manual_provider
        selected_source = "manual_control"
        manual_applied = True
    else:
        for preferred in route_policy.get("preferred", []):
            if preferred in aliases:
                selected = aliases[preferred]
                selected_source = f"policy_auto:{route_policy.get('intent')}:{preferred}"
                break
        # Keep dashboard selected only as a fallback, not as the primary policy.
        if not selected and dashboard_selected:
            selected = dashboard_selected
            selected_source = "dashboard_auto_fallback"
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
    payload["route_policy"] = route_policy
    payload["route_policy_version"] = OMNIROUTE_ROUTE_POLICY_VERSION
    payload["prompt_preview_sha256"] = __import__("hashlib").sha256((prompt_preview or "").encode("utf-8")).hexdigest() if prompt_preview else ""
    payload["policy_boundary"] = "Policy suggestion only; no provider mutation unless a later guarded enforce mode is explicitly enabled."
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


def recent_omniroute_task_execution_events(limit: int = 20) -> list[dict[str, Any]]:
    return _read_jsonl_tail(OMNIROUTE_TASK_EXECUTION_EVENTS, limit)


def recent_omniroute_multi_task_events(limit: int = 20) -> list[dict[str, Any]]:
    return _read_jsonl_tail(OMNIROUTE_MULTI_TASK_EVENTS, limit)


def recent_omniroute_mirror_events(limit: int = 20) -> list[dict[str, Any]]:
    return _read_jsonl_tail(OMNIROUTE_MIRROR_EVENTS, limit)


def omniroute_route_suggest_metrics(limit: int = 200, policy_version: str | None = None) -> dict[str, Any]:
    events = recent_omniroute_mirror_events(limit)
    payloads = [e.get("payload", {}) for e in events if isinstance(e, dict)]
    if policy_version:
        payloads = [p for p in payloads if p.get("route_policy_version") == policy_version]
    suggested = [p for p in payloads if p.get("suggested_provider") or p.get("suggestion_error")]
    exact_matches = [p for p in suggested if p.get("suggestion_matches_actual")]
    class_matches = [p for p in suggested if p.get("suggestion_route_class_matches_actual")]
    errors = [p for p in suggested if p.get("suggestion_error")]
    latencies = [float(p.get("suggestion_latency_ms") or 0.0) for p in suggested if p.get("suggestion_latency_ms") is not None]
    def counts(key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for p in suggested:
            val = str(p.get(key) or "") or "unknown"
            out[val] = out.get(val, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))
    def route_class_counts(which: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for p in suggested:
            if which == "suggested":
                ident = p.get("suggested_provider_identity") if isinstance(p.get("suggested_provider_identity"), dict) else _normalize_provider_identity(p.get("suggested_provider"), "")
                val = str(p.get("suggested_route_class") or ident.get("route_class") or "unknown")
            else:
                ident = p.get("actual_provider_identity") if isinstance(p.get("actual_provider_identity"), dict) else _normalize_provider_identity(p.get("actual_provider") or p.get("provider"), p.get("model"))
                val = str(p.get("actual_route_class") or ident.get("route_class") or "unknown")
            out[val] = out.get(val, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))
    mismatch_pairs: dict[str, int] = {}
    for p in suggested:
        suggested_identity = p.get("suggested_provider_identity") if isinstance(p.get("suggested_provider_identity"), dict) else _normalize_provider_identity(p.get("suggested_provider"), "")
        actual_identity = p.get("actual_provider_identity") if isinstance(p.get("actual_provider_identity"), dict) else _normalize_provider_identity(p.get("actual_provider") or p.get("provider"), p.get("model"))
        sp = str(p.get("suggested_route_class") or suggested_identity.get("route_class") or p.get("suggested_provider") or "unknown")
        ap = str(p.get("actual_route_class") or actual_identity.get("route_class") or p.get("actual_provider") or "unknown")
        pair = f"{sp}->{ap}"
        if sp != ap:
            mismatch_pairs[pair] = mismatch_pairs.get(pair, 0) + 1
    n = len(suggested)
    return {
        "schema": "PGGArchonOmniRouteRouteSuggestMetrics/v1",
        "limit": limit,
        "policy_version_filter": policy_version or "",
        "route_policy_version_current": OMNIROUTE_ROUTE_POLICY_VERSION,
        "total_mirror_events": len(payloads),
        "suggested_events": n,
        "exact_match_count": len(exact_matches),
        "class_match_count": len(class_matches),
        "suggestion_error_count": len(errors),
        "exact_match_rate": round(len(exact_matches) / n, 4) if n else 0.0,
        "class_match_rate": round(len(class_matches) / n, 4) if n else 0.0,
        "suggestion_error_rate": round(len(errors) / n, 4) if n else 0.0,
        "avg_suggestion_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        "max_suggestion_latency_ms": round(max(latencies), 3) if latencies else 0.0,
        "suggested_provider_counts": counts("suggested_provider"),
        "actual_provider_counts": counts("actual_provider"),
        "suggested_route_class_counts": route_class_counts("suggested"),
        "actual_route_class_counts": route_class_counts("actual"),
        "mismatch_route_class_pairs": dict(sorted(mismatch_pairs.items(), key=lambda kv: (-kv[1], kv[0]))),
        "route_enforce_readiness": "HOLD" if n == 0 or len(class_matches) < n or errors else "CANDIDATE_FOR_GUARDED_REVIEW",
        "boundary": "Metrics are observational route-suggest evidence only; not route-enforce approval.",
    }


def _redact_mirror_preview(text: str, limit: int) -> str:
    """Short, bounded preview for mirror ledger; hashes remain the primary evidence."""
    text = str(text or "")
    text = re.sub(r"sk-[A-Za-z0-9_\-]{12,}", "sk-REDACTED", text)
    text = re.sub(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+", r"\1=REDACTED", text)
    text = re.sub(r"Bearer\s+[A-Za-z0-9._\-]{12,}", "Bearer REDACTED", text)
    return text[: max(0, int(limit))]


def _normalize_provider_identity(provider: str | None, model: str | None) -> dict[str, str]:
    raw = str(provider or "").strip()
    model_s = str(model or "").strip()
    key = raw
    family = raw.split(":", 1)[0] if raw else ""
    if raw.startswith("custom:"):
        key = raw.split(":", 1)[1]
        family = "custom"
    comparable = key or family or model_s
    low = (key + " " + model_s).lower()
    if "gpt" in low:
        route_class = "gpt"
    elif "claude" in low or "opus" in low or "sonnet" in low:
        route_class = "claude"
    elif "mimo" in low:
        route_class = "mimo"
    elif "deepseek" in low:
        route_class = "deepseek"
    else:
        route_class = comparable
    return {
        "raw": raw,
        "family": family,
        "key": key,
        "model": model_s,
        "route_class": route_class,
        "comparable": comparable,
    }


def evaluate_route_enforce_canary(route_suggestion: dict[str, Any], actual_provider: str = "", model: str = "") -> dict[str, Any]:
    cfg = read_route_enforce_canary_config()
    route_suggestion = route_suggestion if isinstance(route_suggestion, dict) else {}
    route_policy_raw = route_suggestion.get("route_policy")
    route_policy = route_policy_raw if isinstance(route_policy_raw, dict) else {}
    intent = str(route_policy.get("intent") or "")
    suggested_provider = str(route_suggestion.get("selected_provider") or "")
    suggested_class = _normalize_provider_identity(suggested_provider, "").get("route_class", "")
    actual_class = _normalize_provider_identity(actual_provider, model).get("route_class", "")
    reasons: list[str] = []
    enabled = bool(cfg.get("enabled"))
    mode = str(cfg.get("mode") or "observe_only")
    if not enabled:
        reasons.append("config_disabled_default_off")
    if mode not in {"observe_only", "canary"}:
        reasons.append(f"unsupported_mode:{mode}")
    if intent in set(cfg.get("denied_intents") or []):
        reasons.append(f"intent_denied:{intent}")
    if intent not in set(cfg.get("allowed_intents") or []):
        reasons.append(f"intent_not_allowed:{intent or 'unknown'}")
    req_ver = str(cfg.get("require_policy_version") or "")
    if req_ver and str(route_suggestion.get("route_policy_version") or "") != req_ver:
        reasons.append("policy_version_mismatch")
    if cfg.get("require_route_class_match_actual", True) and suggested_class != actual_class:
        reasons.append(f"route_class_mismatch:{suggested_class}->{actual_class}")
    allowed = enabled and mode == "canary" and not reasons
    decision = {
        "schema": "PGGArchonOmniRouteEnforceDecision/v1",
        "decided_at": _now_iso(),
        "enabled": enabled,
        "mode": mode,
        "allowed": allowed,
        "would_enforce": allowed,
        "fail_open_passthrough": not allowed,
        "suggested_provider": suggested_provider,
        "actual_provider": actual_provider or "",
        "suggested_route_class": suggested_class,
        "actual_route_class": actual_class,
        "intent": intent,
        "reasons": reasons,
        "boundary": "Default-off guarded canary. This function only evaluates and records; caller must separately implement any provider substitution.",
    }
    _append_route_enforce_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "route_enforce_canary_decision", "payload": decision})
    return decision


def recent_route_enforce_events(limit: int = 20) -> list[dict[str, Any]]:
    return _read_jsonl_tail(OMNIROUTE_ENFORCE_EVENTS, limit)


def run_route_enforce_canary_selftest() -> dict[str, Any]:
    previous = read_route_enforce_canary_config()
    cases = [
        ("exact", "Reply exactly: PGG_V28_EXACT", "custom:gpt55_5yuantoken", "gpt-5.5", True),
        ("general", "general hello", "custom:gpt55_5yuantoken", "gpt-5.5", True),
        ("legal", "中文法律合同诉讼法条", "custom:gpt55_5yuantoken", "gpt-5.5", False),
        ("audit", "audit judge benchmark verdict", "custom:gpt55_5yuantoken", "gpt-5.5", False),
        ("agi", "PGG Archon AGI Rust router evolution", "custom:gpt55_5yuantoken", "gpt-5.5", False),
    ]
    started_at = _now_iso()
    results: list[dict[str, Any]] = []
    passed = False
    try:
        write_route_enforce_canary_config({"enabled": True, "mode": "canary"})
        for name, prompt, actual_provider, model, expected_allowed in cases:
            suggestion = decide_omniroute_provider(task_type=name, prompt_preview=prompt)
            decision = evaluate_route_enforce_canary(suggestion, actual_provider, model)
            got = bool(decision.get("allowed"))
            results.append({
                "case": name,
                "expected_allowed": expected_allowed,
                "actual_allowed": got,
                "passed": got == expected_allowed,
                "intent": decision.get("intent"),
                "suggested_provider": decision.get("suggested_provider"),
                "actual_provider": decision.get("actual_provider"),
                "suggested_route_class": decision.get("suggested_route_class"),
                "actual_route_class": decision.get("actual_route_class"),
                "reasons": decision.get("reasons", []),
            })
        passed = all(r["passed"] for r in results)
        return {
            "schema": "PGGArchonOmniRouteEnforceCanarySelfTest/v1",
            "started_at": started_at,
            "finished_at": _now_iso(),
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "results": results,
            "rollback": "pending_finally",
            "boundary": "Selftest toggles canary evaluation only; it does not substitute providers.",
        }
    finally:
        write_route_enforce_canary_config({
            "enabled": bool(previous.get("enabled", False)),
            "mode": str(previous.get("mode") or "observe_only"),
            "allowed_intents": previous.get("allowed_intents") or ["bounded_exact_or_math", "general"],
            "denied_intents": previous.get("denied_intents") or ["chinese_legal", "audit_judge", "agi_architecture_coding"],
            "require_route_class_match_actual": bool(previous.get("require_route_class_match_actual", True)),
            "require_policy_version": previous.get("require_policy_version") or OMNIROUTE_ROUTE_POLICY_VERSION,
        })
        _append_route_enforce_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "route_enforce_canary_selftest_rollback", "payload": {"restored_enabled": bool(previous.get("enabled", False)), "restored_mode": str(previous.get("mode") or "observe_only")}})


def run_route_enforce_canary_window_test(sample_count: int = 50) -> dict[str, Any]:
    sample_count = max(10, min(int(sample_count or 50), 200))
    previous = read_route_enforce_canary_config()
    started_at = _now_iso()
    results: list[dict[str, Any]] = []
    denied_leakage_cases = [
        ("legal", "中文法律合同诉讼法条"),
        ("audit", "audit judge benchmark verdict"),
        ("agi", "PGG Archon AGI Rust router evolution"),
    ]
    try:
        write_route_enforce_canary_config({"enabled": True, "mode": "canary"})
        for i in range(sample_count):
            case = "exact" if i % 2 == 0 else "general"
            prompt = f"Reply exactly: PGG_V29_{case.upper()}_{i:03d}" if case == "exact" else f"general routing smoke {i:03d}"
            suggestion = decide_omniroute_provider(task_type=case, prompt_preview=prompt)
            decision = evaluate_route_enforce_canary(suggestion, "custom:gpt55_5yuantoken", "gpt-5.5")
            match = decision.get("suggested_route_class") == decision.get("actual_route_class")
            results.append({
                "case": case,
                "index": i,
                "allowed": bool(decision.get("allowed")),
                "route_class_match": bool(match),
                "suggested_route_class": decision.get("suggested_route_class"),
                "actual_route_class": decision.get("actual_route_class"),
                "reasons": decision.get("reasons", []),
            })
        leakage: list[dict[str, Any]] = []
        for case, prompt in denied_leakage_cases:
            suggestion = decide_omniroute_provider(task_type=case, prompt_preview=prompt)
            decision = evaluate_route_enforce_canary(suggestion, "custom:gpt55_5yuantoken", "gpt-5.5")
            leakage.append({"case": case, "allowed": bool(decision.get("allowed")), "reasons": decision.get("reasons", []), "suggested_route_class": decision.get("suggested_route_class"), "actual_route_class": decision.get("actual_route_class")})
        allowed_count = sum(1 for r in results if r["allowed"])
        match_count = sum(1 for r in results if r["route_class_match"])
        error_count = sum(1 for r in results if r.get("reasons"))
        leakage_count = sum(1 for r in leakage if r["allowed"])
        class_match_rate = round(match_count / len(results), 4) if results else 0.0
        suggestion_error_rate = round(error_count / len(results), 4) if results else 1.0
        passed = len(results) == sample_count and allowed_count == sample_count and class_match_rate >= 0.95 and suggestion_error_rate <= 0.01 and leakage_count == 0
        return {
            "schema": "PGGArchonOmniRouteEnforceCanaryWindowTest/v1",
            "started_at": started_at,
            "finished_at": _now_iso(),
            "sample_count": sample_count,
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "allowed_count": allowed_count,
            "class_match_rate": class_match_rate,
            "suggestion_error_rate": suggestion_error_rate,
            "leakage_count": leakage_count,
            "leakage": leakage,
            "results_head": results[:5],
            "results_tail": results[-5:],
            "next_gate": "provider_substitution_canary_candidate" if passed else "hold",
            "boundary": "Window test evaluates canary decisions only; no provider substitution.",
        }
    finally:
        write_route_enforce_canary_config({
            "enabled": bool(previous.get("enabled", False)),
            "mode": str(previous.get("mode") or "observe_only"),
            "allowed_intents": previous.get("allowed_intents") or ["bounded_exact_or_math", "general"],
            "denied_intents": previous.get("denied_intents") or ["chinese_legal", "audit_judge", "agi_architecture_coding"],
            "require_route_class_match_actual": bool(previous.get("require_route_class_match_actual", True)),
            "require_policy_version": previous.get("require_policy_version") or OMNIROUTE_ROUTE_POLICY_VERSION,
        })
        _append_route_enforce_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "route_enforce_canary_window_test_rollback", "payload": {"restored_enabled": bool(previous.get("enabled", False)), "restored_mode": str(previous.get("mode") or "observe_only")}})


def _append_substitution_event(event: dict[str, Any]) -> None:
    try:
        OMNIROUTE_SUBSTITUTION_EVENTS.parent.mkdir(parents=True, exist_ok=True)
        with OMNIROUTE_SUBSTITUTION_EVENTS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def recent_provider_substitution_events(limit: int = 20) -> list[dict[str, Any]]:
    return _read_jsonl_tail(OMNIROUTE_SUBSTITUTION_EVENTS, limit)


def plan_provider_substitution_canary(task: str, task_type: str = "exact", actual_provider: str = "custom:gpt55_5yuantoken", model: str = "gpt-5.5") -> dict[str, Any]:
    suggestion = decide_omniroute_provider(task_type=task_type, prompt_preview=task[:1000])
    previous = read_route_enforce_canary_config()
    try:
        write_route_enforce_canary_config({"enabled": True, "mode": "canary"})
        enforce = evaluate_route_enforce_canary(suggestion, actual_provider, model)
    finally:
        write_route_enforce_canary_config({
            "enabled": bool(previous.get("enabled", False)),
            "mode": str(previous.get("mode") or "observe_only"),
            "allowed_intents": previous.get("allowed_intents") or ["bounded_exact_or_math", "general"],
            "denied_intents": previous.get("denied_intents") or ["chinese_legal", "audit_judge", "agi_architecture_coding"],
            "require_route_class_match_actual": bool(previous.get("require_route_class_match_actual", True)),
            "require_policy_version": previous.get("require_policy_version") or OMNIROUTE_ROUTE_POLICY_VERSION,
        })
    allowed = bool(enforce.get("allowed"))
    plan = {
        "schema": "PGGArchonOmniRouteProviderSubstitutionPlan/v1",
        "planned_at": _now_iso(),
        "task_type": task_type,
        "task_preview": task[:160],
        "suggestion": suggestion,
        "enforce_decision": enforce,
        "substitution_provider": suggestion.get("selected_provider") if allowed else "",
        "allowed": allowed,
        "boundary": "Plan only; execution requires explicit canary execute and writes provider participation evidence.",
    }
    _append_substitution_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "provider_substitution_plan", "payload": plan})
    return plan


def execute_provider_substitution_canary(task: str, task_type: str = "exact", timeout: float = 60.0, fallback_provider: str = "deepseek") -> dict[str, Any]:
    import hashlib
    started = datetime.now(timezone.utc)
    canary_id = hashlib.sha256(f"{started.isoformat()}::{task}".encode("utf-8")).hexdigest()[:16]
    plan = plan_provider_substitution_canary(task, task_type=task_type)
    if not plan.get("allowed"):
        result = {
            "schema": "PGGArchonOmniRouteProviderSubstitutionCanary/v1",
            "canary_id": canary_id,
            "started_at": started.isoformat(),
            "success": False,
            "executed": False,
            "plan": plan,
            "error": "substitution plan not allowed",
            "boundary": "No provider call made because guard denied substitution.",
        }
        _append_substitution_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "provider_substitution_canary", "payload": result})
        return result
    provider = str(plan.get("substitution_provider") or "")
    execution = execute_omniroute_task(task, task_type=f"substitution_canary:{task_type}", requested_provider=provider, timeout=timeout)
    fallback_execution: dict[str, Any] = {}
    if provider == "gpt55" and not execution.get("success") and fallback_provider:
        fallback_execution = execute_omniroute_task(task, task_type=f"substitution_canary_fallback:{task_type}", requested_provider=fallback_provider, timeout=timeout)
        fallback_execution["cross_class_fallback"] = _normalize_provider_identity(provider, "").get("route_class") != _normalize_provider_identity(fallback_provider, "").get("route_class")
        fallback_execution["fallback_from_provider"] = provider
        fallback_execution["boundary"] = "Fallback provider participation proof only; cross-class fallback must not be counted as same-class GPT substitution success."
    same_class_success = bool(execution.get("success"))
    fallback_participated = bool(fallback_execution.get("participated"))
    effective_success = same_class_success or fallback_participated
    result = {
        "schema": "PGGArchonOmniRouteProviderSubstitutionCanary/v1",
        "canary_id": canary_id,
        "started_at": started.isoformat(),
        "finished_at": _now_iso(),
        "success": effective_success,
        "same_class_substitution_success": same_class_success,
        "fallback_participation_success": fallback_participated,
        "executed": True,
        "plan": plan,
        "execution": execution,
        "fallback_execution": fallback_execution,
        "boundary": "Single bounded substitution canary. Fallback participation is evidence of callable lane repair, not global route enforcement.",
    }
    _append_substitution_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "provider_substitution_canary", "payload": result})
    return result


def run_provider_substitution_fallback_window(sample_count: int = 20, fallback_provider: str = "deepseek", timeout: float = 60.0) -> dict[str, Any]:
    sample_count = max(2, min(int(sample_count or 20), 50))
    started_at = _now_iso()
    results: list[dict[str, Any]] = []
    for i in range(sample_count):
        case = "exact" if i % 2 == 0 else "general"
        prompt = f"Reply exactly: PGG_V32_{case.upper()}_{i:03d}" if case == "exact" else f"Reply exactly: PGG_V32_GENERAL_{i:03d}"
        item = execute_provider_substitution_canary(prompt, task_type=case, timeout=timeout, fallback_provider=fallback_provider)
        ex = item.get("execution", {}) if isinstance(item, dict) else {}
        fb = item.get("fallback_execution", {}) if isinstance(item, dict) else {}
        results.append({
            "index": i,
            "case": case,
            "success": bool(item.get("success")),
            "same_class_success": bool(item.get("same_class_substitution_success")),
            "fallback_success": bool(item.get("fallback_participation_success")),
            "primary_provider": ex.get("provider"),
            "primary_http": ex.get("http_status"),
            "primary_participated": ex.get("participated"),
            "fallback_provider": fb.get("provider"),
            "fallback_http": fb.get("http_status"),
            "fallback_participated": fb.get("participated"),
            "cross_class_fallback": fb.get("cross_class_fallback"),
            "answer_preview": fb.get("answer_preview") or ex.get("answer_preview"),
        })
    leakage = []
    for case, prompt in [("legal", "中文法律合同诉讼法条"), ("audit", "audit judge benchmark verdict"), ("agi", "PGG Archon AGI Rust router evolution")]:
        plan = plan_provider_substitution_canary(prompt, task_type=case)
        leakage.append({"case": case, "allowed": bool(plan.get("allowed")), "provider": plan.get("substitution_provider"), "reasons": (plan.get("enforce_decision") or {}).get("reasons", [])})
    n = len(results)
    primary_success = sum(1 for r in results if r["same_class_success"])
    fallback_success = sum(1 for r in results if r["fallback_success"])
    total_success = sum(1 for r in results if r["success"])
    leakage_count = sum(1 for r in leakage if r["allowed"])
    passed = n == sample_count and total_success == n and fallback_success == n and primary_success == 0 and leakage_count == 0
    summary = {
        "schema": "PGGArchonOmniRouteProviderSubstitutionFallbackWindow/v1",
        "started_at": started_at,
        "finished_at": _now_iso(),
        "sample_count": sample_count,
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "primary_success_count": primary_success,
        "fallback_success_count": fallback_success,
        "total_success_count": total_success,
        "primary_http_502_count": sum(1 for r in results if r["primary_http"] == 502),
        "cross_class_fallback_count": sum(1 for r in results if r["cross_class_fallback"]),
        "leakage_count": leakage_count,
        "leakage": leakage,
        "results_head": results[:5],
        "results_tail": results[-5:],
        "boundary": "Fallback window proves callable fallback participation only; it is not GPT same-class substitution or global route-enforce.",
    }
    _append_substitution_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "provider_substitution_fallback_window", "payload": summary})
    return summary


def record_omniroute_core_mirror(
    *,
    user_message: Any,
    result: dict[str, Any] | None,
    task_id: str | None = None,
    session_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    platform: str | None = None,
    route_suggestion: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Mirror a Hermes core conversation result into OmniRoute evidence ledger.

    Fail-open caller contract: this function must never affect the original
    conversation answer path; it records hashes/previews only and makes no
    provider calls.
    """
    import hashlib

    user_text = str(user_message or "")
    final_response = ""
    completed = None
    api_calls = None
    if isinstance(result, dict):
        final_response = str(result.get("final_response") or "")
        completed = result.get("completed")
        api_calls = result.get("api_calls")
    route_suggestion = route_suggestion if isinstance(route_suggestion, dict) else {}
    suggested_provider = str(route_suggestion.get("selected_provider") or "")
    actual_provider = provider or ""
    actual_identity = _normalize_provider_identity(actual_provider, model)
    suggested_identity = _normalize_provider_identity(suggested_provider, "")
    enforce_decision = evaluate_route_enforce_canary(route_suggestion, actual_provider, model or "") if route_suggestion else {}
    preview_limit = int(os.getenv("PGG_OMNIROUTE_MIRROR_PREVIEW_CHARS", "120") or "120")
    payload = {
        "schema": "PGGArchonOmniRouteCoreMirror/v1",
        "mirrored_at": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id or "",
        "session_id": session_id or "",
        "provider": actual_provider,
        "model": model or "",
        "platform": platform or "",
        "route_suggestion": route_suggestion,
        "route_policy_version": route_suggestion.get("route_policy_version", ""),
        "suggestion_latency_ms": route_suggestion.get("suggestion_latency_ms"),
        "suggestion_error": route_suggestion.get("suggestion_error", ""),
        "suggested_provider": suggested_provider,
        "actual_provider": actual_provider,
        "suggested_provider_identity": suggested_identity,
        "actual_provider_identity": actual_identity,
        "suggested_route_class": suggested_identity.get("route_class", ""),
        "actual_route_class": actual_identity.get("route_class", ""),
        "suggestion_matches_actual": bool(suggested_provider and actual_provider and suggested_provider == actual_provider),
        "suggestion_route_class_matches_actual": bool(suggested_identity.get("route_class") and actual_identity.get("route_class") and suggested_identity.get("route_class") == actual_identity.get("route_class")),
        "route_enforce_canary": enforce_decision,
        "route_enforce_would_enforce": bool(enforce_decision.get("would_enforce")) if isinstance(enforce_decision, dict) else False,
        "user_sha256": hashlib.sha256(user_text.encode("utf-8")).hexdigest() if user_text else "",
        "user_preview": _redact_mirror_preview(user_text, preview_limit),
        "final_response_sha256": hashlib.sha256(final_response.encode("utf-8")).hexdigest() if final_response else "",
        "final_response_preview": _redact_mirror_preview(final_response, preview_limit),
        "preview_limit_chars": preview_limit,
        "preview_redaction": "enabled: api keys, bearer tokens, token/secret/password assignments; hash remains primary evidence",
        "completed": completed,
        "api_calls": api_calls,
        "result_keys": sorted(result.keys()) if isinstance(result, dict) else [],
        "boundary": "Mirror-only evidence: no route enforcement, no provider substitution, no extra model call, fail-open if recording fails.",
    }
    try:
        OMNIROUTE_MIRROR_EVENTS.parent.mkdir(parents=True, exist_ok=True)
        with OMNIROUTE_MIRROR_EVENTS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": datetime.now(timezone.utc).timestamp(), "event": "core_conversation_mirror", "payload": payload}, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return payload


def _append_multi_task_event(event: dict[str, Any]) -> None:
    try:
        OMNIROUTE_MULTI_TASK_EVENTS.parent.mkdir(parents=True, exist_ok=True)
        with OMNIROUTE_MULTI_TASK_EVENTS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _read_provider_cooldown() -> dict[str, Any]:
    data = _read_json(OMNIROUTE_PROVIDER_COOLDOWN)
    return data if isinstance(data, dict) else {}


def _write_provider_cooldown(data: dict[str, Any]) -> None:
    try:
        OMNIROUTE_PROVIDER_COOLDOWN.parent.mkdir(parents=True, exist_ok=True)
        tmp = OMNIROUTE_PROVIDER_COOLDOWN.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(OMNIROUTE_PROVIDER_COOLDOWN)
    except Exception:
        pass


def _record_provider_failures_for_cooldown(
    calls: list[dict[str, Any]],
    *,
    cooldown_sec: float = 600.0,
    extend_on_cooldown_skip: bool = False,
) -> dict[str, Any]:
    cooldown = _read_provider_cooldown()
    now = datetime.now(timezone.utc).timestamp()
    changed = False
    for c in calls:
        provider = c.get("provider")
        if not provider:
            continue
        if c.get("cooldown_skipped") and not extend_on_cooldown_skip:
            continue
        if c.get("participated"):
            # Clear stale cooldown after a real successful call.
            if provider in cooldown:
                cooldown.pop(provider, None)
                changed = True
            continue
        cooldown[provider] = {
            "provider": provider,
            "cooldown_until": now + cooldown_sec,
            "cooldown_sec": cooldown_sec,
            "reason": c.get("error") or f"http_status={c.get('http_status')}",
            "last_http_status": c.get("http_status"),
            "updated_at": now,
        }
        changed = True
    if changed:
        _write_provider_cooldown(cooldown)
    return cooldown


def get_omniroute_provider_cooldown() -> dict[str, Any]:
    cooldown = _read_provider_cooldown()
    now = datetime.now(timezone.utc).timestamp()
    active = {}
    expired = []
    for provider, item in cooldown.items():
        until = float(item.get("cooldown_until") or 0.0)
        if until > now:
            item = dict(item)
            item["remaining_sec"] = round(until - now, 3)
            active[provider] = item
        else:
            expired.append(provider)
    if expired:
        for provider in expired:
            cooldown.pop(provider, None)
        _write_provider_cooldown(cooldown)
    return {"active": active, "expired": expired, "path": str(OMNIROUTE_PROVIDER_COOLDOWN)}


def clear_omniroute_provider_cooldown(provider: str | None = None) -> dict[str, Any]:
    cooldown = _read_provider_cooldown()
    if provider:
        cooldown.pop(provider.strip(), None)
        action = "clear_provider"
    else:
        cooldown = {}
        action = "clear_all"
    _write_provider_cooldown(cooldown)
    state = get_omniroute_provider_cooldown()
    state["action"] = action
    state["cleared_provider"] = provider or ""
    return state


def _write_task_evidence_package(result: dict[str, Any]) -> str:
    try:
        OMNIROUTE_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        task_id = str(result.get("task_id") or "unknown")
        path = OMNIROUTE_EVIDENCE_DIR / f"omniroute-task-evidence-{task_id}.json"
        package = {
            "schema": "PGGArchonOmniRouteTaskEvidencePackage/v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": result,
            "boundary": "Evidence package for one bounded OmniRoute task execution; not benchmark/legal correctness/full AGI proof.",
        }
        path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        latest = OMNIROUTE_EVIDENCE_DIR / "latest-omniroute-task-evidence.json"
        latest.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)
    except Exception:
        return ""


def _write_multi_evidence_package(result: dict[str, Any]) -> str:
    try:
        OMNIROUTE_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        task_id = str(result.get("task_id") or "unknown")
        path = OMNIROUTE_EVIDENCE_DIR / f"omniroute-evidence-{task_id}.json"
        package = {
            "schema": "PGGArchonOmniRouteEvidencePackage/v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": result,
            "boundary": "Evidence package for a bounded multi-provider task; not legal correctness/benchmark/full AGI proof.",
        }
        path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        latest = OMNIROUTE_EVIDENCE_DIR / "latest-omniroute-evidence.json"
        latest.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)
    except Exception:
        return ""


def _append_task_execution_event(event: dict[str, Any]) -> None:
    try:
        OMNIROUTE_TASK_EXECUTION_EVENTS.parent.mkdir(parents=True, exist_ok=True)
        with OMNIROUTE_TASK_EXECUTION_EVENTS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


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
    started = datetime.now(timezone.utc)
    if _is_third_party_judge_provider(selected):
        result = {
            "schema": "PGGArchonOmniRouteProviderParticipation/v1",
            "called_at": started.isoformat(),
            "decision": decision,
            "provider": selected,
            "participated": False,
            "http_status": 0,
            "visible_chars": 0,
            "elapsed_sec": 0.0,
            "error": "third-party judge provider is reserved for audit/judge paths and cannot be used for ordinary OmniRoute task execution",
            "boundary": "No provider participation; MiMo is reserved for third-party judge/audit paths.",
        }
        _append_provider_call_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "provider_participation", "payload": result})
        return result
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


def execute_omniroute_task(
    task: str,
    *,
    task_type: str = "user_task_probe",
    requested_provider: str = "",
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Execute a bounded task through OmniRoute and persist task-level proof.

    Evidence chain: task_id -> route decision -> provider API call -> answer hash.
    """
    import hashlib

    task = (task or "").strip()
    started = datetime.now(timezone.utc)
    task_id = hashlib.sha256(f"{started.isoformat()}::{task}".encode("utf-8")).hexdigest()[:16]
    if not task:
        result = {
            "schema": "PGGArchonOmniRouteTaskExecution/v1",
            "task_id": task_id,
            "started_at": started.isoformat(),
            "task_type": task_type,
            "task_preview": "",
            "success": False,
            "error": "empty task",
            "boundary": "No provider call was made because task is empty.",
        }
        evidence_path = _write_task_evidence_package(result)
        if evidence_path:
            result["evidence_package_path"] = evidence_path
            result["latest_package_path"] = str(OMNIROUTE_EVIDENCE_DIR / "latest-omniroute-task-evidence.json")
        _append_task_execution_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "task_execution", "payload": result})
        return result
    call = execute_omniroute_provider_call(
        prompt=task,
        task_type=task_type,
        requested_provider=requested_provider,
        timeout=timeout,
    )
    answer = str(call.get("parsed_preview") or "")
    # Use parsed preview here because call_provider does not expose full parsed_text in the participation record by design.
    answer_hash = hashlib.sha256(answer.encode("utf-8")).hexdigest() if answer else ""
    result = {
        "schema": "PGGArchonOmniRouteTaskExecution/v1",
        "task_id": task_id,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "task_type": task_type,
        "task_sha256": hashlib.sha256(task.encode("utf-8")).hexdigest(),
        "task_preview": task[:160],
        "requested_provider": requested_provider,
        "decision": call.get("decision", {}),
        "provider": call.get("provider", ""),
        "model": call.get("model", ""),
        "api_mode": call.get("api_mode", ""),
        "participated": bool(call.get("participated")),
        "http_status": call.get("http_status", 0),
        "visible_chars": call.get("visible_chars", 0),
        "elapsed_sec": call.get("elapsed_sec", 0.0),
        "answer_preview": answer,
        "answer_sha256": answer_hash,
        "success": bool(call.get("participated")) and bool(answer),
        "error": call.get("error", ""),
        "boundary": "Task-level provider participation proof for this bounded task only; not benchmark/legal correctness/full AGI evidence.",
    }
    evidence_path = _write_task_evidence_package(result)
    if evidence_path:
        result["evidence_package_path"] = evidence_path
        result["latest_package_path"] = str(OMNIROUTE_EVIDENCE_DIR / "latest-omniroute-task-evidence.json")
    _append_task_execution_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "task_execution", "payload": result})
    return result


def execute_omniroute_multi_provider_task(
    task: str,
    *,
    task_type: str = "multi_provider_task_probe",
    providers: list[str] | None = None,
    timeout: float = 60.0,
    cooldown_sec: float | None = None,
    force_retry: bool = False,
) -> dict[str, Any]:
    """Execute the same bounded task across multiple providers and record consensus.

    Evidence chain: shared task_id -> per-provider real API calls -> answer hashes
    -> exact-answer consensus/disagreement summary.
    """
    import hashlib
    from agent.pgg_archon_external_benchmark_provider_run import PROVIDERS, _load_env, call_provider

    task = (task or "").strip()
    started = datetime.now(timezone.utc)
    task_id = hashlib.sha256(f"multi::{started.isoformat()}::{task}".encode("utf-8")).hexdigest()[:16]
    selected_names = [p.strip() for p in (providers or []) if p and p.strip()]
    if not selected_names:
        selected_names = _ordinary_callable_provider_names(PROVIDERS)
    _load_env(HOME / ".hermes" / ".env")
    if cooldown_sec is None:
        try:
            cooldown_sec = float(os.getenv("PGG_OMNIROUTE_PROVIDER_COOLDOWN_SEC", "600") or "600")
        except ValueError:
            cooldown_sec = 600.0
    cooldown_sec = max(0.0, float(cooldown_sec))
    calls: list[dict[str, Any]] = []
    active_cooldown = get_omniroute_provider_cooldown().get("active", {})
    for name in selected_names:
        if _is_third_party_judge_provider(name):
            calls.append({
                "provider": name,
                "participated": False,
                "http_status": 0,
                "visible_chars": 0,
                "elapsed_sec": 0.0,
                "answer_preview": "",
                "answer_sha256": "",
                "error": "third-party judge provider is reserved for audit/judge paths and cannot be used for ordinary OmniRoute multi-provider execution",
            })
            continue
        spec = next((s for s in PROVIDERS if s.name == name), None)
        call_started = datetime.now(timezone.utc)
        if name in active_cooldown and not force_retry:
            cd = active_cooldown.get(name, {})
            calls.append({
                "provider": name,
                "participated": False,
                "http_status": 0,
                "visible_chars": 0,
                "elapsed_sec": 0.0,
                "answer_preview": "",
                "answer_sha256": "",
                "cooldown_skipped": True,
                "cooldown_remaining_sec": cd.get("remaining_sec"),
                "error": f"provider in cooldown: {cd.get('reason') or 'recent failure'}",
            })
            continue
        if spec is None:
            calls.append({
                "provider": name,
                "participated": False,
                "http_status": 0,
                "visible_chars": 0,
                "elapsed_sec": 0.0,
                "answer_preview": "",
                "answer_sha256": "",
                "error": f"provider {name!r} not in callable registry",
            })
            continue
        raw = call_provider(spec, task, timeout)
        answer = str(raw.get("parsed_text") or "")
        participated = int(raw.get("http_status") or 0) == 200 and bool(answer)
        calls.append({
            "provider": spec.name,
            "model": spec.model,
            "api_mode": spec.api_mode,
            "called_at": call_started.isoformat(),
            "participated": participated,
            "http_status": int(raw.get("http_status") or 0),
            "visible_chars": len(answer),
            "elapsed_sec": raw.get("elapsed_sec", 0.0),
            "answer_preview": answer[:300],
            "answer_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest() if answer else "",
            "error": raw.get("error", "") if not participated else "",
        })
    successful = [c for c in calls if c.get("participated")]
    failed = [c for c in calls if not c.get("participated")]
    hashes = [c.get("answer_sha256") for c in successful if c.get("answer_sha256")]
    unique_hashes = sorted(set(hashes))
    latencies = [float(c.get("elapsed_sec") or 0.0) for c in calls]
    success_latencies = [float(c.get("elapsed_sec") or 0.0) for c in successful]
    consensus_status = "no_successful_calls"
    if successful and len(unique_hashes) == 1:
        consensus_status = "exact_match"
    elif successful:
        consensus_status = "disagreement"
    cooldown_state = _record_provider_failures_for_cooldown(calls, cooldown_sec=cooldown_sec)
    result = {
        "schema": "PGGArchonOmniRouteMultiProviderTask/v3",
        "task_id": task_id,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "task_type": task_type,
        "task_sha256": hashlib.sha256(task.encode("utf-8")).hexdigest() if task else "",
        "task_preview": task[:160],
        "providers_requested": selected_names,
        "cooldown_sec": cooldown_sec,
        "force_retry": bool(force_retry),
        "provider_count": len(calls),
        "successful_count": len(successful),
        "failed_count": len(failed),
        "success_providers": [c.get("provider") for c in successful],
        "failed_providers": [c.get("provider") for c in failed],
        "consensus_status": consensus_status,
        "unique_answer_hashes": unique_hashes,
        "latency_summary": {
            "avg_elapsed_sec": round(sum(latencies) / max(len(latencies), 1), 3),
            "max_elapsed_sec": round(max(latencies), 3) if latencies else 0.0,
            "avg_success_elapsed_sec": round(sum(success_latencies) / max(len(success_latencies), 1), 3) if success_latencies else 0.0,
        },
        "evidence_export": {
            "task_id": task_id,
            "task_sha256": hashlib.sha256(task.encode("utf-8")).hexdigest() if task else "",
            "providers": selected_names,
            "consensus_status": consensus_status,
            "successful_count": len(successful),
            "failed_count": len(failed),
            "unique_answer_hashes": unique_hashes,
        },
        "cooldown_state": cooldown_state,
        "calls": calls,
        "success": bool(successful),
        "boundary": "Multi-provider task proof for this bounded task only; consensus is exact-answer/hash agreement, not legal correctness or benchmark evidence.",
    }
    evidence_path = _write_multi_evidence_package(result)
    if evidence_path:
        result["evidence_package_path"] = evidence_path
        result["evidence_export"]["evidence_package_path"] = evidence_path
        result["evidence_export"]["latest_package_path"] = str(OMNIROUTE_EVIDENCE_DIR / "latest-omniroute-evidence.json")
    _append_multi_task_event({"ts": datetime.now(timezone.utc).timestamp(), "event": "multi_task_execution", "payload": result})
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
