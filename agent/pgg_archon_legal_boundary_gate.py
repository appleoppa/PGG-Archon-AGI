"""Deterministic legal-boundary gate for PGG Archon reports.

This local gate checks whether a report explicitly preserves legal-task
boundaries before any optional MiMo third-party audit is attempted.

It is intentionally conservative and mechanical. It can prove that required
boundary statements are present; it cannot prove legal correctness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

BOUNDARY = (
    "Deterministic legal boundary gate only; verifies required anti-overclaim "
    "statements are present. Not legal correctness proof, not case filing advice."
)

REQUIRED_RULES = {
    "provided_fact_not_legal_correctness": [
        r"provided[- ]fact",
        r"not legal correctness proof|不是法律正确性证明|不可称案件法律正确性",
    ],
    "constructed_cases_not_real_cases": [
        r"constructed cases|合理构造",
        r"not real case|非真实案号|不得称真实案例",
    ],
    "cms_blocked_not_pass": [
        r"CMS.*BLOCKED|cms.*blocked",
        r"!=\s*PASS|not PASS|不得称.*PASS|不能.*PASS",
    ],
    "not_directly_submit": [
        r"not directly submit|不可直接提交|不得直接提交|主办律师.*复核|human.*review",
    ],
}


@dataclass(frozen=True)
class LegalBoundaryGateResult:
    schema: str
    created_at: str
    status: str
    artifact_path: str
    artifact_sha256: str
    rule_results: dict[str, dict[str, Any]]
    missing_rules: list[str]
    boundary: str = BOUNDARY


def _sha256(path: str | Path) -> str:
    p = Path(path).expanduser()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load_text(path: str | Path) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(str(p))
    if p.suffix.lower() == ".json":
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            return json.dumps(obj, ensure_ascii=False, sort_keys=True)
        except Exception:
            return p.read_text(encoding="utf-8", errors="replace")
    return p.read_text(encoding="utf-8", errors="replace")


def evaluate_legal_boundary_text(text: str) -> tuple[dict[str, dict[str, Any]], list[str]]:
    results: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for rule, patterns in REQUIRED_RULES.items():
        hits = []
        for pat in patterns:
            ok = bool(re.search(pat, text, flags=re.IGNORECASE | re.DOTALL))
            hits.append({"pattern": pat, "matched": ok})
        passed = all(x["matched"] for x in hits)
        results[rule] = {"status": "PASS" if passed else "WATCH", "patterns": hits}
        if not passed:
            missing.append(rule)
    return results, missing


def run_legal_boundary_gate(*, artifact_path: str | Path, out: str | Path | None = None) -> LegalBoundaryGateResult:
    artifact = Path(artifact_path).expanduser()
    text = _load_text(artifact)
    rule_results, missing = evaluate_legal_boundary_text(text)
    result = LegalBoundaryGateResult(
        schema="PGGArchonLegalBoundaryGate/v1",
        created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        status="PASS" if not missing else "WATCH",
        artifact_path=str(artifact),
        artifact_sha256=_sha256(artifact),
        rule_results=rule_results,
        missing_rules=missing,
    )
    if out:
        p = Path(out).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Run deterministic legal boundary gate")
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result = run_legal_boundary_gate(artifact_path=args.artifact, out=args.out)
    print(json.dumps({"status": result.status, "out": args.out, "missing_rules": result.missing_rules}, ensure_ascii=False))


if __name__ == "__main__":
    main()
