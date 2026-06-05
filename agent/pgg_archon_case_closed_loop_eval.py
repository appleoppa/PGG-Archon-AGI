"""PGG Archon case closed-loop evaluator.

Evaluates archived case folders for evidence that the formal Apple CMS/legal
workflow actually ran: materials, CMS flow/ledger, evidence, legal basis,
analysis, inspection, audit, final/draft documents, and raw multi-LLM traces.

Boundary: directory/file evidence is a process score, not proof of legal
correctness or court-submission readiness.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


@dataclass
class CaseClosedLoopReport:
    schema: str
    generated_at: str
    case_root: str
    case_no: str
    file_count: int
    gates: dict[str, bool]
    gate_passed: int
    gate_total: int
    closed_loop_score: float
    cms_guard: dict[str, Any]
    legal_doc_gate: dict[str, Any] | None
    boundary: str
    sample_files: list[str]


def _files(root: Path) -> list[Path]:
    return sorted([p for p in root.rglob("*") if p.is_file() and p.name != ".DS_Store"])


def _rel_text(files: list[Path], root: Path) -> str:
    return "\n".join(str(p.relative_to(root)) for p in files)


def infer_case_no(root: Path, rels: str) -> str:
    import re
    m = re.search(r"PGG-[A-Z]{2}-\d{8}-\d{4}", rels) or re.search(r"PGG-[A-Z]{2}-\d{8}-\d{4}", root.name)
    return m.group(0) if m else root.name


def run_cms_guard(root: Path, case_type: str) -> dict[str, Any]:
    cmd = [str(Path.home() / ".hermes/bin/cms_case_guard"), "--validate", str(root), "--case-type", case_type]
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    raw = (proc.stdout or proc.stderr or "").strip()
    try:
        data = json.loads(raw)
    except Exception:
        data = {"status": "ERROR", "raw": raw, "stderr": proc.stderr, "returncode": proc.returncode}
    data["returncode"] = proc.returncode
    return data


def find_final_doc(files: list[Path]) -> Path | None:
    preferred = [p for p in files if ("FINAL" in p.name or "终版" in p.name) and p.suffix == ".md"]
    if preferred:
        return sorted(preferred, key=lambda p: ("FINAL_v2" not in p.name, len(p.name)))[0]
    docs = [p for p in files if "正式文书" in str(p) and p.suffix == ".md"]
    return docs[0] if docs else None


def find_source_fact(files: list[Path]) -> Path | None:
    preferred = [p for p in files if ("文字提取" in p.name or "原始材料" in p.name or "材料提取全文" in p.name) and p.suffix in {".md", ".txt"}]
    return preferred[0] if preferred else None


def run_legal_doc_gate(final_doc: Path | None, source_fact: Path | None) -> dict[str, Any] | None:
    if final_doc is None:
        return None
    cmd = [str(Path.home() / ".hermes/bin/legal_doc_gate"), str(final_doc)]
    if source_fact is not None:
        cmd.append(str(source_fact))
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    out = (proc.stdout or proc.stderr or "").strip()
    first = out.splitlines()[0] if out else ""
    status = first.replace("LEGAL_DOC_GATE_RESULT:", "").strip() if "LEGAL_DOC_GATE_RESULT:" in first else "UNKNOWN"
    return {"status": status, "returncode": proc.returncode, "final_doc": str(final_doc), "source_fact": str(source_fact) if source_fact else None, "raw": out}


def evaluate_case(root: str | Path, case_type: str, *, run_legal_gate: bool = True) -> dict[str, Any]:
    root = Path(str(root)).expanduser().resolve()
    files = _files(root)
    rels = _rel_text(files, root)
    case_no = infer_case_no(root, rels)
    gates = {
        "materials": any(x in rels for x in ["案件材料", "客户", "原始材料", "材料提取"]),
        "cms_flow": any(x in rels for x in ["CMS流转", "meta.json", "案件台账", "立案台账"]),
        "evidence": "证据" in rels,
        "legal_basis": any(x in rels for x in ["律法", "法律依据", "法律意见"]),
        "analysis": any(x in rels for x in ["分析", "刑事辩护", "案件推演", "结构化分析"]),
        "inspection": "巡视" in rels,
        "audit": any(x in rels for x in ["审计", "自检"]),
        "final_doc": any(x in rels for x in ["正式文书", "FINAL", "申请书", "法律意见书草稿"]),
        "raw_multillm": any(x in rels for x in ["原始输出.json", "三LLM", "4通道"]),
    }
    cms = run_cms_guard(root, case_type)
    legal = None
    if run_legal_gate:
        legal = run_legal_doc_gate(find_final_doc(files), find_source_fact(files))
    passed = sum(1 for v in gates.values() if v)
    report = CaseClosedLoopReport(
        schema="PGGArchonCaseClosedLoopReport/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        case_root=str(root),
        case_no=case_no,
        file_count=len(files),
        gates=gates,
        gate_passed=passed,
        gate_total=len(gates),
        closed_loop_score=round(passed / max(len(gates), 1), 4),
        cms_guard=cms,
        legal_doc_gate=legal,
        boundary="Process/evidence closed-loop score only; not legal correctness proof or substitute for lawyer review.",
        sample_files=[str(p.relative_to(root)) for p in files[:40]],
    )
    return asdict(report)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case_root")
    ap.add_argument("--case-type", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--skip-legal-doc-gate", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else None)
    report = evaluate_case(args.case_root, args.case_type, run_legal_gate=not args.skip_legal_doc_gate)
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
