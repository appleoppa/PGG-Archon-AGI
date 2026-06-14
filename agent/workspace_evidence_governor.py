"""Workspace evidence governor for PGG Archon evolution audits.

The governor classifies untracked workspace artifacts into safe audit buckets. It
is deliberately read-only: it never deletes, moves, stages, or rewrites files.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/workspace-governor")

_BUCKET_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("case_or_evolution_report", ("开智", "开智进化", "AGI", "进化", "报告")),
    ("test_residue", ("_test", "test/", "pytest", "cli_test", "quality_evidence_test")),
    ("github_audit_inventory", ("GITHUB_REPO", "github_", "repo_audit", "fusion_audit")),
    ("flow_or_promotion_evidence", ("flow_reward", "meta_evolution", "autonomous_promotion", "promotion")),
    ("desktop_diff_evidence", ("desktop_diff", "z_dashen", "diff")),
)


@dataclass(frozen=True)
class WorkspaceArtifact:
    path: str
    bucket: str
    reason: str
    tracked_action: str
    size_bytes: int | None = None
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "bucket": self.bucket,
            "reason": self.reason,
            "tracked_action": self.tracked_action,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
        }


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_status(repo_root: Path) -> list[str]:
    cp = subprocess.run(["git", "status", "--short"], cwd=str(repo_root), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or "git status failed")
    return [line.strip() for line in cp.stdout.splitlines() if line.strip()]


def _classify(rel_path: str) -> tuple[str, str, str]:
    text = rel_path.lower()
    if not text.startswith("workspace/"):
        return "non_workspace_untracked", "outside workspace scope", "manual_review"
    for bucket, tokens in _BUCKET_RULES:
        for token in tokens:
            if token.lower() in text:
                return bucket, f"matched token: {token}", "keep_unstaged_review"
    return "workspace_unknown", "no bucket rule matched", "manual_review"


def classify_workspace_artifacts(paths: Iterable[str], *, repo_root: str | Path = REPO_ROOT) -> dict[str, Any]:
    root = Path(repo_root)
    artifacts: list[WorkspaceArtifact] = []
    for raw in paths:
        rel = raw.strip()
        if not rel:
            continue
        if rel.startswith("?? "):
            rel = rel[3:].strip()
        rel = rel.strip('"')
        bucket, reason, action = _classify(rel)
        full = root / rel
        artifacts.append(
            WorkspaceArtifact(
                path=rel,
                bucket=bucket,
                reason=reason,
                tracked_action=action,
                size_bytes=full.stat().st_size if full.exists() and full.is_file() else None,
                content_hash=_sha256_file(full) if full.exists() and full.is_file() else None,
            )
        )
    buckets: dict[str, int] = {}
    for artifact in artifacts:
        buckets[artifact.bucket] = buckets.get(artifact.bucket, 0) + 1
    return {
        "schema": "PGGWorkspaceEvidenceGovernor/v1",
        "artifact_count": len(artifacts),
        "bucket_counts": dict(sorted(buckets.items())),
        "artifacts": [a.to_dict() for a in artifacts],
        "side_effects": "read_only_classification",
        "agi_completion_claim": False,
    }


def build_workspace_evidence_governor_report(
    *,
    repo_root: str | Path = REPO_ROOT,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    write_report: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root)
    status_lines = _git_status(root)
    untracked = [line for line in status_lines if line.startswith("?? ")]
    report = classify_workspace_artifacts(untracked, repo_root=root)
    report["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["repo_root"] = str(root)
    report["git_untracked_count"] = len(untracked)
    report["recommendation"] = "Review workspace_unknown and non_workspace_untracked first; keep all artifacts unstaged until classified."
    if write_report:
        out_dir = Path(report_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"workspace_evidence_governor_{int(time.time())}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report_path"] = str(out)
    return report


__all__ = ["build_workspace_evidence_governor_report", "classify_workspace_artifacts"]
