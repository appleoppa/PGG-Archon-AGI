"""Hermes Agent 0.14 defect repair helpers.

Implements four low-risk, evidence-first repair mechanisms:

1. subagent_legacy_recovery  — persistent subagent result/artifact index
2. gpt_skill_audit           — deterministic skill quality audit sidecar
3. self_capability_audit     — tool/skill/config capability map
4. dual_skill_gene_evolve    — skill -> gene -> fitness -> update-candidate loop

The module is intentionally conservative: it writes JSON evidence files and
never deletes skills, rewrites user content, or performs external side effects.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from hermes_constants import get_hermes_home


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{int(time.time() * 1000)}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def _safe_read_text(path: Path, limit: int = 200_000) -> str:
    try:
        data = path.read_bytes()[:limit]
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 594 — subagent_legacy_recovery
# ---------------------------------------------------------------------------

def _subagent_dir() -> Path:
    return get_hermes_home() / "logs" / "subagents"


def record_subagent_artifact(
    *,
    task_index: int,
    goal: str,
    status: str,
    summary: Optional[str] = None,
    error: Optional[str] = None,
    api_calls: Optional[int] = None,
    duration_seconds: Optional[float] = None,
    model: Optional[str] = None,
    exit_reason: Optional[str] = None,
    files_read: Optional[List[str]] = None,
    files_written: Optional[List[str]] = None,
    output_tail: Optional[List[Dict[str, Any]]] = None,
    diagnostic_path: Optional[str] = None,
    subagent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a recoverable subagent completion record and update index.

    Called by delegate_tool at every child exit path.  Best-effort by caller;
    this function itself raises only for truly unexpected filesystem errors.
    """
    ts = _now_iso()
    ident_seed = f"{ts}|{task_index}|{goal}|{status}|{summary or error or ''}"
    artifact_id = f"subagent_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{_hash_text(ident_seed)}"
    record = {
        "artifact_id": artifact_id,
        "recorded_at": ts,
        "subagent_id": subagent_id,
        "task_index": task_index,
        "goal": goal,
        "status": status,
        "exit_reason": exit_reason,
        "summary": summary,
        "error": error,
        "api_calls": api_calls,
        "duration_seconds": duration_seconds,
        "model": model,
        "files_read": files_read or [],
        "files_written": files_written or [],
        "output_tail": output_tail or [],
        "diagnostic_path": diagnostic_path,
        "evidence_level": "summary+trace" if output_tail or files_written or diagnostic_path else "summary-only",
    }
    root = _subagent_dir()
    detail_path = root / f"{artifact_id}.json"
    _atomic_write_json(detail_path, record)
    index_row = {
        "artifact_id": artifact_id,
        "recorded_at": ts,
        "task_index": task_index,
        "status": status,
        "exit_reason": exit_reason,
        "detail_path": str(detail_path),
        "summary_preview": (summary or error or "")[:240],
        "files_written_count": len(record["files_written"]),
        "evidence_level": record["evidence_level"],
    }
    _append_jsonl(root / "index.jsonl", index_row)
    return {"ok": True, "artifact_id": artifact_id, "detail_path": str(detail_path), "index_path": str(root / "index.jsonl")}


def subagent_recovery_index(limit: int = 50) -> Dict[str, Any]:
    path = _subagent_dir() / "index.jsonl"
    rows: List[Dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, int(limit)):]:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return {"index_path": str(path), "count": len(rows), "items": rows}


# ---------------------------------------------------------------------------
# 595 — gpt_skill_audit replacement: deterministic quality audit sidecar
# ---------------------------------------------------------------------------

def _skills_dir() -> Path:
    return get_hermes_home() / "skills"


def _iter_skill_files() -> Iterable[Path]:
    base = _skills_dir()
    if not base.exists():
        return []
    return [p for p in base.rglob("SKILL.md") if "/.archive/" not in str(p)]


def _parse_frontmatter(text: str) -> Dict[str, Any]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm: Dict[str, Any] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip().strip('"\'')
    return fm


def _load_usage_records() -> Dict[str, Dict[str, Any]]:
    try:
        from tools import skill_usage
        return skill_usage.load_usage()
    except Exception:
        return {}


