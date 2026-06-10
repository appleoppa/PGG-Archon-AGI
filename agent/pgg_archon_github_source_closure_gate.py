"""GitHub source closure gate for PGG evolution-source evidence.

Boundary:
- evaluates evidence cards supplied by the caller; no network/LLM calls;
- distinguishes official VERIFIED_SOURCE from PARTIAL_SOURCE, REPRO_IMPL,
  SOURCE_ARTIFACT, MISSING, and NOISE;
- never promotes GeneDB rows or claims AGI/ASI capability.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

BOUNDARY = "github_source_closure_gate; no promotion; verified requires bidirectional official closure"
STATUSES = {"VERIFIED_SOURCE", "PARTIAL_SOURCE", "REPRO_IMPL", "SOURCE_ARTIFACT", "MISSING", "NOISE"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _truthy(card: Mapping[str, Any], key: str) -> bool:
    val = card.get(key)
    if isinstance(val, bool):
        return val
    if isinstance(val, (list, tuple, set, dict)):
        return bool(val)
    return str(val or "").strip().lower() in {"true", "yes", "1", "strong", "present"}


def evaluate_github_source_card(card: Mapping[str, Any]) -> dict[str, Any]:
    repo_url = str(card.get("repo_url", "")).strip()
    commit_sha = str(card.get("commit_sha", "")).strip()
    local_only = _truthy(card, "local_only_artifact")
    keyword_only = _truthy(card, "keyword_only_hit")
    fork_or_mirror = _truthy(card, "fork_or_mirror_without_official_proof")
    explicit_unofficial = _truthy(card, "explicit_unofficial_or_inspired_by")
    paper_to_repo = _truthy(card, "paper_to_repo_evidence_strong")
    repo_to_paper = _truthy(card, "repo_to_paper_evidence_strong")
    author_org = _truthy(card, "author_org_match_strong")
    core_paths = card.get("core_content_paths") or []
    timeline = _truthy(card, "timeline_reasonable")
    license_citation = _truthy(card, "license_citation_present")
    noise_excluded = _truthy(card, "noise_exclusion_done")

    veto: list[str] = []
    positive: list[str] = []
    missing: list[str] = []

    if not repo_url and not local_only:
        veto.append("repo_url_missing")
    else:
        positive.append("repo_or_local_artifact_present")
    if not commit_sha and not local_only:
        veto.append("commit_sha_missing")
    else:
        positive.append("commit_or_artifact_hash_present")
    if keyword_only:
        veto.append("keyword_only_hit")
    if fork_or_mirror:
        veto.append("fork_or_mirror_without_official_proof")
    if explicit_unofficial:
        veto.append("explicit_unofficial_or_inspired_by")
    if not paper_to_repo:
        missing.append("paper_to_repo_evidence_strong")
    else:
        positive.append("paper_to_repo_evidence_strong")
    if not repo_to_paper:
        missing.append("repo_to_paper_evidence_strong")
    else:
        positive.append("repo_to_paper_evidence_strong")
    if not author_org:
        missing.append("author_org_match_strong")
    else:
        positive.append("author_org_match_strong")
    if not core_paths:
        missing.append("core_content_paths")
    else:
        positive.append("core_content_paths")
    if not timeline:
        missing.append("timeline_reasonable")
    else:
        positive.append("timeline_reasonable")
    if not license_citation:
        missing.append("license_citation_present")
    else:
        positive.append("license_citation_present")
    if not noise_excluded:
        missing.append("noise_exclusion_done")
    else:
        positive.append("noise_exclusion_done")

    if local_only:
        status = "SOURCE_ARTIFACT"
        confidence = 45
        cap_reason = "local/source artifact only; cannot be official GitHub VERIFIED_SOURCE"
    elif "repo_url_missing" in veto or "commit_sha_missing" in veto:
        status = "MISSING"
        confidence = 10
        cap_reason = "missing repo_url or fixed commit_sha"
    elif keyword_only or fork_or_mirror:
        status = "NOISE"
        confidence = 5
        cap_reason = "keyword/fork/mirror noise without official proof"
    elif explicit_unofficial:
        status = "REPRO_IMPL"
        confidence = 55 + min(20, len(core_paths) * 5)
        cap_reason = "explicitly unofficial/inspired-by/reproduction; useful pattern only"
    elif paper_to_repo and repo_to_paper and author_org and core_paths and timeline and noise_excluded:
        status = "VERIFIED_SOURCE"
        confidence = 90 if license_citation else 85
        cap_reason = "bidirectional official evidence and content closure present"
    elif repo_to_paper or paper_to_repo or core_paths:
        status = "PARTIAL_SOURCE"
        confidence = 50 + min(25, 5 * sum(bool(x) for x in [repo_to_paper, paper_to_repo, author_org, core_paths, timeline, license_citation, noise_excluded]))
        cap_reason = "some evidence present but missing bidirectional official closure"
    else:
        status = "MISSING"
        confidence = 20
        cap_reason = "no substantive closure evidence"

    return {
        "schema": "PGGGitHubSourceClosureEvaluation/v1",
        "created_at": _now(),
        "candidate_id": card.get("candidate_id") or card.get("target_name"),
        "target_name": card.get("target_name"),
        "repo_url": repo_url,
        "commit_sha": commit_sha,
        "status": status,
        "confidence": min(100, confidence),
        "status_cap_reason": cap_reason,
        "positive_evidence": positive,
        "missing_evidence": missing,
        "veto_flags": veto,
        "allowed_use": {
            "VERIFIED_SOURCE": "official source evidence, still needs downstream tests before promotion",
            "PARTIAL_SOURCE": "candidate/research pool only",
            "REPRO_IMPL": "absorb engineering/reproduction patterns only",
            "SOURCE_ARTIFACT": "local/source artifact only",
            "MISSING": "do not absorb",
            "NOISE": "reject",
        }[status],
        "boundary": BOUNDARY,
    }


def evaluate_github_source_cards(cards: Sequence[Mapping[str, Any]], *, output_dir: str | Path | None = None) -> dict[str, Any]:
    evaluations = [evaluate_github_source_card(card) for card in cards]
    counts: dict[str, int] = {}
    for ev in evaluations:
        counts[ev["status"]] = counts.get(ev["status"], 0) + 1
    summary = {
        "schema": "PGGGitHubSourceClosureGate/v1",
        "created_at": _now(),
        "boundary": BOUNDARY,
        "total": len(evaluations),
        "counts": counts,
        "verified_count": counts.get("VERIFIED_SOURCE", 0),
        "evaluations": evaluations,
    }
    if output_dir:
        out_dir = Path(output_dir).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{int(time.time())}_github_source_closure_gate.json"
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["output_path"] = str(path)
    return summary


__all__ = ["BOUNDARY", "STATUSES", "evaluate_github_source_card", "evaluate_github_source_cards"]
