# 2026-05-19 custom provider availability check

## Context
A custom 5yuantoken provider was configured for `gpt-5.5`. During the session, direct chat completion first returned HTTP 503 with “No available accounts”. A later re-test returned HTTP 200 and `pong` from the same configured model.

## Lesson
Do not convert a transient provider-account shortage into a durable negative claim. The right lesson is the verification sequence.

## Verification sequence
1. Read current `config.yaml` provider and model.
2. Confirm the key env var is present without exposing the secret.
3. Query `/v1/models` to identify the provider’s current advertised models.
4. Test `/v1/chat/completions` with the exact configured model and a minimal request.
5. If it fails with 503, state that the provider currently has no account for that model.
6. Re-test if the user asks “连上了吗” or if time has passed; availability may recover.

## Reporting wording
Use:
- “接口能通，但当前模型账户暂不可用。”
- “刚刚重新实测，模型已恢复，返回正常。”

Avoid:
- “这个模型不存在” unless `/v1/models` plus provider docs conclusively prove it.
- “工具坏了” or “服务商不能用” when only one model call failed.
