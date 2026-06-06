# 33-card status sync lessons — 2026-06-04

适用场景：PGG Archon / 超级进化 33-card 状态面板、status surface、se_sync、5-LLM verifier-friendly audit。

## 核心学习

1. 33-card 的 `file_id` 不是总能与桌面文件编号或 skill 名称一一对应。
   - 例：`2` 是 GitHub 仓库，不是 LLM 协调。
   - 例：`2.5a` 是 LLM 协调，`2.5b` 是多智能体协作。
   - 例：`7` 是个人智能体生态训练，`8` 是科研统一引擎。
   - 例：`22` 是 APEX 文档规范；`22-doc` 不是原生 33-card id，只是内部扩展映射。

2. se_sync 的 PATCHES 数量不等于 33-card ACTIVE 数量。
   - PATCHES 可以包含 33-card id 空间不存在的内部 id（如 `5.5`、`22-doc`）。
   - 最终状态只能以 synced JSON 的 `status_distribution` 为准。

3. 不能把“surface 模块已 ACTIVE”直接说成“33-card 已 ACTIVE”。
   - 必须先运行 `agent.pgg_archon_se_sync`。
   - 再运行 5-LLM audit。
   - 最后读回 `verifier_friendly_facts_33_synced.json` 的 `status_distribution` 与 `provider_success`。

4. 背景进程 output_preview 经常截断。
   - 看到 `exit 0` 和 commit 还不够。
   - 必须读回最终 JSON，尤其是 `status_dist`、`provider_success`、per-provider verdict。

5. 多 LLM audit 单通道错误不阻塞整体推进。
   - DeepSeek / MiMo / Agnes / gpt5.5 / MiniMax 各自独立记录。
   - MiniMax 常见 HTTP 200 但 STRICT JSON parse ERROR，应标 ERROR，不冒充 PASS。
   - Claude 账号不可用时按用户指示保持不调用/不修复。

## 推荐闭环步骤

```text
1. 读 synced/source JSON，列出 non-ACTIVE file_id/title/status。
2. 对每个 file_id 核查真实含义，避免按旧编号猜测。
3. 新建或复用 4-probe status surface。
4. bootstrap 写真实 state/log/cache/db 文件。
5. pytest 跑对应测试。
6. patch se_sync PATCHES，只映射真实存在的 33-card id。
7. 运行 agent.pgg_archon_se_sync。
8. 运行 5-LLM verifier-friendly audit。
9. 读回 verifier_friendly_facts_33_synced.json。
10. 只提交本轮文件；汇报 commit hash + status_distribution + provider_success。
```

## 验收门禁

- `pytest` 对新增 surface/bootstrap 通过。
- `se_sync` 输出 synced path。
- synced JSON 的 `status_distribution` 已读回。
- 5-LLM audit 的 `provider_success` 已读回。
- Git commit 已落。
- 汇报中明确边界：status surface ≠ full AGI；5-LLM WATCH/ERROR 不冒充 PASS。
