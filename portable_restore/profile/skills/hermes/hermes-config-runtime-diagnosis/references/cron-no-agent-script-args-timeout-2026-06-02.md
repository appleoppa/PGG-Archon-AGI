# Cron no-agent script args / delivery / timeout runbook (2026-06-02)

## Trigger

Use when a Hermes cron job with `no_agent=true` reports `last_status=error`, especially when the job uses `script`, `deliver=origin`, or a long-running shell/Python workflow.

## Failure patterns

### 1. Script field contains arguments

Observed shape:

```json
"script": "pgg_github_knowledge_brief.sh evening"
```

Hermes cron resolves `script` as a script path under `~/.hermes/scripts/`; it does **not** split the field into script + argv. The runner tries to find a literal file named:

```text
~/.hermes/scripts/pgg_github_knowledge_brief.sh evening
```

Symptom:

```text
Script not found: /Users/.../.hermes/scripts/<script>.sh <arg>
```

Fix pattern:

- Create small wrapper scripts under `~/.hermes/scripts/`:

```bash
#!/usr/bin/env bash
set -euo pipefail
exec "$HOME/.hermes/scripts/pgg_github_knowledge_brief.sh" evening
```

- Mark executable with `chmod +x`.
- Update cron `script` to the wrapper filename only.

### 2. `deliver=origin` but origin is null

Symptom:

```text
last_delivery_error: no delivery target resolved for deliver=origin
origin: null
```

Fix pattern:

- If the job was created outside an interactive origin, set `deliver=local`, or explicitly set a known platform target.
- Do not leave unattended no-agent jobs on `origin` when `origin` is null.

### 3. Long no-agent script exceeds cron runner timeout

Symptom:

```text
Script timed out after 360s
```

Diagnosis pattern:

- Time the expensive subcommands with smaller input sizes, e.g. `--per-cat 1`, `--per-cat 3`.
- Check whether output artifacts were partially generated before timeout; do not call the job fully successful if cron state is error.

Fix pattern:

- Bound default workload so the entire shell script finishes under the runner timeout.
- Add an environment-variable override for manual/deep runs, e.g.:

```bash
PER_CAT="${PGG_GITHUB_KNOWLEDGE_DEEP_PER_CAT:-6}"
python3 script.py --per-cat "$PER_CAT"
```

- Preserve verification steps: `bash -n`, a small smoke run, and cron list/readback.

## Verification checklist

1. `cronjob(action='list')` and inspect `last_error`, `last_delivery_error`, `script`, `deliver`, `origin`.
2. Read the script and confirm no arguments are embedded in the cron `script` field.
3. `bash -n` wrapper and target scripts.
4. Run a bounded smoke test (`PER_CAT=1` or equivalent) and read output.
5. Re-list cron jobs to confirm updated `script` and `deliver` fields.

## Reporting contract

Report separately:

- `root_cause`: config path/argument handling vs delivery vs runtime timeout.
- `fix_applied`: exact wrapper/update/workload bound.
- `verification`: syntax check, smoke output, cron readback.
- `remaining_risk`: e.g. full default run not yet waited through until scheduled fire.
