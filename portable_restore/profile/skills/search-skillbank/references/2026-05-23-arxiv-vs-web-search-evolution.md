# 2026-05-23 检索来源选择实证：arXiv vs Web Search for Evolution Topics

## 场景

开智进化循环第21轮（cron批次第1轮）需要外部学习对标"基因回测闭环"和"技能健康监控"短板。

## 搜索策略

### 尝试1：web搜索（bing）
- 查询：`"AI agent skill health monitoring lifecycle management best practices"`
- 结果：通用AI产品页（Google Gemini, DeepSeek, OpenAI, Doubao, Perplexity）
- 问题：全是商业AI产品，无方法论内容

### 尝试2：web搜索（bing）
- 查询：`"evolution gene database closed-loop verification feedback mechanism autonomous AI agents"`
- 结果：Reddit首页、热门帖等完全无关内容
- 问题："gene"被搜索引擎理解为生物基因；"evolution"导向生物进化

### 尝试3：web搜索（bing）
- 查询：`"gene database evolution cycle agent self-improvement closed loop verification"`
- 结果：生物学Gene期刊、GeneCards数据库、生物遗传学内容
- 问题：术语完全被生物信息学污染

### 尝试4：arXiv学术搜索
- 查询：`"autonomous agent self improvement feedback loop verification"`
- 结果：**Paper 2510.27051** — "Adaptive Data Flywheel: Applying MAPE Control Loops to AI Agent Improvement"（NVIDIA，直接相关）
- 结果：另有量子记忆/自动驾驶验证等论文，但第一篇就是直接命中

### 尝试5：arXiv学术搜索
- 查询：`"agent skill management knowledge base maintenance lifecycle"`
- 结果：**Paper 2605.19362** — "Toward User Comprehension Supports for LLM Agent Skill Specifications"（2026-05-19，关于SKILL.md理解）
- 结果：**Paper 2605.10923** — "Dynamic Skill Lifecycle Management for Agentic Reinforcement Learning"（2026-05-11-17，直接关于技能生命周期管理）

## 关键发现

| 维度 | Web搜索 | arXiv搜索 |
|------|---------|-----------|
| 术语歧义 | 高 — "gene"、"evolution"被生物信息学压倒 | 低 — 按分类(cs.AI, cs.LG)精确匹配 |
| 噪声比 | 100%噪声，0%有用 | 3篇论文中2篇直接相关 |
| 时效性 | 混合新旧结果 | 支持sortBy=submittedDate |
| 方法论深度 | 摘要/广告混合 | 论文标题+摘要直接反映研究内容 |
| 可回放性 | URL易变、搜索结果不稳定 | arxiv ID永久稳定 |

## 可迁移规则

1. **学术/进化/方法论类搜索的首选来源是arXiv，不是web搜索引擎。**
2. **通用搜索引擎的术语歧义在学术话题上尤其严重**——"gene"、"evolution"、"agent"都有多个领域的含义。
3. **arXiv的cs.AI/cs.LG/cs.CL分类提供精准的学术检索域**，几乎没有广告噪声。
4. **即使需要web搜索验证，也应先通过arXiv找到论文，再用论文标题去web搜索具体实现**。
5. **搜索"成功"不等于检索"有效"**：web-search-engine正确返回了JSON，但结果内容全为噪声。

## 对本技能的改进

已将此发现写入search-skillbank SKILL.md：
- 新增"检索来源选择指南"表格
- 新增"常见坑"第1条"通用搜索引擎查学术/进化类内容被噪声淹没"
- 新增"常见坑"第3条"混淆搜索工具可用和搜索策略有效"
