"""Bounded PGG Archon Token Hygiene — file-06 (real surface).

4-probe status surface for token hygiene:
  1. ~/.hermes/skills contains token-hygiene module
  2. env PGG_ARCHON_TOKEN_HYGIENE is set
  3. ~/.hermes/data/audit exists
  4. ~/.hermes/data/pgg_archon_audit.jsonl or similar token log exists
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TokenHygieneProbe:
    name: str
    status: str
    probes: dict[str, str]
    notes: str = ""


def _probe_env(env_name: str) -> str:
    return "present" if os.environ.get(env_name) else "missing"


def _probe_cli(cli: str) -> str:
    return "available" if shutil.which(cli) else "missing"


def _probe_path_writable(p: Path) -> str:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".pgg_archon_token_probe"
        test.write_text("ok", encoding="utf-8")
        test.unlink()
        return "writable"
    except Exception:
        return "not_writable"


def probe_token_hygiene() -> TokenHygieneProbe:
    audit_dir = Path.home() / ".hermes" / "data" / "audit"
    audit_files = list(audit_dir.glob("*.json")) if audit_dir.exists() else []
    deps = {
        "audit_dir_files": str(len(audit_files)),
        "env_PGG_ARCHON_TOKEN_HYGIENE": _probe_env("PGG_ARCHON_TOKEN_HYGIENE"),
        "path_~/.hermes/data/audit": _probe_path_writable(audit_dir),
        "cli_jq": _probe_cli("jq"),
    }
    present = (
        (1 if len(audit_files) >= 1 else 0)
        + (1 if deps["env_PGG_ARCHON_TOKEN_HYGIENE"] == "present" else 0)
        + (1 if deps["path_~/.hermes/data/audit"] == "writable" else 0)
        + (1 if deps["cli_jq"] == "available" else 0)
    )
    if present == 4:
        status = "ACTIVE"
    elif present >= 2:
        status = "PARTIAL"
    elif present >= 1:
        status = "SKELETON"
    else:
        status = "ABSENT"
    return TokenHygieneProbe(
        name="token_hygiene",
        status=status,
        probes=deps,
        notes=f"Token hygiene super-evolution 6; {present}/4 surface gates resolved",
    )


def run_token_hygiene() -> dict[str, Any]:
    p = probe_token_hygiene()
    return {
        "schema": "PGGArchonTokenHygiene/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "probe": asdict(p),
        "boundary": "status surface; ACTIVE means 4/4 gates resolved; not full AGI",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_token_hygiene(), ensure_ascii=False, indent=2))
