# PGG Archon 递归物化与底层渐进迁移规则

## 触发背景

用户指出历史缺陷：sidecar pipeline 曾经只支持单次自动前跳，递归 phase sequence 只是生成 blueprint plan，未逐项生成完整物化实体，导致 evolution chain 中途断裂。

## 永久执行规则

1. **sidecar 承担 phase advance 判断**
   - 所有 phase advance judgment logic 由 sidecar auxiliary pipeline 承担。
   - 不修改 Hermes-Agent core scheduler、native main loop、security isolation framework。

2. **禁止 planned-only 虚进化**
   - 每个 scheduled phase 必须完成完整 materialization：
     - source file generation；
     - unit test；
     - JSON report；
     - Markdown report；
     - GeneDB gene archive；
     - experiment serial record；
     - cryptographic unique record hash；
     - append-only ledger / cycle index anchoring。
   - 只生成 roadmap / blueprint / plan 不能称为完成。

3. **连续递归自动推进**
   - phase 完成完整验证后，若 `readiness_score > 75` 且 `next_stage_allowed = true`，必须自动继续下一 phase。
   - 单 phase 结束后不得清空 context/cycle judgment state；必须保留 cursor、ledger、receipt、cycle index 和 replay evidence。
   - 若一次生成了多阶段 plan，必须马上将 plan 中每个 phase 逐项物化；不能停在 `current_phase=N` 的声明。

4. **cycle index governance**
   - 后续 phase 要统一纳入 sustainable circulating index：phase data、gene archive、experiment sequence、hash receipt、replay verification。
   - index 必须 append-only，禁止覆盖历史条目；若发现缺 JSON/MD/GeneDB/experiment/hash，状态应为 HOLD/BLOCKED。

## 底层架构渐进迁移策略

1. **Python 上层业务逻辑长期保留**
   - 保留 Python upper-layer business logic 以维持运行连续性和兼容性。
   - 不做 violent overall reconstruction。

2. **Rust 优先替换底层确定性组件**
   - 优先 Rust 化：ledger hash calculation module、cycle index engine/controller、background sidecar driver、stream circulation middleware、core runtime scheduler sidecar。
   - 首个低风险目标应优先选择 deterministic / low-side-effect / high-reuse 组件，例如 `ledger_hash_calculation_module`。
   - Rust 原型必须先 isolated prototype，再 Python consistency test，再 shadow mode，再 feature flag adapter；不能直接替换 runtime。

3. **Go 次级迁移延后**
   - Go 用于 high-concurrency pipeline dispatcher、io blocking service、chain data append ledger service。
   - 若当前 Go toolchain 不可用，只记录 deferred schedule，不虚构启用。

4. **所有结构升级纳入进化链**
   - Rust prototype、cross-language consistency verification、shadow mode decoupling、feature flag rollback 都必须进入 cycle index hash chain 与 GeneDB。
   - 报告中明确：core scheduler modified=false、main loop modified=false、runtime replaced=false、git commit 状态。

## 验证口径

- Python/Rust hash 一致性测试：用同一 payload 对比 Rust CLI 与 Python `hashlib.sha256`。
- Rust crate 必须执行 `cargo test`。
- Python adapter 必须执行 targeted pytest。
- GeneDB 写入后必须 readback gene id / experiment id。
- 报告必须同时生成 JSON 与 Markdown。

## 常见坑

- 不要把 `next_stage_allowed=true` 的计划报告当作下一阶段完成。
- 不要在一次自动续进后停下，除非 readiness/gate 明确 HOLD/BLOCKED。
- 不要因用户要求“永久/无限”而修改 Hermes core loop；落地为可审计 sidecar recursive iteration，不突破原生安全边界。
- 不要在 Go 未安装时写成 Go 已启用；应写 deferred until toolchain available。
