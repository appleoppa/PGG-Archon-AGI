"""PGG Archon APEX-ASI Gate (总纲8)."""

from __future__ import annotations

import json
import time
from typing import Any, Dict

try:
    import hermes_pgg_apex_asi_gate as _native  # type: ignore[import-untyped]
    _NATIVE = True
except ImportError:
    _NATIVE = False

_SCHEMA = "PGGArchonAPEXASIGate/v1"

VERSION = f"{_native.version()}" if _NATIVE else "0.0.0-python-fallback"


def status() -> Dict[str, Any]:
    """Return gate status."""
    if not _NATIVE:
        return {"schema": _SCHEMA, "status": "ERROR", "detail": "Native module not available", "version": VERSION}

    ts = time.time()
    boundaries = _native.boundary_statement()
    sample_cfg = json.loads(_native.sample_config_json())

    return {
        "schema": _SCHEMA,
        "generated_at": ts,
        "version": VERSION,
        "native_loaded": True,
        "boundary_statement": boundaries,
        "sample_config": sample_cfg,
        "status": "PASS",
        "detail": "APEX-ASI gate available. Read-only state surface. Not full AGI/ASI/T5 claim.",
        "boundary": "Internal engineering gate. No external benchmark. No ASI/full-AGI/zero-risk claim.",
    }


def evaluate(signals: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Evaluate ASI config signals via native gate."""
    if not _NATIVE:
        return {"status": "ERROR", "detail": "Native module not available"}
    return json.loads(_native.evaluate_config_json(json.dumps(signals or {})))


def main() -> int:
    """CLI entry point."""
    import sys

    if "--eval" in sys.argv:
        idx = sys.argv.index("--eval")
        raw = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "{}"
        signals = json.loads(raw)
        print(json.dumps(evaluate(signals), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(status(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    main()
