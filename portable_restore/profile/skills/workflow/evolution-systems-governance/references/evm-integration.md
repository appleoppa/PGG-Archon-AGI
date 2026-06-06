# EVM Integration — Absorbed Detail

Original skill: `evm-integration`.

## Components

1. `evm_formula.py`: EVM formula and defect governance.
2. `hetu_luoshu_llm_router.py`: multi-model five-stage router.
3. `github_factory.py`: GitHub factory/external brain.
4. `oel_evm_integrated.py`: integrated executor.
5. `hetu_luoshu_super_router.py`: real multi-provider router runs and persistence.

## Formula Fixes

| Bug class | Correct rule |
|---|---|
| Ancient factor multiplication | 7 factors only, no Bagua extra multiplication |
| Defect rate | Average plus max-shortboard penalty |
| Ancient wisdom cap | Soft cap, not hard 1.0 cap |
| Boost coefficient | Configurable |

## Provider Quirks

- 5yuantoken: use `json.loads(resp.content)` to avoid Chinese garbling. Special headers may be needed.
- MiniMax: anthropic messages mode. Base URL `https://api.minimaxi.com/anthropic`, endpoint `/v1/messages`, auth `x-api-key`.
- DeepSeek: base URL without `/v1` when router constructs `/chat/completions`.
- GLM: OpenAI-compatible `https://open.bigmodel.cn/api/paas/v4`.
- Empty body trap: HTTP 200 with only thinking/reasoning is invalid; require user-facing output.
- Route necessity gate: do not route every simple task.

## Super Router Verification

Expected checks:

- providers configured;
- all stages return valid text;
- result JSON written;
- cycle/gene/verification row persisted when `--persist` is used.
