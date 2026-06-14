"""PGG Archon absorption surface for audited APEX-AGI capabilities.

This module turns the local APEX-AGI audit findings into bounded, machine
checkable PGG Archon core capability candidates.  It intentionally absorbs the
usable patterns, not the unsafe runtime side effects: no web server start, no
LLM calls, no gene writes, no external deployment, and no AGI-completion claim.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_APEX_AGI_ROOT = Path("/Users/appleoppa/Desktop/APEX-AGI")
DEFAULT_REPORT_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/pgg-archon-apex-agi-absorption")
DEFAULT_LLM_REVIEW_DIR = Path("/Users/appleoppa/.hermes/hermes-agent/workspace/llm_next_stage_reviews")

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*=\s*[^\s#]+"),
    re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+[a-z0-9._\-]+"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
)


@dataclass(frozen=True)
class AbsorptionCandidate:
    capability_id: str
    source_files: tuple[str, ...]
    absorbed_as: str
    risk: str
    status: str
    rationale: str
    blocked_side_effects: tuple[str, ...]
    verification: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "source_files": list(self.source_files),
            "absorbed_as": self.absorbed_as,
            "risk": self.risk,
            "status": self.status,
            "rationale": self.rationale,
            "blocked_side_effects": list(self.blocked_side_effects),
            "verification": list(self.verification),
        }


@dataclass(frozen=True)
class AbsorptionGateResult:
    gate_name: str
    passed: bool
    severity: str
    details: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "passed": self.passed,
            "severity": self.severity,
            "details": self.details,
        }


CANDIDATE_BLUEPRINTS: tuple[dict[str, Any], ...] = (
    {
        "capability_id": "apex_quality_gate_runner",
        "source_files": ("omega_pipeline/quality_gates.py",),
        "absorbed_as": "PGG Archon pre-merge quality-gate schema and gate-result contract",
        "risk": "low",
        "rationale": "Validation-only code is the safest first absorption layer and constrains later merges.",
        "blocked_side_effects": ("no_shell_execution", "no_git_push", "no_gene_write", "no_external_delivery"),
        "verification": ("plan_completeness", "test_presence", "no_regression", "commit_message", "human_review_required_for_push"),
    },
    {
        "capability_id": "apex_self_healing_strategy_catalog",
        "source_files": ("omega_pipeline/self_healing.py",),
        "absorbed_as": "bounded repair-plan taxonomy for Rust/Python errors, not autonomous patch execution",
        "risk": "medium",
        "rationale": "Diagnosis and strategy metadata are useful; automatic file mutation and rollback DB must stay gated.",
        "blocked_side_effects": ("no_auto_patch", "no_subprocess_repair", "no_rollback_write", "no_unreviewed_code_generation"),
        "verification": ("diagnosis_has_confidence", "strategy_has_preconditions", "patch_requires_tests", "rollback_path_declared"),
    },
    {
        "capability_id": "apex_swarm_coordination_lessons",
        "source_files": ("omega-agi/runtime/src/swarm/mod.rs", "omega-agi/runtime/src/swarm/consensus.rs", "omega-agi/runtime/src/swarm/crdt.rs"),
        "absorbed_as": "coordination invariants: unique ids, lock-release-before-await, CRDT operation semantics",
        "risk": "low",
        "rationale": "The audit exposed concrete concurrency/CRDT failure modes that should become core guardrails.",
        "blocked_side_effects": ("no_actor_runtime_import", "no_network_swarm_start", "no_consensus_daemon"),
        "verification": ("unique_id_entropy", "no_write_lock_held_across_nested_read", "operation_semantics_documented"),
    },
    {
        "capability_id": "apex_local_deployment_safety_profile",
        "source_files": ("web_ui/app.py", "launcher.sh", "requirements.txt"),
        "absorbed_as": "local-only deployment checklist: 127.0.0.1 binding, debug disabled, dependency declaration, health probe",
        "risk": "low",
        "rationale": "Deployment lessons are safe as a checklist and prevent accidental 0.0.0.0/debug exposure.",
        "blocked_side_effects": ("no_server_start", "no_port_kill", "no_env_secret_write"),
        "verification": ("loopback_bind", "debug_false", "health_endpoint_http_200", "dependency_manifest_complete"),
    },
    {
        "capability_id": "apex_runtime_lock_guard",
        "source_files": ("omega-agi/avatar/src/chat.rs", "omega-agi/superpowers/src/boost.rs"),
        "absorbed_as": "Tokio/runtime guardrail: avoid blocking_* locks inside async runtime",
        "risk": "low",
        "rationale": "The CLI panic class is reusable as a PGG Archon runtime safety check.",
        "blocked_side_effects": ("no_runtime_patch_without_test",),
        "verification": ("async_runtime_smoke_test", "panic_signature_regression"),
    },
)


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _source_status(root: Path, files: Sequence[str]) -> str:
    if all((root / item).exists() for item in files):
        return "SOURCE_PRESENT"
    if any((root / item).exists() for item in files):
        return "PARTIAL_SOURCE_PRESENT"
    return "SOURCE_MISSING"


def _scan_secret_indicators(root: Path, relative_files: Sequence[str], *, max_bytes: int = 200_000) -> list[str]:
    hits: list[str] = []
    for rel in relative_files:
        path = root / rel
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:max_bytes]
        except Exception:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(rel)
                break
    return hits


def _latest_successful_model_reviews(review_dir: Path = DEFAULT_LLM_REVIEW_DIR) -> list[str]:
    if not review_dir.exists():
        return []
    paths = sorted(review_dir.glob("*apex_agi_absorption_review*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    ok: list[str] = []
    for path in paths[:12]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("status") == 200:
            provider = str(data.get("provider") or path.name)
            ok.append(f"{provider}:{path}")
    return ok


def build_apex_agi_absorption_candidates(
    *,
    source_root: str | Path = DEFAULT_APEX_AGI_ROOT,
) -> list[dict[str, Any]]:
    """Return audited APEX-AGI capability candidates in PGG Archon schema."""
    root = Path(source_root)
    candidates: list[dict[str, Any]] = []
    for item in CANDIDATE_BLUEPRINTS:
        files = tuple(item["source_files"])
        secret_hits = _scan_secret_indicators(root, files)
        status = _source_status(root, files)
        if secret_hits:
            status = "HOLD_SECRET_REVIEW"
        candidate = AbsorptionCandidate(
            capability_id=item["capability_id"],
            source_files=files,
            absorbed_as=item["absorbed_as"],
            risk=item["risk"],
            status=status,
            rationale=item["rationale"],
            blocked_side_effects=tuple(item["blocked_side_effects"]),
            verification=tuple(item["verification"]),
        ).to_dict()
        candidate["secret_review_hits"] = secret_hits
        candidates.append(candidate)
    return candidates


def run_apex_absorption_quality_gates(
    candidates: Sequence[Mapping[str, Any]],
    *,
    model_reviews: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate PGG Archon safety gates for the absorption candidates."""
    reviews = list(model_reviews) if model_reviews is not None else _latest_successful_model_reviews()
    candidate_list = [dict(item) for item in candidates]
    gates = [
        AbsorptionGateResult(
            "candidate_sources_present",
            all(item.get("status") in {"SOURCE_PRESENT", "PARTIAL_SOURCE_PRESENT"} for item in candidate_list),
            "blocking",
            "all candidates must have at least partial audited source presence",
        ),
        AbsorptionGateResult(
            "no_secret_material_absorbed",
            not any(item.get("secret_review_hits") for item in candidate_list),
            "blocking",
            "source files selected for absorption must not carry obvious token/key material",
        ),
        AbsorptionGateResult(
            "all_candidates_bounded",
            all(item.get("blocked_side_effects") for item in candidate_list),
            "blocking",
            "every absorbed capability must declare blocked side effects",
        ),
        AbsorptionGateResult(
            "no_agi_completion_claim",
            True,
            "blocking",
            "absorption records are capability candidates only and keep AGI completion claim false",
        ),
        AbsorptionGateResult(
            "gpt_or_claude_review_present",
            any("gpt" in item.lower() for item in reviews) or any("claude" in item.lower() for item in reviews),
            "blocking",
            "AGI/evolution absorption requires real GPT or Claude review evidence",
        ),
        AbsorptionGateResult(
            "dual_channel_review_present",
            any("gpt" in item.lower() for item in reviews) and any("claude" in item.lower() for item in reviews),
            "warning",
            "critical absorptions should keep GPT and Claude evidence; warning if one channel failed",
        ),
    ]
    return [gate.to_dict() for gate in gates]


