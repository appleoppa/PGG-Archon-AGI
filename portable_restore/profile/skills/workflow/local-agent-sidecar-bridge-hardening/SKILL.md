---
name: local-agent-sidecar-bridge-hardening
description: 通用本地 agent sidecar bridge 硬化：只读基线同步、HMAC签名、防重放、schema白名单、脱敏负测、运行时证明、多LLM复审。
version: 1.0.0
metadata:
  hermes:
    tags: [sidecar, bridge, hardening, hmac, nonce, schema, redaction, runtime-attestation]
---

# Local Agent Sidecar Bridge Hardening

## Trigger

Use when connecting two local agent runtimes through a low-risk bridge, especially when the bridge must remain local, verifiable, and non-invasive.

## Boundaries

- Prefer local sidecar overlay over core mutation.
- Bind to loopback only unless the user explicitly approves remote exposure.
- Do not mutate either runtime's scheduler, main loop, security boundary, or source tree by default.
- Do not expose raw secrets, env values, bearer tokens, absolute internal paths, raw prompts, or full logs in manifests.
- Do not claim equal intelligence, full AGI, production-grade security, or autonomous takeover without task-level benchmarks and independent audit.

## Hardening checklist

1. Runtime handshake:
   - health endpoint/read-only CLI succeeds;
   - listener evidence shows loopback-only;
   - source tree dirty status is recorded.

2. Manifest discipline:
   - strict top-level schema allowlist;
   - required fields present;
   - unknown fields rejected or isolated;
   - payload hash stored.

3. Integrity/replay:
   - HMAC-SHA256 signature over canonical JSON;
   - timestamp + nonce + body hash;
   - nonce registry with 0600 permissions;
   - duplicate nonce rejected.

4. Redaction:
   - deny raw home paths and known secret patterns;
   - run at least 50 negative secret/path samples;
   - scan generated manifest/log/report before claiming clean.

5. Runtime attestation:
   - write a separate attestation JSON with listener hash, script hash, manifest hash, key/nonce file modes, and dirty counts;
   - avoid raw sensitive command output.

6. Multi-model review:
   - call GPT/Claude through Responses API when AGI/evolution/architecture claims are involved;
   - call additional available LLMs when user requests all models;
   - report exact provider status and do not convert prose/empty responses into pass/fail claims.

## Open-source patterns absorbed

- Timestamped HMAC signatures and replay windows from webhook signing patterns.
- Strict JSON schema allowlist from schema validation projects.
- Secret scanning/redaction corpus patterns from detect-secrets/gitleaks style tools.

## UI/config consistency for linked local agents

When a linked local agent has a UI settings page or model pool, do not stop at router/API correctness. Verify the UI-visible provider pool as a separate layer.

- Compare on-disk YAML/config with raw API config from each exposed UI/API port.
- Inspect browser storage for sticky model/provider selections.
- Check that `model.providers` (UI pool), `agent.model`, router tiers/scenarios, and memory model all agree.
- If the UI still shows stale providers, patch the provider pool and restart the gateway/API/UI stack.
- Read back both API config and browser UI before reporting completion.

Reference: `references/pilotdeck-ui-config-consistency.md`.

## Verification

A bridge is only `PASS_HARDENED_BASELINE_LINKED` when:

- loopback listener check passes;
- HMAC verifies;
- nonce is unique;
- schema allowlist passes;
- redaction tests all pass;
- source dirty state is recorded;
- runtime attestation exists;
- final report states remaining blockers and forbidden claims.
