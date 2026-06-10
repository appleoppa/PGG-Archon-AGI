"""PGG local benchmark, gene fusion, and reflexion discovery gates.

Boundary:
- deterministic local-only evaluation;
- no network, no LLM calls, no external code execution;
- no GeneDB writes by this module;
- benchmark is a mini-suite process smoke, not paper benchmark reproduction.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

BOUNDARY = "local deterministic mini-benchmark and candidate gates; no external benchmark/parity/AGI claim; no GeneDB writes"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _has(v: Any) -> bool:
    if isinstance(v, bool): return v
    if isinstance(v, (list, tuple, dict, set)): return bool(v)
    return bool(str(v or "").strip())


def _hash_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def gepa_prompt_evolution_mini_benchmark(packet: Mapping[str, Any]) -> dict[str, Any]:
    """GEPA-inspired mini-suite: select best prompt variant via deterministic validation cases.

    Each case may provide required_terms and forbidden_terms. A variant passes a case when
    its text includes all required terms and none of the forbidden terms. This tests the
    *process shape* of baseline→reflection→variants→holdout metric→selection, not GEPA's
    official algorithm or paper scores.
    """
    baseline = str(packet.get("baseline_prompt", ""))
    variants = packet.get("candidate_variants") or []
    cases = packet.get("validation_cases") or []
    reflective_feedback = packet.get("reflective_feedback") or []
    errors: list[str] = []
    warnings: list[str] = []
    if not baseline: errors.append("missing_baseline_prompt")
    if not isinstance(variants, Sequence) or isinstance(variants, (str, bytes)) or len(variants) < 2:
        errors.append("need_at_least_2_candidate_variants")
    if not isinstance(cases, Sequence) or isinstance(cases, (str, bytes)) or len(cases) < 3:
        errors.append("need_at_least_3_validation_cases")
    if not reflective_feedback:
        warnings.append("missing_reflective_feedback")

    def score(text: str) -> tuple[int, list[str]]:
        passed = 0; failed=[]
        lo = text.lower()
        for case in cases if isinstance(cases, Sequence) else []:
            if not isinstance(case, Mapping):
                failed.append("case_not_mapping"); continue
            req=[str(x).lower() for x in case.get("required_terms", [])]
            forb=[str(x).lower() for x in case.get("forbidden_terms", [])]
            ok=all(r in lo for r in req) and not any(f in lo for f in forb)
            if ok: passed += 1
            else: failed.append(str(case.get("id", "unnamed")))
        return passed, failed

    baseline_score, baseline_failed = score(baseline)
    variant_results=[]
    for idx,v in enumerate(variants if isinstance(variants, Sequence) and not isinstance(variants, (str, bytes)) else []):
        text=str(v.get("prompt", v) if isinstance(v, Mapping) else v)
        sc, failed=score(text)
        complexity=len(text)
        variant_results.append({"index":idx,"score":sc,"failed":failed,"complexity":complexity,"hash":hashlib.sha256(text.encode()).hexdigest()[:16]})
    best=max(variant_results, key=lambda r:(r["score"], -r["complexity"]), default=None)
    passed = not errors and best is not None and best["score"] > baseline_score
    return {
        "schema":"PGGGEPApromptEvolutionMiniBenchmark/v1","created_at":_now(),"status":"PASS" if passed else "BLOCK",
        "baseline_score":baseline_score,"baseline_failed":baseline_failed,"best_variant":best,
        "variant_results":variant_results,"errors":errors,"warnings":warnings,
        "benchmark_regression_passed":passed,"official_gepa_reproduction":False,"boundary":BOUNDARY,
    }


def coral_parallel_workspace_mini_benchmark(packet: Mapping[str, Any]) -> dict[str, Any]:
    """CORAL-inspired mini-suite: deterministic isolated workspace merge simulation."""
    agents = packet.get("agents") or []
    workspaces = packet.get("workspaces") or []
    experiments = packet.get("experiments") or []
    errors=[]; warnings=[]; metrics=[]
    if not isinstance(agents, Sequence) or isinstance(agents,(str,bytes)) or len(agents)<2: errors.append("need_at_least_2_agents")
    if not isinstance(workspaces, Sequence) or isinstance(workspaces,(str,bytes)) or len(workspaces)<2: errors.append("need_at_least_2_workspaces")
    if len(set(map(str,workspaces))) != len(workspaces) if isinstance(workspaces, Sequence) and not isinstance(workspaces,(str,bytes)) else False:
        errors.append("workspaces_not_unique")
    if not isinstance(experiments, Sequence) or isinstance(experiments,(str,bytes)) or len(experiments)<2: errors.append("need_at_least_2_experiments")
    if packet.get("shared_workspace_mutation") is True: errors.append("shared_workspace_mutation_not_allowed")
    passing=[]
    for exp in experiments if isinstance(experiments, Sequence) and not isinstance(experiments,(str,bytes)) else []:
        if not isinstance(exp, Mapping): continue
        if exp.get("regression_passed") is True and float(exp.get("score_delta", 0) or 0) > 0:
            passing.append(exp)
    best=max(passing, key=lambda x:(float(x.get("score_delta",0)), -float(x.get("complexity_delta",0) or 0)), default=None)
    if not best: errors.append("no_positive_regression_passing_experiment")
    if not _has(packet.get("cross_agent_audit")): errors.append("missing_cross_agent_audit")
    if not _has(packet.get("conflict_resolution")): errors.append("missing_conflict_resolution")
    metrics.extend([f"agents:{len(agents) if isinstance(agents, Sequence) and not isinstance(agents,(str,bytes)) else 0}", f"workspaces:{len(workspaces) if isinstance(workspaces, Sequence) and not isinstance(workspaces,(str,bytes)) else 0}"])
    return {"schema":"PGGCORALParallelWorkspaceMiniBenchmark/v1","created_at":_now(),"status":"PASS" if not errors else "BLOCK", "selected_experiment":best, "metrics":metrics, "errors":errors, "warnings":warnings, "benchmark_regression_passed":not errors, "official_coral_reproduction":False, "boundary":BOUNDARY}


def gene_fusion_synergy_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Validate bounded gene fusion by measured synergy, not arbitrary multipliers."""
    parents = packet.get("parents") or []
    offspring = packet.get("offspring") or {}
    errors=[]; warnings=[]
    if not isinstance(parents, Sequence) or isinstance(parents,(str,bytes)) or len(parents)<2: errors.append("need_at_least_2_parent_genes")
    parent_scores=[]
    for p in parents if isinstance(parents, Sequence) and not isinstance(parents,(str,bytes)) else []:
        if isinstance(p, Mapping) and "score" in p: parent_scores.append(float(p.get("score") or 0))
        else: errors.append("parent_missing_score")
    offspring_score=float(offspring.get("score", 0) or 0) if isinstance(offspring, Mapping) else 0.0
    complexity_penalty=float(packet.get("complexity_penalty",0) or 0)
    harmrate_penalty=float(packet.get("harmrate_penalty",0) or 0)
    synergy=offspring_score - (max(parent_scores) if parent_scores else 0.0) - complexity_penalty - harmrate_penalty
    if packet.get("uses_arbitrary_multiplier") is True: errors.append("arbitrary_multiplier_not_allowed")
    if synergy <= 0: errors.append("synergy_not_positive_after_penalties")
    if not _has(packet.get("regression_evidence")): errors.append("missing_regression_evidence")
    if not _has(packet.get("rollback_plan")): errors.append("missing_rollback_plan")
    return {"schema":"PGGGeneFusionSynergyGate/v1","created_at":_now(),"status":"PASS" if not errors else "BLOCK", "synergy":synergy,"parent_scores":parent_scores,"offspring_score":offspring_score,"errors":errors,"warnings":warnings,"fusion_allowed":not errors,"boundary":BOUNDARY}


