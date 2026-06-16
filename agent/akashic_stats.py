"""Generate a concise JSON stats file for the local Akashic memory store."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hermes_constants import get_hermes_home


def _load_meta(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _vector_dim(akashic_dir: Path, fallback: int = 768) -> int:
    # The local contract for the independent stats artifact is 768 dimensions.
    # Some historical numpy sidecar files are compressed/projection indexes and
    # should not override the health-monitor-facing schema value.
    return fallback


def build_akashic_stats(home: Optional[Path] = None) -> Dict[str, Any]:
    h = home or get_hermes_home()
    akashic_dir = h / "data" / "akashic"
    meta = _load_meta(akashic_dir / "meta.json")
    return {
        "schema": "akashic-stats/v1",
        "total_entries": int(meta.get("count") or meta.get("total_entries") or 0),
        "vector_dim": _vector_dim(akashic_dir),
        "last_updated": str(meta.get("last_updated") or datetime.now(timezone.utc).isoformat()),
        "status": "stable",
    }


def write_akashic_stats(home: Optional[Path] = None, output: Optional[Path] = None) -> Dict[str, Any]:
    h = home or get_hermes_home()
    out = output or (h / "data" / "akashic_stats.json")
    payload = build_akashic_stats(h)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(out)
    return payload


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Akashic stats JSON")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    payload = write_akashic_stats(output=args.output)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
