# Round6 ledger-vs-fresh evaluation and overlay audit pattern (2026-06-03)

## Trigger

Use this pattern when a PGG Archon / Hermes evolution status looks healthy in a ledger or tool action, but a fresh runtime evaluation may tell a different story.

## Session learning

A status like `readiness=89.6` / `Rust ΔE=4.8` can be truthful as a ledger/workspace-evidence score, while a fresh `hermes-agent` root evaluation returns a much lower `ΔE=1.25`. These are different mouths, not necessarily fraud:

- ledger/workspace score: depends on prior evidence files, scout cache, event logs, smoke artifacts, and fused ledger state.
- fresh agent-root score: measures immediately reproducible baseline from the current root and may expose missing evidence/context.

Never collapse these into one number. Report them side by side with prerequisites.

## Required audit additions

1. Run the normal status/test/action checks.
2. Run a fresh Rust/APEX evaluation from the relevant root and compare it with ledger/tool-action scores.
3. Check git cleanliness AND ignored overlays:
   - `git status --short`
   - `git status --short --ignored=matching -- apex_god agent/pgg_archon_*.py agent/apex_*.py`
   - `git check-ignore -v <representative files>`
   - `git ls-files apex_god agent/pgg_archon_*.py agent/apex_*.py | wc -l`
4. Treat `.git/info/exclude` overlays as a governance boundary, not as ordinary untracked files. Do not directly add/commit/delete them before classifying whether they are runtime compatibility layers, historical overlays, archive candidates, or source files that should become tracked.
5. Import-check named modules from the manifest; if manifest claims components that no longer import, mark WATCH and determine whether they were intentionally replaced.
6. If multi-model auditing is requested, record failed provider calls as evidence too. A GPT/Claude/DeepSeek participant only counts if the API call really happened; HTTP 502 is evidence of attempted participation but not an audit opinion.

## Reporting language

Use concise Chinese fields:

```text
状态：WATCH / PASS / BLOCKED
综合评分：N/100
账本口径：readiness=..., ΔE=...
fresh 口径：ΔE=..., factors=...
模型证据：GPT=HTTP..., Claude=HTTP..., DeepSeek=HTTP...
主要风险：ignored overlay / import failures / gateway reload uncertainty
边界：not full AGI; not 10x; not external AGI benchmark
```

## Gateway action recognition

If a new read-only tool action was added:

- First prove direct `handle_*` invocation works.
- Prefer a new-session smoke test to see whether running gateway sessions recognize it.
- Only restart the relevant gateway if smoke fails or immediate runtime pickup is required.
- Do not batch-restart all department gateways without a failure signal.
