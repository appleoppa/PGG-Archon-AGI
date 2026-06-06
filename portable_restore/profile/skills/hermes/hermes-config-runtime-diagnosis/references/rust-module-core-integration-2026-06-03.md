# Rust Module Core Integration Runbook

Date: 2026-06-03
Module: hermes_apex_evolution v0.1.0 (Super Evolution 13)

## Context

Python PGG Archon evolution modules (8+ files in agent/, tools/) were deleted during `hermes update` branch switch. Evaluated by GPT-5.5, Claude Opus 4.6, DeepSeek V4 Flash — unanimous: don't restore (empty queue, broken dependency chain, EVM/APEX already covers). Replaced by Rust module.

## Integration Steps

### 1. Native Tool Registration

File: `tools/apex_evolution_tool.py`

```python
from tools.registry import registry

registry.register(
    name="apex_evolution",
    toolset="hermes-cli",
    schema=TOOL_SPEC,
    handler=handle_apex_evolution,
    emoji="🧬",
    max_result_size_chars=50_000,
)
```

Handler dispatches to Rust module functions. Returns JSON string.

### 2. Gateway Startup Hook

Directory: `~/.hermes/hooks/evol-watcher/`

HOOK.yaml:
```yaml
name: evol-watcher-startup
description: Start evol_watcher on gateway startup
events:
  - gateway:startup
```

handler.py: async def that imports hermes_apex_evolution, checks status, starts watcher.

### 3. Launchd Daemon

For persistent background threads that must survive gateway restarts:

- Plist: `~/Library/LaunchAgents/ai.hermes.evol-watcher.plist`
- Daemon script: `~/.hermes/scripts/evol_watcher_daemon.py`
- PID file: `~/.hermes/data/evol_watcher.pid`
- KeepAlive with SuccessfulExit=false (restart on crash, not on clean exit)
- ThrottleInterval=10 (prevent rapid restart loops)

### 4. Cron Health Check

Script: `~/.hermes/scripts/agi_evolution_health_rust.sh`

Single-process pattern (critical for watcher visibility):
```bash
"$PYTHON" << 'PYEOF'
import hermes_apex_evolution as m
m.start_evol_watcher(...)  # start in same process
result = m.py_evaluate(...)  # evaluate in same process
# parse result, generate report
PYEOF
```

### 5. AGENTS.md Documentation

Added `## APEX Evolution Engine (Rust)` section after Gateway section.

## Pitfalls

1. **evol_watcher is process-local**: Thread in current Python process. Cannot be started in one process and checked from another.
2. **threshold must be int**: `start_evol_watcher(dirs, log, 50)` not `50.0`.
3. **stdout mixed with progress**: Rust module prints progress to stdout. Use output files, not stdout parsing.
4. **py_scout network dependency**: arXiv API may fail intermittently.
5. **launchd daemon PID stale**: If daemon crashes and launchd restarts it, old PID file is stale. Daemon writes PID on start.

## Files Created

- `tools/apex_evolution_tool.py` — native tool registration
- `~/.hermes/hooks/evol-watcher/HOOK.yaml` + `handler.py` — gateway hook
- `~/Library/LaunchAgents/ai.hermes.evol-watcher.plist` — launchd daemon
- `~/.hermes/scripts/evol_watcher_daemon.py` — daemon script
- `~/.hermes/scripts/agi_evolution_health_rust.sh` — cron health check
- `AGENTS.md` — documentation section added

## Files Disabled (not deleted)

- `~/.hermes/scripts/pgg_archon_health_watchdog_cron.sh` — old Python watchdog (cron disabled)
- `~/.hermes/scripts/pgg_ultimate_evolution_phase3_ars_cycle.sh` — old ARS cycle (cron disabled, dependency chain broken)
- `~/.hermes/scripts/se20_auto_eval.sh` — old SE20 eval (cron disabled, module deleted)
