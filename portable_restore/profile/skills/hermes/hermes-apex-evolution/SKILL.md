---
name: hermes-apex-evolution
description: "Hermes Rust进化模块管理：hermes_apex_evolution API、APEX ΔE评估、代码审计、evol_watcher、cron集成"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, evolution, rust, apex, pgg-archon, cron]
    related_skills: [hermes-config-runtime-diagnosis, pgg-reasonix-apex-fusion]
---

# Hermes Apex Evolution (Rust Module)

## Trigger

Use when working with the Rust evolution system: APEX ΔE evaluation, code architecture audit, external source scouting, evol_watcher file monitoring, or evolution-related cron jobs.

## Module

`hermes_apex_evolution` v0.1.0 (Super Evolution 13) — Rust-compiled PyO3 module installed in venv as `.so`. Replaces the deleted Python PGG Archon evolution system.

## API Quick Reference

```python
import hermes_apex_evolution as m

m.version()                    # "hermes_apex_evolution 0.1.0 (Super Evolution 13)"
m.py_evaluate(workspace, out)  # APEX ΔE formula → JSON file
m.py_audit(roots, out)         # Code architecture audit → JSON file
m.py_scout(topics, out)        # arXiv scouting → JSON file (may fail on network)
m.start_evol_watcher(dirs, log, threshold_int)  # Background file watcher
m.evol_watcher_status()        # {"running": bool, "log_path": str}
m.stop_evol_watcher()          # Stop watcher
```

## Critical Pitfalls

1. **evol_watcher is process-local**: Background thread in current process. NOT visible from other processes. For cron: run watcher + eval in single Python process.
2. **threshold must be int**: `threshold=50` not `threshold=0.5`.
3. **Progress on stdout**: Rust prints progress (📊, ✅) to stdout mixed with return values. Use output files, don't parse stdout.
4. **py_scout network dependency**: arXiv API may fail transiently. Leave cron enabled, self-heals.

## Cron Integration

Script: `~/.hermes/scripts/agi_evolution_health_rust.sh`
Cron: "AGI进化健康监控(Rust)" every 30min (`5,35 * * * *`)
Pattern: single-process Python that starts watcher, evaluates, audits, reads output files, generates report.

## Replaced Python Modules

All PGG Archon Python evolution modules were deleted from main branch. Three LLMs unanimously recommended NOT restoring. See `references/rust-evolution-module-2026-06-03.md` in `hermes-config-runtime-diagnosis` for full list and rationale.

Surviving PGG modules: `pgg_archon_debate.py`, `pgg_archon_ecc.py`, `pgg_archon_module_status.py`, `pgg_archon_sqlite_persistence.py`.

## Reference

- Detailed API, pitfalls, cron script: `references/api-and-pitfalls.md`
- APEX ΔE convergence / score semantics / workspace-root pitfalls: `references/apex-delta-e-convergence-and-score-semantics.md`
- Truthful `source_scout.json` + `evol_events.jsonl` refresh pattern: `references/source-scout-evol-events-truthful-refresh-20260603.md`
- Truthful `source_scout.json` + `evol_events.jsonl` refresh pattern for real `lambda_phi` / `evol_code` recovery: `references/source-scout-evol-events-refresh-pattern.md`
- Rust-native β·Ω / APEX ΔE evidence hardening: `references/rust-native-beta-delta-e-evidence-pattern.md`
- Rust-native PyO3 β·Ω uplift + ignored overlay readiness/promotion governance: `references/rust-native-beta-overlay-hardening-202606.md`
- Round-level APEX ΔE hardening after high score: `references/apex-delta-e-corpus-overlay-hardening.md` — add corpus/property-style tests, ABI/hash registry, overlay decision matrix, and truthful audit boundaries before reporting stability.
