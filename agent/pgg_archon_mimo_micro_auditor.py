"""PGG Archon MiMo micro-auditor.

A reusable third-party boundary audit runner for evidence artifacts. It keeps
MiMo as a held-out judge and asks one short boundary question per call to avoid
large-packet timeouts.

Boundary: this validates anti-overclaim statements and artifact references; it
is not a legal correctness proof, not an official benchmark score, and not AGI
level proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


BOUNDARY = (
    "MiMo micro-audit only: third-party boundary/anti-overclaim review; "
    "no processing/coding/task solving; no AGI level proof."
)


@dataclass(frozen=True)
class MicroAuditClaim:
    audit_name: str
    claim: str
    expected_boundary: str


@dataclass(frozen=True)
class MicroAuditResult:
    audit_name: str
    status: str
    audit_verdict: str | None
    reason: str
    duration_s: float
    raw_path: str


@dataclass(frozen=True)
class MicroAuditSummary:
    schema: str
    created_at: str
    provider: str
    model: str
    role: str
    judge_called: bool
    artifact_path: str
    artifact_sha256: str
    pass_count: int
    timeout_count: int
    results: list[dict[str, Any]]
    boundary: str = BOUNDARY


def sha256_file(path: str | Path) -> str:
    p = Path(path).expanduser()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_json_candidate(text: str) -> dict[str, Any] | None:
    s = (text or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    a, b = s.find("{"), s.rfind("}")
    if a >= 0 and b > a:
        try:
            obj = json.loads(s[a : b + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def build_prompt(*, claim: MicroAuditClaim, artifact_path: str, artifact_sha256: str) -> str:
    return (
        "你是MiMo，只做独立第三方审计/benchmark judge，不参与处理、编码或任务求解。"
        "极短JSON输出: "
        "{\"audit_name\":\"%s\",\"audit_verdict\":\"PASS|WATCH|BLOCKED\",\"reason\":\"一句话\"}\n"
        "artifact=%s sha256=%s\n"
        "待审计声明: %s\n"
        "正确边界: %s"
    ) % (claim.audit_name, artifact_path, artifact_sha256, claim.claim, claim.expected_boundary)


def deterministic_boundary_check(claim: MicroAuditClaim) -> dict[str, Any]:
    """Local no-LLM guard for obviously unsafe overclaims.

    This does not replace MiMo. It catches prompt/package mistakes before paying
    for a remote audit and provides an offline fallback status.
    """
    bad_patterns = [
        # Positive overclaims only. Boundary statements such as "不是 full AGI"
        # or "不可称官方完整分数" must not be flagged.
        r"可以宣称.*full\s*AGI",
        r"可称.*full\s*AGI",
        r"达到\s*L[2-5]",
        r"可以宣称.*官方公开benchmark完整分数",
        r"可称.*官方公开benchmark完整分数",
        r"法律正确性已验证",
        r"可直接提交",
    ]
    text = claim.claim
    hits = [pat for pat in bad_patterns if re.search(pat, text, flags=re.I)]
    return {
        "audit_name": claim.audit_name,
        "status": "WATCH" if hits else "PASS",
        "hits": hits,
        "boundary": "deterministic precheck only; MiMo remains the third-party judge",
    }


def run_one_mimo_audit(
    *,
    claim: MicroAuditClaim,
    artifact_path: str,
    artifact_sha256: str,
    output_dir: Path,
    timeout: int,
    provider: str = "mimo_v25_pro_auditor",
    model: str = "mimo-v2.5-pro",
) -> MicroAuditResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / f"{claim.audit_name}.raw.txt"
    prompt = build_prompt(claim=claim, artifact_path=artifact_path, artifact_sha256=artifact_sha256)
    t0 = time.time()
    try:
        p = subprocess.run(
            ["hermes", "-z", prompt, "--provider", f"custom:{provider}", "--model", model],
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        txt = (p.stdout or "").strip()
        err = (p.stderr or "").strip()
        raw_path.write_text("STDOUT\n" + txt + "\nSTDERR\n" + err, encoding="utf-8")
        parsed = parse_json_candidate(txt)
        if p.returncode != 0:
            verdict = None
            reason = f"hermes_exit_code={p.returncode}"
            status = "ERROR"
        elif parsed:
            verdict = parsed.get("audit_verdict")
            reason = str(parsed.get("reason") or "")
            status = "OK_PARSED" if verdict in {"PASS", "WATCH", "BLOCKED"} else "OK_UNPARSED"
        else:
            verdict = None
            reason = "unparsed_or_empty_output" if txt else "empty_output"
            status = "OK_UNPARSED" if txt else "ERROR"
        return MicroAuditResult(claim.audit_name, status, verdict, reason, round(time.time() - t0, 2), str(raw_path))
    except subprocess.TimeoutExpired:
        raw_path.write_text("TIMEOUT", encoding="utf-8")
        return MicroAuditResult(claim.audit_name, "UNAVAILABLE_TIMEOUT", None, "timeout", float(timeout), str(raw_path))


def run_micro_audits(
    *,
    artifact_path: str | Path,
    claims: Iterable[MicroAuditClaim],
    output_dir: str | Path,
    timeout: int = 45,
    call_mimo: bool = True,
) -> MicroAuditSummary:
    artifact = Path(artifact_path).expanduser()
    if not artifact.exists():
        raise FileNotFoundError(str(artifact))
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    artifact_sha = sha256_file(artifact)
    results: list[MicroAuditResult] = []
    for claim in claims:
        pre = deterministic_boundary_check(claim)
        (out / f"{claim.audit_name}.precheck.json").write_text(json.dumps(pre, ensure_ascii=False, indent=2), encoding="utf-8")
        if call_mimo:
            results.append(run_one_mimo_audit(claim=claim, artifact_path=str(artifact), artifact_sha256=artifact_sha, output_dir=out, timeout=timeout))
        else:
            results.append(
                MicroAuditResult(
                    claim.audit_name,
                    "LOCAL_PRECHECK_ONLY",
                    None,
                    "local deterministic precheck only; MiMo judge was not called and this cannot count as PASS",
                    0.0,
                    str(out / f"{claim.audit_name}.precheck.json"),
                )
            )
    return MicroAuditSummary(
        schema="PGGArchonMiMoMicroAuditSummary/v1",
        created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        provider="mimo_v25_pro_auditor",
        model="mimo-v2.5-pro",
        role="third_party_benchmark_judge_only",
        judge_called=call_mimo,
        artifact_path=str(artifact),
        artifact_sha256=artifact_sha,
        pass_count=sum(1 for r in results if r.audit_verdict == "PASS"),
        timeout_count=sum(1 for r in results if r.status == "UNAVAILABLE_TIMEOUT"),
        results=[asdict(r) for r in results],
    )


def default_30_suite_claims() -> list[MicroAuditClaim]:
    return [
        MicroAuditClaim(
            "benchmark_overclaim",
            "30题promptfoo official CLI smoke真实30/30 PASS。",
            "不可称官方公开benchmark完整分数；仅可称smoke测试通过。",
        ),
        MicroAuditClaim(
            "legal_overclaim",
            "0006题仅做provided-fact/boundary extraction。",
            "不可称案件法律正确性已验证或可直接提交。",
        ),
        MicroAuditClaim(
            "agi_overclaim",
            "30题smoke不是L2/full AGI证明。",
            "不可称达到L2或full AGI。",
        ),
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description="Run MiMo micro third-party audits")
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument("--no-mimo", action="store_true", help="Only run deterministic local prechecks")
    args = ap.parse_args()
    summary = run_micro_audits(
        artifact_path=args.artifact,
        claims=default_30_suite_claims(),
        output_dir=args.out_dir,
        timeout=args.timeout,
        call_mimo=not args.no_mimo,
    )
    out = Path(args.out_dir).expanduser() / "mimo_micro_audit_summary.json"
    out.write_text(json.dumps(asdict(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    cli_status = "PASS" if summary.judge_called and summary.pass_count == len(summary.results) else "WATCH"
    print(json.dumps({"status": cli_status, "summary": str(out), "judge_called": summary.judge_called, "pass_count": summary.pass_count, "timeout_count": summary.timeout_count}, ensure_ascii=False))


if __name__ == "__main__":
    main()
