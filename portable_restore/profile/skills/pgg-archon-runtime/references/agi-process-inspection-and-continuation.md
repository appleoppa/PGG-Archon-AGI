# AGI process inspection and continuation notes

Use this reference when the user asks to “读取系统文件 / 查看现在 AGI 进程” or says “继续” during a PGG Archon / SE20 evolution run.

## Inspection sequence

1. Confirm live runtime state instead of relying on memory:
   - process list for Hermes Web UI, gateway/bridge, cron, Python sidecars, APEX-MEM sidecar;
   - launchd/cron job status where available;
   - repo `git status`, HEAD, staged files, ignored workspace artifacts;
   - GeneDB / manifest readback for legal AGI and SE20 state.
2. Classify state honestly:
   - `running service`: live process exists;
   - `scheduled sidecar`: cron/launchd exists and last status is known;
   - `persisted state`: DB/manifest row exists but no daemon is live;
   - `not running / not verified`: no live evidence.
3. For legal AGI, keep the bounded口径:
   - OK: L6 有边界法律办案流程门禁强化版 / process-gate reinforcement;
   - forbidden: full AGI, zero risk, lawyer replacement, unsupervised production takeover, official third-party certification.

## Continuation pattern learned from this session

- Before adding new work, resolve uncommitted or sibling-agent diffs; do not silently preserve unsupported audit-score inflation.
- Default bypass/integration scripts must be static and side-effect-free; live network probes require an explicit `--live` flag.
- Sidecar bridges such as APEX-MEM should be loopback-only and should summarize large payloads before returning tool output.
- Keep commits local only when the user has authorized local snapshots; do not push or open PRs without explicit authorization.

## Active repair during inspection

Inspection is not read-only reporting when a low-risk reversible runtime defect is exposed. If a scheduled AGI sidecar reports `last_status=error`:

1. Read the scheduled script and run it directly from its declared workdir.
2. Check executable mode before debugging application logic.
3. Inspect the called function's return schema. Empty queues and no-op paths often return a smaller payload than success paths; shell wrappers should use defensive defaults such as `result.get("errors", [])` and `result.get("remaining_in_queue", 0)`.
4. Apply the smallest reversible patch, rerun the script directly, then trigger or wait for one real scheduler tick.
5. Re-read scheduler state and report recovery only when `last_status=ok` is visible. A successful manual run alone is not scheduler recovery evidence.
6. Record the changed script hash when the repair affects a recurring evolution job.

When invoking Python modules manually, reproduce the service runtime context: use the checkout workdir, its venv Python, and the same `PYTHONPATH` carried by launchd. A bare interpreter failure does not prove the daemon module is unavailable.

## Additional inspection pitfalls

- Run an APEX-GOD health probe from the same runtime used by launchd (normally the Hermes agent checkout plus its venv). If a system `python3 -m apex_god.health` probe fails outside that context, retry in the service context before classifying the module as unavailable.
- Parse the structured health JSON and report both the final exit code and `overall_healthy` / passed-check count. A fail-closed test probe may deliberately emit a warning while still completing successfully; do not treat probe stderr alone as an active outage.
- Keep `live process`, `launchd service`, `Hermes cron job`, and `persisted manifest` as separate evidence classes. A component mentioned in a manifest is not a live daemon unless process or launchd evidence exists.
- For department gateways, derive the count from the actual process rows and deduplicate profile names before reporting. Do not hand-expand a list from memory. A running department gateway is not evidence that it owns messaging credentials; inspect profile config separately when messaging-channel contention matters.
- Resolve the actual Git root before stating HEAD or working-tree status. A nested workspace directory may not itself be a repository even when its parent is. Report clean/dirty status only for the verified Git root.
- When reporting several score sources, label their provenance and timestamp separately: daemon live scorecard, manifest persisted score, and bounded legal-AGI gate score are different measurements and should not be merged.

## Report shape

Use short fields:

```text
AGI进程：running / scheduled / persisted / not running
证据：process / cron / DB / manifest / test / commit
边界：what is not running or not claimed
下一步：only if >75% safe and reversible, continue directly
```
