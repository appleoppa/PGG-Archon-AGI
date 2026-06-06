# 终极进化公式 sidecar 融合模式

## 适用场景

用户要求把 `APEX_AK = Ω_A · EVM_full - ΣΔ_all`（终极进化公式）与 Hermes Agent / PGG Archon 深度融合，用 GPT-5.5 主导并联合 Claude、DeepSeek、MiniMax 做 ARS（自动研究/审查/修复建议）闭环。

## 已验证的安全落地顺序

1. **先走真实模型证据**
   - 先用 `qr route` 确认任务类型和 GPT/Claude 等 provider 健康状态。
   - GPT-5.5 / Claude 必须走 Responses API `/v1/responses`，不得退回 `/v1/chat/completions`。
   - 记录 provider、model、status、latency、response id 或响应文件路径。

2. **先读 Hermes Agent 原生架构，不直接改主循环**
   - `run_agent.py`：`AIAgent`、主 conversation loop、系统提示词与工具调用汇合点。
   - `model_tools.py`：`handle_function_call`、工具注册/分发、`pre_tool_call` / `post_tool_call` / `transform_tool_result` hooks。
   - `hermes_cli/runtime_provider.py`：provider / api_mode / key_env / base_url 解析。
   - `agent/chat_completion_helpers.py`：`codex_responses`、`anthropic_messages`、`chat_completions` 等 API 模式分流。
   - `cron/scheduler.py`、`gateway/session.py`、`hermes_state.py`：周期执行、外部入口、SessionDB 轨迹。

3. **第一阶段用 read-only sidecar**
   - 新增独立 scoring surface（评分面）模块，而不是直接改 `run_agent.py` 主循环。
   - sidecar 输出报告和 ARS plan（计划），不自动修改核心、memory、skills、provider routing 或工具权限。
   - 报告必须声明边界：候选评分基因；不证明 AGI 完成。

4. **第二阶段暴露为 Hermes 原生只读 tool**
   - 新增 `tools/pgg_archon_tools.py`，通过 `registry.register(name="pgg_ultimate_evolution", toolset="pgg_archon", ...)` 接入 ToolRegistry。
   - 在 `toolsets.py` 增加 `pgg_archon` toolset，包含 `pgg_ultimate_evolution`。
   - 工具 action：`score` / `ars_plan` / `runtime_status`。
   - 工具仍为 read-only：只返回 JSON report/ARS plan，不写文件、不改 memory、不改 provider routing、不执行修复。
   - 验证：`tests/tools/test_pgg_archon_tools.py` 覆盖注册、toolset 可见性、`model_tools.handle_function_call` 分发。

5. **公式工程化 schema**
   - `EVM_full`：任务成功率、正确性、闭环率、推理稳定性、工具使用、长上下文状态、自我修复。
   - `Ω_A`：架构协同放大系数，范围建议 `[0.5, 2.0]`，正式值应来自基线对照，不允许主观拔高。
   - `ΣΔ_all`：幻觉、安全、未闭环债务、成本、延迟、不稳定、记忆污染、工具风险、治理债务。
   - P0 熔断：关键安全/真实性/越权/虚假完成信号出现时，直接 `BLOCKED`，不能被高分抵消。

5. **多模型 ARS 分工**
   - GPT-5.5：primary_synthesizer（主综合与最终裁决）。
   - Claude：code_architecture_critic（代码架构审查）。
   - DeepSeek：logic_and_cn_legal_reasoning_critic（逻辑/中文法律推理审查）。
   - MiniMax：cheap_broad_reviewer（低成本广域复核）。

7. **验证门禁**
   - `py_compile` 新模块和测试。
   - `pytest` 覆盖：happy path、P0 熔断、Ω_A 边界、ΣΔ 归一化、ARS plan 只读、runtime status 映射。
   - 工具阶段还需覆盖：ToolRegistry 注册、`pgg_archon` toolset 可见、`model_tools.handle_function_call` 可调。
   - 写 workspace 报告。
   - 写入 PGG SQLite experiments / genes 并读回；不能只生成 Markdown 或 JSON。

## GPT Responses API 输出提取注意

第三方 Responses API 兼容实现可能不返回顶层 `output_text`，而是在：

```json
output[0].content[0].type = "output_text"
output[0].content[0].text = "..."
```

解析时应递归提取 `output_text` / `text` / 字符串 `content`，不要因为顶层 `output_text` 为空就误判模型无输出。

## 完成态口径

可以说：
- “终极进化公式已作为 read-only sidecar 融入 PGG Archon/Hermes 原生面。”
- “已生成 ARS plan，GPT-5.5 为主，Claude/DeepSeek/MiniMax 作为审查角色。”
- “已测试并写入 PGG gene DB 读回。”

不能说：
- “Hermes Agent 核心已完全重构。”
- “AGI 已完成。”
- “多模型已自动接管所有工具/核心代码。”
- “sidecar 等于真实自主 AGI。”
