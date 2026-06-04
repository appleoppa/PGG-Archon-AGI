"""Initialize a per-profile MEMORY.md from SOUL.md + skills + config headline.

Usage:
  python -m agent.scripts.init_profile_memory \
    --profiles pgg-zhixing pgg-xingshi pgg-minshi ... \
    --template agent/scripts/templates/memory_template.md

Behavior:
  - For each profile, render MEMORY.md from the template plus:
      * skills count
      * SOUL.md first non-blank line
      * config.yaml provider list
  - Idempotent: skips if file already exists unless --force.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def _first_meaningful_line(p: Path) -> str:
    if not p.exists():
        return "(no SOUL.md)"
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            return s[:200]
    return "(empty SOUL.md)"


def _skill_count(p: Path) -> int:
    if not p.exists():
        return 0
    return len([f for f in p.iterdir() if f.is_dir()])


def _config_provider_summary(p: Path) -> str:
    if not p.exists():
        return "(no config.yaml)"
    text = p.read_text(encoding="utf-8", errors="replace")
    providers = re.findall(r"^\s*-\s*id:\s*([\w\-]+)", text, flags=re.M)
    return ",".join(providers) if providers else "(no provider list)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", nargs="+", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    tmpl = Path(args.template).read_text(encoding="utf-8")
    base = Path.home() / ".hermes" / "profiles"
    now = datetime.now(timezone.utc).isoformat()

    written = 0
    skipped = 0
    for profile in args.profiles:
        target = base / profile / "MEMORY.md"
        if target.exists() and not args.force:
            skipped += 1
            print(f"SKIP  {target}")
            continue
        soul = _first_meaningful_line(base / profile / "SOUL.md")
        skills = _skill_count(base / profile / "skills")
        cfg = _config_provider_summary(base / profile / "config.yaml")
        body = tmpl.format(
            profile=profile,
            soul_line=soul,
            skill_count=skills,
            provider_summary=cfg,
            generated_at=now,
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        written += 1
        print(f"WRITE {target} skills={skills}")
    print(f"RESULT written={written} skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
