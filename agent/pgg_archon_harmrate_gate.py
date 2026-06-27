"""PGG internal HarmRate gate — Rust/PyO3 bridge.

Boundary:
- PGG internal risk/negative-utility gate only;
- not an APEX-MOSS verified implementation;
- no zero-risk, no production-safety certification, no AGI/ASI claim;
- no LLM calls, no network.

Rust replacement discipline:
- This file contains NO HarmRate formula logic.
- It only imports ``hermes_pgg_archon_utils`` and calls native Rust functions.
- If the .so is unavailable, calls fail closed instead of using a Python fallback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

BOUNDARY = "PGG_internal_HarmRate_gate; APEX_MOSS_VERIFIED=false; no_zero_risk_claim; no_external_safety_certification"
DEFAULT_BLOCK_THRESHOLD = 0.34
DEFAULT_WATCH_THRESHOLD = 0.20
SENSITIVE_TASK_TYPES = {"legal", "production", "security", "credential", "external_public"}

try:
    import hermes_pgg_archon_utils as _native
except ImportError:  # pragma: no cover - fail-closed runtime boundary
    _native = None


def _require_native() -> Any:
    if _native is None:
        raise RuntimeError("BLOCKED_MISSING_RUST_NATIVE: hermes_pgg_archon_utils .so not importable")
    return _native


def compute_harmrate(
    task: Mapping[str, Any],
    *,
    block_threshold: float = DEFAULT_BLOCK_THRESHOLD,
    watch_threshold: float = DEFAULT_WATCH_THRESHOLD,
) -> dict[str, Any]:
    native = _require_native()
    raw = native.compute_harmrate_json(
        json.dumps(dict(task), ensure_ascii=False),
        float(block_threshold),
        float(watch_threshold),
    )
    return json.loads(raw)


def write_harmrate_report(report: Mapping[str, Any], output_dir: str | Path) -> str:
    native = _require_native()
    return str(
        native.write_harmrate_report_json(
            json.dumps(dict(report), ensure_ascii=False),
            str(Path(output_dir).expanduser()),
        )
    )


__all__ = ["BOUNDARY", "compute_harmrate", "write_harmrate_report"]
