# 4-Channel Case-LLM Orchestration Pattern

> Created: 2026-06-05 from PGG-MS-20260605-0006 (燕赵财险雇主责任险合同纠纷)
> Models used: DeepSeek + Agnes + gpt5.5 + MiMo (claude banned, MiniMax observed)
> Replaces previous 3-LLM `delegate_task` pattern for analytical comparison work

---

## When to use this pattern

Use the **direct-HTTP 4-channel pattern** when:

- Task is analytical/comparative, not requiring isolated sub-contexts (e.g. multi-LLM voting on a legal issue, parallel research, parallel drafting).
- User explicitly asks for "all LLMs / 调用所有 LLM / 4 通道协作" — they want the channels compared, not isolated workers.
- Output is structured (STRICT JSON) and can be aggregated.
- Audit trail is required (raw outputs must be persisted for review).

Use the **`delegate_task` 3-LLM pattern** (see `multi-llm-collaborative-dispatch.md`) when:

- Each LLM needs a long, isolated context (e.g. one writes the complaint, another drafts settlement).
- Subagents need to do tool-calling (e.g. web research) — direct-HTTP does not support this.
- The task is "send work to specialists" not "compare perspectives".

---

## Architecture

```text
case_llm.py (thin wrapper)
  ├── imports: agent.pgg_archon_super_evolution_card._PROVIDERS + _ask
  ├── filters: drops `claude` (per user instruction)
  ├── verdict: classifies each channel as PASS / WATCH / ERROR
  ├── runs: ThreadPoolExecutor(max_workers=4) for parallel HTTP
  └── outputs: dict {per_provider: {...}, consensus: {PASS, WATCH, ERROR, total}}
```

### Channel registry (verified 2026-06-05)

5 providers in `super_evolution_card._PROVIDERS`, minus claude = 4 active channels:

| Label | Model | URL | Key env | Default max_tokens |
|---|---|---|---|---|
| `deepseek` | deepseek-v4-flash | api.deepseek.com/v1/chat/completions | DEEPSEEK_V4_FLASH_API_KEY | 4096 (reasoning) |
| `mimo` | mimo-v2.5-pro | token-plan-cn.xiaomimimo.com/v1/chat/completions | MIMO_V25_PRO_API_KEY | 4096 (reasoning) |
| `agnes` | agnes-2.0-flash | apihub.agnes-ai.com/v1/chat/completions | AGNES_AI_API_KEY | 2200 |
| `gpt55` | gpt-5.5 | chuangagent.eu.cc/v1/chat/completions | GPT55_5YUANTOKEN_API_KEY | 4096 (chat only) |
| `minimax` | MiniMax-M3 | api.minimax.chat/v1/chat/completions | MINIMAX_API_KEY | 2200 |

> **gpt5.5 critical**: `chuangagent.eu.cc/v1/chat/completions` is the only working endpoint. Other `5yuantoken`/`minimax` domains return SSL EOF or 401. `/responses` mode returns 0 chars; chat mode works.

---

## Verdict classification (do not skip)

Every channel call records three fields; if any is empty or invalid, verdict is ERROR, **never** PASS:

```json
{
  "label": "deepseek",
  "http_status": 200,
  "visible_chars": 1951,
  "verdict": "PASS" | "WATCH" | "ERROR",
  "content": "...",
  "elapsed_s": 20.7
}
```

| Verdict | Conditions | Aggregation treatment |
|---|---|---|
| **PASS** | http_status==200, content not empty, JSON parse succeeds | Counted in consensus mean (e.g. win probability) |
| **WATCH** | http_status==200, content present but not strict JSON, OR contains reasoning-only `<think>` blocks | Recorded but **excluded** from numeric consensus |
| **ERROR** | http_status != 200, content empty (0 chars), or JSON parse fails | Recorded as ERROR; **never** silently upgraded to PASS or WATCH |

**Hard rule**: a single channel's failure must not be hidden. If 3 of 4 channels ERROR, the task is BLOCKED, not "done with 75% confidence". Report the missing channels in the consensus block.

---

## Consensus aggregation

Two patterns:

1. **Numeric consensus** (e.g. win probability, score, count): mean of PASS values; record range `min-max`; report WATCH/ERROR channels separately.
2. **Semantic consensus** (e.g. arguments, evidence, risks): collect all PASS outputs, dedupe by string, mark per-argument "verified by [channels]". Disagreements are first-class data, not noise.

For semantic consensus, prefer the longest/thoroughest PASS-channel response as the **primary** version (e.g. gpt5.5 at 14364 chars beat deepseek at 3060 chars in 0006).

---

## Audit trail (required)

Every 4-channel run persists:

1. `99-台账/PGG-{type}-{date}-{seq}-<task>_4通道原始输出.json` — full per-provider response
2. `<department>/PGG-{type}-{date}-{seq}-<task>_v1.{md,json}` — merged consensus deliverable
3. 4-channel consensus row in the case ledger

