#!/usr/bin/env python3
"""PGG Self-Healing Pipeline v2.1 — bounded local self-heal.

Purpose for the daily autonomy wrapper:
  1) Repair Hermes CLI launcher compatibility.
  2) Repair legacy hermes-agent/venv path compatibility by symlinking to .venv.
  3) Verify both ~/.local/bin/hermes and the legacy venv path can execute --version.
  4) Write bounded evidence into EVOLUTION_MANIFEST.

Boundaries: local launcher/symlink only; no credentials, provider config,
launchd plist mutation, scheduler/security core mutation, production route switch,
legal finalization, or cross-profile writes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES_HOME = HOME / ".hermes"
REPO = HERMES_HOME / "hermes-agent"
BIN = HERMES_HOME / "bin"
DATA = HERMES_HOME / "data"
MANIFEST = DATA / "EVOLUTION_MANIFEST.json"
WORKSPACE = HERMES_HOME / "workspace" / "pgg-archon-governance" / "autonomy-v2"
LOCAL_BIN = HOME / ".local" / "bin"
HERMES_LAUNCHER = LOCAL_BIN / "hermes"

BOUNDARY = (
    "low-risk local launcher/symlink repair only; "
    "no credential/config/scheduler/security/production mutation"
)


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 60) -> dict[str, Any]:
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return {"rc": cp.returncode, "output": cp.stdout}
    except FileNotFoundError as e:
        return {"rc": 127, "output": f"FileNotFoundError: {e}"}
    except subprocess.TimeoutExpired as e:
        out = e.stdout if isinstance(e.stdout, str) else ""
        return {"rc": 124, "output": out[-2000:]}
    except Exception as e:
        return {"rc": 1, "output": f"{type(e).__name__}: {e}"}


def _manifest_append(key: str, val: dict[str, Any]) -> None:
    try:
        d = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
        if not isinstance(d, dict):
            d = {}
        d[key] = val
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(d, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    except Exception as e:
        print(f"[WARN] manifest write failed: {e}")


def _launcher_script(agent_dir: Path = REPO) -> str:
    return f'''#!/usr/bin/env bash
set -euo pipefail
unset PYTHONPATH
unset PYTHONHOME
export PATH="$HOME/.local/bin:$HOME/.hermes/node/bin:$HOME/.npm-global/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

HERMES_AGENT_DIR="{agent_dir}"
for candidate in \
  "$HERMES_AGENT_DIR/.venv/bin/hermes" \
  "$HERMES_AGENT_DIR/venv/bin/hermes" \
  "$HERMES_AGENT_DIR/hermes"
do
  if [[ -x "$candidate" ]]; then
    exec "$candidate" "$@"
  fi
done

printf 'hermes launcher error: no executable found under %s/.venv/bin/hermes or venv/bin/hermes\n' "$HERMES_AGENT_DIR" >&2
exit 127
'''


def ensure_hermes_cli_compatibility() -> dict[str, Any]:
    """Repair and verify Hermes CLI + legacy venv path compatibility."""
    actions: list[str] = []
    errors: list[str] = []
    dotvenv_path = REPO / ".venv"
    venv_path = REPO / "venv"

    # 1) Keep old launchd/scripts that call hermes-agent/venv/bin/hermes alive.
    if dotvenv_path.exists():
        try:
            if venv_path.is_symlink():
                target = os.readlink(venv_path)
                if target != ".venv":
                    venv_path.unlink()
                    venv_path.symlink_to(".venv", target_is_directory=True)
                    actions.append("reset_venv_symlink_to_dotvenv")
            elif not venv_path.exists():
                venv_path.symlink_to(".venv", target_is_directory=True)
                actions.append("created_venv_symlink_to_dotvenv")
            elif venv_path.is_dir():
                actions.append("kept_existing_venv_dir")
            else:
                errors.append(f"venv_path_exists_but_not_dir_or_symlink:{venv_path}")
        except Exception as e:
            errors.append(f"venv_symlink_error:{type(e).__name__}:{e}")
    else:
        errors.append(f"dotvenv_missing:{dotvenv_path}")

    # 2) Keep ~/.local/bin/hermes from hard-failing on a single old path.
    expected = _launcher_script()
    try:
        current = HERMES_LAUNCHER.read_text(encoding="utf-8") if HERMES_LAUNCHER.exists() else ""
        old_hardcoded = f"{REPO}/venv/bin/hermes" in current and ".venv/bin/hermes" not in current
        missing_fallback = ".venv/bin/hermes" not in current or "venv/bin/hermes" not in current
        if old_hardcoded or missing_fallback or not HERMES_LAUNCHER.exists():
            LOCAL_BIN.mkdir(parents=True, exist_ok=True)
            HERMES_LAUNCHER.write_text(expected, encoding="utf-8")
            HERMES_LAUNCHER.chmod(0o755)
            actions.append("rewrote_local_hermes_launcher_with_fallbacks")
        else:
            try:
                HERMES_LAUNCHER.chmod(0o755)
            except Exception:
                pass
            actions.append("launcher_already_compatible")
    except Exception as e:
        errors.append(f"launcher_error:{type(e).__name__}:{e}")

    # 3) Real execution verification.
    version_checks: dict[str, Any] = {}
    version_checks["local_launcher"] = _run([str(HERMES_LAUNCHER), "--version"], timeout=60)
    old_cli = REPO / "venv/bin/hermes"
    version_checks["old_venv_path"] = _run([str(old_cli), "--version"], timeout=60)

    ok = (
        not errors
        and version_checks["local_launcher"].get("rc") == 0
        and version_checks["old_venv_path"].get("rc") == 0
    )
    status = "PASS" if ok and actions == ["launcher_already_compatible"] else ("APPLIED" if ok else "WATCH")

    return {
        "name": "hermes_cli_venv_compat",
        "status": status,
        "actions": actions,
        "errors": errors,
        "launcher": str(HERMES_LAUNCHER),
        "venv_path": str(venv_path),
        "dotvenv_path": str(dotvenv_path),
        "version_checks": version_checks,
        "boundary": BOUNDARY,
    }


def verify_goal() -> dict[str, Any]:
    goal = BIN / "hermes-goal"
    r = _run([str(goal)], timeout=180)
    if r["rc"] != 0:
        return {"status": "WATCH", "rc": r["rc"], "output": r["output"][:1000]}
    try:
        # pgg-python-module-runner prints provenance to stderr merged after JSON.
        # Decode only the first JSON object so provenance does not create a false PASS.
        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(r["output"].lstrip())
        return {
            "status": "PASS" if data.get("overall_status") == "PASS" and data.get("blocked_count", 0) == 0 else "WATCH",
            "overall_status": data.get("overall_status"),
            "summary": data.get("summary"),
            "watch_count": data.get("watch_count"),
            "blocked_count": data.get("blocked_count"),
        }
    except Exception as e:
        return {"status": "WATCH", "parse_error": f"{type(e).__name__}: {e}", "raw_head": r["output"][:500]}


def main() -> int:
    print("=" * 60)
    print("PGG Self-Healing Pipeline v2.1")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    print("\n[1/3] Hermes CLI / venv compatibility...")
    cli_health = ensure_hermes_cli_compatibility()
    local_rc = (cli_health.get("version_checks") or {}).get("local_launcher", {}).get("rc")
    old_rc = (cli_health.get("version_checks") or {}).get("old_venv_path", {}).get("rc")
    print(f"  {cli_health['status']} local_rc={local_rc} old_rc={old_rc} actions={cli_health.get('actions')}")
    if cli_health.get("errors"):
        print(f"  errors={cli_health['errors']}")

    print("\n[2/3] Verify hermes-goal...")
    goal = verify_goal()
    print(f"  {goal.get('status')} overall={goal.get('overall_status')} pass={goal.get('pass_count')} watch={goal.get('watch_count')} blocked={goal.get('blocked_count')}")

    print("\n[3/3] Knowledge settle...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    entry = {
        "schema": "PGGSelfHealingPipeline/v2.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cli_health": cli_health,
        "verify_goal": goal,
        "boundary": BOUNDARY,
    }
    key = f"auto_self_heal_cli_venv_compat_{ts}"
    _manifest_append(key, entry)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    artifact = WORKSPACE / f"self_heal_cli_venv_compat_{ts}.json"
    artifact.write_text(json.dumps(entry, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"  manifest={key}")
    print(f"  artifact={artifact}")
    print("=" * 60)
    return 0 if cli_health.get("status") in ("PASS", "APPLIED") else 1


if __name__ == "__main__":
    sys.exit(main())
