# Phase File Simulation Fix Patterns — 2026-06-02

Date: 2026-06-02
Scope: Replaced 5 pre-existing PGG Archon phase files that returned hardcoded simulated results with real daemon/config/system checks.
Detected via: GPT + Claude cross-audit (agnes provider, gpt-5.5 + claude-opus-4)

## Files Fixed

### 1. `agent/pgg_archon_phase151_benchmark_local_mock_run.py`
**Problem**: Returned hardcoded `readiness_score=88.0`, `pass_rate=1.0` (3/3), no real benchmark executed.
**Fix**: Counts real Python files in `agent/` and `tests/` directories. Computes readiness from file/test ratio.

### 2. `agent/pgg_archon_phase155_production_pilot_approval_sim.py`
**Problem**: `decision='SIMULATED_APPROVAL_READY'`, `real_production_action_executed: False`, hardcoded `readiness_score=87.0`.
**Fix**: Checks config.yaml exists, venv/bin/python exists, and gateway daemon is running via launchctl. Readiness computed from real condition checks. Decision requires `readiness >= 85.0 AND (approved OR all_controls)`.

### 3. `agent/pgg_archon_phase166_bounded_long_duration_run.py`
**Problem**: Generated 48 simulated ticks with `i*30` simulated minutes, all hardcoded OK. `readiness_score=90.0`.
**Fix**: Checks actual ARS, AutoLoop, gateway, webui daemon states via launchctl list. Reports real running count.

### 4. `agent/pgg_archon_phase170_extended_runtime_sim.py`
**Problem**: Generated simulated ticks with `i%47` incident pattern, hardcoded `kill_switch_checked=True`, `resource_budget_ok=True`.
**Fix**: Checks 6 daemons (4 standard + pgg-minshi + pgg-xingshi). Real incident detection = daemons not running. Readiness penalized per-incident.

### 5. `agent/pgg_archon_phase30_registration_impact.py`
**Problem**: Schema said "Simulation", was essentially a set membership check.
**Fix**: Tries to import real `tools.registry` and read `_tools` directly. Reports existing tool count and similar-name conflicts.

## Repair Pattern (used for all 5)

```
1. Read the original file
2. Identify hardcoded constants (readiness_score 87-90, tick counts, simulated_hours)
3. Identify bogus false flags (real_production_action_executed: False)
4. Add subprocess.call to check real system state (launchctl list, path.exists)
5. Compute readiness from real measurements, not constants
6. Update return dict to include both computed values AND evidence fields (daemons_running: N)
7. Camelot/smoke test: import + run, verify output says something real
```

## git commit

```
fa2669a72 fix: replace hardcoded simulation stubs with real daemon/config checks (5 phase files + fail_closed)
```
