"""Read-only readiness gate for external Hermes MemoryProvider activation.

This module audits available memory-provider plugins and config state.  It does
not enable providers, mutate config, connect to cloud memory, or print secrets.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

from hermes_constants import get_hermes_home


LOCAL_FIRST = {"holographic", "hindsight"}
CLOUDISH = {"mem0", "supermemory", "honcho"}


def _read_config() -> Dict[str, Any]:
    cfg = get_hermes_home() / "config.yaml"
    if yaml is None or not cfg.exists():
        return {}
    try:
        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception as e:
        return {"_load_error": f"{type(e).__name__}: {str(e)[:240]}"}


def _provider_dirs() -> List[Path]:
    root = Path(__file__).resolve().parents[1]
    dirs = []
    for base in [root / "plugins" / "memory", get_hermes_home() / "plugins" / "memory"]:
        if base.exists():
            dirs.extend([p for p in base.iterdir() if p.is_dir() and not p.name.startswith("__")])
    seen = set()
    out = []
    for p in dirs:
        if p.name not in seen:
            seen.add(p.name)
            out.append(p)
    return sorted(out, key=lambda x: x.name)


def _secret_presence_for(name: str) -> Dict[str, bool]:
    candidates = {
        "mem0": ["MEM0_API_KEY"],
        "supermemory": ["SUPERMEMORY_API_KEY"],
        "honcho": ["HONCHO_API_KEY"],
        "holographic": [],
        "hindsight": [],
    }.get(name, [])
    return {k: bool(os.environ.get(k)) for k in candidates}


def _provider_summary(p: Path) -> Dict[str, Any]:
    name = p.name
    tool_count = 0
    for py in p.glob("**/*.py"):
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
            tool_count += text.count("register(") + text.count("@tool")
        except Exception:
            pass
    privacy = "local" if name in LOCAL_FIRST else ("cloud" if name in CLOUDISH else "unknown")
    recommendation = "sandbox_local_first" if name in LOCAL_FIRST else ("requires_secret_and_privacy_review" if privacy == "cloud" else "review_before_activation")
    return {
        "name": name,
        "path": str(p),
        "privacy_risk": privacy,
        "tool_count": tool_count,
        "secret_env_presence": _secret_presence_for(name),
        "recommendation": recommendation,
    }


def audit_memory_provider_readiness() -> Dict[str, Any]:
    cfg = _read_config()
    mem_cfg = cfg.get("memory", {}) if isinstance(cfg.get("memory"), dict) else {}
    active = mem_cfg.get("provider") or ""
    providers = [_provider_summary(p) for p in _provider_dirs()]
    names = {p["name"] for p in providers}
    recommended = "holographic" if "holographic" in names else (sorted(names)[0] if names else "")
    active_known = not active or active in names
    status = "PASS_READ_ONLY_AUDIT" if active_known else "WATCH_ACTIVE_PROVIDER_NOT_FOUND"
    return {
        "schema": "PGGMemoryProviderReadiness/v1",
        "status": status,
        "hermes_home": str(get_hermes_home()),
        "active_external_provider": active,
        "provider_count": len(providers),
        "recommended_provider": recommended,
        "recommended_next_step": "sandbox_eval_before_default_activation" if recommended else "no_provider_candidate_found",
        "config_modified": False,
        "secrets_printed": False,
        "providers": providers,
        "boundary": "Read-only provider readiness gate; no config/provider/credential mutation.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = audit_memory_provider_readiness()
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"memory provider readiness: {res['status']} active={res['active_external_provider']!r} recommended={res['recommended_provider']}")
    return 0 if str(res.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
