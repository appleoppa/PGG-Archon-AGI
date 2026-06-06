# P7 民事起诉状事实幻觉：LLM 巡视+审计 失守 + 正则自检兜底

> Case study: PGG-MS-20260605-0006 燕赵财险雇主责任险合同纠纷
> Date: 2026-06-05
> Status: 已闭环（v2 起诉状 15/15 真实事实 + 0/8 虚假事实通过程序自检）
> 关联技能: `apple-hub-orchestrator`, `apple-civil-litigation`, `agent-cms`, `dept-inspection-team`, `dept-audit-team`

## 1. 失守事件

P7 民事起诉状 FINAL v1 由 4 通道 LLM（deepseek/agnes/gpt5.5/mimo）协作生成。
- gpt5.5 90s timeout ERROR
- minimax 90s timeout ERROR
- 剩余 3 通道 PASS

v1 起诉状的事实与理由段被 LLM 自由发挥，包含 6+ 项 **真实材料中不存在的事实**：

| 维度 | v1（幻觉） | 真实材料 |
|---|---|---|
| 事故时间 | 2025年3月15日 | 2025年1月12日 |
| 事故地点 | 工地/运送建筑材料 | 因工外出/交通事故 |
| 拒赔理由 | 高血压既往病史 | 特别约定第13条按30%扣减 |
| 保单期限 | 2024-11-01至2025-10-31 | 2025-01-01至2025-01-31 |
| 被告已付 | 未明确 | 240,000元 |
| 争议金额 | 未明确 | 560,000元 |
| 派遣单位 | 漏 | 河南世通食品有限公司 |

**关键**：P5 巡视组（4 通道 PASS）+ P6 审计组（4 通道 PASS）**均未发现 v1 起诉状的事实错误**。

## 2. 根因分析

| 层级 | 问题 | 后果 |
|---|---|---|
| Prompt 层 | 客户《情况说明》真实事实段未强制引用 | LLM 自由发挥 |
| 通道层 | gpt5.5+minimax 长任务 timeout 丢上下文 | 3 通道损失 fact_block |
| 巡视层 | LLM 巡视与生成模型同源（gpt-class） | 同源盲点 |
| 审计层 | LLM 审计与生成模型同源 | 同源盲点 |
| 验证层 | 缺程序化事实比对 | 0 兜底 |

## 3. 修正方案（已落盘）

### 3.1 Prompt 强制 FACT_BLOCK 引用
在 4 通道 prompt 顶部粘贴客户《情况说明》真实事实 verbatim。

### 3.2 长任务排除 gpt5.5
P7 民事起诉状（4891+ 字 facts_and_reasons）改用 3 通道
（deepseek+agnes+mimo）替代 4 通道，跳过 gpt5.5 的长任务 timeout。

### 3.3 程序正则自检（核心兜底）
在 `事实与理由` 段写 python regex 自检：
- 15 项 `required_facts`（必须出现）
- 8 项 `forbidden_facts`（v1 错误事实，必须 0 命中）

### 3.4 失败处理
- 1-2 项缺失 → patch 补全
- ≥3 项缺失或任意 forbidden 命中 → 标 `.OBSOLETE_事实错误` + 重生成

## 4. 教训

**LLM 巡视 + LLM 审计不能作为事实正确性的最终兜底**。
程序化、可重跑、零漏检的事实自检才是 P7 终版的兜底层。

适用边界：
- ✅ 民事起诉状/答辩状/代理意见的事实与理由段
- ✅ 法律意见书的案件事实概述段
- ✅ 任何"客户材料 → 4 通道 LLM → 长文本"链路
- ❌ 不适用于纯法律论证（无具体事实）

## 5. 沉淀到其他技能的引用

- `apple-hub-orchestrator/SKILL.md` pitfalls #11/#12/#13 + reference
  `p7-fact-hallucination-regex-selfcheck.md`
- `apple-civil-litigation/SKILL.md` 新增"P7 民事起诉状 FINAL 事实幻觉 pitfall"小节
- `agent-cms` 旧 entry（10-subdir worked example PGG-MS-20260605-0006）仍准确，无需更新

## 6. v2 起诉状结果

- 程序自检：**15/15 真实事实命中** + **0/8 虚假事实命中** ✅
- 4 通道 LLM 协作（3 PASS + 2 ERROR）：deepseek 4891 字 / agnes 4882 字 / mimo 3351 字
- meta.json 加 `v2_self_check: PASS` + `final_version: FINAL_v2`
- v1 三个文件标 `.OBSOLETE_事实错误` 保留为审计追溯
