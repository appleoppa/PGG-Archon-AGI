# Router/Web Runtime Gate and Anti-Stall Workflow — 2026-06-06

## Why this exists

In a PGG Archon Router/Web hardening session, the user explicitly challenged the agent with “怎么又卡了” after a skill was loaded but no concrete action followed. Treat that as a durable workflow correction for system-repair and governance tasks: loading a skill is not progress unless followed immediately by real inventory/test/repair actions and concise progress evidence.

## Anti-stall rule for important tasks

After loading any relevant skill for AGI/evolution/Hermes/system-repair work:

1. Immediately perform the next concrete tool action: inventory, read diff, run focused test, or produce review pack.
2. If a step may take more than ~10 seconds, send a one-line Chinese progress note with the expected window, then execute the tool.
3. Do not stop at “已加载技能/研判中”. The user experiences that as non-execution.
4. If the user asks “怎么又卡了”, acknowledge the stall briefly and resume with a concrete tool call; do not defend the pause.

## PGG Router/Web runtime gate pattern

Use this pattern when hardening local router, model/provider routing, Web API execution endpoints, or run-agent hooks.

### Scope split

Keep groups separate and commit only one group at a time:

- Router/Web/runtime hook files.
- Provider/legal benchmark runners.
- Rust/PyO3 surfaces.
- pnpm/workspace artifacts.

Before commit, run a forbidden-stage check to ensure unrelated files are not staged.

### MiMo / audit judge isolation

When MiMo is reserved as third-party judge/benchmark auditor, block it from ordinary execution at multiple layers:

1. Router/provider call execution layer rejects aliases before calling `call_provider`.
2. Default multi-provider pools filter out judge aliases.
3. Web API validators reject judge aliases with HTTP 400 for ordinary task/call/multicall endpoints.
4. Tests prove explicit MiMo requests do not reach provider invocation.

Typical aliases:

```text
mimo
mimo_v25_pro_auditor
custom:mimo_v25_pro_auditor
```

### Web API bounds

For execution endpoints, add helper validators before calling the executor:

- Non-empty task/prompt.
- Max task/prompt length.
- Timeout clamp with finite lower/upper bounds.
- Max provider count for multicall.
- Provider alias blocklist for judge-only models.

Focused tests should cover empty input, overlong input, timeout lower/upper clamp, provider-list limit, and blocked judge aliases.

### run_agent hook boundary

If a runtime hook is meant to be mirror-only or route-suggest only, verify and document:

- It does not mutate `self.provider`, `self.model`, user message, system message, history, or task id.
- It does not substitute the selected provider into the actual execution path.
- The real `run_conversation` or equivalent call receives the original execution arguments.
- Evidence/mirror recording is wrapped fail-open (`try/except` that does not break normal task execution).

### Multi-LLM review pack

For Claude/MiMo/GPT review, include enough code to avoid “missing diff” WATCH:

- Full targeted diff or critical code snippets for every file you intend to stage.
- Focused test output and py_compile output.
- Exact stage list and hold list.
- Truth boundary: local gate ≠ production traffic, external benchmark, legal correctness, or AGI level.

If v1 review returns WATCH because code snippets were incomplete, generate a targeted v2 review pack with the missing snippets and rerun before committing.

## Commit and manifest closure

A truthful close requires:

1. Focused tests and compile checks pass.
2. LLM review failures/timeouts are labeled `ERROR`/`WATCH`, not hidden.
3. Only scoped files are staged.
4. Commit is read back by `git show --name-status` and `git status --short`.
5. `EVOLUTION_MANIFEST.json` is updated and read back.

## Boundary wording

Safe claim: local Router/Web execution gates and mirror-only hooks passed focused tests and targeted LLM review.

Unsafe claim without more evidence: production Web UI traffic has been validated, routing has taken over Hermes provider selection, legal correctness is proven, external benchmarks passed, or AGI/T-level increased.
