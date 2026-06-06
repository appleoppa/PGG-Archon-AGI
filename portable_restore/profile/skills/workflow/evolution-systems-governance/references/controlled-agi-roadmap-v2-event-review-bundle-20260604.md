# Controlled AGI Roadmap V2 — event ledger, dashboard, cron audit, review bundle

## Trigger

Use when the user says to continue AGI/PGG evolution strictly according to plan, avoid disruptive/destructive flows, and self-resolve blockers.

## Durable lesson

After a controlled roadmap phase is closed, do not rely on compressed or preserved todo state. First re-read the live truth sources:

1. `agent.pgg_archon_autonomous_status` dashboard output.
2. `~/.hermes/data/EVOLUTION_MANIFEST.json` capability `last_completed` / `next_step`.
3. `git status --short` and latest commits.
4. The latest gate artifact for the component being continued.

If preserved todos disagree with live evidence, correct the todos and proceed from the manifest/dashboard state.

## V2 sequence pattern

Advance exactly one component per round:

```text
V2-P0  autonomous loop appends event ledger
V2-P1  dashboard reads event ledger
V2-P2  cron/event audit gate
V2-P3  review bundle gate
V2-P4  open-source targeted absorption only if a real blocker appears
```

## Acceptance patterns

### V2-P0 — loop event integration

- Add append-only `PGGAutonomousEvolutionEvent/v1` emission per autonomous loop cycle.
- Preserve original cycle ledger and no-agent silence behavior.
- Event write failure should not destructively break the loop; record `event_ledger_status=WATCH` in the cycle record.
- Verify with `py_compile`, one real loop run, latest event readback, latest cycle readback, and `git diff --check`.

### V2-P1 — status dashboard event readback

- Dashboard adds `event_ledger_summary` with latest event, `by_source`, `by_status`, and event count.
- Read-only only; no runtime or ledger mutation.
- Known gaps should include unreadable/missing event ledger.

### V2-P2 — cron event audit

- Add a read-only gate that checks: cron present/enabled/no_agent, last status ok, cycle ledger readable/PASS, event ledger readable, latest event from python loop, event status matches cycle status, event references cycle ledger.
- Do not create, update, pause, resume, or replace cron from this gate.

### V2-P3 — review bundle gate

- Combine existing readiness package, main patch gate, and LLM quorum gate into a single read-only bundle.
- PASS means `READY_FOR_HUMAN_MAIN_PATCH_REVIEW`, not permission to apply the patch.
- Never call providers, apply patches, commit, or write GeneDB from the bundle gate.

### V2-P4 — open-source absorption

- Only trigger when a real blocker exists: failed gate, known gap, test failure, design blocker, or review bundle blocker.
- If `known_gaps=[]`, review bundle blockers are empty, and git is clean, do not browse GitHub/VX just to continue.

## Tool-output discipline

For terminal-facing reports, prefer compact status blocks and narrow key/value lists over wide tables. Wide tables wrap and reduce readability in this user’s terminal.

## Pitfalls

- Do not treat `generated_count=0` as failure by itself; a no-new-work cron tick can be PASS if ledgers and event audit agree.
- Do not let P4 become generic open-source wandering. It is a targeted blocker-resolution gate only.
- Do not auto-apply main patches or promote GeneDB from readiness/review bundle status.
- Do not let preserved task lists from context compression override live dashboard/manifest/git evidence.
