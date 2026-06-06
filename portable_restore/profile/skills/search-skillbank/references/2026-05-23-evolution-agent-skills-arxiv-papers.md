# 开智进化循环第4轮 — arXiv论文发现与检索经验

## 背景
2026-05-23 开智进化循环第4轮执行中，围绕「技能利用率度量」和「能力孤岛检测」短板进行外部学习。

## 检索对比实证

### Web搜索 (bing_web_pc)
- 查询词: "AI agent skill usage tracking metrics utilization rate"
- 结果: 完全无关 — Gemini/DeepSeek/OpenAI/ChatGPT 等通用AI工具首页
- 查询词: "agent skill capability utilization metric coverage tracking"
- 结果: 剑桥词典"agent"释义 + 零相关
- **结论**: web搜索引擎对于agent技能生态/编排类技术话题完全被通用关键词污染

### arXiv搜索
- 查询词: `all:AI+agent+skill+management+capability+registry`
- 结果: 274684 篇匹配, 前5篇全部高度相关

## 核心论文

### 1. Skilldex: 包管理器与分层搜索
**arXiv:2604.16911** | cs.AI | 2026-04
> LLM Agent通过skill包扩展能力。两个缺口：没有公共工具对skill包进行格式规范评分；没有机制将关联skill捆绑共享上下文。
**落地**: 在cron-rounds状态中添加skills_used追踪字段——技能利用率热力图的第一步。
**查询建议**: `all:agent+skill+package+manager+registry+hierarchical`

### 2. Skill Retrieval Augmentation for Agentic AI
**arXiv:2604.24594** | cs.CL, cs.AI | 2026-04
> 当前主流策略是将可用skill全量枚举到上下文窗口内——但随着skill库扩大，上下文带宽成为瓶颈，需要动态检索而非全量枚举。
**落地**: 印证了"不加载全部技能"的策略。skills_used追踪可帮助识别哪些技能值得进检索池。
**查询建议**: `all:skill+retrieval+augmentation+agentic+AI`

### 3. Toward User Comprehension Supports for LLM Agent Skill Specifications
**arXiv:2605.19362** | cs.HC, cs.AI | 2026-05
> 用户通过SKILL.md选择技能。分析了878个网络安全技能的文本质素。研究SKILL.md如何帮助用户形成对技能"消费、生产、覆盖范围"的合理预期。
**落地**: SKILL.md的description字段质量直接影响agent是否加载该技能——应定期审计description准确性和清晰度。
**查询建议**: `all:user+comprehension+skill+specifications+LLM+agent`

### 4. Under the Hood of SKILL.md: Semantic Supply-chain Attacks on AI Agent Skill Registries
**arXiv:2605.11418** | cs.AI, cs.CR | 2026-05
> SKILL.md的自然语言元数据可影响哪些技能被准入、展示和选择，引入语义供应链风险。
**落地**: skill-vetter应增强SKILL.md元数据核查，不仅是代码安全审查。
**查询建议**: `all:SKILL.md+supply+chain+attack+agent+registry`

### 5. Agentic Skill Discovery
**arXiv:2405.15019** | cs.RO, cs.AI, cs.LG | 2025-05
> 使用LLM从底层动作中自动发现多样化技能。重点在机器人领域，但方法论可迁移。
**查询建议**: `all:agentic+skill+discovery`

## 检索经验总结

| 维度 | web搜索 | arXiv搜索 |
|------|---------|-----------|
| agent技能生态类话题 | ❌ 全噪声 | ✅ 精准命中 |
| 进化方法论类话题 | ❌ 被生物基因污染 | ✅ 直接命中MAPE等 |
| 通用技术类 | ✅ 时效性好 | ⚠️ 有延迟 |
| 法律/法规 | ⚠️ 不保证版本 | ❌ 不适用 |

**规则更新**: 开智进化cron中涉及技能生态、Agent编排、进化方法论的学习需求，优先走arXiv。web搜索作为补充适用于时效性高的工具/框架/API变更类查询。
