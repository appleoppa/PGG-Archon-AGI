# PGG Archon 第三方审计 LLM 接入模式

适用：PGG Archon / AGI / 进化任务需要引入专用第三方审计模型，而不是把主模型自评当审计。

## MIMO 审计 provider

```text
provider name: mimo_v25_pro_auditor
model: mimo-v2.5-pro
base_url: https://token-plan-cn.xiaomimimo.com/v1
key_env: MIMO_V25_PRO_API_KEY
api_mode: chat_completions
role: third-party audit only
```

## 使用规则

1. 审计模型不替代主执行模型；用于审查真实性、夸大风险、可交付边界、下一步瓶颈。
2. 先做 provider probe：`/models` 确认模型存在，`/chat/completions` 确认 response_id。
3. 审计结果必须与 GPT/Claude 交叉复核时，明确各自 response_id。
4. 如果 MIMO 返回 `reasoning_content` 而 `content` 为空，不能直接判定失败；应抽取 `content or reasoning_content`，但报告中标明字段来源。
5. 不打印 key，不把 secret 写入报告、GeneDB 或 skill。

## 证据字段

报告至少包含：

- provider / model / base_url / key_env
- http_status
- response_id
- content_chars 或 reasoning_content_chars
- sha256
- 审计结论：是否夸大、是否可交付、主要风险、下一步

## 真实性边界

第三方审计通道打通 ≠ 外部官方评测通过。

只能说：

- 第三方 LLM 审计通道可用；
- 本轮材料经 MIMO 审查；
- 审查意见已吸收进门禁/报告。

不能说：

- 已通过官方 benchmark；
- 已由独立机构验收；
- AGI 已最终完成。
