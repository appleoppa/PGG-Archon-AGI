---
name: pgg-archon-external-repo-absorption
description: 外部仓库最大合规吸收：多 LLM 代入公式、证据门禁、分层吸收、禁止整包吞高风险代码
version: 1.0.0
tags: [pgg-archon, absorption, multi-llm, security, evidence]
---

# PGG Archon External Repo Absorption

## Trigger

Use when the user asks to absorb, merge, harden, or learn from an external repository into PGG Archon/Hermes, especially if the repo claims agent, AGI, evolution, prompt, memory, routing, or governance capabilities.

Also use when converting an external agent platform into an auxiliary/second AGI-like node: first deploy and smoke-test the upstream project unchanged, then add an additive PGG overlay for shared context, formulas, and evidence. If the auxiliary agent must be physically independent from Hermes, do not place it under `~/.hermes/workspace` and do not create visible Home-root project folders. Use hidden roots analogous to `~/.hermes` (for example `~/.pilotdeck-agi`) and a hidden neutral bridge (for example `~/.agent-bridge`). Configuration comes before evolution: verify the target agent's UI, gateway, native config loader, Web UI config API, and startup environment before pushing formulas/manifests. See `references/hidden-agent-bridge-second-agi.md` and `references/second-agent-config-first-bridge.md`.

Reference: for GitHub mirror/fork comparisons before absorption, use `references/apex-skill-remote-mirror-comparison.md`. For local multi-source Desktop/workspace repos plus spec-folder integration into a user-owned private GitHub repo, use `references/local-multisource-private-repo-sync-usage-docs.md`: hidden clone, clean non-destructive sync, spec-to-usage-docs, nested-project verification, scoped push, and remote content readback.

Also use when the user wants an external repo to become an independent agent that co-evolves with Hermes/PGG Archon. In that case, do **not** default to placing the repo under `~/.hermes/workspace`; first decide whether the correct shape is absorption into Hermes or physical isolation as a separate agent bridged through a neutral exchange directory.

Also use when converting an external agent platform into an auxiliary/second AGI-like node: first deploy and smoke-test the upstream project unchanged, then add an additive PGG overlay for shared context, multi-LLM audit, and formula gates. If upstream provider protocols conflict with Hermes model discipline, keep incompatible providers out of native upstream config and call them from the overlay through the correct endpoints. For a standalone agent such as PilotDeck, keep physical isolation from Hermes and avoid visible Home-root project folders: use hidden roots such as `~/.pilotdeck-agi` and a separate hidden bridge such as `~/.agent-bridge`; do not place the standalone agent under `~/.hermes/workspace` or create visible folders like `~/PilotDeckAGI`. Before any file operation, explicitly choose hidden roots and verify Home-root pollution risk. For the generalized hidden-directory + localhost LLM bridge pattern, see `references/independent-agent-hidden-bridge.md`; for the original PilotDeck session detail, see `references/pilotdeck-second-agent-overlay-20260602.md`.

## Formula

`AK_absorb = EvidenceFit*0.25 + Safety*0.25 + Utility*0.20 + Reversibility*0.15 + Testability*0.15 - RiskDebt*0.30`

Promote only when evidence is real and score is high enough. Never mark a gene verified without tool/model/test/readback evidence.

## Workflow

### Phase A — Activation discipline (use when activating absorbed modules one-by-one)

#### Module boundary declaration pattern

Before activating any module, explicitly declare what it does NOT do as a docstring block at the top of the module file:

```python
"""PGG Archon <ModuleName>.
Boundary: no LLM calls, no filesystem writes, no Hermes core mutation, <other-specific-exclusions>.
"""
```

Common exclusions per module type:

