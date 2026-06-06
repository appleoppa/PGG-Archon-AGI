# Phase12：终极进化公式嵌入 Hermes MCP 原生只读服务面

## 适用场景

当用户要求继续学习/融合“终极进化公式”并接入 Hermes Agent / MCP / 多模型 ARS 时，优先采用本模式：先把公式作为 read-only MCP surface（只读 MCP 服务面）暴露，再逐步接入 optskill draft、cron gate、CI gate；不得直接改主对话循环或自动接管核心。

## 核心公式

`APEX_AK = Ω_A · EVM_full - ΣΔ_all`

工程定位：净有效进化能力评分基因，不是 AGI 完成证明。

## 本轮验证过的安全融合点

1. 复用已有公式核心：`agent/pgg_archon_ultimate_evolution_formula.py`。
2. 复用 Hermes 原生 tool handler：`tools/pgg_archon_tools.py::_handle_pgg_ultimate_evolution`。
3. 在 `mcp_serve.py` 新增 MCP tool：`pgg_ultimate_evolution`。
4. MCP tool 只做 read-only report / read-only ARS plan，不写文件、memory、skills、provider、credentials、core loop。
5. MCP 入参中的 `evm_signals_json`、`delta_signals_json`、`runtime_status_json` 可接受 JSON string 或 object；非法 JSON 返回结构化 error。
6. 测试必须覆盖：tool 注册、只读 ARS plan、非法 JSON 拒绝。

## GPT-5.5 主审调用门禁

- GPT/Claude 必须走 Responses API：`/v1/responses`。
- provider 示例：`gpt55_5yuantoken/gpt-5.5`。
- 需保留 evidence：response_id、status、latency、输出文件。
- 首次大输出超时时，可降低 `max_output_tokens` 重试；记录成功调用，不把超时当成模型不可用。

## ARS 分工建议

- GPT-5.5：primary_synthesizer（主综合与裁决）。
- Claude：code_architecture_critic（代码架构审查）。
- DeepSeek：logic_and_cn_legal_reasoning_critic（逻辑/中文法律推理审查）。
- MiniMax：cheap_broad_reviewer（低成本广域复核）。

要求：只有真实 provider/API 调用后才能声称对应模型参与；不得用角色扮演冒充多模型。

## 禁止事项

- 不直接嵌入 `run_conversation` 主循环。
- 不让 LLM 自动修改核心代码。
- 不自动注册任意外部 MCP。
- 不读取或暴露 secrets。
- 不绕过 approval（授权审批）。
- 不宣称 AGI 已完成。

## 验证命令模板

```bash
python -m py_compile mcp_serve.py tools/pgg_archon_tools.py agent/pgg_archon_ultimate_evolution_formula.py
python -m pytest tests/test_mcp_serve.py::TestToolRegistration tests/tools/test_pgg_archon_tools.py tests/agent/test_pgg_archon_ultimate_evolution_formula.py -q
```

最低完成态：targeted pytest 通过；生成报告；写入 PGG gene DB / experiments 并读回。

## 后续演进顺序

1. Phase12：read-only MCP surface。
2. Phase13：`optskill_draft`，只生成 workspace 草稿，不写 active skills。
3. Phase14：MCP registry candidate scanner，只读候选发现 + 风险分级。
4. Phase15：human-approved registration，必须 approval 后才写配置。
