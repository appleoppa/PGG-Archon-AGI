# hermes_apex_evolution API and Pitfalls — 2026-06-03

## Installation

```bash
# Installed in venv via pip (Rust .so wheel)
~/.hermes/hermes-agent/venv/bin/python -c "import hermes_apex_evolution as m; print(m.version())"
# → "hermes_apex_evolution 0.1.0 (Super Evolution 13)"
```

## Full API

### version()
Returns version string.

### py_evaluate(workspace: str, output: str) -> str
Evaluates APEX ΔE formula on a workspace directory. Writes JSON to `output`, returns JSON string.

Return schema:
```json
{
  "evaluated_at": "ISO timestamp",
  "formula": "APEX_ΔE = α·Ψ + β·Ω + λ·Φ + ∇Θ + Evol_code",
  "items": [
    {"item": "alpha_psi_truth_gate", "status": "pending|completed", "score": 0.0-1.0, "evidence": "..."},
    {"item": "beta_omega_native_core", ...},
    {"item": "lambda_phi_scout", ...},
    {"item": "nabla_theta_eval_loop", ...},
    {"item": "evol_code_native", ...}
  ]
}
```

### py_audit(roots: list[str], output: str) -> str
Scans directories for code architecture issues. Writes JSON to `output`.

Return schema:
```json
{
  "captured_at": "ISO timestamp",
  "roots": ["/path1", "/path2"],
  "total_files": 210,
  "duplicate_groups": [],
  "large_files": [],
  "stale_pyc": [],
  "redundant_reports": []
}
```

### py_scout(topics: list[str], output: str) -> str
Searches arXiv for topics. May fail with `RuntimeError: Scout error: arXiv API call failed`.

### start_evol_watcher(watch_dirs: list[str], log_path: str, threshold: int)
Starts background file watcher. `threshold` must be int (event count). Returns confirmation string.

### evol_watcher_status() -> dict
Returns `{"running": bool, "log_path": str}`. Process-local — only sees watcher in current process.

### stop_evol_watcher()
Stops watcher in current process.

## Pitfall Details

### Process-local watcher
The evol_watcher uses a Rust background thread scoped to the current Python process. Starting it in process A and checking status from process B returns `running: false`.

**Bad pattern** (daemon approach):
```bash
# Start daemon
python3 -c "import hermes_apex_evolution as m; m.start_evol_watcher(...)" &
# Check from different process → running: false
python3 -c "import hermes_apex_evolution as m; print(m.evol_watcher_status())"
```

**Good pattern** (single-process cron):
```bash
python3 << 'EOF'
import hermes_apex_evolution as m
m.start_evol_watcher(dirs, log, 50)  # starts in this process
status = m.evol_watcher_status()      # running: true (same process)
result = m.py_evaluate(workspace, output_file)
# process exits, watcher thread dies with it
EOF
```

### stdout mixing
Progress output from Rust goes to stdout:
```
📊 Eval: APEX ΔE on /path...
✅ Eval complete: APEX ΔE = 2.000
   α·Ψ=0.00  β·Ω=1.00  λ·Φ=0.00  ∇Θ=1.00  Evol=0.00
   Output: /tmp/evol_evaluate.json
```

The actual return value comes after these lines. **Don't parse stdout** — use the output file parameter.

### threshold type
```python
m.start_evol_watcher(dirs, log, 50)    # ✅ int
m.start_evol_watcher(dirs, log, 0.5)   # ❌ TypeError
```

## Cron Script Template

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /Users/appleoppa/.hermes/hermes-agent
PYTHON="venv/bin/python"

"$PYTHON" << 'PYEOF'
import hermes_apex_evolution as m
import json
from datetime import datetime, timezone

TS = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")

# Start watcher (process-local)
m.start_evol_watcher(
    ["/Users/appleoppa/.hermes/hermes-agent/agent",
     "/Users/appleoppa/.hermes/hermes-agent/tools",
     "/Users/appleoppa/.hermes/workspace/evolution",
     "/Users/appleoppa/.hermes/workspace/evo_master_db"],
    "/Users/appleoppa/.hermes/logs/evol_watcher.log", 50)
ws = m.evol_watcher_status()

# Evaluate (writes to file)
m.py_evaluate("/Users/appleoppa/.hermes/workspace/evolution", "/tmp/evol_evaluate.json")

# Audit (writes to file)
m.py_audit(["/Users/appleoppa/.hermes/hermes-agent/agent",
            "/Users/appleoppa/.hermes/hermes-agent/tools"], "/tmp/evol_audit.json")

# Read output files and generate report
eval_data = json.load(open("/tmp/evol_evaluate.json"))
audit_data = json.load(open("/tmp/evol_audit.json"))
# ... format report from eval_data and audit_data
PYEOF
```
