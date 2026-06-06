# OmniRoute multi-provider execution cockpit — custom task + evidence export

Date: 2026-06-05
Scope: Current Node WebUI `http://127.0.0.1:8648/omniroute.html`.

## Trigger

Use when multi-provider task proof should become an interactive cockpit with custom task input, provider selection, latency/failure summary, and evidence export.

## Pattern

Backend v2 fields added to multi-provider result:

- `success_providers`
- `failed_providers`
- `latency_summary.avg_elapsed_sec`
- `latency_summary.max_elapsed_sec`
- `latency_summary.avg_success_elapsed_sec`
- `evidence_export`

Current WebUI cockpit features:

- Custom task textarea.
- Provider checkboxes.
- Default providers: DeepSeek + MiMo.
- gpt55 remains optional because recent multicalls recorded HTTP 502; do not default-enable flaky channels when the user wants stable cockpit behavior.
- Button: `执行自定义多模型任务`.
- Button: `导出最新证据 JSON`.

## Verification evidence

API custom cockpit:

```text
task_id=3cd948f4a7b4e9bc
providers=[deepseek,mimo]
successful=2/2
consensus=exact_match
avg_elapsed_sec=4.048
failed=[]
answer=PGG_COCKPIT_OK
```

Browser cockpit:

```text
task_id=166ff2bb5034febd
successful=2/2
consensus=exact_match
hashes=1
avg=4.849s
failed=none
cockpitStatus=exact_match
```

Evidence export:

```text
exportStatus=exported evidence for 166ff2bb5034febd
```

Screenshot:
`/Users/appleoppa/.hermes/workspace/github_absorption/9router/analysis/current-webui-omniroute-execution-cockpit-20260605.png`

Manifest key:
`latest_pgg_omniroute_multi_provider_execution_cockpit_20260605`

## Boundary

Exact-match consensus means answer-hash agreement among selected successful providers. It is not legal correctness, benchmark score, or full AGI evidence. Failed providers must stay visible as failures; do not fake success for flaky channels.
