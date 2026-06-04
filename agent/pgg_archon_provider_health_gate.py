"""Provider health gate for PGG Archon benchmark results.

Converts provider-backed benchmark evidence into routing recommendations while
separating provider transport failures from model capability failures.

Boundary: internal provider routing guidance only. It is not an external model
benchmark, not full AGI proof, and not legal correctness proof.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ProviderHealthDecision:
    provider_id: str
    model: str
    health: str
    route: str
    weighted_score: float
    passed_tasks: int
    total_tasks: int
    evolution_queue_count: int
    transport_failures: int
    capability_failures: int
    reasons: list[str]


@dataclass(frozen=True)
class ProviderHealthGateReport:
    schema: str
    generated_at: str
    status: str
    primary_provider: str | None
    fallback_providers: list[str]
    blocked_providers: list[str]
    decisions: list[dict[str, Any]]
    boundary: str


def _prediction_records(provider_result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    records = provider_result.get("predictions") or []
    return [x for x in records if isinstance(x, Mapping)]


def _benchmark_run(provider_result: Mapping[str, Any]) -> Mapping[str, Any]:
    integrated = provider_result.get("integrated_result") or {}
    if not isinstance(integrated, Mapping):
        return {}
    run = integrated.get("benchmark_run") or {}
    return run if isinstance(run, Mapping) else {}


def _evolution_queue_count(provider_result: Mapping[str, Any]) -> int:
    integrated = provider_result.get("integrated_result") or {}
    if not isinstance(integrated, Mapping):
        return 0
    try:
        return int(integrated.get("evolution_queue_count") or 0)
    except Exception:  # noqa: BLE001
        return 0


def classify_provider_result(provider_result: Mapping[str, Any]) -> ProviderHealthDecision:
    """Classify one provider result into health and routing action."""
    provider = provider_result.get("provider") or {}
    if not isinstance(provider, Mapping):
        provider = {}
    provider_id = str(provider.get("provider_id") or "unknown")
    model = str(provider.get("model") or "unknown")
    records = _prediction_records(provider_result)
    run = _benchmark_run(provider_result)

    total_tasks = int(run.get("total_tasks") or len(records) or 0)
    passed_tasks = int(run.get("passed_tasks") or 0)
    weighted_score = float(run.get("weighted_score") or 0.0)
    queue_count = _evolution_queue_count(provider_result)

    transport_failures = 0
    for record in records:
        ok = bool(record.get("ok"))
        http_status = record.get("http_status")
        error = str(record.get("error") or "")
        if not ok and (http_status or "HTTP" in error or "missing api key" in error or "empty prediction" in error):
            transport_failures += 1
    capability_failures = max(0, total_tasks - passed_tasks - transport_failures)

    reasons: list[str] = []
    if transport_failures:
        reasons.append(f"transport_failures={transport_failures}")
    if capability_failures:
        reasons.append(f"capability_failures={capability_failures}")
    reasons.append(f"weighted_score={weighted_score:.6f}")

    if total_tasks and transport_failures == total_tasks:
        health = "DOWN"
        route = "BLOCK_PROVIDER_USE_FALLBACK"
    elif weighted_score >= 0.95 and transport_failures == 0:
        health = "HEALTHY"
        route = "PRIMARY_CANDIDATE"
    elif weighted_score >= 0.50 and transport_failures == 0:
        health = "DEGRADED_CAPABILITY"
        route = "FALLBACK_OR_SPECIALIZED"
    elif transport_failures > 0:
        health = "UNSTABLE_TRANSPORT"
        route = "FALLBACK_UNTIL_RECOVERED"
    else:
        health = "LOW_SCORE"
        route = "DO_NOT_ROUTE_UNTIL_IMPROVED"

    return ProviderHealthDecision(
        provider_id=provider_id,
        model=model,
        health=health,
        route=route,
        weighted_score=weighted_score,
        passed_tasks=passed_tasks,
        total_tasks=total_tasks,
        evolution_queue_count=queue_count,
        transport_failures=transport_failures,
        capability_failures=capability_failures,
        reasons=reasons,
    )


def build_provider_health_gate_report(multi_provider_result: Mapping[str, Any]) -> ProviderHealthGateReport:
    """Build health gate report from PGGArchonMultiProviderBenchmarkResult."""
    results = multi_provider_result.get("results") or []
    decisions = [classify_provider_result(x) for x in results if isinstance(x, Mapping)]
    ordered = sorted(decisions, key=lambda d: (d.health == "HEALTHY", d.weighted_score, -d.transport_failures), reverse=True)

    primary = next((d.provider_id for d in ordered if d.health == "HEALTHY"), None)
    fallbacks = [d.provider_id for d in ordered if d.health in {"DEGRADED_CAPABILITY", "UNSTABLE_TRANSPORT"}]
    blocked = [d.provider_id for d in ordered if d.health in {"DOWN", "LOW_SCORE"}]

    status = "PASS" if primary else "WATCH" if fallbacks else "BLOCKED"
    return ProviderHealthGateReport(
        schema="PGGArchonProviderHealthGate/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        primary_provider=primary,
        fallback_providers=fallbacks,
        blocked_providers=blocked,
        decisions=[asdict(d) for d in ordered],
        boundary="Internal provider health/routing guidance; not external benchmark or AGI proof.",
    )


def load_multi_provider_result(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def write_provider_health_gate_report(report: ProviderHealthGateReport, output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "provider_health_gate.json"
    path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"health_gate": str(path)}


def build_and_write_provider_health_gate(input_path: str | Path, output_dir: str | Path) -> dict[str, str]:
    data = load_multi_provider_result(input_path)
    report = build_provider_health_gate_report(data)
    return write_provider_health_gate_report(report, output_dir)
