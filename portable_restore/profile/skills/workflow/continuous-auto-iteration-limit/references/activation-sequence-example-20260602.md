# Activation Sequence Example — 2026-06-02 (Full 8-Module Sequence)

## Context

After rolling back from a failed attempt where 3 modules were activated simultaneously (causing system slowness and user frustration), this session demonstrated the correct one-at-a-time activation sequence.

## The Complete Sequence: 8 Modules Absorbed From APEX Repos

| # | Module | Source | Type | Tests | Health |
|---|---|---|---|---|---|
| 1 | DeltaG constraint gate | apex-spiral/delta_g | Foundation constraint | 7 | 16→17 |
| 2 | CodeGenesis scanner | apex-spiral/l5_self_fix | Quality scanner | 5 | 17→18 |
| 3 | Σ_memory + τ_trace | apex-spiral/intel | Measurement | 7 | 18→19 |
| 4 | V10.3 self-loop | apex-spiral/v103 | Scoring surface | 9 | 19→20 |
| 5 | Skill Health scanner | GeneNexus + SelfCheck | Read-only scanner | 4 | 20→21 |
| 6 | Doubt-Driven Γ review | apex-spiral/doubt_driven | Risk classifier | 6 | 21→22 |
| 7 | Planning runner | apex-spiral/apex_skills | Dep graph + slicing | 5 | 22→23 |
| 8 | APEX schema validator | apex-standard/ schemas | Schema validation | 5 | 23→24 |

Final state: **24/24 health, 31 components, 56 tests, load ~2.5–3.1, git clean with 12 commits**.

## Key Verification Steps Performed After Each Activation

- New unit tests pass
- Existing regression tests pass
- Health check: clean (+1 per activation)
- Manifest: component + capability + milestone entries
- python -m apex_god.evolution_manifest --update + JSON readback
- System load: stable (< 3.0 typical)
- Daemons: ARS + AutoLoop running
- Git: clean commit with 4 files (module + tests + health + manifest)
- No residual: no uncommitted files, no drafts left behind

## Module Boundary Declaration Pattern

Every absorbed module explicitly declared what it does NOT do:

| Module | Bounded From |
|---|---|
| DeltaG | No LLM calls, no Hermes core mutation |
| CodeGenesis | No auto-fix, no Hermes core mutation |
| MemoryTrace | No writes, no persistence |
| V10.3 | No auto-repair, no history without data |
| SkillHealth | No writes, no manifest creation, no Hermes core |
| DoubtGamma | No LLM calls, no auto-review |
| PlanningRunner | No broken lambda_ctx calc, no auto-verify |
| SchemaValidator | No JS adapter, no /root/* hardcoded paths |

## Pitfall: Stale __pycache__ After Git Rollback

When you `git reset --hard` to roll back modules, old `.pyc` files remain. If the reverted module had different field schemas (e.g. extra dataclass fields), pytest imports the stale `.pyc` causing `TypeError: missing 2 required positional arguments` — misleading because it points at the current .py source.

**Fix**: `find . -path '*__pycache__*' -delete` before any test cycle after a rollback.

## What Was Learned

1. One module at a time, verify between each — not 3 simultaneously
2. Simulate formula-heavy modules in /tmp first — verify no NaN/Inf before Python module
3. Declare boundaries explicitly — each module's docstring should state what it does NOT do
4. Stale pycache = misleading TypeError — clear __pycache__ after any git rollback
5. Health check cells must be individually verifiable — no combined checks that mask failures
6. Land before proceeding — user says "落地后再继续" means stop and present landing state

## Original Corrections (User)

1. "激活一个调试顺畅一个，再顺序激活" — Activate one, debug smooth, then sequence in order
2. "为什么总是突然停下来" — Don't stop mid-task
3. "按照组件与兼容性环境，逐步优化修复并激活组件" — Component and compatibility-first activation
4. "先将完成的优化、验证、审计、再落地。落地后再继续解锁" — Land, then unlock
