# Functional Evaluation Example: skill-auto-maintain

实际会话中评估一个 GitHub 开源技能的完整案例（2026-05-18）。

## 背景

用户要求评估 https://github.com/jangyuxue/skill-auto-maintain，自述是 "自动查找、整理和清理 Hermes Agent 技能的自动化工具"。需要决定是否安装。

## 评估流程

### Phase 1: 概览（GitHub 页面 + curl README）

- 3 stars, 0 forks, 22 commits
- MIT license, 纯 Python 3 标准库
- v2.0.0 released 3 days ago，说明持续维护
- 中英文双语 README，mermaid 流程图

### Phase 2: 架构评估（curl SKILL.md + maintain.py）

核心逻辑四阶段：扫描→比对→优化→报告

关键发现：
- 依赖 `.bundled_manifest` 文件来区分内置 vs 用户技能
- 自动将 "走丢" 技能迁移到 `user_skills/` 目录
- 如果 `.bundled_manifest` 不存在，直接拒绝运行（安全设计不错）
- 相似度比对用 4 维打分（名称/关键词/结构/交叉引用）

### Phase 3: 环境兼容性检查

**致命不兼容**：这个工具假设技能存放在分类子目录中（creative/, devops/ 等），而我们 60+ 个技能全部平铺在 skills/ 根目录，且带版本号后缀（-1.0.0）。运行时它会：
1. 发现 skills/ 下没有 .bundled_manifest（我们没有）
2. 把所有 60 个技能视为 "走丢孤儿"
3. 自动迁移全部到 user_skills/，其中：
   - 版本号后缀（-1.0.0）会污染注册表名称
   - 迁移过程可能破坏现有引用和 cron 配置
4. 即使有 .bundled_manifest，也需要维护一份持续更新的白名单

### Phase 4: 必要性评估

我们已经有的覆盖：
- skill_manage 体系 → 创建/更新/删除技能
- skill-vetter → 安全审查
- skill-creator/hermes-agent-skill-authoring → 质量把关
- skill-extraction-workflow（新创建）→ 周期性技能萃取提案

缺少的是它架构中最有价值的部分：**比对去重和生命周期管理**。但这一部分已通过 skill-extraction-workflow 的吸收实现。

### 结论

安全通过、架构合格、但安装不适合。不装工具，吸收思路。

## 启示

1. **安全审查只是第一道门**。真正的决策需要功能评估和环境兼容性检查
2. **不要被工具的完善文档迷惑去安装不适合的东西**。这个技能文档非常专业（中英双语、mermaid、changelog、release notes），但环境匹配度直接否决
3. **工具的核心思路可以吸收而不安装**。从 skill-auto-maintain 学到了四阶段架构和比对打分机制，直接复用到 skill-extraction-workflow
4. **先问"我们已经有这个能力吗"再决定是否安装**
