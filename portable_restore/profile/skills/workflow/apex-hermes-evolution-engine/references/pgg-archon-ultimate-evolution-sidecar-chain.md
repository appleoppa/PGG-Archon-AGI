# PGG Archon 终极进化 sidecar 融合模式

适用场景：用户连续要求“继续/继续融合”推进 PGG Archon、APEX、AGI 或自我进化链路时，需要在不修改核心循环的前提下，把候选能力逐步落成可验证 sidecar（旁路）状态面。

## 本次沉淀的 class-level 模式

1. 先把候选公式/能力做成只读 scoring surface（评分面）。
2. 再用周期 ARS sidecar 生成报告，报告必须有 JSON + Markdown。
3. cron 持续运行前必须加 semantic fingerprint（语义指纹）或同等去重门禁，避免重复 gene 入库污染。
4. 每一阶段都要写入 PGG DB，并做 readback（读回）验证；重复执行必须返回既有 gene_id，而不是继续插入。
5. promotion gate（晋升门禁）必须融合：
   - 上一阶段报告状态；
   - score 阈值；
   - trend 是否 stable；
   - dedup gate 是否 active；
   - GPT/Claude 或至少 GPT/Claude 之一的真实 provider 审查证据；
   - P0 blocker 是否不存在。
6. 继续融合时，优先把已验证 sidecar 接入原生 ToolRegistry action，而不是直接改 `run_agent.py`。
7. 最终应形成 evidence chain（证据链）状态面，把报告链、DB readback、cron wrapper、模型审查证据统一为可读状态。

## 推荐阶段命名

- Phase3：periodic ARS sidecar
- Phase4：trend replay + semantic fingerprint dedup gate
- Phase5：promotion gate + real GPT/Claude review
- Phase6：native tool status surface
- Phase7：evidence chain status surface

## 验证门禁

每阶段至少验证：

- `py_compile` 通过；
- 相关 pytest 通过；
- CLI/script 实测输出包含 status、report path、gene_id；
- PGG DB readback 可查；
- cron wrapper 使用 venv Python 并包含最新 phase flags；
- 重复运行不新增同名 phase gene。

## 边界

- 不把 sidecar 说成核心接管；
- 不把公式评分说成 AGI 完成；
- 不修改 `run_agent.py`，除非用户明确授权核心改造；
- 不读 secret，不部署，不 git push；
- 进化/AGI/PGG 任务需要真实 GPT/Claude provider 调用留证，不能用角色扮演或子智能体冒充。

## 复用提醒

用户说“继续”或“继续融合”时，如果当前状态 score >=75 且风险低，应直接推进下一阶段：实现 → 测试 → 报告 → 入库 → 读回 → cron/tool 融合，而不是只汇报计划。
