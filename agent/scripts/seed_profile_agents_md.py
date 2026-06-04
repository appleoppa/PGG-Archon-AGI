"""Seed AGENTS.md for each profile with a bounded core-cognition prompt.

Usage:
  python -m agent.scripts.seed_profile_agents_md --profiles default pgg-zhixing pgg-xingshi pgg-minshi pgg-zhengju pgg-zhinao pgg-anguan pgg-feisu pgg-guwen pgg-shenji pgg-tuiyan pgg-xunshi --template agent/scripts/templates/agents_md_template.md

Behavior:
  - For each profile, write ~/.hermes/profiles/<profile>/AGENTS.md from the template.
  - If the file already exists, skip (idempotent) unless --force.
  - Profile-specific block is rendered with profile name and a short topic.
  - Bounded: only writes AGENTS.md, no other mutation.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

PROFILE_TOPICS = {
    "default": "Apple Didi / 苹果中枢 / default coordinator",
    "pgg-zhixing": "Apple Knowledge (智脑知识) — knowledge-center",
    "pgg-xingshi": "Apple Criminal Defense (刑事辩护) — criminal-defense",
    "pgg-minshi": "Apple Civil Litigation (民事诉讼) — civil-litigation",
    "pgg-zhengju": "Apple Evidence Management (证据管理) — evidence-management",
    "pgg-zhinao": "Apple Sports Master (体育大师) — sports-master",
    "pgg-anguan": "Apple Bankruptcy (破产) — bankruptcy",
    "pgg-feisu": "Apple Non-Litigation (非诉) — non-litigation",
    "pgg-guwen": "Apple Legal Advisor (法律顾问) — legal-advisor",
    "pgg-shenji": "Apple Inspection Team (巡视) — inspection-team",
    "pgg-tuiyan": "Apple Case Simulation (案件推演) — case-simulation",
    "pgg-xunshi": "Apple M&A Law (并购重组) — ma-law",
}

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
        target = base / profile / "AGENTS.md"
        if target.exists() and not args.force:
            skipped += 1
            print(f"SKIP  {target}")
            continue
        topic = PROFILE_TOPICS.get(profile, profile)
        body = tmpl.format(profile=profile, topic=topic, generated_at=now)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        written += 1
        print(f"WRITE {target} ({len(body)} chars)")
    print(f"RESULT written={written} skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
