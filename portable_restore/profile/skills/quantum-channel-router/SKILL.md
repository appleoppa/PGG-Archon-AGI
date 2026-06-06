---
name: quantum-channel-router
description: 量子通道路由 — Rust 实现的多模型智能路由引擎，支持分级路由、健康检查、轨迹缓存
version: 1.2.0
author: Hermes Agent
trigger_conditions:
  - 用户下达任何涉及多步骤、复杂推理或法律分析的任务
  - 用户下达代码开发、分析、研究、写作或办案任务
  - 任何非纯聊天的实质性任务（任务涉及执行、生成、分析、研究）
  - 当当前模型能力不足或用户对输出质量不满时考虑切换模型
metadata:
  hermes:
    tags: [router, routing, llm, trajectory, cache, quantum, rust]
---

# Quantum Channel Router — Compact

## Trigger

Use when a task needs model/provider routing, multi-step reasoning, legal/AGI/evolution model selection, route evidence, health checks, or trajectory cache decisions.

## Routing discipline

- Do not claim a model/provider participated unless a real call or route evidence exists.
- User/model preference overrides generic routing.
- If the active conversation model is already GPT and the user says “用 GPT 设计”, treat the current GPT session as the GPT designer; do not redundantly call an external GPT API unless the user explicitly asks for external/multi-model review.
- For PGG/AGI/evolution tasks, prefer GPT or Claude real provider calls when high-impact and when the task truly needs external provider participation.
- For Chinese legal work, DeepSeek is preferred unless complexity requires GPT/Claude review.
- Fallback follows the active user policy, not stale router defaults.
- Fallback follows the active user policy, not stale router defaults.

## Current boundary

The router informs selection and can produce route evidence. It does not by itself prove task completion, AGI status, or legal correctness. Completion still needs task-specific tests/readback/legal verification.

## Minimal route workflow

1. Classify task type: legal / evolution / coding / research / daily.
2. Select candidate providers using current config and user policy.
3. Health-check only if needed; avoid wasteful model calls for trivial tasks.
4. Execute the real task with selected provider/tool.
5. Record route evidence in report when user asked for routing or audit.

## 9router / OmniRoute absorption note

When absorbing external LLM gateway/router projects into PGG quantum routing, do not copy risky account/OAuth/free-provider behavior. Absorb safe class-level patterns: universal ingress, format translation, fallback/cooldown, evidence-preserving RTK, route evidence ledger, and explicit provider-participation boundaries. If the active model is already GPT and the user says "用 GPT 设计", use the current GPT session; only call external GPT/multi-model providers when explicitly requested for independent audit. See `references/9router-omniroute-fusion-20260605.md`.

## Reference

Full historical super-evolution routing notes are archived at:

- `references/full-skill-archive-20260601.md`
- `references/omniroute-9router-dashboard-evm-fusion-20260605.md` — 9router dashboard 吸收、Rust OmniRoute、量子路由与 EVM/河图洛书融合实战；含当前 GPT 不重复外调 GPT 的 workflow pitfall。
- `references/omniroute-9router-dashboard-absorption-20260605.md` — Rust-native OmniRoute absorption pattern: external router structural learning, dashboard data surface, evidence-preserving RTK, Python status bridge, and the pitfall that active GPT sessions do not require redundant external GPT calls.
- `references/9router-realtime-sync-omniroute-20260605.md` — 9router 实时状态同步反编译对照：Zustand TTL store + dynamic no-store API + EventEmitter + SSE；PGG OmniRoute 应先吸收只读 SSE snapshot / event ledger / generation_id，一律禁止把实时显示冒充 provider 正式参与。
- `references/current-node-webui-omniroute-live-shim-20260605.md` — 当前正在运行的 Node `hermes-web-ui` 接入 OmniRoute/河图洛书实时面板的低风险 shim：静态页 + loopback FastAPI/SSE bridge + CORS preflight + manual/auto 切换验证。
- `references/9router-realtime-dashboard-implementation-20260605.md` — 用户纠正“不要继续试探可行性”后的落地模式：直接实现 OmniRoute 实时面板 / 统一入口 / 自由切换 / SSE / control ledger，并区分 FastAPI dashboard 与当前 Desktop/Node Web UI 运行面。
- `references/9router-omniroute-fusion-20260605.md`
- `references/omniroute-route-policy-calibration-v25-20260606.md` — v2.5 policy calibration：修复 all-MiMo suggestion 根因，route-enforce HOLD。
- `references/omniroute-fresh-calibrated-evaluation-v26-20260606.md` — v2.6 fresh calibrated route-suggest metrics：policy_version filtered window、classifier priority fix、route-enforce HOLD 证据。
- `references/omniroute-guarded-route-enforce-canary-v27-20260606.md` — v2.7 guarded route-enforce canary scaffold：default-off、exact/general allowlist、legal/audit/AGI denylist、ledger + API/WebUI，Claude 403 如实记录。
- `references/omniroute-live-canary-toggle-test-v28-20260606.md` — v2.8 live canary toggle selftest：4/5 LLM review、enable→test exact/general allow + legal/audit/AGI deny→rollback、API/WebUI 按钮、仍无 provider substitution。
- `references/omniroute-exact-general-50-window-v29-20260606.md` — v2.9 exact/general 50-sample window：50/50 allow、class_match_rate=1.0、error=0、legal/audit/AGI leakage=0、rollback OK，v3.0 substitution candidate only。
- `references/omniroute-provider-substitution-canary-v30-20260606.md` — v3.0 provider substitution canary scaffold：plan/API/WebUI/ledger 落地；plan 允许 gpt55，但真实执行因 gpt55 502 阻塞；已修正失败文本不可计 provider participation。
- `references/omniroute-callable-provider-lane-repair-v31-20260606.md` — v3.1 callable provider lane repair：诊断 gpt55 三路失败、DeepSeek/MiMo 可执行；接入 DeepSeek fallback participation，标 cross_class_fallback=true，不冒充 GPT same-class substitution。
- `references/omniroute-fallback-provider-window-v32-20260606.md` — v3.2 fallback-provider substitution window：20 样本 gpt55 primary 全 502、DeepSeek fallback 20/20 participation、cross_class_fallback=20、leakage=0；WebUI 静态文件缺失如实记录。
- `references/omniroute-webui-restore-v33-20260606.md` — v3.3 WebUI restore：定位当前权威 WebUI 包 `~/.hermes/webui/node_modules/hermes-web-ui/dist/client`，恢复 `/omniroute.html` 并显示 v3.2 fallback window，浏览器 DOM 验证可见。
- `references/omniroute-gpt55-lane-reconciliation-v34-20260606.md` — v3.4 GPT55 lane reconciliation：响应用户纠正，区分 main/orchestrator GPT55 lane 可用 vs proof lane payload 错误；修 external registry Responses payload，GPT55 same-class substitution canary 200/participated=true。
- `references/omniroute-gpt55-same-class-window-v35-20260606.md` — v3.5 GPT55 same-class substitution window：20 样本 exact/general primary GPT55 20/20 success、fallback 0、HTTP 502=0、leakage=0；仍非全局 route-enforce。
