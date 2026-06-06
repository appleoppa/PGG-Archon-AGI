# Hermes Context / Token Governance Pattern

Use this reference when a Hermes Agent session or gateway task shows rapid context growth, compression hangs, or model daily-limit exhaustion caused by oversized prompts/tool outputs.

## Durable lesson

Token bloat usually comes from a chain, not one bad message:

```text
large tool outputs → late compression trigger → summarizer receives too much old tool data → compression request itself becomes huge → provider quota/daily limit fails
```

Treat the fix as layered risk reduction. Do not rely on a single threshold.

## Four-layer mitigation sequence

1. **Compression trigger hygiene**
   - Avoid a universal percentage threshold across all models.
   - Prefer a hybrid trigger:
     - absolute large-context trigger around `150000` tokens;
     - cap by a safety fraction of the active model context window for smaller models, e.g. `min(150000, context_length * 0.70)`.
   - Keep legacy percentage only as fallback for configs that lack the absolute threshold.

2. **Summarizer input hard cap**
   - Keep a separate hard cap on what is serialized into the compression request.
   - This is not the same as the trigger threshold.
   - The cap prevents the compression call itself from becoming the quota-burning request.

3. **Tool result budgets**
   - Add per-result and per-turn output budgets.
   - For oversized results, persist full output to a file and keep only a small preview in conversation context.
   - Validate by checking both the preview and the saved full-output path.

4. **SessionDB persistence hygiene**
   - Do not persist verbose reasoning/codex blobs by default.
   - Preserve in-memory reasoning replay for the current turn, but avoid storing hidden reasoning blocks in the long-term session database unless explicitly opted in.
   - Use a config flag such as `session_storage.persist_reasoning: false`, with an environment override for special debugging.

5. **Prompt file slimming**
   - Large always-injected context files such as `AGENTS.md` should be compact operational indexes, not full manuals.
   - Move long explanations, legacy details, and examples into `references/` or docs files.
   - Keep the main injected file focused on high-frequency rules, entry points, tests, safety gates, and pointers to detailed references.

## Verification checklist

- Read back selected config fields without exposing secrets.
- Run targeted tests for threshold math, serialization cap, tool-result budgets, and persistence behavior.
- Use `git diff --check` and the narrowest relevant test suite before commit.
- Commit only the files for the token-governance change; do not mix unrelated working tree changes.
- After gateway-affecting changes, restart or reload the gateway and verify:
  - exactly one gateway process;
  - connected platforms;
  - logs show the new threshold or compression behavior.

## Reporting pattern

Report in concise fields:

```text
问题链条:
本轮砍掉的源头:
前后数据:
测试:
提交/推送:
运行状态:
剩余最大头:
```

Avoid large tables for Feishu/mobile output.
