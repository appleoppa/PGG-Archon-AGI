# 多模型推进高风险核心函数：characterization contract gate

## 触发场景
- 用户要求 GPT + Claude 一起推进，并让 MIMO 作第三方审计。
- 目标涉及 PGG Archon / AGI / Hermes-Agent 核心路径，尤其是大函数、核心 loop、provider（模型供应商）路径、scheduler（调度器）或 security boundary（安全边界）附近。
- CodeGenesis / AST / slicer 已发现 hotspot（热点），但直接重构风险高。

## 本次沉淀的稳定方法
1. 先真实调用模型，而不是用子智能体角色扮演。
   - GPT / Claude：按当前配置走 Responses API（`/v1/responses`），保留 HTTP status、原始 JSON、SHA-256。
   - MIMO：作为第三方 auditor（审计者），走 chat_completions，保留 HTTP status、原始 JSON、SHA-256。
2. 如果串行网络请求看似“卡住”，不要停在解释；立即读回证据目录，确认哪些通道已返回、哪些缺失，再继续执行。
3. 多模型意见如果一致认为直接 refactor（重构）不安全，应落地最小可验证 safety net（安全网），而不是写方案报告。
4. 对超大核心函数，优先新增 read-only characterization contract（只读特征契约）/ trace gate（轨迹门禁）：
   - 不 import（导入）核心函数；
   - 不 execute（执行）核心函数；
   - 不 patch（修改）核心函数；
   - 只通过 AST / source readback（源码读回）锁定当前行为契约。
5. contract（契约）字段应是机器可断言的布尔项，并生成 `contract_status`：
   - 全部满足：`PASS`；
   - 任一缺失：`WATCH`。
6. 每轮必须跑：targeted pytest、py_compile、git diff --check、APEX-GOD health、EVOLUTION_MANIFEST update，并只提交本轮相关文件。

## 适用于 run_conversation 的契约示例
RC-S01 bootstrap（启动阶段）可先锁定：
- `session_context_bound`
- `stdio_guard_installed`
- `retry_counters_reset`
- `turn_exit_reason_initialized`
- `stream_callback_initialized`
- `persist_override_initialized`

## 明确禁止
- 禁止无 characterization tests（特征保持测试）直接批量重写 4000+ 行核心函数。
- 禁止把模型建议当成完成；必须有代码、测试、health、manifest、commit。
- 禁止在未授权情况下改 Hermes core scheduler（核心调度器）或 security boundary（安全边界）。
- 禁止因网络调用耗时而停在“我在调用”；要读回证据并继续。
