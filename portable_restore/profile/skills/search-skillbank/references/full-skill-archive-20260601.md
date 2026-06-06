---
name: search-skillbank
description: 复杂检索增强：Select-Read-Act-Review-Evolve
---

# SearchSkillBank — 检索技能化工作流

## 核心原则

复杂检索不要随机搜。先选择检索技能，再读取该技能规则，再执行检索，最后复盘是否沉淀或淘汰。

## Select：选择检索技能

| 场景 | 技能 | 目标 |
|---|---|---|
| 事实查证 | fact-check | 找权威来源，确认真假 |
| 法条/规范 | legal-source | 找现行有效原文和版本 |
| 类案/判例 | case-search | 找裁判来源、裁判要旨、相似度 |
| 时间敏感 | time-bound | 限定日期、版本、发布时间 |
| 多跳问题 | multi-hop | 分解实体、关系、条件逐步查 |
| 冲突信息 | cross-verify | 多源交叉验证，标出冲突 |
| 外部学习 | learning-source | 找原文、论文、项目文档、官方说明 |

## Read：读取技能规则

每次检索前只读取本表，不整篇扩展上下文：

| 技能 | 查询模板 | 验收标准 |
|---|---|---|
| fact-check | 关键词 + 官方/原文/出处 | 至少1个权威源，标注不确定性 |
| legal-source | 法规名 + 条号 + 现行有效/修订 | 原文、版本、施行/修订时间 |
| case-search | 案由 + 争点 + 地区/法院/年份 | 来源、案号、裁判观点、相似/差异 |
| time-bound | 关键词 + 日期范围 + 最新/修订 | 明确时间边界 |
| multi-hop | 拆成实体→关系→结论三段 | 每一跳有来源 |
| cross-verify | 同一问题 + 不同来源/搜索引擎 | 至少2源对照，冲突单列 |
| learning-source | 主题 + paper/docs/repo/tutorial | 有原文链接和可吸收点 |

## 检索来源选择指南

不同检索任务的首选来源不同。实证数据（2026-05-23 开智进化循环第21轮执行）：

| 场景 | 推荐来源 | 理由 |
|---|---|---|
| 学术/进化方法论 | arXiv论文（通过arxiv skill） | 泛化web搜"gene database evolution"会被生物基因污染；arXiv直接命中MAPE控制环、动态技能生命周期论文 |
| 最新技术/工具 | web搜索引擎（bing/google） | 时效性高于arXiv |
| 法律/法规 | 专业法律数据库 | 搜索引擎不保证版本和效力 |
| 通用知识 | web搜索引擎 | 覆盖面广 |

关键教训：**不要只用web搜索查学术/进化类内容**——通用搜索引擎的术语歧义会导致结果严重偏离。arXiv作为学术来源返回的论文标题+摘要质量远高于通用搜索的摘要/广告混合页面。

**第4轮实证（2026-05-23）**：关于Agent技能生态的话题("skill package management", "skill retrieval augmentation", "SKILL.md supply chain")，web搜索返回全噪声(通用AI首页+字典释义)，arXiv返回5篇高度相关论文。详见 `references/2026-05-23-evolution-agent-skills-arxiv-papers.md`。

## Act：执行检索

1. 写出本次选择的技能名。
2. 生成1-3个精准查询，不做泛泛搜索。
3. 优先读原文/官方/项目文档，不把搜索摘要当证据。
4. 提取结论、来源、证据等级、剩余不确定性。
5. 只返回关键字段，避免大段网页灌入上下文。

## Review：复盘

- 成功：记录可复用查询模式或判断门禁。
- 失败：记录失败原因，如关键词过宽、来源不权威、时间范围错误、多跳断裂。
- 重复/低效：不沉淀技能，避免 SkillBank 膨胀。

## Evolve：轻量进化

只有满足以下任一条件才沉淀：

- 同一检索模式重复成功 ≥2 次；
- 一次失败代价高，且形成明确防错规则；
- 法律/办案/开智系统长期会反复使用。

