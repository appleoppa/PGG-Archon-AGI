# Cron Dependency Chain Audit — 2026-06-03

## When to use

Multiple cron jobs failing with `ModuleNotFoundError`, `Script not found`, or `FileNotFoundError` after code cleanup, rename, or `hermes update`.

## Step-by-step

### 1. Identify broken jobs
```bash
python3 -c "
import json
d = json.load(open('/Users/appleoppa/.hermes/cron/jobs.json'))
for j in d.get('jobs', d):
    if j.get('last_status') == 'error':
        print(f'{j[\"id\"]} | {j[\"name\"]} | {j.get(\"last_error\",\"\")[:80]}')
"
```

### 2. Extract script paths
```bash
python3 -c "
import json
d = json.load(open('/Users/appleoppa/.hermes/cron/jobs.json'))
for j in d.get('jobs', d):
    if j.get('last_status') == 'error' and j.get('script'):
        print(f'{j[\"name\"]}: {j[\"script\"]}')
"
```

### 3. Check script existence
```bash
for f in script1.sh script2.sh; do
    [ -f ~/.hermes/scripts/$f ] && echo "✅ $f" || echo "❌ $f MISSING"
done
```

### 4. Read each script and extract Python imports
```bash
cat ~/.hermes/scripts/broken_script.sh | grep -E "^(import |from |source )"
```

### 5. Check each imported module
```bash
# For agent/ modules
[ -f ~/.hermes/hermes-agent/agent/module_name.py ] && echo "✅" || echo "❌"
# For tools/ modules
[ -f ~/.hermes/hermes-agent/tools/module_name.py ] && echo "✅" || echo "❌"
# For scripts/
[ -f ~/.hermes/hermes-agent/scripts/script_name.py ] && echo "✅" || echo "❌"
```

### 6. Classify and act

| Classification | Action |
|---------------|--------|
| Module exists, was transiently unavailable | Re-enable job, test manually |
| Module deleted permanently | Disable job, set `paused_reason` |
| Module moved/renamed | Create wrapper script at expected path, or update shell script |
| Network/timeout transient | Leave enabled, self-heals |

### 7. Disable a job
```bash
python3 -c "
import json
d = json.load(open('/Users/appleoppa/.hermes/cron/jobs.json'))
for j in d.get('jobs', d):
    if j['id'] == 'TARGET_ID':
        j['enabled'] = False
        j['paused_reason'] = 'description of why'
json.dump(d, open('/Users/appleoppa/.hermes/cron/jobs.json','w'), ensure_ascii=False, indent=2)
"
```

### 8. Re-enable a job
Same as above but set `enabled=True` and `paused_reason=None`.

## Pitfalls

- **Don't assume missing = deleted**: Module may exist but import fails due to venv issues, missing dependencies, or the file being temporarily replaced during `hermes update`.
- **Check deeper dependencies**: A module may import another module that's missing. Always try actually importing: `cd ~/.hermes/hermes-agent && venv/bin/python -c "from agent.foo import bar"`.
- **Wrapper scripts for moved code**: When a script references `scripts/X.py` but code moved to `agent/X.py`, create a thin wrapper at the old path that imports from the new location.
- **Test before re-enabling**: Always run the script manually before re-enabling the cron job.
