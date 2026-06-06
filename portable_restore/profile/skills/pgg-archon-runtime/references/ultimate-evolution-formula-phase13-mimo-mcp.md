# Phase13 — APEX+MIMO+MCP 公式吸收为只读编排面

## 触发场景

用户提供新的“终极公式”：

```text
Agent_APEX+MIMO+MCP
= Model • Harness ∘ M_IMO ∘ F_auto ∘ Φ_MCP
= Model • Harness ∘ (Σ_i w_i x_i) ∘ (⋃_{s∈TopK} Φ_MCP ∘ s) ∘ Φ_MCP
```

该公式应被视为 `APEX_AK = Ω_A · EVM_full - ΣΔ_all` 的上层执行/编排展开，而不是替代净有效进化评分公式。

## 工程映射

- `APEX_AK`：评分与安全扣减层，负责净有效进化值、P0 熔断、是否可推进。
- `M_IMO = Σ_i w_i x_i`：多输入/多输出聚合层，负责把 objective、inputs、available_services、policy 变成可审计分数。
- `F_auto = ⋃ TopK`：候选服务选择层，只能生成 TopK 计划，不得自动安装/启用/调用未知 MCP。
- `Φ_MCP`：MCP 边界层，只暴露 read-only report/plan schema；注册、写权限、secret 访问必须另走明确授权。
- `Model • Harness`：模型与工具外壳；GPT/Claude 审查必须真实 provider 调用，不得角色扮演。

## 推荐落地形态

1. 新增独立模块，例如 `agent/pgg_archon_mimo_mcp_formula.py`。
2. 提供只读函数：
   - `build_mimo_mcp_report(...)`
   - `build_mimo_mcp_ars_plan(...)`
3. 通过既有 `pgg_ultimate_evolution` tool 增加 action，而不是新增宽权限工具：
   - `mimo_mcp_score`
   - `mimo_mcp_ars_plan`
4. MCP server 只接收 JSON 输入并返回报告；不得在该 action 内执行安装、发现、启动、调用外部 MCP server。
5. 测试至少覆盖：
   - 安全 TopK 选择；
   - unknown/secret/write/auto_install/no_audit/irreversible MCP 被阻断；
   - ARS plan 标记 `requires_human_authorization_before_mcp_registration = true`；
   - MCP tool 输出 `side_effects = read_only_report/read_only_plan`；
   - 非法 JSON 拒绝。

## 默认安全 policy

```text
allow_unknown_mcp = False
allow_secret_access = False
allow_auto_install = False
allow_write_scope_by_default = False
minimum_service_score = 60
top_k = 3
```

阻断项包括：unknown source、secret access、credential request、auto install、未经授权写权限、无审计、不可逆操作。

## 完成态门禁

完成后必须有：

- GPT-5.5 或 Claude 真实审查证据；进化/AGI 任务不要用 DeepSeek 作为主审。
- py_compile 或等价语法验证。
- targeted pytest 覆盖新模块、tool action、MCP action。
- workspace 报告。
- PGG DB gene/experiment 入库并读回。

## 禁止口径

不得宣称：

- AGI 已完成；
- 全球 MCP 自动注册已完成；
- Hermes 已允许自动安装/启用未知 MCP；
- 多模型已自动接管核心主循环。

允许宣称：

- 新公式已被吸收为 APEX+MIMO+MCP read-only orchestration surface；
- 已接入 Hermes 原生 tool/MCP 的只读调用路径；
- 已测试、已报告、已入库。