| Module Type | Typical Boundaries |
|---|---|
| Constraint/Formula | No LLM calls, no I/O |
| Scanner/Analyzer | No auto-fix, no mutation |
| Scoring/Measurement | No writes, no persistence |
| Classifier/Review | No LLM calls, no auto-approve |
| Plan/Scheduler | No broken upstream formulas (verify range), no auto-verify |
| Validator | No external deps (JS/ruby), no hardcoded /root/* paths |

Include these boundaries in the manifest component entry under a `"boundary"` field for auditability. A module without a boundary declaration is incomplete — it's implicitly claiming unlimited scope.

1. **Dependency order first**: Determine DAG — foundation layer (DeltaG) → scanner (CodeGenesis) → measurement (memory/trace) → upper-layer (self-loop). Never activate children before parents.
2. **Audit upstream code** before writing any local module: check hardcoded paths, I/O side effects, external deps, package naming issues. Note risks (write behavior, /root/ paths, duplicated formulas) but do not automatically re-implement them.
3. **Simulate in isolation** for risky or complex formulas: create a standalone script in /tmp, verify outputs are bounded (no NaN, no Inf, no negative clamp bypass), then delete it. Only proceed to activation if the simulation is clean.
4. **One module at a time, per-step verification**:
   - Create module file + tests → run tests only for this module.
   - Run all prior modules' regression tests.
   - Integrate into health check (add R# check + _ALL_CHECKS entry).
   - Update manifest (milestone entry + component map + capability dict).
   - Run `python -m apex_god.evolution_manifest --update` and confirm via JSON readback.
   - Run full system health check (`python -m apex_god.health`) — every R# must pass.
   - Check system load (uptime) — must be stable (<= 3.0).
   - Only then commit and proceed to the next module.
5. **Land before proceeding**: After the last module in a batch, generate a final landing report under `workspace/治理/apex_repo_unlock_audit/APEX_UNLOCK_FINAL_YYYYMMDD.md`. Delete temporary simulation files and supersede any stale draft reports from earlier broken attempts. If the user says "落地后再继续", stop and present the landing state — do not proceed to the next batch without explicit continuation.

### Reference: full 8-module walkthrough

See `references/8-module-absorption-walkthrough-20260602.md` for a complete walk-through of absorbing 8 modules, and `references/phase-file-simulation-fix-patterns-20260602.md` for concrete patterns to detect and fix hardcoded simulation stubs in phase evolution files.

### Pitfall: stale __pycache__ after git rollback

When you `git reset --hard` to roll back modules, old `.pyc` files remain in `agent/__pycache__/` and `tests/agent/__pycache__/`. If the reverted module had different field schemas (e.g. extra dataclass fields), pytest imports the stale `.pyc` instead of recompiling, causing `TypeError: missing 2 required positional arguments` that points at the current .py source (misleadingly). The fix:

```bash
find . -path '*__pycache__*' -delete
```

Run this before any test cycle after a git rollback that touched Python modules. To verify the cache is clean, confirm that `find . -path '*__pycache__*' -name '*.pyc' | wc -l` returns 0 or is very small after deletion.

### Pitfall: sibling subagent file interference

When multiple subagents work on the same repo concurrently, they can modify files between your reads and writes. This manifests as:
- `LSP diagnostics introduced by this edit` errors naming fields from a different version of the file
- `File was modified by sibling subagent <id> at <time>` errors from patch() when the file content doesn't match what you read
- Stale variable-name references (e.g. `ast_hotspot_summary` vs `ast_hotspots`) because a sibling added fields to a dataclass while you were working on the return statement

**Mitigation before any write or patch:**
1. Re-read the file immediately before writing/patching, even if you read it earlier in the session
2. Clear `__pycache__` after resolving a conflict (`find . -path '*__pycache__*' -delete`)
3. Check for fields in the dataclass definition that may differ from the return statement — siblings may have added fields to one without updating the other

### Pitfall: phase file simulation stubs

Pre-existing phase evolution files often return hardcoded PASS statuses without doing real work. Signals:
- Schema name contains `Simulation`, `Mock`, or `Sim` (e.g. `PGGArchonPhase151BenchmarkLocalMockRun/v1`)
- Variables named `simulated_*` (`simulated_hours`, `simulated_minutes`, `simulated_stall`)
- Hardcoded `readiness_score` (e.g. 88.0, 87.0, 90.0)
- `third_party_eval_completed: False` + `external_code_execution: False` paired with `PASS` status
- `ticks` computed from loop iteration, not real system state
- `real_production_action_executed: False` and `network_action_executed: False` without documented expectation

Fix pattern (replace hardcoded sim with real system checks):
```python
# Before: hardcoded pass
out = {"readiness_score": 88.0, "third_party_eval_completed": False, "status": "PASS"}

# After: real daemon/file/config check
import subprocess
daemons = ["com.appleoppa.apex-god.ars", "com.appleoppa.apex-god.autoloop", ...]
running = sum(1 for d in daemons
    if subprocess.run(["launchctl", "list", d], capture=True, timeout=5).returncode == 0
    and "PID" in r.stdout)
out = {
    "readiness_score": 60.0 + (running / len(daemons)) * 35.0,
    "third_party_eval_completed": running > 0,
    "status": "PASS" if running >= threshold else "FAIL",
    "daemons_running": running,
    "daemons_total": len(daemons),
}
```

### Pitfall: pre-existing health check failures

Before absorbing new modules, check if there are pre-existing health check or test failures that are unrelated to your work. Run `python -m apex_god.health` and a full pytest suite before starting. Document any pre-existing failures in a note so they don't get blamed on your new modules:
- If a health check R# was already 24/24 before you started, and becomes 23/24 after your changes, the failure is in YOUR code, not pre-existing.
- If a test failure predates your changes (e.g. `test_apply_auto_core_takeover_context_is_bounded_and_idempotent`), note it as pre-existing before you start modifying anything.

### Verification step: GPT + Claude cross-audit for simulation detection

After activating 2+ modules, optionally run a cross-audit using both GPT and Claude (via the agnes custom provider) to detect simulation/hardcoded patterns before final integration:

```python
# Call both GPT-5.5 and Claude Opus 4 via codex_responses API
for name in ["gpt55_5yuantoken", "claude_opus46_5yuantoken"]:
    r = requests.post(
        base_url + "/responses",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": model,
            "input": f"Audit these files for simulation/fake/hardcoded code: {json.dumps(file_summaries)}",
            "instructions": """Classify each file as REAL / SIMULATED / MIXED.
For SIMULATED files, identify the specific fake aspects and whether fix is needed.""",
            "max_output_tokens": 2000
        }
    )
```

Both models must independently agree on the classification. Fix all files classified as SIMULATED before running the final health check. Update the reference file documenting which files were fixed and what the replacement checks are (e.g. `references/phase-file-simulation-fix-20260602.md`).

### Phase B — Absorption workflow

1. Create a bounded evidence pack: repo HEAD, tests, security scans, audit reports, candidate list.
2. Call real configured LLM providers when requested; record provider/model/status/elapsed/output path.
3. Classify each candidate:
   - `PROMOTE_TO_VERIFIED_CANDIDATE`: process/rule/test pattern with real verification.
   - `PROMOTE_TO_ACTIVE_REVIEW_GENE`: useful but needs local code review before enforcement.
   - `KEEP_ACTIVE_CANDIDATE`: keep as watch item.
   - `BLOCK`: unsafe, unverified, or too invasive.
4. Absorb in layers:
   - first: process/rule/test templates;
   - second: security review gates;
   - third: code patterns only after P1/P2 debt is closed;
   - never auto-mutate Hermes core scheduler/main loop/security boundary.
5. Verify with readback: report path, sha256, GeneDB rows if written, tests if code changed.
6. If the upstream repo is useful but fails its own packaging/integrity checks, use the private mirror repair pattern: preserve the upstream failure evidence, repair only in the private backup/mirror, re-run the same tests, push, and read back private visibility/head before reporting. See `references/private-mirror-repair-pattern.md`.
7. If the user asks to save an external repo as a private remote and compare a local copy, preserve upstream/private HEAD first, then cherry-pick only verified useful local deltas. Never force-push an older local branch over a newer upstream mirror. See `references/private-mirror-local-delta-cherry-pick.md`.
8. If the user asks to compare user-owned private mirrors, delete the obsolete mirror, and repair the surviving repo, use `references/private-mirror-diff-delete-and-test-repair.md`: verify exact remote identity, compare commit graph and file diffs from remote refs, delete only the named user-owned repo, reproduce/fix tests, push scoped changes, and read back the remote head.
9. If the user wants a local external repo saved to their own private GitHub for cross-machine deployment and the local repo is shallow or LFS-constrained, use `references/private-github-deploy-snapshot-shallow-lfs-pattern.md`: direct push may fail with missing objects; create a clean tracked-file snapshot excluding secrets/runtime state, handle `.gitattributes`/Git LFS filters explicitly, push the private snapshot, and read back remote files. If upstream LFS budget blocks media fetches, call it a code/deployment snapshot and document the media boundary instead of claiming a full asset mirror.

## Independent agent physical isolation

When the external repo is intended to become a separate agent, enforce a three-root layout before deployment:

```text
Hermes root: ~/.hermes
External agent root: an explicit non-Hermes directory such as ~/PilotDeckAGI
Bridge root: a neutral exchange directory such as ~/AgentBridge
```

Only the bridge exchanges read-only snapshots, inbox/outbox messages, health reports, and mutual-learning proposals. Do not let the external agent share Hermes runtime/config/state folders. See `references/independent-agent-physical-isolation-bridge.md` for the full checklist and pitfalls.

## Boundaries

- Do not claim all LLMs participated unless each provider was really called; missing API key = skipped.
- Do not整包吞噬 repos with unresolved P0/P1 security debt.
- Do not copy secrets, credentials, or unvetted network/provider code into Hermes core.
- GeneDB writes require evidence fields: source refs, boundary, reusable rule, verification status, hash.

## Rust/runtime/live gate closure pattern

When a PGG Archon task claims a Rust module, routing surface, dashboard/API, or web UI has landed, require a layered evidence chain before staging or reporting completion:

1. **Rust compile gate** — enumerate every `Cargo.toml`; run `cargo test` and `cargo build --release` per crate; for PyO3/cdylib crates, copy/sign/import-smoke the `.dylib/.so`; record env, exit codes, artifacts, sha256, and boundary.
2. **Runtime integration gate** — prove Python/API/UI bridge participation with focused pytest. If tests reveal API contract drift, add backward-compatible wrappers rather than rewriting production paths or changing tests to hide the drift.
3. **Live Web/API gate** — start a temporary local web server with a fixed session token; test snapshot/control/SSE endpoints; verify 401/400 negative cases and POST side-effect readback; terminate the server; store `result.json`.
4. **Frontend build gate** — run the TypeScript/Vite build. If pnpm blocks dependency build scripts, use the smallest project-scoped approval needed and record it as build-environment evidence, not as capability proof.
5. **Multi-LLM + open-source learning gate** — call available daily LLMs, GPT/Claude via the configured Hermes provider path when direct Responses calls fail, and Agnes only as third-party judge if policy says so. Public GitHub/docs learning is read-only unless explicit code absorption is authorized.
6. **Pre-commit gate** — create a bounded review pack, call Claude for stage/hold advice, then perform self-review. Stage only scoped files covered by tests; hold workspace evidence, generated high-noise package files, unrelated modified files, and unreviewed crates. Re-run staged verification before commit.

If a user policy says a provider is third-party judge only, treat any diff that moves it into ordinary processing pools as a correctness bug even if tests were updated to pass. See `references/rust-runtime-live-gate-closure-20260605.md` for the session pattern.

## Blocker remediation pattern

When an item is blocked, do not stop at explanation. Run a second loop:

1. Locate concrete code surfaces for the blocker.
2. Ask real available LLMs to review a bounded fix plan.
3. Search authoritative open-source references before deciding whether a scanner warning is a true risk or a guarded false positive.
4. Implement low-risk fixes with tests.
5. Re-run tests and security scans.
6. Re-call LLMs on post-fix evidence.
7. If using a static-analysis suppression such as `# nosec`, make it line-specific, rule-specific, and explain the guard inline; never add broad exclusions.
8. Promote only to the highest truthful status:
   - `verified`: fixed + tested + readback, no material boundary, or explicitly bounded pattern-only verification.
   - `active`: useful rule/pattern absorbed, but residual static noise or core-not-merged boundary remains.
   - `candidate`: reference only.
9. Write GeneDB rows only after post-fix evidence exists.

Residual Bandit/static-analysis noise may be documented or suppressed only when code-level guard, authoritative references, and regression tests prove the boundary. Detailed reference: `references/static-analysis-remediation.md`.

### Pitfall: cross-session provider-role drift

When continuing PGG Archon / multi-LLM work across sessions, provider roles may have been updated elsewhere. Before treating a provider-role diff as wrong, search recent sessions or current memory for explicit user updates.

Current durable rule from 2026-06-06: MiMo (`mimo_v25_pro_auditor`) is the fixed third-party benchmark/audit judge and should be excluded from ordinary processing pools; Agnes is unstable and may be used only as ordinary/non-critical collaboration with failures recorded honestly. If code/tests still encode the older “Agnes = third-party judge” rule, update them to MiMo-as-judge and add tests that assert:

- default/ordinary provider pools exclude MiMo;
- third_party_judge pools include MiMo;
- Agnes may appear only in ordinary/non-critical pools and is not relied on as the fixed judge;
- failure/instability of Agnes is surfaced as `ERROR`, not silently converted into PASS.

## Desktop evolution/formula-note absorption pattern

When the user provides local AGI/evolution formula notes or reports claiming hidden features / 10x gains / AGI levels, use `references/desktop-evolution-formula-learning-pattern.md`: hash/read all files, call configured LLMs, distinguish HTTP success from visible model output, downgrade unverifiable claims, absorb formulas as bounded process/rubric assets, and verify with health/convergence/Rust evaluate before updating the manifest.

## GitHub knowledge radar / cron briefing pattern

When the user asks for broad GitHub absorption plus wiki/KB creation, parser handling, “all LLM” audit, and daily briefings, use the class-level pattern in `references/github-knowledge-radar-cron-pattern.md`. For the second-stage README/LICENSE/tree enrichment and capability factor scoring pattern, use `references/github-knowledge-enrichment-factor-matrix.md`.

Key additions:

- Build a dedicated workspace knowledge base with `wiki/`, `data/`, `gallery/`, `audits/`, `briefs/`, `scripts/`.
- Treat ambiguous project names as candidates until uniquely verified; GitHub search hits are not proof of intended identity.
- Persist normalized repo cards and Markdown project cards before claiming absorption.
- Preferred parsers/search tools must be actually available and run; otherwise use a recorded compatible fallback.
- After first-pass radar, if next-step value is >75%, continue into read-only enrichment: fetch README/LICENSE/tree/API metadata, generate a capability factor matrix and per-repo factor cards.
- Penalize low-evidence repos in the factor matrix so noisy keyword hits cannot outrank well-evidenced projects.
- Keep morning/evening cron bounded; put heavier Top10/full-category enrichment into a separate local deep cron to avoid timeout and channel spam.
- Daily morning/evening briefings can be scheduled as `no_agent=true` cron when the script itself produces final stdout.
- Distinguish “continuous ingestion/enrichment loop installed” from “all repositories fully understood”.
- For high-readiness PGG evolution sessions where the remaining gap is “cross-domain benchmark not run,” use the bounded local process-smoke pattern in `references/bounded-cross-domain-process-smoke-20260603.md`: validate evidence across legal/governance, provider/runtime, Rust evolution, open-source research, audit hashes, formula semantics, and ops supervision, but keep it explicitly separate from external AGI benchmarks such as MMLU/GSM8K/AgentBench.
- For evolution prompts that ask to learn from GitHub/open source, use the bounded read-only scout pattern in `references/bounded-github-scout-evolution-absorption.md`: track search JSON, README snapshots, visible-output LLM counts, promoted patterns, and blocked claims without importing/running external code unless separately authorized.
- After Rust/PyO3/runtime integration gates pass for a Web UI/API feature, do **not** claim live readiness until a temporary local server smoke verifies protected snapshot/control/SSE endpoints, negative auth/payload cases, control side-effect readback, and frontend TypeScript build. Use `references/live-web-api-gate-multillm-oss-20260605.md` for the full multi-LLM + OSS + live Web/API gate pattern.

## Local replacement + private mirror workflow

Use this when the user wants to discard an older local repo and keep an externally cloned fork/project as the canonical local/remote artifact.

1. **Delete only user-owned targets**: remove the stale local clone and check the user's own remote with `gh repo view <user>/<repo>` before deleting. Do not attempt to delete or mutate upstream repositories owned by others.
2. **Preserve upstream separately**: set `origin` to the user's private mirror and keep the original source as `upstream` so future pulls/audits remain traceable.
3. **Sanitize before mirroring**: remove tracked runtime artifacts (`data/*.db`, `*.pid`, `__pycache__`, `*.pyc`, local logs), add durable `.gitignore` patterns, replace secret-like placeholders (`sk-*`, `ghp_*`) with inert `REPLACE_ME_*` values, and prefer localhost default binds for services.
4. **Audit + fix before push**: run real local verification (`cargo fmt --check`, `cargo check`, `cargo test`, `cargo clippy --all-targets -- -D warnings`, release build/smoke for Rust projects) and incorporate multi-agent / multi-LLM audit findings before committing.
5. **Remote readback**: after push, verify `gh repo view`, `git ls-remote`, and local `git rev-parse` agree on branch and commit. If `--force-with-lease` rejects due to stale info, fetch the mirror and retry with an explicit lease (`--force-with-lease=branch:<old_sha>`) after inspecting the remote head.

## Output contract

Return: model call evidence, open-source references consulted, scanner/test before-after counts, promoted items, blocked items, written files/DB rows, cron job IDs when scheduled, knowledge base paths, and remaining blockers.

## Live Web/API + multi-LLM closure pattern

When the user asks to “调用所有 LLM + GitHub/开源网站全量学习解决” after a Rust/runtime gate, do not stop at advisory reports. Use this closure sequence:

1. **Multi-LLM evidence**: call available daily providers; call GPT/Claude through the configured Hermes provider path if direct Responses HTTP fails; use Agnes only as third-party judge when that is the user rule. Record direct failures separately and do not hide them.
2. **Read-only open-source scout**: use authoritative docs and GitHub search as patterns only; do not import or execute external code unless separately authorized. For SSE/EventSource gates, durable patterns include `text/event-stream`, `event:/data:` framing, EventSource no-custom-header limitation, side-effect readback for control endpoints, and negative auth/payload tests.
3. **Live API gate**: start a temporary loopback server with fixed ephemeral session token; verify snapshot schema, control POST side-effect readback, SSE stream chunk/header framing, unauthorized 401, invalid payload 400; terminate the server and write a result JSON.
4. **Frontend gate**: run TypeScript/Vite build or equivalent contract check; if package-manager security blocks build scripts, apply the minimal explicit approval needed and report it as a build-environment action, not as application logic.
5. **Manifest + boundary**: update `EVOLUTION_MANIFEST.json` only after readback. Boundary must state that local live gates are not browser visual QA, production traffic proof, official external benchmark success, or AGI-level advancement.

For a concrete session pattern and evidence checklist, see `references/live-web-api-multillm-closure-20260605.md`.
