"""APEX Gene Principle Ontology (GPO) derived from Omega static learning.

GPO is a read-only ontology surface. It absorbs Omega's research-principle
vocabulary and static class-distribution ideas without importing, executing, or
trusting Omega runtime code.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

_DEFAULT_OMEGA_PATH = Path.home() / ".hermes" / "workspace" / "github_repos" / "omega"

PRINCIPLES: list[Dict[str, Any]] = [
    {"id": "P-ABSTRACTION", "name": "abstraction", "axis": "representation", "keywords": ["abstraction", "abstract", "hierarchy", "level"]},
    {"id": "P-COMPRESSION", "name": "compression", "axis": "information", "keywords": ["compression", "compress", "compressibility", "bottleneck"]},
    {"id": "P-ENTROPY", "name": "entropy", "axis": "uncertainty", "keywords": ["entropy", "randomness", "uncertainty", "noise"]},
    {"id": "P-BIAS-VARIANCE", "name": "bias_variance", "axis": "generalization", "keywords": ["bias", "variance", "regularization", "overfit"]},
    {"id": "P-DIRECTIONALITY", "name": "directionality", "axis": "geometry", "keywords": ["direction", "directional", "boundary", "gradient"]},
    {"id": "P-DISCRETE-CONTINUOUS", "name": "discrete_continuous", "axis": "representation", "keywords": ["discrete", "continuous", "hybrid", "quantization"]},
    {"id": "P-SIMILARITY", "name": "similarity", "axis": "relation", "keywords": ["similarity", "distance", "neighbor", "knn", "attention"]},
    {"id": "P-ADAPTATION", "name": "adaptation", "axis": "control", "keywords": ["adaptive", "adaptation", "dynamic", "feedback"]},
    {"id": "P-ENSEMBLE", "name": "ensemble", "axis": "aggregation", "keywords": ["ensemble", "bagging", "forest", "boosting", "stacking"]},
    {"id": "P-MODULARITY", "name": "modularity", "axis": "architecture", "keywords": ["module", "modular", "component", "interface"]},
    {"id": "P-COUNTERFACTUAL", "name": "counterfactual", "axis": "verification", "keywords": ["counterfactual", "shadow", "replay", "ablation"]},
    {"id": "P-HOMEOSTASIS", "name": "homeostasis", "axis": "stability", "keywords": ["homeostasis", "stability", "rollback", "drift"]},
]

_RISK_MARKERS = ("exec(", "eval(", "os.remove", "anthropic", "messages.create", "ThreadPoolExecutor", "fetch_", "torch")


def _safe_repo_root(path: Path | None = None) -> Path:
    root = (path or _DEFAULT_OMEGA_PATH).expanduser().resolve()
    workspace = (Path.home() / ".hermes" / "workspace").resolve()
    try:
        root.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("Omega static scan must stay under ~/.hermes/workspace") from exc
    return root


def tag_text(text: str) -> list[str]:
    lower = str(text or "").lower()
    tags = []
    for principle in PRINCIPLES:
        if any(keyword in lower for keyword in principle["keywords"]):
            tags.append(principle["id"])
    return sorted(set(tags))


def tag_candidate(candidate: Mapping[str, Any]) -> list[str]:
    joined = " ".join(str(candidate.get(key) or "") for key in ("id", "name", "title", "summary", "topic", "decision"))
    return tag_text(joined)


def coverage(candidates: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    all_ids = {item["id"] for item in PRINCIPLES}
    seen: set[str] = set()
    count = 0
    for candidate in candidates:
        count += 1
        seen.update(tag_candidate(candidate))
    return {
        "schema": "ApexGPOCoverage/v1",
        "candidate_count": count,
        "covered_count": len(seen),
        "principle_count": len(all_ids),
        "coverage_ratio": round(len(seen) / max(1, len(all_ids)), 4),
        "missing_principles": sorted(all_ids - seen),
        "side_effects": "read_only_report",
    }


def diversity(candidate_a: Mapping[str, Any], candidate_b: Mapping[str, Any]) -> float:
    a = set(tag_candidate(candidate_a))
    b = set(tag_candidate(candidate_b))
    if not a and not b:
        return 0.0
    return round(1.0 - (len(a & b) / max(1, len(a | b))), 4)


def scan_omega_static(repo_path: Path | None = None) -> Dict[str, Any]:
    """Scan Omega statically. No import, no exec, no network."""
    root = _safe_repo_root(repo_path)
    if not root.exists():
        return {"schema": "ApexOmegaStaticScan/v1", "status": "MISSING", "repo_exists": False, "side_effects": "read_only_report"}
    py_files = [p for p in root.rglob("*.py") if ".git" not in p.parts and "__pycache__" not in p.parts and "egg-info" not in p.parts]
    class_tags: Dict[str, int] = {}
    risk_files = []
    class_count = 0
    parse_errors = 0
    for path in py_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        markers = [marker for marker in _RISK_MARKERS if marker in text]
        if markers:
            risk_files.append({"file": str(path.relative_to(root)), "markers": markers[:8]})
        try:
            tree = ast.parse(text)
        except SyntaxError:
            parse_errors += 1
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_count += 1
                for tag in tag_text(node.name):
                    class_tags[tag] = class_tags.get(tag, 0) + 1
    return {
        "schema": "ApexOmegaStaticScan/v1",
        "status": "PASS",
        "repo_exists": True,
        "py_file_count": len(py_files),
        "class_count": class_count,
        "parse_errors": parse_errors,
        "tag_counts": class_tags,
        "risk_file_count": len(risk_files),
        "risk_files": risk_files[:20],
        "runtime_allowed": False,
        "side_effects": "read_only_report",
    }


def build_gpo_report(repo_path: Path | None = None) -> Dict[str, Any]:
    scan = scan_omega_static(repo_path)
    return {
        "schema": "ApexGenePrincipleOntologyReport/v1",
        "status": "PASS" if scan.get("status") in {"PASS", "MISSING"} else "WATCH",
        "principle_count": len(PRINCIPLES),
        "axes": sorted({item["axis"] for item in PRINCIPLES}),
        "principles": [{"id": item["id"], "name": item["name"], "axis": item["axis"]} for item in PRINCIPLES],
        "omega_static_scan": scan,
        "runtime_allowed": False,
        "absorbed_as": "reference_only_static_ontology",
        "side_effects": "read_only_report",
    }


__all__ = ["PRINCIPLES", "build_gpo_report", "coverage", "diversity", "scan_omega_static", "tag_candidate", "tag_text"]
