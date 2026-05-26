# APEX Skill 标准框架 · v1.0

> 璇玑帝国 · 2026-05-08 固化

---

## 1. 目录结构标准

每个 APEX Skill 必须位于 `/root/.openclaw/workspace/skills/<skill-name>/`，结构如下：

```
<skill-name>/
├── SKILL.md          ✅ 必需：主配置文件
├── _meta.json        ✅ 必需：元数据
├── references/       ✅ 必需：参考文档目录
│   ├── overview.md   （可选）
│   ├── examples.md   （可选）
│   └── faq.md        （可选）
└── scripts/          （可选：辅助脚本）
    └── *.sh / *.js
```

**强制结构说明：**
- `SKILL.md` — 技能的核心配置，YAML frontmatter + Markdown 正文
- `_meta.json` — SkillHub 发布的元数据，必须存在
- `references/` — 所有外部参考资料、示例、FAQ 必须放在此目录

---

## 2. SKILL.md 格式规范

### 2.1 Frontmatter（强制）

```yaml
---
name: <skill-slug>
description: >
  简短描述，一行概括技能用途。
  触发词应嵌入描述中。
version: "1.0.0"
apex_standard: v1.0
schema_version: "1.0"
author: 璇玑帝国-墨羽
triggers:
  - trigger_word_1
  - trigger_word_2
  - 中文触发词
permissions: []
tags:
  - tag1
  - tag2
---
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | Skill唯一标识，kebab-case |
| `description` | string | ✅ | 描述，包含触发场景和功能概述 |
| `version` | string | ✅ | 语义化版本，如 "1.0.0" |
| `apex_standard` | string | ✅ | APEX标准版本，固定 "v1.0" |
| `schema_version` | string | ✅ | 固定 "1.0" |
| `author` | string | ✅ | 作者，璇玑帝国成员格式 |
| `triggers` | string[] | ✅ | 触发词/场景列表 |
| `permissions` | string[] | ✅ | 权限列表，空数组 [] |
| `tags` | string[] | ❌ | 分类标签 |

### 2.2 正文结构（推荐）

```markdown
# <Skill名称>

## 核心功能
（技能的主要功能说明）

## 触发场景
（什么情况下激活此Skill）

## 使用方式
（工具调用、参数说明）

## 示例
（使用示例代码/命令）

## 注意事项
（限制条件、已知问题）
```

---

## 3. _meta.json Schema

```json
{
  "ownerId": "<string>",
  "slug": "<string>",
  "version": "<string>",
  "publishedAt": <number>,
  "status": "active",
  "apex_compliant": true
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ownerId` | string | ✅ | 发布者ID |
| `slug` | string | ✅ | Skill slug，与name一致 |
| `version` | string | ✅ | 版本号，与SKILL.md一致 |
| `publishedAt` | number | ✅ | Unix ms 时间戳 |
| `status` | string | ✅ | 固定 "active" |
| `apex_compliant` | boolean | ✅ | 固定 true |

---

## 4. 触发词命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 英文触发 | kebab-case | `apex_workflow`, `stock_analyst` |
| 中文触发 | 中文词组 | `璇玑工作流`, `股票分析` |
| 场景触发 | 动词短语 | `帮我分析股票`, `搜索网页` |

**规范：**
- 触发词必须嵌入 `description` 中
- `triggers` 数组至少包含1个触发词
- 中英文触发词可并存

---

## 5. 当前合规状态总览

| Skill | SKILL.md | _meta.json | references/ | Frontmatter | 状态 |
|-------|----------|------------|-------------|-------------|------|
| apex-workflow | ✅ | ✅ | ✅ | ✅ | **完全合规** |
| apex-core | ✅ | ❌ | ❌ | ❌ | **不合规** |
| memu | ✅ | ✅ | ❌(examples/) | ✅ | ⚠️ 缺references |
| github | ✅ | ✅ | ❌ | ✅ | ⚠️ 缺references |
| cn-stock-analyst | ✅ | ✅ | ✅ | ✅ | **完全合规** |
| web-tools-guide | ✅ | ✅ | ✅ | ✅ | **完全合规** |
| agent-browser-clawdbot | ✅ | ✅ | ❌ | ✅ | ⚠️ 缺references |
| find-skills | ✅ | ❌ | ❌ | ✅ | ⚠️ 缺_meta.json |
| memory-hygiene | ✅ | ✅ | ❌ | ✅ | ⚠️ 缺references |
| openclaw-tavily-search | ✅ | ✅ | ❌ | ✅ | ⚠️ 缺references |
| skillhub-preference | ✅ | ❌ | ❌ | ✅ | ⚠️ 缺_meta.json |
| tencentcloud-lighthouse-skill | ✅ | ✅ | ❌ | ✅ | ⚠️ 缺references |
| tencent-cos-skill | ✅ | ✅ | ✅ | ✅ | **完全合规** |
| tencent-docs | ✅ | ✅ | ✅ | ✅ | **完全合规** |
| hms-self-train | ✅ | ❌ | ❌ | ❌ | **不合规** |

---

## 6. 不合规修复清单

### 🔴 apex-core — 需修复
1. 缺少 frontmatter YAML 头
2. 缺少 _meta.json
3. 缺少 references/ 目录

### 🔴 hms-self-train — 需修复
1. 缺少 frontmatter YAML 头
2. 缺少 _meta.json
3. 缺少 references/ 目录

### 🟡 find-skills — 需修复
1. 缺少 _meta.json

### 🟡 skillhub-preference — 需修复
1. 缺少 _meta.json

### 🟡 其余缺 references/ 的Skill（不影响核心功能）
- memu, github, agent-browser-clawdbot, memory-hygiene, openclaw-tavily-search, tencentcloud-lighthouse-skill

---

## 7. 合规率统计

| 指标 | 数量 | 占比 |
|------|------|------|
| 完全合规（含references） | 4 | 27% |
| 基本合规（缺references） | 9 | 60% |
| 严重不合规（缺多项核心） | 2 | 13% |
| **合计** | **15** | 100% |

**核心文件合规率（SKILL.md + _meta.json）：** 11/15 = 73%
