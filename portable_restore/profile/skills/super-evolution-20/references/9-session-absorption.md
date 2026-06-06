# Session 9: External AGI Absorption — APEX-MEM + nanoGPT-claw 全量吸收

**Date**: 2026-06-01
**Sources**:
- [APEX-MEM](https://github.com/hernandez42/APEX-MEM) — 2 hours old at absorption
- [nanoGPT-claw](https://github.com/hernandez42/nanoGPT-claw) — Rust闭环进化框架

## Absorbed Patterns

### 1. 5D Memory Dimensions (from APEX-MEM)

**File**: `agent/akashic_memory.py`

| Dimension | Decay | Intended Content |
|-----------|-------|------------------|
| WORKING | 1h | Active conversation context, transient |
| EPISODIC | 7d | Time-stamped events, decisions |
| SEMANTIC | 6mo | Concepts, facts, relations |
| PROCEDURAL | 1yr | Skills, methods, procedures |
| DECLARATIVE | 5yr | Stable facts, identity |

Key additions:
- `MemoryTier(IntEnum)` — 5 levels with half-life constants
- `fragment_strength(entry, now)` — exponential decay + access boost
- `rrf_fuse(*ranked_lists, k=60)` — Reciprocal Rank Fusion
- `store()` now accepts `tier` parameter
- `search()` now supports `min_tier` and `min_strength` filters
- `get_fragment()` updates access_count + last_accessed

### 2. Memory Flush (from APEX-MEM)

**File**: `agent/memory_flush.py`

Two extraction methods:
- `flush(messages, memory)` — heuristic: lines starting with `*` (task), `!` (decision), `?` (question) → episodic tier
- `llm_flush(messages, memory, llm_callable)` — LLM-extracted JSON facts → appropriate tier

### 3. Dreaming Consolidation (from APEX-MEM)

**File**: `agent/dreaming.py`

Four-step sweep (runs during ARS cycle):
- `decay_dead(threshold=0.05)` — removes dead fragments
- `promote_strong()` — WORKING→EPISODIC (access≥5), EPISODIC→SEMANTIC (access≥20)
- `merge_similar(threshold=0.85)` — merges near-duplicates via cosine sim
- `discover_relations(threshold=0.4)` — creates graph edges

### 4. 8-Skill Closed Loop (inspired by nanoGPT-claw)

Pattern: check → fix → retry (max 3 attempts). Python equivalents:
- `ast.parse` for syntax check
- `formula_precheck` for SE20 gate check
- `convergence_gate` for contradiction check
- LLM-generated fixes capped at 3 attempts

### 5. AutoLoop Daemon (shared pattern)

Both projects use same pattern:
- Daemon registered via launchd
- Runs fixed-interval cycle (30min SE20, 2h ARS)
- Measures → scores → feeds back → logs history

## Absorption Process

1. Browse source repos (GitHub profile or README)
2. Extract key patterns vs current implementation
3. Consult GPT + Claude for design feasibility
4. Implement in priority order (Claude-recommended: 1→3→2→4→5)
5. Verify all imports + smoke test
6. Update SOUL.md and skill docs

## File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `agent/akashic_memory.py` | ~400 | 5D memory with TF-IDF + decay + fusion |
| `agent/memory_flush.py` | ~120 | Heuristic + LLM extraction before compaction |
| `agent/dreaming.py` | ~200 | Dreaming consolidation sweep |
| `se20/__init__.py` | 180 | SE20Agent + se20_wrap dispatcher |
| `se20/middleware/*.py` | 5 files | Precheck/akashic/post_eval/convergence/evm |
| `se20/workers/ars_daemon.py` | 93 | ARS continuous daemon |
| `se20/workers/autoloop_daemon.py` | 174 | AutoLoop 30min cycle |
| `se20/ops/launchd/*.plist` | 2 files | launchd for ARS + AutoLoop |
