# Gateway Crash Loop Diagnosis — 2026-06-03

## Symptom pattern

Gateway restarts multiple times in short succession. `hermes gateway status` shows different PIDs and `LastExitStatus=15` (SIGTERM from launchd auto-restart).

## Diagnostic steps

1. **Find the root error** — read `~/.hermes/logs/gateway.log` from the BOTTOM UP, looking for the FIRST `NameError`/`ImportError`/`AttributeError`/`ModuleNotFoundError`. Ignore the cascade of repeated errors after it.

2. **Check PID history**:
   ```bash
   grep -E "PID|Starting|Shutdown|NameError|ImportError" ~/.hermes/logs/gateway.log | tail -50
   ```

3. **Check if upstream fix exists**:
   ```bash
   cd ~/.hermes/hermes-agent && git log --oneline -5
   hermes update  # pulls latest from main
   ```

4. **Verify file was actually updated**:
   ```bash
   ls -la ~/.hermes/hermes-agent/agent/conversation_loop.py
   # Timestamp should match the update time
   ```

5. **Restart and verify**:
   ```bash
   hermes gateway restart
   hermes gateway status  # check new PID, no more crashes
   ```

## Common root causes

| Error | Typical cause | Fix |
|-------|--------------|-----|
| `NameError: current_turn_user_idx` | Code path bug in conversation_loop.py | `hermes update` |
| `ModuleNotFoundError: agent.X` | Module deleted during cleanup | Re-enable if module exists; disable cron if deleted |
| `sqlite3.DatabaseError: database disk image is malformed` | Gateway crash truncated state.db | Delete corrupt file, restart |
| `No module named pip` | venv incomplete | `pip install -e ".[all]"` in hermes-agent dir |

## Related: post-update verification

After `hermes update`, always verify:
1. Gateway PID is stable (check twice with 10s gap)
2. Feishu/Lark reconnected: `grep "feishu connected" ~/.hermes/logs/gateway.log | tail -1`
3. Cron jobs are running: `grep "cron" ~/.hermes/logs/gateway.log | tail -5`
4. All profile gateways are up: `hermes gateway status | grep "✓"`
