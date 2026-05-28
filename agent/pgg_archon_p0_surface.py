"""PGG Archon — P0Surface/v1 unified surface.

Aggregates three absorbed P0 surfaces (RiskPrediction, CrossProjectPattern,
LifeHarness) into a single machine-checkable report that the PGG Archon
status surface can consume.

Each sub-surface is tested at import time for basic integrity (version check,
constructor smoke test). The report does not claim AGI completion, does not
write genes, does not call models, and does not start daemons.

Boundary:
  - Read-only: no disk writes unless write_report=True
  - No LLM calls
  - No gene writes
  - No daemon start
  - No AGI completion claim
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from agent.pgg_archon_risk_prediction import (
    scan_content as _risk_scan,
    SURFACE_VERSION as RISK_VERSION,
    SURFACE_SOURCE as RISK_SOURCE,
)
from agent.pgg_archon_cross_project_pattern import (
    Pattern,
    extract_patterns_from_file as _pattern_extract,
    compare_patterns as _pattern_compare,
    SURFACE_VERSION as PATTERN_VERSION,
    SURFACE_SOURCE as PATTERN_SOURCE,
)
from agent.pgg_archon_life_harness import (
    make_heartbeat as _lh_heartbeat,
    make_health_summary as _lh_summary,
    compute_status,
    SystemStatus,
    SURFACE_VERSION as LH_VERSION,
    SURFACE_SOURCE as LH_SOURCE,
)

DEFAULT_REPORT_DIR = Path.home() / ".hermes" / "workspace" / "agi-routing" / "pgg-archon-p0-surfaces"

SURFACE_VERSION = "PGGArchonP0Surface/v1"


# ── Smoke-test each sub-surface at import time ──

def _smoke_risk_prediction() -> dict[str, Any]:
    """Verify RiskPrediction scans a known-bad and a known-clean sample."""
    bad = scan_content('''def x(): execute(f"SELECT * FROM t WHERE id = {uid}")''')
    good = scan_content("x = 1")
    return {
        "importable": True,
        "surface_version": RISK_VERSION,
        "surface_source": RISK_SOURCE,
        "detects_risk": bool(bad.risk_score > 0 and bad.vulnerabilities),
        "clean_code_pass": bool(len(good.vulnerabilities) == 0),
        "schema_ok": bool(getattr(bad, "to_dict", None) is not None),
    }


def _smoke_cross_project_pattern() -> dict[str, Any]:
    """Verify CrossProjectPattern can extract and compare patterns."""
    import tempfile, os
    importable = True
    extraction_ok = False
    comparison_ok = False
    patterns: list = []
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello(): pass\ndef world(): pass\n")
            tmp = f.name
        patterns = _pattern_extract(tmp, "smoke_test")
        extraction_ok = len(patterns) >= 2
        os.unlink(tmp)
    except Exception:
        importable = False

    if importable and extraction_ok:
        try:
            existing = [Pattern("e1", "code", "p1", "a.py", "def hello(): pass", "h")]
            results = _pattern_compare(patterns, existing, threshold=0.9)
            comparison_ok = len(results) == 2
        except Exception:
            comparison_ok = False

    return {
        "importable": importable,
        "surface_version": PATTERN_VERSION,
        "surface_source": PATTERN_SOURCE,
        "extraction_ok": extraction_ok,
        "comparison_ok": comparison_ok,
    }


def _smoke_life_harness() -> dict[str, Any]:
    """Verify LifeHarness heartbeat/health/recovery constructors."""
    try:
        hb = _lh_heartbeat(successes=5, failures=0, uptime=100)
        hs = _lh_summary(hb)
        status_ok = hs.status == SystemStatus.HEALTHY.value

        hb_fail = _lh_heartbeat(successes=0, failures=3, uptime=0)
        hs_fail = _lh_summary(hb_fail, errors=["test error"])
        fail_ok = hs_fail.status == SystemStatus.CRITICAL.value

        return {
            "importable": True,
            "surface_version": LH_VERSION,
            "surface_source": LH_SOURCE,
            "heartbeat_healthy_ok": hb.healthy,
            "heartbeat_unhealthy_ok": not hb_fail.healthy,
            "summary_status_ok": status_ok,
            "critical_status_ok": fail_ok,
        }
    except Exception as exc:
        return {
            "importable": False,
            "surface_version": LH_VERSION,
            "error": str(exc),
        }


def build_pgg_archon_p0_surface(
    *,
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    """Build a unified P0 surface report from the three absorbed sub-surfaces.

    Returns a dict with schema=PGGArchonP0Surface/v1, per-surface smoke test
    results, and an aggregate PASS/WARN/BLOCK status.

    When write_report=True, also writes a JSON report to report_dir.
    """
    risk = _smoke_risk_prediction()
    pattern = _smoke_cross_project_pattern()
    life = _smoke_life_harness()

    surfaces = {
        "risk_prediction": risk,
        "cross_project_pattern": pattern,
        "life_harness": life,
    }

    failures: list[str] = []
    for name, result in surfaces.items():
        if not result.get("importable", False):
            failures.append(f"{name}: not importable")
        elif any(
            not result.get(k, True)
            for k in result
            if k not in ("importable", "surface_version", "surface_source", "error")
        ):
            failures.append(f"{name}: smoke test failure")

    all_ok = len(failures) == 0
    status = "PASS" if all_ok else "BLOCK"

    report = {
        "schema": SURFACE_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        "aggregate": {
            "surfaces_ok": sum(1 for s in surfaces.values() if s.get("importable")),
            "surfaces_total": len(surfaces),
            "no_smoke_failures": all_ok,
            "blocking_failures": failures,
        },
        "surfaces": surfaces,
        "agi_completion_claim": False,
        "boundary": (
            "P0 surface report is read-only. No model calls, no gene writes, "
            "no daemon start, no AGI completion claim."
        ),
    }

    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_pgg_archon_p0_surface.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report_path"] = str(out)

    return report


# Re-export core functions so callers can use them directly
scan_content = _risk_scan
extract_patterns_from_file = _pattern_extract
compare_patterns = _pattern_compare
make_heartbeat = _lh_heartbeat
make_health_summary = _lh_summary
compute_system_status = compute_status

__all__ = [
    "build_pgg_archon_p0_surface",
    "scan_content",
    "extract_patterns_from_file",
    "compare_patterns",
    "make_heartbeat",
    "make_health_summary",
    "compute_system_status",
    "SURFACE_VERSION",
]
