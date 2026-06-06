---
name: super-evolution-22-core-cognition
description: 超级进化22核心认知门禁：Agent核心配置默认只读，授权例外走 LLM_judge + IDE_verify 分工校验。
version: 1.0.0
author: 苹果哥
license: MIT
metadata:
  source_sha256: d89469ae0b4899271d04c8287b8efb3ed28c7db8b9e96d2a88fbf47bc0345d5a
  related_skills: [super-evolution-20, evolution-systems-governance, agent-operational-governance]
---

# 超级进化22 — 核心认知只读门禁

## 触发条件

涉及 Hermes / PGG Archon / Agent 自身核心配置、identity prompt（身份提示词）、安全策略、tool permissions（工具权限）、skills（技能）、runtime code（运行时代码）持久修改时加载。

## 核心公式

```text
Agent_read ∩ overline(Agent_edit) = Max(Safety)
Total_stable = LLM_judge + IDE_verify
```

## 默认规则

1. Agent 对自身核心配置默认只读：允许读取、引用和提出建议，不允许未经授权直接持久化编辑。
2. 禁止把 md/prompt 写入说成模型权重改写或全域不可绕过。
3. 例外仅限明确特殊需求、confirmed bug（已确认缺陷）或用户明确要求。
4. 例外修改必须具备：明确授权、最小 diff、影响说明、回滚路径、schema/语法校验、targeted tests（定向测试）、审计记录。
5. Credential store（凭证库）不通过通用 sidecar 授权写入，只能走专用 setup/configuration flow（配置流程）。
6. 禁止削弱安全、审计、审批或权限边界的自我修改。

## 工程入口

```python
from se20.core_config_write_gate import assess_write, policy_manifest

result = assess_write(
    "~/.hermes/config.yaml",
    action="patch",
    explicit_authorization=True,
    exception_reason="confirmed bug",
    verification_plan={"diff_review", "schema_or_syntax_check", "targeted_tests"},
    rollback_plan_present=True,
)
```

## 判定含义

- `ALLOW_READ`：只读访问允许。
- `BLOCK_CORE_WRITE_NO_AUTH`：核心写入无授权，阻断。
- `REVIEW_VERIFY_INCOMPLETE`：缺少 IDE/CI 校验证据，只能停留在方案阶段。
- `ALLOW_BOUNDED_EXCEPTION`：满足明确授权、验证与回滚，可执行限定例外。
- `BLOCK_CREDENTIAL_STORE`：凭证库必须走专用流程。

## 边界

这是 policy sidecar（策略侧车）和可验证决策门禁，不是 OS-level mandatory access control（操作系统强制访问控制），不证明所有外部进程不可绕过，也不改写第三方模型权重。
