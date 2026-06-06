# Claude 自动路由审计与修复记录

**日期：** 2026-05-29
**触发：** 用户投诉 Claude 被自动调用且走了 `/v1/chat/completions` 导致高消费
**涉及文件：** 9 个（config + 4 个代码文件 + 4 个脚本文件）

---

## 问题链路图

```
gpt-5.5 失败
    ↓
fallback_providers 只剩 MiniMax（之前误删了 gpt-5.5）
    ↓
静态链走完 → 无可用 fallback
    ↓
触发 qr dynamic failover（quantum-router）
    ↓
qr route selected claude_opus47_5yuantoken
    ↓
route_chain_evidence_gate.py MODEL_TIERS['C'] 硬编码 claude-opus-4-6
    ↓
同时：scripts/kaizhi_10_rounds_15min_gap.py AGENT_PROVIDER=claude
      + github_gene_reviewer_cron model=claude-opus-4-7
      + hetu_luoshu_router.mirrors 含 claude
      + route_chain_gate trigger 含"调用GPT和Claude"
    ↓
Claude 被调用多次 × 走了错误 API 路径
```

---

## 修复清单

| 文件 | 修复内容 |
|------|---------|
| `config.yaml` | `fallback_providers` 恢复 gpt-5.5；新增 `provider_routing.ignore`；删除 `hetu_luoshu_router.mirrors` 中的 Claude；删除 `route_chain_gate.trigger_phrases` 中的 `调用GPT和Claude` |
| `route_chain_evidence_gate.py` | `MODEL_TIERS['C']` 从 Claude 换 DeepSeek；所有 chain 模板不再引用 Claude |
| `hetu_luoshu_super_router.py` | step2/step5 从 `claude_opus47` 换 `deepseek_v4_flash` |
| `hetu_luoshu_llm_router.py` | 旁证压缩从 Claude 换 DeepSeek |
| `kaizhi_10_rounds_15min_gap.py` | `AGENT_PROVIDER`/`AGENT_MODEL` 从 Claude 换 gpt-5.5 |
| `github_gene_reviewer_cron` (cron) | model 从 `claude-opus-4-7` 换 `gpt-5.5`（via cronjob update） |

---

## 关键发现

1. **`model_failover_tool.py` 不存在** — 早期对话记忆有误，该文件从未存在，真正的拦截逻辑在 `chat_completion_helpers.py` 的 `try_activate_fallback()` 函数中。

2. **Claude 走 `/v1/chat/completions` 而非 `/v1/responses`** — `config.yaml` 中 `claude_opus47_5yuantoken` 的 `api_mode` 实际是 `codex_responses`（正确），但外部脚本（`route_chain_evidence_gate.py` 等）hardcode 了 `base_url` 而没有正确传递 `api_mode`，导致走了错误的 API 路径。

3. **`fallback_providers` 之前只剩 MiniMax** — 是因为 DeepSeek 持续报 `HTTP 400 reasoning_content` 被移除，但移除后没有补回 gpt-5.5，导致 gpt-5.5 失败后没有本地 fallback，直接触发了 qr dynamic failover。

---

## 修复后的自动 fallback 链

```
gpt-5.5 (custom:gpt55_5yuantoken)
    → MiniMax-M2.7-highspeed (custom:minimax_m27_highspeed)
    → [Claude 完全阻断，不在链中]
```

---

## 验证命令

```bash
cd /Users/appleoppa/.hermes/hermes-agent && ./venv/bin/python -m pytest tests/run_agent/test_provider_fallback.py -v --tb=short
```

**结果：** 24/24 passed ✅

---

## 经验教训

1. **从自动链移除 provider 时要同步补回主 model** — DeepSeek 移除后 fallback 链只剩 MiniMax，gpt-5.5 成了孤家寡人，引发 qr failover 到 Claude
2. **多文件联合审计优于单文件修复** — Claude 在 9 个位置有引用，只修 config.yaml 不够
3. **外部脚本（如 route_chain_evidence_gate.py）也是路由源** — 不能只检查 Hermes core 配置
4. **Cron job 模型配置也要检查** — 有独立的 model 字段
5. **用户禁止项要在所有层同时阻断** — 单层阻断不可靠（`provider_routing.ignore` + `fallback_providers` 排除 + `route_chain_evidence_gate.py` 替换 三层保险）