沉淀优先顺序：先补本技能规则，其次写短记忆，最后才创建新技能。

Session-specific absorption notes live in `references/2026-05-20-searchskill-absorption.md`, `references/2026-05-23-arxiv-vs-web-search-evolution.md`, and `references/2026-05-23-evolution-agent-skills-arxiv-papers.md`.

## 超级进化联动：长上下文检索沉淀

当检索任务来自长文档、外部学习或"超级进化/开智"类材料时，必须和 `apex-hermes-evolution-engine` 联动：

1. 检索不是终点，目标是形成可复用技能条款。
2. 搜索摘要只作线索；原文、官方文档、代码、论文或权威来源才可作为证据。
3. 对每次复杂检索输出：查询策略、可信来源、冲突点、可迁移规则、是否沉淀。
4. 若检索发现的是方法论材料，按"原则 → 流程 → 验证 → 风险边界 → 技能更新"压缩。
5. 不因文章或愿景材料提到 GPT、多模型、Rust/Go/C、自动进化，就声称当前系统已经实现或调用。

## 外部学习参考

- `references/2026-05-23-skill-decision-bias-external-learning.md` — LLM Agent Skill/Tool 调用决策偏差（Edison Tech Blog 2026-04-14）：三种解法（确定性注入/专用skill加载tool/退出前强制检查）及对Hermes技能利用率提升的启示。加载学习类检索时先阅读此参考。

## 常见坑

1. **通用搜索引擎查学术/进化类内容被噪声淹没**：关键词如"gene database evolution agent self-improvement"在通用搜索引擎上被生物基因/生物信息学内容压倒性覆盖，完全找不到AI进化相关内容。应对方法：学术/进化/方法论类搜索优先走arXiv（arxiv skill），而不是web-search-engine。arXiv使用精确的分类和摘要匹配，没有广告噪声和术语污染。
2. **把搜索结果列表当结论**：搜索返回的摘要和标题不是证据，只是线索。
3. **混淆"搜索工具可用"和"搜索策略有效"**：web-search-engine返回了结果JSON，但结果全为噪声——搜索成功不等于检索成功。
4. **不为一次性检索创建新技能**。
5. **不用"全量融合""写入所有文件"污染规则系统**。
6. **不因文章主张而贸然改底层语言栈或架构**。

## 超级进化3吸收：SearchSkill 原生化内核路线

来源：`/Users/appleoppa/Desktop/进化文件/超级进化3-深度自进化.md`。

该材料的核心要求不是把所有 Hermes 主链路一次性重写，而是把 SearchSkill / SkillBank 从普通 Markdown 技能提升为可执行、可验证、可训练数据化的底层机制。

当前第一阶段落地为 Rust 只读原型：`/Users/appleoppa/.hermes/native/skillbank-core/`。

执行边界：

1. Python 只做粘合是目标路线；当前 Hermes 主体仍大量 Python，不能虚报已完成原生化。
2. `skillbank-core` 先承担 Select/scan 的只读核心，不直接修改技能、记忆、配置或 Hermes 主链路。
3. 复杂检索必须输出 Select → Read → Act → Review → Evolve 轨迹，后续才能变成训练样本。
4. SkillBank 动态迭代必须经过候选、验证、合并/淘汰门禁，不能自动污染技能库。
5. 两阶段 SFT 当前只允许先沉淀轨迹数据格式和样本，不得宣称已完成模型微调。

## 输出模板

| 字段 | 内容 |
|---|---|
| Select | 选择了哪个检索技能 |
| Query | 实际查询词 |
| Evidence | 权威来源/原文来源 |
| Result | 核心结论 |
| Gap | 仍不确定什么 |
| Evolve | 是否沉淀，沉淀到哪里 |

## APEX Sequence Note

For evolution/learning/configuration tasks that need APEX ordering, use `apex-sequence-logic`: 21354审错优先, 12534融合固化, 14325规划反证. Keep this as a short pointer; do not duplicate the full rule here.
