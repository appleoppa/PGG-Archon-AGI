"""PGG Archon human approval token schema gate.

Boundary: creates and validates an auditable human approval token for a future
main-worktree patch transaction. It never applies patches, commits, mutates
GeneDB, calls providers, or treats token creation as approval execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

TOKEN_SCHEMA = "PGGArchonHumanApprovalToken/v1"
VALIDATION_SCHEMA = "PGGArchonHumanApprovalTokenValidation/v1"
APPROVAL_PURPOSE = "approved_main_patch_transaction"
REQUIRED_BOUNDARY_ACKS = (
    "reviewed_dry_run_result",
    "accepts_target_files",
    "understands_mutation_scope",
    "requires_rollback_package",
    "no_genedb_promotion_by_token",
    "no_full_agi_claim",
)


@dataclass(frozen=True)
class HumanApprovalTokenValidation:
    schema: str
    generated_at: str
    status: str
    token_path: str
    dry_run_result: str
    repo_head: str | None
    target_files: list[str]
    checks: dict[str, bool]
    blockers: list[str]
    token_hash: str | None
    next_action: str
    boundary: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {p}")
    return data


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).expanduser().read_bytes()).hexdigest()


def _canonical_hash(payload: dict[str, Any]) -> str:
    material = {k: v for k, v in payload.items() if k != "token_hash"}
    blob = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def build_human_approval_token(
    *,
    dry_run_result: str | Path,
    approver_id: str,
    repo_head: str,
    approval_statement: str,
    expires_at: str | None = None,
) -> dict[str, Any]:
    """Build a signed-by-hash approval token payload.

    The token is intentionally explicit rather than implicit: it binds the
    approver statement to the exact dry-run result sha256, repo head, target
    files, and boundary acknowledgements. The hash is integrity evidence, not a
    cryptographic identity signature.
    """
    dry_path = Path(dry_run_result).expanduser()
    dry = _load_json(dry_path)
    now = datetime.now(timezone.utc).isoformat()
    token: dict[str, Any] = {
        "schema": TOKEN_SCHEMA,
        "created_at": now,
        "expires_at": expires_at,
        "purpose": APPROVAL_PURPOSE,
        "approver": {"id": approver_id, "kind": "human"},
        "approval_statement": approval_statement,
        "dry_run_result": str(dry_path),
        "dry_run_sha256": _sha256_file(dry_path),
        "dry_run_status": dry.get("status"),
        "repo_head": repo_head,
        "target_files": list(dry.get("target_files") or []),
        "required_boundary_acknowledgements": list(REQUIRED_BOUNDARY_ACKS),
        "approval_scope": {
            "allows": ["future gated main patch transaction review"],
            "forbids": [
                "automatic git apply without transaction gate",
                "automatic commit without transaction gate",
                "GeneDB promotion",
                "provider audit fabrication",
                "full AGI claim",
            ],
        },
        "boundary": "Approval token only; no patch application, no commit, no GeneDB mutation, no provider calls, no full AGI proof.",
    }
    token["token_hash"] = _canonical_hash(token)
    return token


def validate_human_approval_token(*, token_path: str | Path, dry_run_result: str | Path | None = None, repo_head: str | None = None) -> HumanApprovalTokenValidation:
    path = Path(token_path).expanduser()
    token = _load_json(path)
    dry_path = Path(dry_run_result or token.get("dry_run_result") or "").expanduser()
    dry = _load_json(dry_path) if dry_path.is_file() else {}
    now = datetime.now(timezone.utc)
    expires_at = token.get("expires_at")
    not_expired = True
    if expires_at:
        try:
            not_expired = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00")) > now
        except ValueError:
            not_expired = False
    token_acks = token.get("required_boundary_acknowledgements")
    target_files = list(token.get("target_files") or [])
    expected_hash = _canonical_hash(token)
    checks = {
        "schema_valid": token.get("schema") == TOKEN_SCHEMA,
        "purpose_valid": token.get("purpose") == APPROVAL_PURPOSE,
        "approver_present": bool((token.get("approver") or {}).get("id")),
        "approval_statement_present": bool(str(token.get("approval_statement") or "").strip()),
        "dry_run_result_exists": dry_path.is_file(),
        "dry_run_sha256_matches": dry_path.is_file() and token.get("dry_run_sha256") == _sha256_file(dry_path),
        "dry_run_passed": dry.get("status") == "PASS_MAIN_PATCH_DRY_RUN",
        "repo_head_matches": repo_head is None or token.get("repo_head") == repo_head,
        "target_files_match_dry_run": sorted(target_files) == sorted(list(dry.get("target_files") or [])),
        "boundary_acknowledgements_complete": isinstance(token_acks, list) and all(ack in token_acks for ack in REQUIRED_BOUNDARY_ACKS),
        "token_hash_matches": token.get("token_hash") == expected_hash,
        "not_expired": not_expired,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    status = "VALID_HUMAN_APPROVAL_TOKEN" if not blockers else "BLOCKED_HUMAN_APPROVAL_TOKEN"
    return HumanApprovalTokenValidation(
        schema=VALIDATION_SCHEMA,
        generated_at=now.isoformat(),
        status=status,
        token_path=str(path),
        dry_run_result=str(dry_path),
        repo_head=str(token.get("repo_head") or "") or None,
        target_files=target_files,
        checks=checks,
        blockers=blockers,
        token_hash=str(token.get("token_hash") or "") or None,
        next_action=(
            "proceed to approved main patch transaction gate; still do not apply patch outside that gate"
            if status == "VALID_HUMAN_APPROVAL_TOKEN"
            else "resolve token blockers before any approved main patch transaction"
        ),
        boundary="Validation only; no patch application, no commit, no GeneDB mutation, no provider calls, no full AGI proof.",
    )


def write_human_approval_token(
    *,
    dry_run_result: str | Path,
    approver_id: str,
    repo_head: str,
    approval_statement: str,
    output_dir: str | Path,
    expires_at: str | None = None,
) -> dict[str, Any]:
    out = Path(output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    token = build_human_approval_token(
        dry_run_result=dry_run_result,
        approver_id=approver_id,
        repo_head=repo_head,
        approval_statement=approval_statement,
        expires_at=expires_at,
    )
    token_path = out / "human_approval_token.json"
    token_path.write_text(json.dumps(token, ensure_ascii=False, indent=2), encoding="utf-8")
    validation = validate_human_approval_token(token_path=token_path, dry_run_result=dry_run_result, repo_head=repo_head)
    validation_path = out / "human_approval_token_validation.json"
    validation_path.write_text(json.dumps(validation.to_json_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"token": str(token_path), "validation": str(validation_path), "status": validation.status, "blockers": validation.blockers, "token_hash": token.get("token_hash")}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or validate a PGG human approval token.")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--dry-run-result", required=True)
    create.add_argument("--approver-id", required=True)
    create.add_argument("--repo-head", required=True)
    create.add_argument("--approval-statement", required=True)
    create.add_argument("--output-dir", required=True)
    create.add_argument("--expires-at")
    validate = sub.add_parser("validate")
    validate.add_argument("--token", required=True)
    validate.add_argument("--dry-run-result")
    validate.add_argument("--repo-head")
    validate.add_argument("--output-dir")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "create":
        result = write_human_approval_token(
            dry_run_result=args.dry_run_result,
            approver_id=args.approver_id,
            repo_head=args.repo_head,
            approval_statement=args.approval_statement,
            output_dir=args.output_dir,
            expires_at=args.expires_at,
        )
    else:
        validation = validate_human_approval_token(token_path=args.token, dry_run_result=args.dry_run_result, repo_head=args.repo_head)
        result = validation.to_json_dict()
        if args.output_dir:
            out = Path(args.output_dir).expanduser()
            out.mkdir(parents=True, exist_ok=True)
            path = out / "human_approval_token_validation.json"
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            result = {"validation": str(path), "status": validation.status, "blockers": validation.blockers, "token_hash": validation.token_hash}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
