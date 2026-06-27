"""APEX Gene Principle Ontology (GPO) derived from omega-agi-supremacy static learning.

GPO is a read-only ontology surface. It absorbs the omega-agi-supremacy
architecture vocabulary and static module-distribution ideas without importing,
executing, installing, or trusting runtime code from that repository.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

_DEFAULT_SOURCE_REPO = "omega-agi-supremacy"
_DEFAULT_SOURCE_PATH = Path.home() / ".hermes" / "workspace" / "github_repos" / _DEFAULT_SOURCE_REPO
# Backward-compatible alias: old omega repository has been retired/deleted.
_DEFAULT_OMEGA_PATH = _DEFAULT_SOURCE_PATH

PRINCIPLES: list[Dict[str, Any]] = [
    {"id": "P-SCHEDULING", "name": "priority_scheduling", "axis": "runtime", "keywords": ["scheduler", "priority", "deadline", "task", "queue"]},
    {"id": "P-MEMORY", "name": "memory_efficiency", "axis": "runtime", "keywords": ["memory", "pool", "cache", "session", "context"]},
    {"id": "P-CAPABILITY-SECURITY", "name": "capability_security", "axis": "security", "keywords": ["capability", "ring", "security", "permission", "scope"]},
    {"id": "P-SANDBOX", "name": "sandbox_isolation", "axis": "security", "keywords": ["sandbox", "wasm", "isolation", "runtime", "actor"]},
    {"id": "P-SWARM-CONSENSUS", "name": "swarm_consensus", "axis": "coordination", "keywords": ["swarm", "consensus", "crdt", "coordinator", "agent"]},
    {"id": "P-HEALTH-MONITOR", "name": "health_monitoring", "axis": "observability", "keywords": ["health", "snapshot", "throughput", "alert", "monitor"]},
    {"id": "P-SELF-HEALING", "name": "self_healing", "axis": "resilience", "keywords": ["self_heal", "healing", "repair", "degradation", "rollback"]},
    {"id": "P-QUALITY-GATE", "name": "industrial_quality_gate", "axis": "verification", "keywords": ["gate", "cmmi", "blocking", "warning", "quality"]},
    {"id": "P-TEST-VERIFICATION", "name": "test_verification", "axis": "verification", "keywords": ["test", "pytest", "cargo test", "verification", "regression"]},
    {"id": "P-FORMULA-SENSITIVITY", "name": "formula_sensitivity", "axis": "diagnosis", "keywords": ["formula", "sensitivity", "weakest", "score", "metric"]},
    {"id": "P-PIPELINE", "name": "three_phase_pipeline", "axis": "process", "keywords": ["pipeline", "planning", "execution", "audit", "phase"]},
    {"id": "P-EVOLUTION", "name": "bounded_evolution", "axis": "evolution", "keywords": ["evolution", "improvement", "candidate", "promotion", "fitness"]},
]

_RISK_MARKERS = (
    "subprocess",
    "os.system",
    "exec(",
    "eval(",
    "requests.",
    "urllib",
    "openai",
    "anthropic",
    "git push",
    "cargo build",
    "cargo test",
    "os.remove",
    "shutil.rmtree",
)


def _safe_repo_root(path: Path | None = None) -> Path:
    root = (path or _DEFAULT_SOURCE_PATH).expanduser().resolve()
    workspace = (Path.home() / ".hermes" / "workspace").resolve()
    try:
        root.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("GPO static scan must stay under ~/.hermes/workspace") from exc
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
    """Scan omega-agi-supremacy statically. No import, no exec, no network."""
    root = _safe_repo_root(repo_path)
    if not root.exists():
        return {
            "schema": "ApexOmegaStaticScan/v2",
            "status": "MISSING",
            "source_repo": _DEFAULT_SOURCE_REPO,
            "repo_exists": False,
            "runtime_allowed": False,
            "side_effects": "read_only_report",
        }
    source_repo = root.name
    source_head = None
    git_head = root / ".git" / "HEAD"
    try:
        if git_head.exists():
            head = git_head.read_text(encoding="utf-8", errors="ignore").strip()
            if head.startswith("ref:"):
                ref = root / ".git" / head.split(" ", 1)[1]
                if ref.exists():
                    source_head = ref.read_text(encoding="utf-8", errors="ignore").strip()
            else:
                source_head = head
    except OSError:
        source_head = None

    code_files = [
        p
        for p in root.rglob("*")
        if p.is_file()
        and ".git" not in p.parts
        and "__pycache__" not in p.parts
        and p.suffix in {".py", ".rs", ".md", ".toml", ".yaml", ".yml"}
    ]
    py_files = [p for p in code_files if p.suffix == ".py"]
    rs_files = [p for p in code_files if p.suffix == ".rs"]
    md_files = [p for p in code_files if p.suffix.lower() == ".md"]
    tag_counts: Dict[str, int] = {}
    axis_counts: Dict[str, int] = {}
    risk_files = []
    class_count = 0
    function_count = 0
    parse_errors = 0
    for path in code_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        markers = [marker for marker in _RISK_MARKERS if marker.lower() in text.lower()]
        if markers:
            risk_files.append({"file": str(path.relative_to(root)), "markers": markers[:8]})
        tags = tag_text(f"{path.name} {text[:50000]}")
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            axis = next((item["axis"] for item in PRINCIPLES if item["id"] == tag), "unknown")
            axis_counts[axis] = axis_counts.get(axis, 0) + 1
        if path.suffix == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                parse_errors += 1
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_count += 1
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    function_count += 1
    return {
        "schema": "ApexOmegaStaticScan/v2",
        "status": "PASS",
        "source_repo": source_repo,
        "source_head": source_head,
        "repo_exists": True,
        "scanned_file_count": len(code_files),
        "py_file_count": len(py_files),
        "rs_file_count": len(rs_files),
        "md_file_count": len(md_files),
        "class_count": class_count,
        "function_count": function_count,
        "parse_errors": parse_errors,
        "tag_counts": tag_counts,
        "axis_counts": axis_counts,
        "risk_file_count": len(risk_files),
        "risk_files": risk_files[:30],
        "runtime_allowed": False,
        "source_policy": "reference_only_static_knowledge",
        "side_effects": "read_only_report",
    }


def build_gpo_report(repo_path: Path | None = None) -> Dict[str, Any]:
    scan = scan_omega_static(repo_path)
    return {
        "schema": "ApexGenePrincipleOntologyReport/v2",
        "status": "PASS" if scan.get("status") in {"PASS", "MISSING"} else "WATCH",
        "source_repo": scan.get("source_repo", _DEFAULT_SOURCE_REPO),
        "source_policy": "reference_only_static_knowledge",
        "principle_count": len(PRINCIPLES),
        "axes": sorted({item["axis"] for item in PRINCIPLES}),
        "principles": [{"id": item["id"], "name": item["name"], "axis": item["axis"]} for item in PRINCIPLES],
        "omega_static_scan": scan,
        "runtime_allowed": False,
        "absorbed_as": "reference_only_static_ontology",
        "side_effects": "read_only_report",
    }


__all__ = ["PRINCIPLES", "build_gpo_report", "coverage", "diversity", "scan_omega_static", "tag_candidate", "tag_text"]
