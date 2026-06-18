"""PGG memory layer sync/status bridge.

Read-only compatibility module for the ``pgg_memory_layer_sync`` wrapper.
It reports concise JSON for the user's five-layer memory architecture and
three-layer discipline without mutating config, credentials, scheduler, or
memory content.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from hermes_constants import get_hermes_home


def _compact_status(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("status") or value.get("runtime_status") or "UNKNOWN")
    return "UNKNOWN"


def build_five_layer_status(home: Optional[Path] = None) -> Dict[str, Any]:
    """Return concise read-only status for five memory layers."""
    h = home or get_hermes_home()
    try:
        from agent.memory_system_status import build_memory_system_status

        full = build_memory_system_status(h)
        ak_stats = (full.get("akashic") or {}).get("stats") if isinstance(full.get("akashic"), dict) else None
        layers = {
            "layer1_curated_memory_user": {
                "status": _compact_status(full.get("curated")),
                "authoritative": bool((full.get("curated") or {}).get("authoritative")) if isinstance(full.get("curated"), dict) else False,
            },
            "layer2_akashic_vector": {
                "status": _compact_status(full.get("akashic")),
                "stats_present": bool(ak_stats),
            },
            "layer3_department_swr": {
                "status": _compact_status(full.get("department_swr")),
                "write_allowed": bool((full.get("department_swr") or {}).get("write_allowed")) if isinstance(full.get("department_swr"), dict) else False,
                "apply_allowed": bool((full.get("department_swr") or {}).get("apply_allowed")) if isinstance(full.get("department_swr"), dict) else False,
            },
            "layer4_external_provider": {
                "status": _compact_status(full.get("external_provider")),
                "active_external_provider_present": bool((full.get("external_provider") or {}).get("active_external_provider")) if isinstance(full.get("external_provider"), dict) else False,
            },
            "layer5_manifest_holographic": {
                "status": _compact_status(full.get("holographic")),
                "manifest_exists": bool((full.get("manifest") or {}).get("exists")) if isinstance(full.get("manifest"), dict) else False,
            },
        }
        overall_raw = full.get("overall")
        overall: Dict[str, Any] = overall_raw if isinstance(overall_raw, dict) else {}
        return {
            "schema": "pgg-memory-layer-sync/v1",
            "mode": "five",
            "read_only": True,
            "config_modified": False,
            "hermes_home": str(h),
            "status": "PASS" if not overall.get("failed_or_watch") else "WATCH",
            "layers": layers,
            "failed_or_watch": overall.get("failed_or_watch", []),
        }
    except Exception as exc:
        return {
            "schema": "pgg-memory-layer-sync/v1",
            "mode": "five",
            "read_only": True,
            "config_modified": False,
            "hermes_home": str(h),
            "status": "ERROR",
            "error": f"{type(exc).__name__}: {str(exc)[:240]}",
        }


def build_three_layer_discipline(home: Optional[Path] = None) -> Dict[str, Any]:
    """Return concise status for three discipline layers."""
    h = home or get_hermes_home()
    memory_file = h / "memories" / "MEMORY.md"
    user_file = h / "memories" / "USER.md"
    akashic_stats = h / "data" / "akashic_stats.json"
    manifest = h / "data" / "EVOLUTION_MANIFEST.json"
    layers = {
        "discipline1_curated_authority": {
            "status": "PASS" if memory_file.exists() and user_file.exists() else "WATCH_MISSING_CURATED",
            "memory_exists": memory_file.exists(),
            "user_exists": user_file.exists(),
        },
        "discipline2_observe_first_no_mutation": {
            "status": "PASS",
            "read_only": True,
            "config_modified": False,
            "credential_access": False,
        },
        "discipline3_health_evidence": {
            "status": "PASS" if akashic_stats.exists() and manifest.exists() else "WATCH_MISSING_EVIDENCE",
            "akashic_stats_exists": akashic_stats.exists(),
            "manifest_exists": manifest.exists(),
        },
    }
    status = "PASS" if all(v["status"] == "PASS" for v in layers.values()) else "WATCH"
    return {
        "schema": "pgg-memory-layer-sync/v1",
        "mode": "three",
        "read_only": True,
        "config_modified": False,
        "hermes_home": str(h),
        "status": status,
        "disciplines": layers,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="PGG memory layer sync/status bridge")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--five", action="store_true", help="query five-layer memory status")
    group.add_argument("--three", action="store_true", help="query three-layer discipline status")
    args = parser.parse_args(argv)
    payload = build_five_layer_status() if args.five else build_three_layer_discipline()
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload.get("status") in {"PASS", "WATCH"} else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
