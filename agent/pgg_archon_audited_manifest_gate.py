"""Audited manifest gate for PGG Archon artifacts.

This module wires the MiMo micro-auditor into EVOLUTION_MANIFEST writes:
PASS is allowed only when all configured micro-audits return PASS and no timeout
occurs. Otherwise the manifest entry is downgraded to WATCH.

Boundary: this is an evidence/anti-overclaim gate, not a legal correctness proof,
not an official benchmark score, and not AGI level proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from agent.pgg_archon_legal_boundary_gate import run_legal_boundary_gate
from agent.pgg_archon_mimo_micro_auditor import MicroAuditClaim, run_micro_audits

BOUNDARY = (
    "Audited manifest gate: PASS only if all MiMo micro-audits PASS; "
    "otherwise WATCH. Not legal correctness proof, not official benchmark score, "
    "not AGI level proof."
)


@dataclass(frozen=True)
class AuditedManifestGateResult:
    schema: str
    created_at: str
    manifest_path: str
    manifest_key: str
    requested_status: str
    final_status: str
    artifact_path: str
    artifact_sha256: str
    audit_summary_path: str
    audit_summary_sha256: str
    pass_count: int
    timeout_count: int
    audit_count: int
    downgrade_reasons: list[str]
    boundary: str = BOUNDARY


def _sha256(path: str | Path) -> str:
    p = Path(path).expanduser()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def decide_manifest_status(*, requested_status: str, audit_summary: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    results = audit_summary.get("results") or []
    reported_pass_count = int(audit_summary.get("pass_count") or 0)
    timeout_count = int(audit_summary.get("timeout_count") or 0)
    judge_called = bool(audit_summary.get("judge_called"))
    eligible_pass_count = sum(
        1
        for r in results
        if isinstance(r, dict)
        and r.get("status") == "OK_PARSED"
        and r.get("audit_verdict") == "PASS"
    )
    if reported_pass_count != eligible_pass_count:
        reasons.append(f"reported_pass_count_mismatch={reported_pass_count}_vs_eligible_{eligible_pass_count}")
    if requested_status != "PASS":
        reasons.append(f"requested_status_is_{requested_status}")
    if not judge_called:
        reasons.append("mimo_judge_not_called")
    if not results:
        reasons.append("no_audit_results")
    if timeout_count:
        reasons.append(f"audit_timeout_count={timeout_count}")
    if eligible_pass_count != len(results):
        reasons.append(f"eligible_audit_pass_count={eligible_pass_count}_of_{len(results)}")
    final_status = "PASS" if requested_status == "PASS" and results and not reasons else "WATCH"
    return final_status, reasons


def write_audited_manifest_entry(
    *,
    manifest_path: str | Path,
    manifest_key: str,
    artifact_path: str | Path,
    title: str,
    requested_status: str,
    claims: Iterable[MicroAuditClaim],
    audit_output_dir: str | Path,
    call_mimo: bool = True,
    timeout: int = 45,
    run_legal_boundary_precheck: bool = False,
    extra: dict[str, Any] | None = None,
) -> AuditedManifestGateResult:
    manifest = Path(manifest_path).expanduser()
    artifact = Path(artifact_path).expanduser()
    if not artifact.exists():
        raise FileNotFoundError(str(artifact))
    manifest.parent.mkdir(parents=True, exist_ok=True)
    audit_summary = run_micro_audits(
        artifact_path=artifact,
        claims=list(claims),
        output_dir=audit_output_dir,
        timeout=timeout,
        call_mimo=call_mimo,
    )
    audit_dir = Path(audit_output_dir).expanduser()
    legal_boundary_data = None
    if run_legal_boundary_precheck:
        legal_boundary_path = audit_dir / "legal_boundary_gate.json"
        legal_boundary = run_legal_boundary_gate(artifact_path=artifact, out=legal_boundary_path)
        legal_boundary_data = asdict(legal_boundary)
    audit_summary_path = audit_dir / "mimo_micro_audit_summary.json"
    audit_summary_path.write_text(json.dumps(asdict(audit_summary), ensure_ascii=False, indent=2), encoding="utf-8")
    audit_data = json.loads(audit_summary_path.read_text(encoding="utf-8"))
    final_status, reasons = decide_manifest_status(requested_status=requested_status, audit_summary=audit_data)
    result = AuditedManifestGateResult(
        schema="PGGArchonAuditedManifestGateResult/v1",
        created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        manifest_path=str(manifest),
        manifest_key=manifest_key,
        requested_status=requested_status,
        final_status=final_status,
        artifact_path=str(artifact),
        artifact_sha256=_sha256(artifact),
        audit_summary_path=str(audit_summary_path),
        audit_summary_sha256=_sha256(audit_summary_path),
        pass_count=int(audit_data.get("pass_count") or 0),
        timeout_count=int(audit_data.get("timeout_count") or 0),
        audit_count=len(audit_data.get("results") or []),
        downgrade_reasons=reasons,
    )
    data = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    entry = {
        "schema": "PGGArchonEvolutionManifestEntry/v1",
        "created_at": result.created_at,
        "status": result.final_status,
        "requested_status": requested_status,
        "title": title,
        "boundary": result.boundary,
        "artifact_path": result.artifact_path,
        "artifact_sha256": result.artifact_sha256,
        "audit_summary_path": result.audit_summary_path,
        "audit_summary_sha256": result.audit_summary_sha256,
        "audit_gate": {
            "judge_called": bool(audit_data.get("judge_called")),
            "pass_count": result.pass_count,
            "audit_count": result.audit_count,
            "timeout_count": result.timeout_count,
            "downgrade_reasons": result.downgrade_reasons,
        },
    }
    if legal_boundary_data is not None:
        entry["legal_boundary_gate"] = {
            "status": legal_boundary_data.get("status"),
            "missing_rules": legal_boundary_data.get("missing_rules"),
            "artifact_sha256": legal_boundary_data.get("artifact_sha256"),
            "note": "local deterministic legal-boundary precheck; not MiMo audit PASS and not legal correctness proof",
        }
    if extra:
        entry["extra"] = extra
    data[manifest_key] = entry
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    gate_path = audit_dir / "audited_manifest_gate_result.json"
    gate_path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def default_promptfoo_claims(*, sample_count: int = 30, suite_label: str = "promptfoo official CLI smoke") -> list[MicroAuditClaim]:
    """Build standard anti-overclaim MiMo claims for a promptfoo smoke suite.

    The old 30-suite helper remains as a compatibility wrapper below, but new
    callers should pass the real sample_count so 50-suite gates do not carry
    stale 30-suite wording into third-party audit prompts.
    """
    return [
        MicroAuditClaim(
            "benchmark_overclaim",
            f"{sample_count}题{suite_label}真实{sample_count}/{sample_count} PASS。",
            "不可称官方公开benchmark完整分数；仅可称smoke测试通过。",
        ),
        MicroAuditClaim(
            "legal_overclaim",
            "0006题仅做provided-fact/boundary extraction。",
            "不可称案件法律正确性已验证或可直接提交。",
        ),
        MicroAuditClaim(
            "agi_overclaim",
            f"{sample_count}题smoke不是L2/full AGI证明。",
            "不可称达到L2或full AGI。",
        ),
    ]


def default_promptfoo_30_claims() -> list[MicroAuditClaim]:
    return default_promptfoo_claims(sample_count=30)


def main() -> None:
    ap = argparse.ArgumentParser(description="Write manifest entry gated by MiMo micro-audits")
    ap.add_argument("--manifest", default="/Users/appleoppa/.hermes/data/EVOLUTION_MANIFEST.json")
    ap.add_argument("--key", required=True)
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--requested-status", default="PASS", choices=["PASS", "WATCH", "BLOCKED"])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument("--no-mimo", action="store_true")
    ap.add_argument("--legal-boundary-precheck", action="store_true")
    args = ap.parse_args()
    result = write_audited_manifest_entry(
        manifest_path=args.manifest,
        manifest_key=args.key,
        artifact_path=args.artifact,
        title=args.title,
        requested_status=args.requested_status,
        claims=default_promptfoo_30_claims(),
        audit_output_dir=args.out_dir,
        call_mimo=not args.no_mimo,
        timeout=args.timeout,
        run_legal_boundary_precheck=args.legal_boundary_precheck,
    )
    print(json.dumps(asdict(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