def skill_quality_audit(write: bool = True) -> Dict[str, Any]:
    usage = _load_usage_records()
    rows: List[Dict[str, Any]] = []
    seen_names: set[str] = set()
    duplicate_names: set[str] = set()
    name_to_path: Dict[str, str] = {}

    raw_rows: List[Tuple[str, Path, str, Dict[str, Any]]] = []
    for skill_md in _iter_skill_files():
        text = _safe_read_text(skill_md)
        fm = _parse_frontmatter(text)
        name = str(fm.get("name") or skill_md.parent.name)
        if name in seen_names:
            duplicate_names.add(name)
        seen_names.add(name)
        name_to_path.setdefault(name, str(skill_md))
        raw_rows.append((name, skill_md, text, fm))

    for name, skill_md, text, fm in raw_rows:
        rec = usage.get(name, {}) if isinstance(usage.get(name), dict) else {}
        issues: List[str] = []
        score = 100
        if not fm.get("name"):
            score -= 15; issues.append("missing_frontmatter_name")
        if not fm.get("description"):
            score -= 15; issues.append("missing_description")
        if len(text.strip()) < 300:
            score -= 35; issues.append("too_short")
        if name in duplicate_names:
            score -= 20; issues.append("duplicate_name")
        if re.search(r"\b(PR|issue|bug)\s*#?\d+\b", name, re.I):
            score -= 10; issues.append("over_specific_name")
        activity = 0
        for k in ("use_count", "view_count", "patch_count"):
            try:
                activity += int(rec.get(k) or 0)
            except Exception:
                pass
        if activity == 0:
            # Activity telemetry is evidence of use, not evidence of low quality.
            # Keep it visible for audits, but do not lower score or create an
            # evolution gene from this signal alone.
            issues.append("no_recorded_activity")
        state = rec.get("state", "active")
        if state == "stale":
            score -= 10; issues.append("already_stale")
        score = max(0, min(100, score))
        candidate = score <= 70 and not rec.get("pinned")
        rows.append({
            "name": name,
            "path": str(skill_md),
            "score": score,
            "issues": issues,
            "activity_count": activity,
            "state": state,
            "pinned": bool(rec.get("pinned")),
            "stale_candidate": candidate,
            "delete_allowed": False,
            "archive_requires_review": candidate,
        })

    rows.sort(key=lambda r: (r["score"], r["name"]))
    report = {
        "generated_at": _now_iso(),
        "skill_count": len(rows),
        "stale_candidates": sum(1 for r in rows if r["stale_candidate"]),
        "duplicate_names": sorted(duplicate_names),
        "rules": {
            "delete_allowed": False,
            "stale_formula": "low_score + evidence + review; score alone never deletes",
        },
        "items": rows,
    }
    if write:
        _atomic_write_json(_skills_dir() / ".quality_audit.json", report)
    return report


# ---------------------------------------------------------------------------
# 596 — self_capability_audit
# ---------------------------------------------------------------------------

def self_capability_audit(write: bool = True) -> Dict[str, Any]:
    tools: List[Dict[str, Any]] = []
    try:
        from tools.registry import discover_builtin_tools, registry
        discover_builtin_tools()
        for name in registry.get_all_tool_names():
            spec = registry.get_entry(name)
            tools.append({
                "name": name,
                "toolset": getattr(spec, "toolset", None),
                "available": True,
            })
    except Exception as exc:
        tools.append({"name": "<registry_unavailable>", "available": False, "error": str(exc)})

    skills = []
    for skill_md in _iter_skill_files():
        text = _safe_read_text(skill_md, limit=8000)
        fm = _parse_frontmatter(text)
        skills.append({
            "name": str(fm.get("name") or skill_md.parent.name),
            "path": str(skill_md),
            "description": str(fm.get("description") or "")[:300],
        })

    providers: List[Dict[str, Any]] = []
    try:
        from hermes_cli.config import load_config
        cfg = load_config()
        prov = cfg.get("providers") or {}
        if isinstance(prov, dict):
            for name, p in sorted(prov.items()):
                if isinstance(p, dict):
                    providers.append({
                        "name": name,
                        "model": p.get("model"),
                        "base_url": p.get("base_url"),
                        "api_mode": p.get("api_mode"),
                        "key_configured": bool(os.getenv(str(p.get("api_key_env") or ""))),
                    })
    except Exception as exc:
        providers.append({"name": "<config_unavailable>", "error": str(exc)})

    report = {
        "generated_at": _now_iso(),
        "tool_count": len([t for t in tools if t.get("available")]),
        "skill_count": len(skills),
        "provider_count": len(providers),
        "tools": tools,
        "skills": skills,
        "providers": providers,
        "gaps": _capability_gaps(tools, skills, providers),
        "rule": "能力声明 = 工具可用性 + 技能存在 + 历史/配置证据 + 当前权限边界",
    }
    if write:
        _atomic_write_json(get_hermes_home() / "capability_map.json", report)
    return report


