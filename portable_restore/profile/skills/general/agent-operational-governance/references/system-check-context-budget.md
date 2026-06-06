# 系统检测与上下文预算治理

## 触发条件

当用户要求：

- 查看系统各模块状态；
- 检测是否具备办案/运行/部署条件；
- 审计 Hermes / PGG Archon / 法律知识库 / Kanban / cron；
- 解释为什么上下文暴涨或 token 消耗异常。

## 本会话暴露的问题

一次“只做检测”也可能让上下文增加 40k，原因通常不是检测耗时，而是：

```text
长 skill 全文 + 长工具 JSON + Kanban/DB/legal-kb 原始输出 + 未做摘要回传
```

特别注意：运行时间不吃上下文，工具返回内容才吃上下文。

## 正确执行模式

检测类任务必须使用“落盘 + 摘要回传”模式：

```text
工具原始输出 → 写入 workspace 审计文件 / JSON
              → 脚本内部解析
              → 当前会话只回传 PASS/FAIL、数量、异常、证据路径
```

## 输出预算

- 普通系统检测：2k–5k token；
- 多模块健康检查：最多 8k token；
- 原始日志、完整 JSON、Kanban context、DB 表样本：默认不贴进对话；
- legal-kb：只返回 count、首条标题、关键命中字段、source_path 是否存在；
- Kanban：只返回 board、任务数、异常数、assignee 覆盖，不返回完整 context；
- SQLite：只返回核心表名和必要计数，不返回样本长字段；
- skill：优先加载 compact skill 或 targeted reference，不要连续加载多个大 skill 全文。

## 推荐脚本返回字段

```json
{
  "status": "PASS/WATCH/BLOCKED",
  "score": 0,
  "checked": [],
  "counts": {},
  "blockers": [],
  "evidence_files": [],
  "raw_output_saved": true
}
```

## 汇报口径

用户问“为什么上下文涨了”时，应明确：

- 是工具输出进入上下文；
- compression（压缩）多在触发后生效，不能替代当前轮工具输出预算；
- summarizer input hard cap 只防止压缩请求爆炸，不阻止本轮新工具输出膨胀；
- Rust tokenizer / token hygiene 多为 sidecar（旁路），不是所有工具调用的强制拦截器。

## 未来动作门禁

在检测类任务中，如果需要 3 个以上工具调用，优先用 `execute_code` 聚合并过滤；但脚本必须在内部裁剪输出，不得把完整命令结果拼成大 JSON 返回当前会话。
