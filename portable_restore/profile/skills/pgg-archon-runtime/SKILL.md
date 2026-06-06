---
name: pgg-archon-runtime
description: PGG Archon 本地运行入口：真实使用 Multi-Agent Debate、ECC三层治理、模块三态检查、SQLite持久化与DSPy/AgentVerse吸收模式。
version: 1.0.0
---

# PGG Archon Runtime — Compact

## Trigger

Use when running or auditing local PGG Archon runtime, Multi-Agent Debate, ECC governance, module three-state checks, SQLite persistence, GeneDB, legal AGI status, or DSPy/AgentVerse absorption patterns.

## Must-do local loop

```text
inspect local state → run bounded tool/module → verify output/readback → write report/gene only if evidence exists
```

## Three-state module口径

- `PASS`: implemented and verified by test/readback.
- `WATCH`: partially implemented or evidence insufficient.
- `BLOCKED`: missing dependency, unsafe boundary, or failed verification.

## Legal AGI boundary

Current legal AGI can be described only as bounded L6 process-gate reinforcement. Do not claim full AGI, zero-risk legal output, replacement of lawyer review, unsupervised production takeover, or official third-party certification.

## Feishu/provider boundary

Only default profile should hold active Feishu/Lark gateway credentials unless user explicitly authorizes otherwise. PGG department profiles should not compete for the same Feishu app.

## Execution evidence

Acceptable evidence:

- test output;
- DB/GeneDB row readback;
- report path + sha256;
- module status JSON;
- provider call trace when model audit is claimed.

## AGI process inspection

When the user asks to read system files or view the current AGI process, do not answer from memory or status slogans. Inspect live processes, launchd/cron sidecars, GeneDB/manifest rows, repo HEAD/status, and bounded test/readback evidence. Run module health probes from the same checkout + venv context used by launchd, separate live versus persisted evidence, deduplicate department gateway process rows, and label score provenance separately. Report separately: running services, scheduled evolution jobs, persisted AGI/legal-AGI state, recent commits, and boundaries/not-running daemons. If inspection reveals a low-risk reversible scheduled-sidecar defect, repair it immediately and verify both a direct rerun and a real scheduler-tick `last_status=ok` readback before reporting recovery. If a gate/sidecar artifact has a schema-consumer mismatch (for example a “summary” file contains a full manifest and readiness fields read as null), split the compact summary and full manifest, add deterministic schema/hash verification, smoke the consuming hook, and commit only relevant low-risk script changes after tests pass. See `references/agi-process-inspection-and-continuation.md`.

## Local non-Hermes agent inventory

When the user asks to inspect “other agents” on this machine, explicitly separate Hermes/PGG internal profiles from external agent systems. Use a bounded inventory loop: live processes → launchd services/plists → ports/health endpoints → package managers/CLI presence → app/native-host remnants → workspace repos/binaries → logs. Classify each finding as `running`, `installed_not_running`, `residual_broken`, `config_only`, `Hermes_internal_not_external`, or `intentionally_removed_unknown_until_user_confirms`; avoid treating historical manifests, installed packages, or filesystem presence as current online status. If a missing component is found during inventory, do not auto-restore it unless it is a verified active dependency or the user explicitly requests recovery. Cleanup may verify absence and delete mirrors/log remnants only when the user asks to delete them. See `references/local-non-hermes-agent-inventory.md`.

## Continuation hardening

When continuing a PGG Archon / SE20 evolution run, first inspect the working tree and verify any pre-existing diffs before adding new work. Do not preserve audit-score or model-audit claims unless backed by a real provider trace. Health/CLI readbacks may emit log noise, so capture stdout/stderr separately and parse structured JSON robustly. See `references/se20-continuous-evolution-hardening.md`.

For SE20 sidecar/egress/APEX-MEM continuation work: keep sidecar bridges loopback-only, strip large tool payloads, make live network bypass probes opt-in (`--live`), test resolved-IP and urllib3 interception, and stage only the verified files. See `references/se20-apex-mem-egress-continuation.md`.

## Core-takeover safety fuse

When a sidecar evolution chain reaches any "auto core takeover" or core-promotion boundary, add a separate safety-fuse gate instead of mutating Hermes core by default. Require explicit human authorization plus a rollback plan before any run_agent.py / scheduler / main-loop / security-boundary mutation. A blocked safety-fuse state is a valid PASS when it preserves the boundary. See `references/phase10-safe-core-takeover-fuse.md`.

## APEX repo unlock audit

When inspecting a local APEX/evolution repository for “unlocked modules,” use a repo-inventory → bounded-test → current-manifest comparison loop. Distinguish upstream PASS from local APEX-GOD integration, and classify candidates as P0/P1/P2/P3 with PASS/WATCH/BLOCKED evidence. See `references/apex-repo-unlock-audit-pattern.md`.

## Reference

Full historical runtime notes and command catalogue are archived at:

- `references/full-skill-archive-20260601.md`
- `references/phase10-safe-core-takeover-fuse.md`
