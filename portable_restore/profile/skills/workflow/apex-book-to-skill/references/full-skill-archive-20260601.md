---
name: apex-book-to-skill
version: 1.0.0
description: 超级进化16 过目不忘 book-to-skill 管线。将书籍/文档解析为可追溯 skill 草案、懒加载 manifest、证据地图。
metadata:
  source: /Users/appleoppa/Desktop/超级进化16-激活神技能过目不忘 .md
  formula: ApexBookSkill = DoclingParse × SkillStruct × LazyLoad × MemLLM × ParallelAgent
---

# APEX Book-to-Skill 过目不忘

## 主公式

```text
ApexBookSkill = DoclingParse × SkillStruct × LazyLoad × MemLLM × ParallelAgent
```

| 组件 | Hermes 落地 |
|---|---|
| DoclingParse | `book_to_skill` 工具：md/txt直接解析，pdf用 PyMuPDF 可选降级 |
| SkillStruct | 生成 `SKILL_DRAFT.md`，含术语、来源、流程、验证清单 |
| LazyLoad | 生成 `manifest.json` + `chunks.jsonl` + `evidence_map.json` |
| MemLLM | 可用 `memllm.query/store` 做索引与长期反馈 |
| ParallelAgent | 大书可按章节拆给 `delegate_task` 并行处理 |

## 使用方式

```text
book_to_skill.compile(source_file, title, dry_run=True)
```

默认 `dry_run=True`，只生成草案和索引，不发布正式 skill。

## 发布门禁

| 门禁 | 要求 |
|---|---|
| 来源门禁 | 每条 claim 必须能回链 source_hash + chunk_hash |
| 解析门禁 | 低置信度内容不得自动进入正式 skill |
| 结构门禁 | 必须包含适用场景、步骤、输入输出、失败条件、验证样例 |
| 记忆门禁 | MemLLM 只作索引和反馈，不替代原文证据 |
| 并行门禁 | 多Agent输出必须经合并器去重、冲突检测、证据校验 |
| 发布门禁 | 未人工验证前只能是 draft |

## 当前状态

已用 `/Users/appleoppa/Desktop/超级进化16-激活神技能过目不忘 .md` 做真实编译测试：

| 项 | 结果 |
|---|---|
| parser | direct_text |
| chunks | 1 |
| published | false |
| manifest | `/Users/appleoppa/.hermes/workspace/book_to_skill/超级进化16-过目不忘-book-to-skill_20260525_185142/manifest.json` |
