"""Sync a subset of skills from a source profile to a target profile.

Usage:
  python -m agent.scripts.sync_profile_skills --target pgg-zhixing --source default --exclude zhixing_specific

Behavior:
  - Source skills live in ~/.hermes/profiles/<source>/skills/<skill>/SKILL.md (or directory).
  - For each skill dir under source, if it is missing under target, copy it over.
  - --exclude names are substrings matched against skill directory names.
  - Bounded: only writes under target/skills/, never deletes.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--source", default="default")
    ap.add_argument("--exclude", nargs="*", default=[])
    args = ap.parse_args()

    base = Path.home() / ".hermes" / "profiles"
    src = base / args.source / "skills"
    dst = base / args.target / "skills"
    if not src.exists():
        print(f"ERROR  source skills missing: {src}")
        return 1
    dst.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped_existing = 0
    skipped_excluded = 0
    for entry in sorted(src.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if any(ex in name for ex in args.exclude):
            skipped_excluded += 1
            continue
        target = dst / name
        if target.exists():
            skipped_existing += 1
            continue
        shutil.copytree(entry, target)
        copied += 1
        print(f"COPY {target}")
    print(f"RESULT copied={copied} skipped_existing={skipped_existing} skipped_excluded={skipped_excluded}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
