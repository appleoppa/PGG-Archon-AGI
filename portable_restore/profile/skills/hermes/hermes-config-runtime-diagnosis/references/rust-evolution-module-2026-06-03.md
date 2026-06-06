# Rust Evolution Module (hermes_apex_evolution) — 2026-06-03

## Module info

- Package: `hermes_apex_evolution` v0.1.0 (Super Evolution 13)
- Type: Rust-compiled `.so` (PyO3), installed in venv
- Location: `~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/hermes_apex_evolution/`
- Replaces: Python PGG Archon evolution system (`agent/pgg_archon_*`, `agent/apex_*`, `tools/pgg_archon_tools`)

## API Reference

```python
import hermes_apex_evolution as m

# Version
m.version()  # → "hermes_apex_evolution 0.1.0 (Super Evolution 13)"

# APEX ΔE evaluation
result = m.py_evaluate(
    workspace="/Users/appleoppa/.hermes/workspace/evolution",  # workspace dir
    output="/tmp/evol_evaluate.json"  # output file path
)
# Returns JSON string with: formula, items[], total score
# Items: alpha_psi_truth_gate, beta_omega_native_core, lambda_phi_scout, nabla_theta_eval_loop, evol_code_native

# Code audit
result = m.py_audit(
    roots=["/path/to/agent", "/path/to/tools"],  # list of directories
    output="/tmp/evol_audit.json"
)
# Returns JSON string with: total_files, duplicate_groups[], large_files[], stale_pyc[]

# External scouting (arXiv)
result = m.py_scout(
    topics=["AGI", "evolution", "legal-ai"],  # search topics
    output="/tmp/evol_scout.json"
)
# May fail with RuntimeError if arXiv API unreachable

# Background file watcher
m.start_evol_watcher(
    watch_dirs=["/path/to/watch", ...],
    log_path="/Users/appleoppa/.hermes/logs/evol_watcher.log",
    threshold=50  # MUST be int, not float
)
m.evol_watcher_status()  # → {"running": bool, "log_path": str}
m.stop_evol_watcher()
```

## Critical Pitfalls

### 1. evol_watcher is process-local
The watcher is a background thread in the CURRENT Python process. Starting it in one process does NOT make it visible from another. `evol_watcher_status()` from a different process returns `{"running": false}`.

**Implication**: Cannot use a persistent daemon approach. Must start watcher, run evaluation, and exit in a single Python process.

### 2. threshold must be int
`start_evol_watcher(threshold=0.5)` → `TypeError: 'float' object cannot be interpreted as an integer`. Use `threshold=50`.

### 3. Progress messages on stdout
The Rust module prints progress (📊, ✅, 🔍) to stdout, mixed with the return value. Do NOT parse stdout. Use the `output` file parameter and read the JSON file instead.

### 4. py_scout network dependency
`py_scout()` calls arXiv API. Fails with `RuntimeError: Scout error: arXiv API call failed` when network is unavailable. This is transient — leave enabled in cron, it self-heals.

## Cron Script Pattern

Script: `~/.hermes/scripts/agi_evolution_health_rust.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /Users/appleoppa/.hermes/hermes-agent
PYTHON="/Users/appleoppa/.hermes/hermes-agent/venv/bin/python"
EVAL_FILE="/tmp/evol_evaluate.json"
AUDIT_FILE="/tmp/evol_audit.json"

# Single Python process: start watcher + evaluate + audit + report
"$PYTHON" << 'PYEOF'
import hermes_apex_evolution as m
import json
from datetime import datetime, timezone

# 1. Start watcher (process-local)
m.start_evol_watcher(
    ["/Users/appleoppa/.hermes/hermes-agent/agent",
     "/Users/appleoppa/.hermes/hermes-agent/tools",
     "/Users/appleoppa/.hermes/workspace/evolution",
     "/Users/appleoppa/.hermes/workspace/evo_master_db"],
    "/Users/appleoppa/.hermes/logs/evol_watcher.log", 50)
ws = m.evol_watcher_status()

# 2. Evaluate (output goes to file)
m.py_evaluate("/Users/appleoppa/.hermes/workspace/evolution", "/tmp/evol_evaluate.json")

# 3. Audit (output goes to file)
m.py_audit(["/Users/appleoppa/.hermes/hermes-agent/agent",
            "/Users/appleoppa/.hermes/hermes-agent/tools"], "/tmp/evol_audit.json")

# 4. Read output files and generate report
# ... (read JSON files, format report)
PYEOF
```

## Replaced Python modules (deleted, do NOT restore)

These were removed from main branch during Hermes update. All had broken dependency chains. The Rust module replaces their functionality:

- `agent/apex_runtimeos_autonomy.py` (61KB) — health watchdog
- `agent/pgg_archon_ultimate_evolution_formula.py` (451 lines) — evolution formula
- `agent/pgg_archon_ultimate_evolution_ars_cycle.py` — ARS cycle
- `tools/pgg_archon_tools.py` (470+ lines) — tool registration shell (8 dependencies, all deleted)
- `tools/post_task_evaluation_tool.py` (334 lines) — task evaluation queue
- `agent/apex_runtimeos_sequence.py`, `agent/apex_runtimeos_evm_gate.py`
- `agent/pgg_archon_context_formula.py`, `agent/pgg_archon_legal_gap_closure_gate.py`
- `agent/pgg_archon_legal_l6_promotion_gate.py`, `agent/pgg_archon_l5_self_fix.py`
- `agent/pgg_archon_mimo_mcp_formula.py`, `agent/pgg_archon_super_agi_formula.py`

Three LLM evaluation (GPT-5.5, Claude Opus 4.6, DeepSeek V4 Flash) unanimously recommended NOT restoring these: 74 cron executions with empty queues, 8-layer dependency chain fully broken, Rust module covers the same functionality.

## Surviving PGG Archon modules (still valuable)

- `agent/pgg_archon_debate.py` — multi-agent debate pipeline
- `agent/pgg_archon_ecc.py` — evolution control center
- `agent/pgg_archon_module_status.py` — module status visualization
- `agent/pgg_archon_sqlite_persistence.py` — SQLite persistence
