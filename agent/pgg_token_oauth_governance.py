"""Token and OAuth governance gate.

No secret values are printed. This gate distinguishes user authorization from
actual credential rotation: GitHub CLI OAuth tokens cannot be made least-privilege
without re-auth/replacement by the account owner.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home() / ".hermes"
DATA = HOME / "data"
LATEST = DATA / "pgg_token_oauth_governance_latest.json"
LEDGER = DATA / "pgg_token_oauth_governance_ledger.jsonl"
DANGEROUS_SCOPES = {"delete_repo", "admin:org", "admin:enterprise", "admin:public_key", "admin:gpg_key", "admin:ssh_signing_key", "admin:repo_hook"}
TARGET_SCOPES = ["repo", "workflow", "read:org", "gist"]


def _run(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except Exception as exc:  # noqa: BLE001
        return {"returncode": 999, "stdout": "", "stderr": repr(exc)}


def _parse_scopes(text: str) -> list[str]:
    line = ""
    for candidate in text.splitlines():
        if "Token scopes:" in candidate:
            line = candidate
            break
    if not line:
        return []
    raw = line.split("Token scopes:", 1)[1]
    return [s.strip().strip("'").strip('"') for s in raw.split(",") if s.strip().strip("'").strip('"')]


def build_status() -> dict[str, Any]:
    gh = _run(["gh", "auth", "status"], 30)
    combined = (gh.get("stdout") or "") + (gh.get("stderr") or "")
    scopes = _parse_scopes(combined)
    dangerous_present = sorted(set(scopes) & DANGEROUS_SCOPES)
    # GitHub CLI browser/device auth stores an OAuth token in the OS keyring and
    # reports it as a gho_ token. Do not read or print the value; only classify
    # the token family from gh auth status output.
    oauth_active_count = 1 if "Token: gho_" in combined else 0
    auth_json = HOME / "auth.json"
    if oauth_active_count == 0 and auth_json.exists():
        try:
            data = json.loads(auth_json.read_text(encoding="utf-8"))
            text = json.dumps(data).lower()
            oauth_active_count = text.count('"oauth"') if "access_token" in text else 0
        except Exception:
            oauth_active_count = 0
    unmasked_secret = bool(re.search(r"(ghp_|github_pat_)[A-Za-z0-9_]{12,}", combined.replace("*", "")))
    checks = {
        "gh_auth_readable": gh.get("returncode") == 0 and "Logged in" in combined,
        "secret_values_not_printed": not unmasked_secret,
        "least_privilege_target_documented": True,
        "dangerous_scope_absent": not dangerous_present,
        "active_oauth_credential_present": oauth_active_count > 0,
    }
    # Authorization is not enough to fabricate a replacement token; rotation remains blocked until a new token/OAuth login exists.
    status = "PASS_TOKEN_OAUTH_MIN_PRIVILEGE" if all(checks.values()) else "WATCH_TOKEN_OAUTH_REQUIRES_CREDENTIAL_ROTATION"
    rec = {
        "schema": "PGGTokenOAuthGovernance/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "checks": checks,
        "scope_count": len(scopes),
        "dangerous_scope_count": len(dangerous_present),
        "dangerous_scopes_present": dangerous_present,
        "target_minimal_scopes": TARGET_SCOPES,
        "oauth_active_count_detected": oauth_active_count,
        "required_user_side_action": "Create/login with a fine-grained token or OAuth app credential limited to repo/workflow/gist/read:org, then replace GitHub CLI keyring token. Existing broad token cannot be down-scoped in place by this process.",
        "boundary": "No secret values printed; no token contraction claimed until replacement credential is actually installed and read back.",
    }
    DATA.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    LEDGER.open("a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rec = build_status()
    if args.json:
        print(json.dumps({"schema": "PGGTokenOAuthGovernancePublic/v1", "recorded": True}, ensure_ascii=False))
    else:
        print("PGG_TOKEN_OAUTH_GOVERNANCE_RECORDED")
    return 0 if rec["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
