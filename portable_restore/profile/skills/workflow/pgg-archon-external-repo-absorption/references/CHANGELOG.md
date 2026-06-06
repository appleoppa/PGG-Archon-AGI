# PGG Archon External Repo Absorption — Skill Update Log

## 2026-06-02 Update

### Added to SKILL.md body:

1. **Pitfall: sibling subagent file interference** — when multiple subagents modify the same files, re-read before write, clear `__pycache__`, watch for dataclass field mismatch
2. **Pitfall: phase file simulation stubs** — signals to detect (`simulated_*`, hardcoded `readiness_score`, `third_party_eval_completed: False` paired with `PASS`), and fix pattern (replace with real daemon/config/system checks)
3. **Pitfall: pre-existing health check failures** — document unrelated failures before starting
4. **Verification step: GPT + Claude cross-audit** — call both models via agnes to detect simulation patterns, with concrete API call pattern

### Added reference file:

- `references/phase-file-simulation-fix-patterns-20260602.md` — concrete details on 5 phase files that were fixed this session