The audit JSON must include `per_provider` with all 4 channels, even if some are ERROR, plus a `consensus` block with counts.

---

## Transient channel health management (mandatory)

Channel health is **transient** in both directions. Real observed patterns from 0006:

| Channel | Run 1 | Run 2 | Run 3 | Run 4 | Verdict |
|---|---|---|---|---|---|
| deepseek | PASS | PASS | PASS | PASS | 100% stable |
| agnes | PASS | PASS | PASS | PASS | 100% stable |
| gpt55 | PASS | PASS | ERROR* | PASS | 1 timeout (long task) |
| mimo | ERROR (0 chars) | WATCH (transient) | ERROR (0 chars) | PASS | 0-char transient, recovers |
| minimax | WATCH (think) | ERROR (timeout) | ERROR (timeout) | ERROR (timeout) | persistent 90s timeout |

\* gpt55 timed out once on a 3500-token research task; passed on subsequent 4000-token task.

**Pattern**: A single transient failure does not warrant declaring a channel dead. Two consecutive failures on similar tasks → switch to a backup prompt. Three consecutive failures → mark channel as degraded for the session; do not retry.

**Hard rule for minimax**: it has timed out 4/4 times in the 0006 case at 90s with `max_tokens ∈ {2200, 3000, 3500, 4000}`. Treat it as currently-degraded. Do not rely on its output for the case. Investigate the channel separately (plist MINIMAX_API_KEY, endpoint, request format) before next case.

---

## Worked example — PGG-MS-20260605-0006

4-channel orchestration, 4 task rounds, 16 LLM calls:

| Round | Task | PASS | WATCH | ERROR | Primary version |
|---|---|---|---|---|---|
| 1 | 案件结构化分析 | 3 | 1 | 1 | deepseek/agnes/gpt5.5 |
| 2 | 法律依据+类案检索 | 2 | 0 | 3 | deepseek+agnes (long task) |
| 3 | 法律意见书 | 4 | 0 | 1 | deepseek+agnes+gpt55+mimo |
| 4 | 民事起诉状 | 4 | 0 | 1 | gpt55 (14364 chars) |

**4-channel win-probability consensus**: 65% (4 channels perfectly agreed).

**Total elapsed**: ~19 min for P0-P7 (立案 → 4 阶段分析 → 起诉状 v1).

---

## Pitfalls (real ones from 0006)

| # | Pitfall | Mitigation |
|---|---|---|
| 1 | Importing the wrong function name (`call_llm_providers` doesn't exist; real one is `collect_card` in `super_evolution_card`) | The thin wrapper `case_llm.py` provides a clean `call_one`/`call_all` API; do not call `super_evolution_card` internals directly from case scripts |
| 2 | `super_evolution_card._PROVIDERS` is a private tuple — if Hermes refactors it, this pattern breaks | Wrap in your own provider list; refresh from `config.yaml` on each new case |
| 3 | Long task (max_tokens ≥ 3500) may time out gpt55 / minimax | Split into 2 shorter rounds; or accept the ERROR and run with PASS-only consensus |
| 4 | mimo / minimax can return 0 chars / `<think>` reasoning-only output | Classify as WATCH/ERROR; do not silently treat as PASS |
| 5 | 4 channels may give conflicting JSON keys (e.g. "issue" vs "dispute") | Normalize keys when merging; pick the longest PASS-channel response as primary |
| 6 | Forgetting to persist the raw 4-channel JSON audit | Always write `*_4通道原始输出.json` next to the merged `*_v1.md` |
| 7 | Treating WATCH as PASS in aggregation | WATCH is recorded but **excluded** from numeric means; semantic consensus may include WATCH for completeness |
| 8 | Forgetting to record elapsed_s / http_status | These are part of the audit trail; if either is empty, the channel is ERROR, not PASS |

---

## case_llm.py API (portable)

Save to `scripts/case_llm.py` (under this skill or in the case workspace). Usage:

```bash
PYTHONPATH=$HOME/.hermes/hermes-agent python3 case_llm.py --ping          # 4-channel health check
PYTHONPATH=$HOME/.hermes/hermes-agent python3 case_llm.py --prompt "..."  # 4-channel parallel call
PYTHONPATH=$HOME/.hermes/hermes-agent python3 case_llm.py --prompt "..." --max-tokens 3500
```

Inside a case script:

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent"))
from case_llm import call_all

result = call_all("your prompt here", json_mode=True, max_tokens=3000)
# result = {"per_provider": {...}, "consensus": {"PASS": N, "WATCH": M, "ERROR": K, "total": N+M+K}}
```

The wrapper handles: provider lookup, key loading, parallel HTTP, JSON mode prompt suffix, verdict classification, elapsed timing.
