# OmniRoute multi-provider task proof — consensus ledger

Date: 2026-06-05
Scope: PGG OmniRoute / HeTuLuoShu current Node WebUI and local quantum router.

## Trigger

Use when task-level proof should be upgraded from a single selected provider to multiple providers under the same task.

## Pattern

Evidence chain:

```text
shared task_id
  -> provider list
  -> real per-provider API calls
  -> per-provider answer hashes
  -> successful/failed counts
  -> exact-hash consensus or disagreement
  -> multi-provider ledger
  -> WebUI display
```

Implementation:

1. `execute_omniroute_multi_provider_task(task, task_type, providers, timeout)`
   - Uses callable `PROVIDERS` from `agent.pgg_archon_external_benchmark_provider_run`.
   - Calls each provider with the same task.
   - Records `participated`, `http_status`, `visible_chars`, `elapsed_sec`, `answer_preview`, `answer_sha256`, `error`.
   - Computes `consensus_status`:
     - `exact_match`: all successful calls share one answer hash.
     - `disagreement`: successful calls have different hashes.
     - `no_successful_calls`: no provider produced visible output.
   - Writes `~/.hermes/data/omniroute_multi_task_events.jsonl`.
2. `POST /api/omniroute/multicall` executes the multi-provider task.
3. Snapshot includes `recent_multi_task_events`.
4. Current WebUI page shows `Multi-provider task proof` and button `多模型任务执行`.

## Verification evidence

Direct multi:

```text
task_id=8ea5381d2bdd51e9
providers=deepseek,mimo,gpt55
DeepSeek OK 200 PGG_MULTI_OK
MiMo OK 200 PGG_MULTI_OK
gpt55 ERROR 502
successful=2/3
consensus=exact_match among successful calls
```

API multi:

```text
task_id=d8ddeb5975a40e76
successful=2/3
consensus=exact_match
gpt55 502 recorded as failure, not faked
```

Browser button:

```text
task_id=19b730f6ba047f66
successful=2/3
consensus=exact_match
SSE live
latest multi proof visible
```

Screenshot:
`/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/current-webui-omniroute-multi-provider-proof-20260605.png`

Manifest key:
`latest_pgg_omniroute_multi_provider_task_proof_20260605`

## Boundary

This proves multi-provider participation and exact-answer hash consensus for a bounded task. Consensus is only over successful calls; failed providers remain failures. It is not legal correctness, benchmark performance, full AGI evidence, or proof for unrelated tasks.