def build_pgg_archon_apex_agi_absorption_surface(
    *,
    source_root: str | Path = DEFAULT_APEX_AGI_ROOT,
    write_report: bool = False,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    model_reviews: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build the read-only absorption surface and optionally write evidence."""
    candidates = build_apex_agi_absorption_candidates(source_root=source_root)
    reviews = list(model_reviews) if model_reviews is not None else _latest_successful_model_reviews()
    gates = run_apex_absorption_quality_gates(candidates, model_reviews=reviews)
    blocking_failures = [item for item in gates if item["severity"] == "blocking" and not item["passed"]]
    warnings = [item for item in gates if item["severity"] == "warning" and not item["passed"]]
    ready = [item for item in candidates if item.get("status") == "SOURCE_PRESENT" and not item.get("secret_review_hits")]
    surface = {
        "schema": "PGGArchonApexAGIAbsorptionSurface/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_root": str(source_root),
        "candidate_count": len(candidates),
        "ready_candidate_count": len(ready),
        "status": "PASS" if not blocking_failures else "HOLD",
        "candidates": candidates,
        "quality_gates": gates,
        "blocking_failures": blocking_failures,
        "warnings": warnings,
        "model_review_evidence": reviews[:8],
        "absorbed_core_patterns": [item["capability_id"] for item in ready],
        "merge_policy": "blueprint_and_gate_absorption_only; no unreviewed external runtime execution",
        "side_effects": "report_write" if write_report else "read_only_absorption_surface",
        "agi_completion_claim": False,
    }
    surface["surface_hash"] = _sha256_obj(surface)
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}_pgg_archon_apex_agi_absorption_surface.json"
        out.write_text(json.dumps(surface, ensure_ascii=False, indent=2), encoding="utf-8")
        surface["report_path"] = str(out)
    return surface


__all__ = [
    "build_apex_agi_absorption_candidates",
    "run_apex_absorption_quality_gates",
    "build_pgg_archon_apex_agi_absorption_surface",
]
