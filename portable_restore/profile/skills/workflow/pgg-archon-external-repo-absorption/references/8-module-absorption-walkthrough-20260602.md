# 8-Module APEX Repo Absorption Walkthrough — 2026-06-02

## Scope

Full absorption of 8 modules from apex-spiral/LLM-Pangu/apex-standard/CodeGenesis repositories into PGG Archon read-only scoring surfaces. All P0 and P1 items from the APEX_REPO_UNLOCK_AUDIT completed in 2 sessions.

## Sequence & Key Decisions

### Session 1: Foundation (4 modules)

| Step | Module | Upstream Source | Why This Order |
|---|---|---|---|
| 1 | DeltaG constraint gate | apex-spiral delta_g | Foundation — all later modules depend on bounded verification |
| 2 | CodeGenesis quality scanner | apex-spiral l5_self_fix | Scanner — can run as soon as constraints exist |
| 3 | Σ_memory + τ_trace scoring | apex-spiral intel | Measurement — needs code to measure first |
| 4 | V10.3 self-loop scoring | apex-spiral v103 | Upper-layer formula — standalone pure math, lowest risk |

**Key decision**: V10.3 was simulated in /tmp first (standalone Python) to verify no NaN/Inf outputs before creating the formal module. Simulation script was deleted after confirmation.

### Session 2: Gene chain + P1 items (4 modules)

| Step | Module | Upstream Source | Risk Level |
|---|---|---|---|
| 5 | Skill Health scanner | GeneNexus + skill_self_check | 🟢 — bypassed gene_reader /root/* paths |
| 6 | Doubt-Driven Γ review | apex-spiral doubt_driven.py | 🟢 — pure logic, no I/O |
| 7 | Planning / Incremental Runner | apex-spiral apex_skills.py | 🟡 — fixed broken lambda_ctx range |
| 8 | APEX Schema Validator | apex-standard/ | 🟢 — parameterized paths, no JS dep |

## Boundary Declarations Per Module

Each module's docstring explicitly declared what it does NOT do:

```python
# Module 1: agent/pgg_archon_delta_gate.py
# Boundary: no LLM calls, no Hermes core mutation

# Module 5: agent/pgg_archon_skill_health_checker.py
# Boundary: no writes, no manifest creation, no Hermes core mutation

# Module 7: agent/pgg_archon_planning_runner.py
# Boundary: no broken lambda_ctx calc, no auto-verify
```

## Manifest Entry Pattern

Each module added 3 things to `apex_god/evolution_manifest.py`:

1. **Component mapping** in `COMPONENT_MAP`:
   ```python
   ("agent/pgg_archon_X.py", "component_name", "category"),
   ```

2. **Milestone entry** in `_get_milestones()`:
   ```python
   {"ts": "...", "phase": "APEX仓库解锁", "title": "Name",
    "type": "capability", "component": "name",
    "impact": "description with boundary note"},
   ```

3. **Capability definition** in `_get_builtin_capabilities()`:
   ```python
   "name": {... "boundary": "no LLM, no writes, ..."},
   ```

## Health Check Integration

Each module added 1 cell to `apex_god/health.py`:

1. Add `_check_module_name` to `_ALL_CHECKS` list
2. Add function that imports the module and calls a basic method
3. If import fails, set `healthy=False` with the error message

Health check naming convention: `R#` where # starts at R1 (core), increments per module. Current max: R16.

## Commit Discipline

Each module commit included exactly 4 files:

```
agent/pgg_archon_X.py             # Module
tests/agent/test_pgg_archon_X.py   # Tests
apex_god/health.py                 # Health check integration
apex_god/evolution_manifest.py     # Manifest integration
```

No mixing unrelated files. No leftover stashes or uncommitted work.

## Rollback Recovery Pattern

When `git reset --hard` reverts committed modules:

1. `find . -path '*__pycache__*' -delete` — prevents stale .pyc misleading TypeError
2. Re-examine the test file: if upstream had extra dataclass fields, the test may reference fields that no longer exist in the reset source
3. Re-run `python -m apex_god.health` to confirm clean baseline before starting fresh
