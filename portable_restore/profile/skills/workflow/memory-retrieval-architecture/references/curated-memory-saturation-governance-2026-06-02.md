# Curated Memory Saturation Governance (2026-06-02)

## Problem

Hermes profile memory has two prompt-injected curated stores:

- `~/.hermes/memories/MEMORY.md`
- `~/.hermes/memories/USER.md`

The memory tool rejects writes when `ENTRY_DELIMITER.join(entries)` exceeds configured limits. On default profile the observed state was:

- `MEMORY.md`: 4,926 / 5,000 chars
- `USER.md`: 2,962 / 3,000 chars

This is not disk exhaustion and not an LLM bug. It is a deliberate prompt-injection budget for high-signal curated facts.

## LLM Audit Consensus

Real calls were made to GPT-5.5, DeepSeek V4 Flash, MIMO V2.5 Pro, Agnes 2.0 Flash; Claude Opus 4-6 returned empty content and was excluded from evidence. Consensus:

- Do not blindly raise `memory_char_limit` / `user_char_limit`; that only expands prompt cost and injection surface.
- Keep prompt-injected memory as a compact high-value index.
- Move process details, implementation notes, old state, and long histories into `SKILL.md` references, archives, session logs, or retrieval stores.
- Preserve full pre-compaction state before rewriting.

## OSS Learning

Public GitHub/API evidence checked:

- Letta/MemGPT: stateful agent memory is a first-class state layer, not an ever-growing prompt blob.
- mem0: universal memory layer for agents, focused on memory management/RAG/state management.
- LangGraph: stateful orchestration/checkpointing separated from prompt text.
- AutoGPT: agent platform patterns similarly separate runtime state/workflows from short prompt facts.

## Safe Fix Pattern

1. Archive full current memory before any rewrite:

```bash
mkdir -p ~/.hermes/memories/backups ~/.hermes/workspace/治理
cp ~/.hermes/memories/MEMORY.md ~/.hermes/memories/backups/MEMORY.md.pre-tiering-YYYYMMDD
cp ~/.hermes/memories/USER.md ~/.hermes/memories/backups/USER.md.pre-tiering-YYYYMMDD
```

2. Create a human-readable archive under workspace governance, e.g.:

```text
/Users/appleoppa/.hermes/workspace/治理/profile-memory-archive-2026-06-02.md
```

3. Rewrite `MEMORY.md` / `USER.md` as short index entries only:

- stable user preferences
- durable execution boundaries
- provider/API invariants
- canonical pointers to skill/reference/archive paths
- do not store task progress, PR IDs, commit SHAs, old phase logs, or long procedures

4. Verify with MemoryStore and tests:

```bash
cd ~/.hermes/hermes-agent
venv/bin/python - <<'PY'
import yaml, pathlib
from tools.memory_tool import MemoryStore
cfg=yaml.safe_load(pathlib.Path('/Users/appleoppa/.hermes/config.yaml').read_text())
mem_cfg=cfg['memory']
s=MemoryStore(memory_char_limit=mem_cfg['memory_char_limit'], user_char_limit=mem_cfg['user_char_limit'])
s.load_from_disk()
print('memory_chars', s._char_count('memory'), 'limit', s._char_limit('memory'), 'entries', len(s.memory_entries))
print('user_chars', s._char_count('user'), 'limit', s._char_limit('user'), 'entries', len(s.user_entries))
print('drift_memory', s._detect_external_drift('memory'))
print('drift_user', s._detect_external_drift('user'))
PY
venv/bin/python -m pytest tests/tools/test_memory_tool.py -q
```

5. Update the evolution manifest:

```bash
python -m apex_god.evolution_manifest --update
```

## Anti-patterns

- Raising limits as the primary fix.
- Appending every task result to `MEMORY.md`.
- Storing procedures in memory instead of skills.
- Direct shell appends that break `§` delimiter roundtrip.
- Claiming memory was “expanded” or “fixed” without readback and MemoryStore drift checks.

## Observed Default-profile Outcome

After tiering on 2026-06-02:

- Full archive: `/Users/appleoppa/.hermes/workspace/治理/profile-memory-archive-2026-06-02.md`
- Backups:
  - `/Users/appleoppa/.hermes/memories/backups/MEMORY.md.pre-tiering-20260602`
  - `/Users/appleoppa/.hermes/memories/backups/USER.md.pre-tiering-20260602`
- `MEMORY.md` reduced from 4,926 chars to a compact index.
- `USER.md` reduced from 2,962 chars to a compact index.

## Observed Default-profile Outcome — 2026-06-05 Core Hardening

用户指出 memory 不应堆流水账，而应按五层记忆/三层存储分工。已执行 default profile 真实分层治理：

- Archive: `/Users/appleoppa/.hermes/workspace/治理/profile-memory-tiered-archive-20260605-224537.md`
- Backups:
  - `/Users/appleoppa/.hermes/memories/backups/MEMORY.md.pre-tiering-20260605-224537`
  - `/Users/appleoppa/.hermes/memories/backups/USER.md.pre-tiering-20260605-224537`
- `MEMORY.md`: 9951 chars / 36 entries → 2054 chars / 13 entries.
- `USER.md`: 3785 chars / 32 entries → 1024 chars / 13 entries.
- MemoryStore verification: `memory_chars=2053/10000`, `user_chars=1023/5000`, `drift_memory=None`, `drift_user=None`.
- Manifest key: `latest_profile_memory_tiering_20260605`.

Core rule now fused into SOUL: prompt-injected MEMORY/USER only hold durable declarative facts and indexes; procedural details go to skills/references; episodic history goes to session_search/archive; state goes to manifest; long knowledge goes to retrieval/APEX-MEM/akashic. Memory saturation is fixed by tiering, not by raising limits or appending more text.

## Review/curation lesson — 2026-06-05

When asked to review a session and update skills, do not only save a memory or write a one-off note. Patch the class-level skill that governed the work. For memory saturation, the governing umbrella is this skill; for Hermes provider/Web UI routing, use `hermes-config-runtime-diagnosis`; for Ralph/Rust core formula landing, use `rust-core-module-development` plus `pgg-archon-closed-loop-formula`. Prefer support files under `references/` for session evidence and keep `SKILL.md` as compact trigger/runbook guidance.
