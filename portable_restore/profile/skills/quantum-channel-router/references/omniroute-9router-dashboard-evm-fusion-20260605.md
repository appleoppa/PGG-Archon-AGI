# OmniRoute × 9router Dashboard × EVM/河图洛书融合实战（2026-06-05）

## 背景

用户要求研究 GitHub `decolua/9router`，吸收其最好的功能，并用 Rust 实现，同时区分并融合 PGG 的河图洛书与量子路由。

本次落地形成了 Rust-native `hermes_pgg_omniroute`：

- 路径：`~/.hermes/hermes-agent/rust_modules/hermes_pgg_omniroute`
- CLI：`pgg-omniroute-smoke smoke|decide <text>|dashboard`
- Dashboard JSON：`~/.hermes/workspace/github_absorption/9router/analysis/pgg-omniroute-dashboard-20260605.json`
- Dashboard HTML：`~/.hermes/workspace/github_absorption/9router/analysis/pgg-omniroute-dashboard-20260605.html`

## 关键工作流

1. 先确认 9router 真实仓库：`decolua/9router`。
2. 只读克隆/审查 README、ARCHITECTURE、`open-sse/services/*`、`open-sse/rtk/*`、executor/transformer。
3. 吸收结构，不整包吞：
   - provider cards
   - fallback chain
   - blocked reasons
   - RTK token saver stats
   - route evidence ledger
   - truth boundary
4. Rust 实现核心路由：
   - `TaskClass`
   - `ProviderState`
   - `RouteRequest`
   - `RouteDecision`
   - `evidence_preserving_rtk`
   - `ledger_entry`
5. 再接入 `agent/pgg_archon_quantum_channel_router.py`，让 Python 状态面能读 Rust dashboard。
6. 最后融合 EVM/河图洛书：`OrderFactors`、`OrderInfluence`、`route_score_with_order`、`decide_route_with_order`。

## 9router 与 PGG 量子路由/河图洛书区别

- 9router：工程 gateway 层，偏 provider 接入、格式转换、fallback、token saver、dashboard。
- 量子路由：任务/模型选择层，偏 task class、provider score、route evidence、多模型真实性。
- 河图洛书/EVM：秩序/治理层，偏进化方向、缺陷率、秩序因子，不是 provider gateway。
- OmniRoute：把三者融合成 Rust-native 可执行路由核心。

## 重要设计修正

不要把 7 个古典因子直接作为路由惩罚相乘使用。实测 `0.9^7≈0.48`，会把健康状态误打成 BLOCK。

正确模式：

```text
ancient_product = 七因子原始乘积，用于证据展示
order_strength = ancient_product^(1/7)，用于路由影响
route_multiplier = bounded(0.90 + order_strength*0.10 - defect_rate*0.20)
```

这样保留 EVM 证据，又避免把河图洛书当成过强的神秘惩罚项。

## 用户纠正：当前 GPT 不应重复外调 GPT

当当前会话模型本身就是 GPT，用户说“用 GPT 设计”通常应理解为“由当前 GPT 会话设计”。不要再外调 GPT API，除非用户明确要求外部 GPT、多模型复核或真实跨模型协作。外调失败也不得冒充参与。

## 验证门禁

- Rust：`/Users/appleoppa/.cargo/bin/cargo fmt && /Users/appleoppa/.cargo/bin/cargo test`
- Python bridge：`PYTHONPATH=. python3 -m pytest -q tests/test_pgg_archon_omniroute_dashboard_bridge.py tests/test_pgg_archon_router_evomaster_cognition.py`
- Dashboard readback：确认 JSON 中有：
  - `schema = PGGArchonOmniRouteDashboard/v1`
  - `summary.selected_provider`
  - `order_influence.schema = PGGArchonOrderInfluence/v1`
  - `provider_cards.length >= 1`

## 真实性边界

Dashboard/route decision 是数据面和决策面，不是上游 provider 真实调用证明；不能据此宣称 GPT/Claude 已参与、full AGI、或绕过 provider 限制。
