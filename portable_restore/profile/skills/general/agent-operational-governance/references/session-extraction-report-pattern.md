# Session Extraction Report Pattern

Use this reference when the user provides a large exported conversation/session file and asks to analyze, extract key information, and organize it into a Markdown document.

## Trigger

- User attaches a session export or large `.md`/JSON-like transcript.
- User asks: “分析并提取关键信息，整理成md文档”, “总结这段会话”, “提炼完成态/恢复入口/证据链”.

## Procedure

1. **Do not read the whole export into the main context.** First inspect metadata with a script: file size, line count, message count, role counts, headings, session id/title/model/provider if present.
2. **Parse structured exports programmatically.** For Hermes Web UI session exports, parse JSON and extract only `user` / narrative `assistant` messages. Ignore huge tool payloads except where they contain key evidence paths.
3. **Extract by decision states, not chronology alone.** Build sections around:
   - source and scope;
   - overall conclusion;
   - per-module/stage status;
   - completed actions;
   - evidence paths / gene ids / scripts / logs;
   - blockers and corrected blockers;
   - boundaries that cannot be overstated;
   - next recovery entry.
4. **Preserve completion-state discipline.** Distinguish completed / partially completed / blocked / suspended. Do not quote an earlier “complete” claim if later messages corrected it.
5. **Write a user-facing `.md` under the appropriate workspace area.** For evolution work, prefer `~/.hermes/workspace/开智/日志/` unless the user specifies another path.
6. **Read back and verify.** Confirm file exists, line count/size, and that key strings such as final status, gene ids, evidence paths, and recovery entry are present.

## Recommended report skeleton

```markdown
# <Topic>: 关键信息提取与状态整理

> 来源文件：`...`
> 整理时间：YYYY-MM-DD
> 文件性质：...

## 1. 总体结论
| 模块 | 当前结论 | 完成等级 | 关键证据 | 主要边界 |

## 2. 会话基础信息
| 字段 | 内容 |

## 3. <模块一>
### 原始目标
### 已完成动作
### 证据链
### 完成态判断

## 4. <模块二>
...

## N. 未完成项与风险

## N+1. 下一步恢复入口

## N+2. 关键文件索引

## 最终摘要
```

## Pitfalls

- Do not let early failed attempts dominate the final report if later steps resolved them; capture the corrected root cause and final verified state.
- Do not include secrets or raw tokens from the transcript; only state that authentication was verified or blocked.
- Do not inflate sidecar/prototype completion into core-system completion. Label Rust/Rust-sidecar, dry-run, and no-mainline-integration boundaries explicitly.
- Avoid dumping raw transcript excerpts. The deliverable is a structured extraction, not a chat log mirror.
