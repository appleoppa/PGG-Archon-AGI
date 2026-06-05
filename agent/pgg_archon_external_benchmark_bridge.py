"""PGG Archon external benchmark bridge and evolution-gain ledger.

This module turns the L1->L2 gap into auditable evidence objects:

1. external benchmark source registry (official/adapted/internal distinction)
2. cross-domain real-task registry with verifier/evidence fields
3. before/after evolution-gain reports over frozen task evidence

Boundary: registry/bridge evidence only. It does not claim official benchmark
scores unless a real official harness result with provenance is ingested.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


BOUNDARY = (
    "Benchmark bridge / cross-domain evidence ledger only; not an official AGI "
    "benchmark pass, not L2 proof, and not full AGI proof. Official/adapted/internal "
    "sources must remain explicitly separated."
)


@dataclass(frozen=True)
class BenchmarkSource:
    source_id: str
    framework: str
    repo: str
    source_type: str  # official_harness | adapted_external | internal_frozen_smoke
    license_note: str
    task_family: str
    sample_count: int | None = None
    metric: str | None = None
    version: str | None = None
    provenance_url: str | None = None
    boundary: str = BOUNDARY

    def __post_init__(self) -> None:
        allowed = {"official_harness", "adapted_external", "internal_frozen_smoke"}
        if self.source_type not in allowed:
            raise ValueError(f"unsupported source_type={self.source_type!r}")


@dataclass(frozen=True)
class CrossDomainTask:
    task_id: str
    domain: str
    title: str
    real_or_synthetic: str
    source_of_truth: str
    input_artifacts: list[str]
    output_artifacts: list[str]
    acceptance_criteria: list[str]
    verifier: str
    status: str
    evidence_paths: list[str] = field(default_factory=list)
    human_review_required: bool = True
    boundary: str = BOUNDARY

    def __post_init__(self) -> None:
        if self.status not in {"PASS", "WATCH", "BLOCKED"}:
            raise ValueError(f"unsupported status={self.status!r}")
        if self.real_or_synthetic not in {"real", "synthetic", "mixed"}:
            raise ValueError(f"unsupported real_or_synthetic={self.real_or_synthetic!r}")


@dataclass(frozen=True)
class EvolutionGainItem:
    task_id: str
    before_status: str
    after_status: str
    before_score: float
    after_score: float
    evidence_path: str
    regression_reason: str = ""

    @property
    def delta(self) -> float:
        return round(float(self.after_score) - float(self.before_score), 6)


@dataclass(frozen=True)
class BridgeReport:
    schema: str
    generated_at: str
    benchmark_sources: list[dict[str, Any]]
    cross_domain_tasks: list[dict[str, Any]]
    evidence_summary: dict[str, Any]
    third_party_judge_policy: dict[str, Any]
    case_0006_review: dict[str, Any]
    boundary: str = BOUNDARY


@dataclass(frozen=True)
class EvolutionGainReport:
    schema: str
    generated_at: str
    status: str
    baseline_label: str
    evolved_label: str
    items: list[dict[str, Any]]
    aggregate: dict[str, Any]
    boundary: str = BOUNDARY


def default_external_benchmark_sources() -> list[BenchmarkSource]:
    """Return a conservative registry learned from public open-source eval tools."""
    return [
        BenchmarkSource(
            "lm_eval_harness",
            "lm-evaluation-harness",
            "EleutherAI/lm-evaluation-harness",
            "official_harness",
            "Use upstream license/dataset terms per task; record task config before scoring.",
            "few-shot LLM benchmarks such as MMLU/GSM8K/BBH when actually run",
            provenance_url="https://github.com/EleutherAI/lm-evaluation-harness",
        ),
        BenchmarkSource(
            "openai_evals",
            "evals",
            "openai/evals",
            "official_harness",
            "Use upstream eval registry and dataset licenses; store eval name/version.",
            "LLM and LLM-system benchmark registry",
            provenance_url="https://github.com/openai/evals",
        ),
        BenchmarkSource(
            "inspect_ai",
            "inspect_ai",
            "UKGovernmentBEIS/inspect_ai",
            "adapted_external",
            "Useful for reproducible LLM-system evals; record task definition hash.",
            "agent/system eval harness",
            provenance_url="https://github.com/UKGovernmentBEIS/inspect_ai",
        ),
        BenchmarkSource(
            "deepeval",
            "deepeval",
            "confident-ai/deepeval",
            "adapted_external",
            "Useful for LLM app metrics; not a general AGI benchmark by itself.",
            "LLM app evaluation framework",
            provenance_url="https://github.com/confident-ai/deepeval",
        ),
        BenchmarkSource(
            "promptfoo",
            "promptfoo",
            "promptfoo/promptfoo",
            "adapted_external",
            "Useful for prompt/agent/RAG regression and red-team CI evidence.",
            "prompt/agent/RAG tests and red teaming",
            provenance_url="https://github.com/promptfoo/promptfoo",
        ),
        BenchmarkSource(
            "pgg_internal_100",
            "pgg_archon_external_benchmark_provider_run.py",
            "local hermes-agent",
            "internal_frozen_smoke",
            "Internal frozen smoke only; never label as official MMLU/GSM8K/BigBench/LegalBench.",
            "logic/tool-use/legal-boundary/long-context/self-boundary internal smoke",
            sample_count=100,
            metric="deterministic short-answer substring match",
        ),
    ]


def case_0006_cross_domain_task(case_root: str | Path) -> CrossDomainTask:
    root = Path(case_root).expanduser()
    final_v2 = root / "正式文书" / "PGG-MS-20260605-0006-民事起诉状_FINAL_v2.md"
    ledger = root / "总结报告" / "PGG-MS-20260605-0006-案件台账.md"
    cms = root / "审计记录" / "PGG-MS-20260605-0006-cms_case_guard_validate.json"
    existing = [str(p) for p in (final_v2, ledger, cms) if p.exists()]
    status = "WATCH"
    return CrossDomainTask(
        task_id="legal_case_0006_final_v2_review",
        domain="legal_real_case",
        title="0006 燕赵财险雇主责任险合同纠纷 FINAL v2 证据化复核",
        real_or_synthetic="real",
        source_of_truth="客户《情况说明》原件/提取版 + 案件台账 + FINAL v2；类案/当事人信息/具体法院仍需人工补正",
        input_artifacts=[str(root / "案件材料")],
        output_artifacts=[str(final_v2), str(ledger)],
        acceptance_criteria=[
            "FINAL v2 保留 15/15 真实事实、0/8 v1 虚假事实自检记录",
            "类案必须继续标注为合理构造示例，外部提交前替换为真实判例",
            "当事人信息与具体基层法院必须标为待补/待核定",
            "CMS BLOCKED/WATCH 状态必须诚实保留，不得改写为 PASS",
        ],
        verifier="read final_v2 + ledger + cms_guard_validate; human lawyer review required before filing",
        status=status,
        evidence_paths=existing,
        human_review_required=True,
    )


def build_bridge_report(
    *,
    case_root: str | Path | None = None,
    extra_tasks: Sequence[CrossDomainTask] = (),
) -> BridgeReport:
    sources = default_external_benchmark_sources()
    tasks: list[CrossDomainTask] = []
    if case_root is not None:
        tasks.append(case_0006_cross_domain_task(case_root))
    tasks.extend(extra_tasks)
    status_counts: dict[str, int] = {}
    domain_counts: dict[str, int] = {}
    evidence_paths: list[str] = []
    for task in tasks:
        status_counts[task.status] = status_counts.get(task.status, 0) + 1
        domain_counts[task.domain] = domain_counts.get(task.domain, 0) + 1
        evidence_paths.extend(task.evidence_paths)
    return BridgeReport(
        schema="PGGArchonExternalBenchmarkBridge/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        benchmark_sources=[asdict(x) for x in sources],
        cross_domain_tasks=[asdict(x) for x in tasks],
        evidence_summary={
            "benchmark_source_count": len(sources),
            "source_types": {t: sum(1 for s in sources if s.source_type == t) for t in sorted({s.source_type for s in sources})},
            "cross_domain_task_count": len(tasks),
            "task_status_counts": status_counts,
            "domain_counts": domain_counts,
            "evidence_path_count": len(evidence_paths),
            "evidence_bundle_hash": hashlib.sha256("\n".join(sorted(evidence_paths)).encode("utf-8")).hexdigest() if evidence_paths else "",
        },
        third_party_judge_policy={
            "provider_id": "mimo_v25_pro_auditor",
            "role": "third_party_benchmark_judge_only",
            "allowed": ["independent benchmark validation", "evidence bundle review", "anti-overclaim audit"],
            "forbidden": ["daily task handling", "case drafting", "ordinary evolution processing", "candidate answer optimization"],
            "reason": "Agnes link is unstable; MiMo is held out as the fixed third-party judge.",
        },
        case_0006_review={
            "status": "WATCH",
            "positive_evidence": ["P0-P7 ledger exists", "FINAL v2 exists", "v1 fact-error correction documented"],
            "open_gaps": ["CMS guard recorded BLOCKED", "constructed cases must be replaced", "party details pending", "specific grassroots court pending"],
            "usable_for_agi_scoring": "real-world landing evidence only at WATCH level until open gaps close",
        },
    )


def compute_evolution_gain(
    *,
    baseline_label: str,
    evolved_label: str,
    items: Iterable[EvolutionGainItem],
) -> EvolutionGainReport:
    rows = list(items)
    if not rows:
        raise ValueError("items must not be empty")
    pass_before = sum(1 for x in rows if x.before_status == "PASS")
    pass_after = sum(1 for x in rows if x.after_status == "PASS")
    before_mean = round(sum(x.before_score for x in rows) / len(rows), 6)
    after_mean = round(sum(x.after_score for x in rows) / len(rows), 6)
    regressions = [x for x in rows if x.delta < 0 or x.after_status == "BLOCKED"]
    status = "PASS" if pass_after > pass_before and not regressions else "WATCH"
    return EvolutionGainReport(
        schema="PGGArchonEvolutionGainReport/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        baseline_label=baseline_label,
        evolved_label=evolved_label,
        items=[{**asdict(x), "delta": x.delta} for x in rows],
        aggregate={
            "task_count": len(rows),
            "pass_before": pass_before,
            "pass_after": pass_after,
            "pass_delta": pass_after - pass_before,
            "score_before_mean": before_mean,
            "score_after_mean": after_mean,
            "score_delta_mean": round(after_mean - before_mean, 6),
            "regression_count": len(regressions),
            "truth_rule": "If evidence_path is missing or only LLM prose exists, keep verdict WATCH.",
        },
    )


def write_json_report(report: BridgeReport | EvolutionGainReport, path: str | Path) -> str:
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="PGG Archon external benchmark bridge report")
    ap.add_argument("--case-root", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    report = build_bridge_report(case_root=args.case_root or None)
    write_json_report(report, args.out)
    print(json.dumps({"status": "OK", "path": args.out, "schema": report.schema}, ensure_ascii=False))


if __name__ == "__main__":
    main()