def reflexion_discovery_gate(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Convert task traces into candidate genes with evidence; never auto-promote."""
    traces=packet.get("traces") or []
    errors=[]; warnings=[]; candidates=[]
    if not isinstance(traces, Sequence) or isinstance(traces,(str,bytes)) or len(traces)<2: errors.append("need_at_least_2_traces")
    for idx,tr in enumerate(traces if isinstance(traces, Sequence) and not isinstance(traces,(str,bytes)) else []):
        if not isinstance(tr, Mapping): continue
        if not _has(tr.get("observation")) or not _has(tr.get("lesson")):
            warnings.append(f"trace_{idx}_missing_observation_or_lesson"); continue
        cid="candidate_reflexion_"+hashlib.sha256((str(tr.get('observation'))+str(tr.get('lesson'))).encode()).hexdigest()[:12]
        candidates.append({
            "type":"apex_gene_candidate","id":cid,"category":"reflexion_discovery",
            "signals_match":tr.get("signals_match",[]),"preconditions":tr.get("preconditions",[]),
            "strategy":tr.get("strategy",[str(tr.get("lesson"))]),"constraints":tr.get("constraints",{}),
            "validation":tr.get("validation",[]),"origin":"pgg_reflexion_discovery_gate","status":"candidate",
            "evidence_hash":_hash_obj(tr)
        })
    if not candidates: errors.append("no_candidate_gene_extracted")
    if packet.get("auto_promote") is True: errors.append("auto_promote_not_allowed")
    return {"schema":"PGGReflexionDiscoveryGate/v1","created_at":_now(),"status":"PASS" if not errors else "BLOCK", "candidate_count":len(candidates),"candidates":candidates,"errors":errors,"warnings":warnings,"promotion_performed":False,"boundary":BOUNDARY}


def evaluate_all(packet: Mapping[str, Any], *, output_dir: str|Path|None=None) -> dict[str, Any]:
    sections={
        "gepa_benchmark":gepa_prompt_evolution_mini_benchmark(packet.get("gepa_benchmark",{})),
        "coral_benchmark":coral_parallel_workspace_mini_benchmark(packet.get("coral_benchmark",{})),
        "gene_fusion":gene_fusion_synergy_gate(packet.get("gene_fusion",{})),
        "reflexion_discovery":reflexion_discovery_gate(packet.get("reflexion_discovery",{})),
    }
    blocked=[k for k,v in sections.items() if v.get("status")!="PASS"]
    out={"schema":"PGGBenchmarkAndGeneGates/v1","created_at":_now(),"status":"PASS" if not blocked else "BLOCK","blocked":blocked,"sections":sections,"boundary":BOUNDARY,"promotion_performed":False}
    if output_dir:
        d=Path(output_dir).expanduser(); d.mkdir(parents=True, exist_ok=True)
        path=d/f"{int(time.time())}_benchmark_gene_gates.json"; path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8'); out['output_path']=str(path)
    return out

__all__=["gepa_prompt_evolution_mini_benchmark","coral_parallel_workspace_mini_benchmark","gene_fusion_synergy_gate","reflexion_discovery_gate","evaluate_all"]
