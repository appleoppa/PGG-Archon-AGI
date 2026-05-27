"""Helpers for generating read-only RuntimeOS quality evidence bundles."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Sequence

from runtime.quality.gate_runner import load_evidence_bundle_schema

_MAX_SUMMARY = 240


def _truncate(value: Any, *, limit: int = _MAX_SUMMARY) -> str:
    text = str(value or "").replace("\n", " ").replace("\r", " ").strip()
    return text[:limit]


def build_quality_evidence_bundle(
    *,
    test_exit_code: int | None = None,
    test_summary: str = "",
    audit_present: bool = False,
    audit_summary: str = "",
    documentation_present: bool = False,
    documentation_summary: str = "",
    source: str = "apex-runtimeos-quality-evidence",
) -> Dict[str, Any]:
    """Build a schema-valid CMMI evidence bundle.

    The bundle records only aggregate booleans and short summaries. It does not
    include stdout/stderr, environment variables, local paths, credentials, or raw
    prompts/messages.
    """
    test_present = test_exit_code == 0 if test_exit_code is not None else False
    bundle: Dict[str, Any] = {
        "schema": "ApexRuntimeOSQualityEvidenceBundle/v1",
        "source": _truncate(source, limit=160),
        "evidence": {
            "test_report": {
                "present": bool(test_present),
                "summary": _truncate(test_summary or ("test command passed" if test_present else "test command did not pass")),
            },
            "audit_log": {
                "present": bool(audit_present),
                "summary": _truncate(audit_summary or ("audit evidence present" if audit_present else "audit evidence missing")),
            },
            "documentation": {
                "present": bool(documentation_present),
                "summary": _truncate(documentation_summary or ("documentation evidence present" if documentation_present else "documentation evidence missing")),
            },
        },
    }
    # Validate before returning so callers never emit malformed bundles silently.
    from jsonschema import Draft202012Validator

    Draft202012Validator(load_evidence_bundle_schema()).validate(bundle)
    return bundle


def run_test_command_for_evidence(command: Sequence[str], *, timeout: int = 600, cwd: str | None = None) -> Dict[str, Any]:
    """Run a test command and return sanitized aggregate execution evidence."""
    started = time.time()
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            shell=False,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
        exit_code = int(completed.returncode)
        timed_out = False
    except subprocess.TimeoutExpired:
        exit_code = 124
        timed_out = True
    elapsed_ms = int((time.time() - started) * 1000)
    return {
        "schema": "ApexRuntimeOSTestEvidence/v1",
        "exit_code": exit_code,
        "passed": exit_code == 0,
        "timed_out": timed_out,
        "elapsed_ms": elapsed_ms,
        "summary": "test command passed" if exit_code == 0 else ("test command timed out" if timed_out else "test command failed"),
        "side_effects": "runs_requested_test_command_only",
    }


def write_quality_evidence_bundle(path: Path, bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Write a validated evidence bundle to a caller-selected path."""
    from jsonschema import Draft202012Validator

    Draft202012Validator(load_evidence_bundle_schema()).validate(bundle)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"written": True, "path": str(path), "schema": bundle.get("schema")}


__all__ = [
    "build_quality_evidence_bundle",
    "run_test_command_for_evidence",
    "write_quality_evidence_bundle",
]