def _capability_gaps(tools: List[Dict[str, Any]], skills: List[Dict[str, Any]], providers: List[Dict[str, Any]]) -> List[str]:
    names = {t.get("name") for t in tools}
    skill_names = {s.get("name") for s in skills}
    gaps: List[str] = []
    if "delegate_task" not in names:
        gaps.append("delegation_tool_missing")
    if "skill_view" not in names and "skills_list" not in names:
        gaps.append("skill_read_tools_missing")
    if not skill_names:
        gaps.append("no_active_skills_found")
    if not providers:
        gaps.append("no_configured_providers_found")
    return gaps


# ---------------------------------------------------------------------------
# 597 — dual_skill_gene_evolve
# ---------------------------------------------------------------------------

def dual_skill_gene_evolve(write: bool = True) -> Dict[str, Any]:
    audit = skill_quality_audit(write=True)
    genes: List[Dict[str, Any]] = []
    for item in audit.get("items", []):
        issues = item.get("issues") or []
        material_issues = [i for i in issues if i != "no_recorded_activity"]
        if not material_issues:
            continue
        fitness = round((100 - int(item.get("score", 0))) / 100, 3)
        action = "review_and_patch" if item.get("score", 100) >= 40 else "review_for_archive_or_merge"
        genes.append({
            "gene_id": f"skill_gene_{_hash_text(item['name'] + '|'.join(material_issues))}",
            "source_skill": item["name"],
            "source_path": item["path"],
            "issues": material_issues,
            "audit_observations": issues,
            "fitness": fitness,
            "recommended_action": action,
            "mutation_allowed": False,
            "requires_evidence": ["read_skill", "patch_or_merge_plan", "post_update_validation"],
        })
    report = {
        "generated_at": _now_iso(),
        "gene_count": len(genes),
        "loop": "skill -> gene -> fitness -> skill_update_candidate -> validation",
        "mutation_policy": "report-only by default; no skill rewrite without explicit patch + validation",
        "genes": genes,
    }
    if write:
        _atomic_write_json(_skills_dir() / ".gene_evolution.json", report)
    return report


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "subagent_recovery_index",
                "skill_quality_audit",
                "self_capability_audit",
                "dual_skill_gene_evolve",
                "all",
            ],
            "description": "Which Hermes Agent 0.14 defect repair audit to run.",
        },
        "write": {"type": "boolean", "description": "Write evidence sidecar files (default true)."},
        "limit": {"type": "integer", "description": "Limit for recovery index rows."},
    },
    "required": ["action"],
}


def hermes_agent_014_defect_tool(args: Dict[str, Any], **_kw) -> Dict[str, Any]:
    action = str(args.get("action") or "all")
    write = bool(args.get("write", True))
    if action == "subagent_recovery_index":
        return subagent_recovery_index(limit=int(args.get("limit") or 50))
    if action == "skill_quality_audit":
        return skill_quality_audit(write=write)
    if action == "self_capability_audit":
        return self_capability_audit(write=write)
    if action == "dual_skill_gene_evolve":
        return dual_skill_gene_evolve(write=write)
    if action == "all":
        return {
            "subagent_recovery": subagent_recovery_index(limit=int(args.get("limit") or 50)),
            "skill_quality": skill_quality_audit(write=write),
            "capability": self_capability_audit(write=write),
            "gene_evolution": dual_skill_gene_evolve(write=write),
        }
    return {"error": f"unknown action: {action}"}


from tools.registry import registry

registry.register(
    name="hermes_agent_014_defects",
    toolset="skills",
    schema=SCHEMA,
    handler=hermes_agent_014_defect_tool,
    emoji="🧬",
)
