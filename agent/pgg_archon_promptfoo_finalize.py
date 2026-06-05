"""Finalize promptfoo suite artifacts with audited manifest gate.

Pipeline:
  promptfoo raw result + run log + config
  -> normalized PGG report
  -> MiMo audited manifest gate
  -> EVOLUTION_MANIFEST entry

Boundary: finalizes smoke evidence only. It does not turn promptfoo smoke into an
official benchmark score, legal correctness proof, or AGI level proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from agent.pgg_archon_audited_manifest_gate import default_promptfoo_30_claims, write_audited_manifest_entry

BOUNDARY = (
    "Real promptfoo CLI smoke finalized through audited manifest gate; not an "
    "official public benchmark score, not legal correctness proof, not L2/full AGI proof."
)


def sha256_file(path: str | Path) -> str:
    p = Path(path).expanduser()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_promptfoo_counts(log_text: str) -> dict[str, int]:
    match = re.search(
        r"Results:\s*\n\s*(?:✓|✔)?\s*(\d+) passed.*?\n\s*(?:✗|✖|x)?\s*(\d+) failed.*?\n\s*(?:✗|✖|x)?\s*(\d+) errors",
        log_text,
        re.S,
    )
    if not match:
        raise ValueError("Could not parse promptfoo counts from log")
    passed, failed, errors = map(int, match.groups())
    return {"passed_count": passed, "failed_count": failed, "error_count": errors}


def load_promptfoo_raw(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser()
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # promptfoo schema may evolve, but JSON must parse
        raise ValueError(f"Promptfoo raw output is not valid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("Promptfoo raw output must be a JSON object")
    return obj


def build_promptfoo_report(
    *,
    raw_result: str | Path,
    run_log: str | Path,
    config: str | Path,
    prompt: str | Path | None,
    provider: str | Path | None,
    output_dir: str | Path,
    suite_id: str,
    source_type: str,
    domains: dict[str, int],
    framework_package: str = "promptfoo@0.121.15 via npm exec",
) -> dict[str, Any]:
    raw_path = Path(raw_result).expanduser()
    log_path = Path(run_log).expanduser()
    cfg_path = Path(config).expanduser()
    for p in [raw_path, log_path, cfg_path]:
        if not p.exists():
            raise FileNotFoundError(str(p))
    raw_obj = load_promptfoo_raw(raw_path)
    counts = parse_promptfoo_counts(log_path.read_text(encoding="utf-8", errors="replace"))
    sample_count = sum(counts.values())
    if domains and sum(domains.values()) != sample_count:
        raise ValueError(f"domains total {sum(domains.values())} != sample_count {sample_count}")
    outdir = Path(output_dir).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)
    legal_boundary_statements = []
    if any("legal" in key.lower() or "case" in key.lower() for key in domains):
        legal_boundary_statements = [
            "provided-fact extraction only; not legal correctness proof; 不可称案件法律正确性已验证",
            "constructed cases / 合理构造 examples are not real case numbers / 非真实案号",
            "CMS BLOCKED != PASS; cms blocked must not be represented as PASS",
            "not directly submit; 不可直接提交; human lawyer review required / 主办律师人工复核必需",
        ]
    report = {
        "schema": "PGGArchonPromptfooSuiteFinalReport/v1",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "framework": "promptfoo",
        "framework_package": framework_package,
        "source_type": source_type,
        "suite_id": suite_id,
        "sample_count": sample_count,
        "domains": domains,
        **counts,
        "exit_code": 0 if counts["error_count"] == 0 else 100,
        "metric": "promptfoo assertions pass/fail/error counts from CLI log",
        "raw_result_path": str(raw_path),
        "raw_result_sha256": sha256_file(raw_path),
        "run_log_path": str(log_path),
        "run_log_sha256": sha256_file(log_path),
        "config_path": str(cfg_path),
        "config_sha256": sha256_file(cfg_path),
        "prompt_path": str(Path(prompt).expanduser()) if prompt else "",
        "provider_path": str(Path(provider).expanduser()) if provider else "",
        "raw_top_keys": sorted(raw_obj.keys())[:50],
        "legal_boundary_statements": legal_boundary_statements,
        "boundary": BOUNDARY,
    }
    report_path = outdir / f"{suite_id}_final_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def finalize_promptfoo_suite(
    *,
    raw_result: str | Path,
    run_log: str | Path,
    config: str | Path,
    prompt: str | Path | None,
    provider: str | Path | None,
    output_dir: str | Path,
    suite_id: str,
    source_type: str,
    domains: dict[str, int],
    manifest_key: str,
    title: str,
    manifest_path: str | Path = "/Users/appleoppa/.hermes/data/EVOLUTION_MANIFEST.json",
    requested_status: str = "PASS",
    call_mimo: bool = True,
    timeout: int = 45,
    legal_boundary_precheck: bool = False,
) -> dict[str, Any]:
    report = build_promptfoo_report(
        raw_result=raw_result,
        run_log=run_log,
        config=config,
        prompt=prompt,
        provider=provider,
        output_dir=output_dir,
        suite_id=suite_id,
        source_type=source_type,
        domains=domains,
    )
    outdir = Path(output_dir).expanduser()
    report_path = outdir / f"{suite_id}_final_report.json"
    gate = write_audited_manifest_entry(
        manifest_path=manifest_path,
        manifest_key=manifest_key,
        artifact_path=report_path,
        title=title,
        requested_status=requested_status,
        claims=default_promptfoo_30_claims(),
        audit_output_dir=outdir / "audit_gate",
        call_mimo=call_mimo,
        timeout=timeout,
        run_legal_boundary_precheck=legal_boundary_precheck,
        extra={
            "suite_id": suite_id,
            "source_type": source_type,
            "sample_count": report["sample_count"],
            "passed_count": report["passed_count"],
            "failed_count": report["failed_count"],
            "error_count": report["error_count"],
            "domains": domains,
        },
    )
    closure = {
        "schema": "PGGArchonPromptfooFinalizeClosure/v1",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "suite_id": suite_id,
        "report_path": str(report_path),
        "report_sha256": sha256_file(report_path),
        "manifest_key": manifest_key,
        "manifest_final_status": gate.final_status,
        "audit_summary_path": gate.audit_summary_path,
        "audit_summary_sha256": gate.audit_summary_sha256,
        "boundary": BOUNDARY,
    }
    closure_path = outdir / f"{suite_id}_finalize_closure.json"
    closure_path.write_text(json.dumps(closure, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"report": report, "gate": gate, "closure_path": str(closure_path), "closure_sha256": sha256_file(closure_path)}


def _parse_domains(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    if not text:
        return out
    for part in text.split(","):
        if not part.strip():
            continue
        key, value = part.split(":", 1)
        out[key.strip()] = int(value.strip())
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Finalize promptfoo suite with audited manifest gate")
    ap.add_argument("--raw-result", required=True)
    ap.add_argument("--run-log", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--prompt", default="")
    ap.add_argument("--provider", default="")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--suite-id", required=True)
    ap.add_argument("--source-type", required=True)
    ap.add_argument("--domains", required=True, help="comma list e.g. arithmetic:10,gsm8k:10,legal:10")
    ap.add_argument("--manifest-key", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--requested-status", default="PASS", choices=["PASS", "WATCH", "BLOCKED"])
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument("--no-mimo", action="store_true")
    ap.add_argument("--legal-boundary-precheck", action="store_true")
    args = ap.parse_args()
    result = finalize_promptfoo_suite(
        raw_result=args.raw_result,
        run_log=args.run_log,
        config=args.config,
        prompt=args.prompt or None,
        provider=args.provider or None,
        output_dir=args.out_dir,
        suite_id=args.suite_id,
        source_type=args.source_type,
        domains=_parse_domains(args.domains),
        manifest_key=args.manifest_key,
        title=args.title,
        requested_status=args.requested_status,
        call_mimo=not args.no_mimo,
        timeout=args.timeout,
        legal_boundary_precheck=args.legal_boundary_precheck,
    )
    print(json.dumps({
        "status": result["gate"].final_status,
        "report": result["closure_path"].replace("_finalize_closure.json", "_final_report.json"),
        "closure": result["closure_path"],
        "closure_sha256": result["closure_sha256"],
        "audit_summary": result["gate"].audit_summary_path,
        "manifest_key": args.manifest_key,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
