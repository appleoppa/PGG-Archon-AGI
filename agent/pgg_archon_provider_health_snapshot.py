"""Live provider health snapshot for PGG OmniRoute.

Runs one real lightweight probe per configured provider and records:
- http status
- visible output chars
- JSON/text parse success proxy
- elapsed time
- healthy = HTTP 200 and visible_chars > 0

Adds TTL caching so dashboards do not call upstream providers on every render.

Boundary: this is a local routing health probe, not a benchmark score, not proof
of legal correctness, and not full AGI evidence.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from agent.pgg_archon_external_benchmark_provider_run import (
    PROVIDERS,
    _load_env,
    probe_provider,
)

DEFAULT_OUT = (
    Path.home()
    / ".hermes"
    / "workspace"
    / "github_absorption"
    / "9router"
    / "analysis"
    / "pgg-omniroute-provider-health-20260605.json"
)
DEFAULT_TTL_SEC = 300.0


@dataclass
class ProviderHealthSnapshot:
    schema: str
    generated_at: str
    generated_epoch_ms: int
    expires_at: str
    expires_epoch_ms: int
    probe_prompt: str
    timeout_sec: float
    ttl_sec: float
    cache_status: str
    cache_control: dict[str, Any]
    age_sec: float
    provider_count: int
    providers: list[dict[str, Any]]
    summary: dict[str, Any]
    boundary: str


def _parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _epoch_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _cache_age_sec(payload: dict[str, Any]) -> float | None:
    generated = _parse_dt(str(payload.get("generated_at", "")))
    if generated is None:
        return None
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - generated).total_seconds())


def _ttl_from_env(default: float) -> float:
    raw = os.environ.get("PGG_OMNIROUTE_HEALTH_TTL_SEC", "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(0.0, min(value, 24 * 3600.0))


def _force_from_env(default: bool = False) -> bool:
    raw = os.environ.get("PGG_OMNIROUTE_HEALTH_FORCE_REFRESH", "").strip().lower()
    if raw in {"1", "true", "yes", "force", "refresh"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    return default


def _load_fresh_cache(path: Path, ttl_sec: float) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if payload.get("schema") != "PGGArchonProviderHealthSnapshot/v1":
        return None
    age = _cache_age_sec(payload)
    if age is None or age > ttl_sec:
        return None
    payload = dict(payload)
    generated = _parse_dt(str(payload.get("generated_at", ""))) or datetime.now(timezone.utc)
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    expires = generated + timedelta(seconds=ttl_sec)
    payload["cache_status"] = "hit"
    payload["age_sec"] = round(age, 3)
    payload["ttl_sec"] = ttl_sec
    payload["generated_epoch_ms"] = payload.get("generated_epoch_ms", _epoch_ms(generated))
    payload["expires_at"] = expires.isoformat()
    payload["expires_epoch_ms"] = _epoch_ms(expires)
    payload["cache_control"] = {
        "enabled": True,
        "cache_hit": True,
        "force_refresh": False,
        "source": "ttl_cache",
        "output_path": str(path),
        "generated_at": generated.isoformat(),
        "expires_at": expires.isoformat(),
        "age_sec": round(age, 3),
        "ttl_sec": ttl_sec,
    }
    payload["output_path"] = str(path)
    payload["boundary"] = payload.get(
        "boundary",
        "Cached provider health snapshot; not benchmark/legal correctness/upstream task participation proof.",
    )
    return payload


def run_provider_health_snapshot(
    output_path: str | Path = DEFAULT_OUT,
    *,
    timeout: float = 18.0,
    ttl_sec: float = DEFAULT_TTL_SEC,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Return provider health, using a TTL cache unless force_refresh is set.

    Cache hit avoids upstream API calls. Cache miss/expired/force_refresh runs one
    real probe per provider and writes a new snapshot.
    """
    ttl_sec = _ttl_from_env(ttl_sec)
    force_refresh = _force_from_env(force_refresh)
    out = Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    if not force_refresh:
        cached = _load_fresh_cache(out, ttl_sec)
        if cached is not None:
            return cached

    _load_env(Path.home() / ".hermes" / ".env")
    probe_item = {
        "id": "omniroute-health-probe",
        "domain": "routing_health",
        "prompt": "Reply with exactly: OK",
        "expected": "yes",
    }
    results: list[dict[str, Any]] = []
    for spec in PROVIDERS:
        r = probe_provider(spec, probe_item, timeout)
        visible = int(r.get("probe_chars") or 0)
        http_status = int(r.get("probe_http") or 0)
        healthy = bool(r.get("healthy"))
        results.append(
            {
                "provider": spec.name,
                "model": spec.model,
                "api_mode": spec.api_mode,
                "healthy": healthy,
                "http_status": http_status,
                "visible_chars": visible,
                "json_validity": "visible_text" if visible > 0 else "no_visible_text",
                "probe_error": r.get("probe_error", ""),
                "probe_note": r.get("probe_note", ""),
                "probe_preview": r.get("probe_parsed_preview", ""),
                "supports": {
                    "responses": spec.api_mode == "codex_responses",
                    "legal": spec.name in {"deepseek", "gpt55"},
                    "coding": True,
                    "evolution": spec.name in {"gpt55", "mimo"},
                },
            }
        )
    healthy_count = sum(1 for r in results if r["healthy"])
    avg_visible = round(sum(r["visible_chars"] for r in results) / max(len(results), 1), 2)
    generated = datetime.now(timezone.utc)
    expires = generated + timedelta(seconds=ttl_sec)
    snap = ProviderHealthSnapshot(
        schema="PGGArchonProviderHealthSnapshot/v1",
        generated_at=generated.isoformat(),
        generated_epoch_ms=_epoch_ms(generated),
        expires_at=expires.isoformat(),
        expires_epoch_ms=_epoch_ms(expires),
        probe_prompt=probe_item["prompt"],
        timeout_sec=timeout,
        ttl_sec=ttl_sec,
        cache_status="refresh_forced" if force_refresh else "refresh_miss_or_expired",
        cache_control={
            "enabled": True,
            "cache_hit": False,
            "force_refresh": force_refresh,
            "source": "live_probe",
            "output_path": str(out),
        },
        age_sec=0.0,
        provider_count=len(results),
        providers=results,
        summary={
            "healthy_count": healthy_count,
            "unhealthy_count": len(results) - healthy_count,
            "avg_visible_chars": avg_visible,
            "providers": [r["provider"] for r in results],
        },
        boundary="Live provider health probe with TTL cache; not benchmark, not legal correctness, not upstream task participation proof.",
    )
    payload = asdict(snap)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload | {"output_path": str(out)}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PGG OmniRoute provider health snapshot with TTL cache")
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    parser.add_argument("--timeout", type=float, default=18.0)
    parser.add_argument("--ttl", type=float, default=DEFAULT_TTL_SEC)
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()
    print(json.dumps(
        run_provider_health_snapshot(args.output, timeout=args.timeout, ttl_sec=args.ttl, force_refresh=args.force_refresh),
        ensure_ascii=False,
        indent=2,
    ))
