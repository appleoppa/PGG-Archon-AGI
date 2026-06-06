# Rust CLI 飞书上下文记忆与报错分诊模式

## 适用场景

Rust CLI / daemon 项目已经接入 Feishu/Lark webhook，但用户反馈机器人“笨”“不懂上下文”“报错后不会修复”。常见根因不是主模型完全不可用，而是 webhook 入口把每条消息当一次性问答处理。

## 症状

- 用户说“继续 / 修复 / 还是报错 / 不对”，机器人不知道指上一轮什么问题。
- 飞书群或私聊内多轮对话无法延续。
- 模型调用失败时只返回原始错误，如 `处理失败：...`，没有形成可执行修复路径。
- 中文 prompt 预览若用字节切片（如 `&prompt[..50]`）可能在 UTF-8 边界 panic。

## 推荐实现

1. **按 chat_id 建立上下文表**

SQLite 表建议字段：

```sql
CREATE TABLE IF NOT EXISTS feishu_chat_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id TEXT NOT NULL,
  message_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  UNIQUE(chat_id, message_id, role)
);
CREATE INDEX IF NOT EXISTS idx_feishu_chat_messages_chat_ts
  ON feishu_chat_messages(chat_id, timestamp DESC);
```

2. **入口处理顺序**

```text
收到 Feishu message
→ 验 token / 去重
→ 写入 user 消息
→ 按 chat_id 读取最近 N 条
→ 构造 contextual prompt
→ 调用 scheduler / provider
→ 写入 assistant 回复
→ 发送飞书消息
```

3. **contextual prompt 必须包含行为规则**

至少包含：

```text
你不是一次性问答器。
必须结合同一个 chat_id 的最近对话上下文回答。
用户说“继续/修复/还是报错/不对”时，默认指上一轮问题。
如果出现报错，先解释可能原因，再给出可执行修复步骤。
不能编造已经执行的动作。
```

4. **错误回复要转化为分诊任务**

不要只输出原始错误。建议格式：

```text
状态：模型调用或消息处理报错
用户消息：...
错误摘要：...
下一步可选：
1. 重试上一条
2. 修复这个报错
3. 贴完整日志
```

5. **中文字符串预览不要字节切片**

错误写法：

```rust
&prompt[..prompt.len().min(50)]
```

安全写法：

```rust
let preview: String = prompt.chars().take(50).collect();
```

## 测试门禁

- 单元测试：context store 写入/读回最近消息。
- 单元测试：contextual prompt 同时包含历史消息和当前消息。
- 集成烟测：连续向 webhook POST 两条同 chat_id 消息，第二条询问第一条内容，读回 DB 确认 user/assistant 都已保存。
- 部署门禁：`cargo test`、`cargo check --all-targets`、`cargo build --release`、复制安装二进制、codesign、launchd restart、`/healthz`。

## 注意边界

这一步只让机器人“会记上下文、会把报错包装成修复任务”。它仍不等于完整 agent：如果没有工具执行器，它不能真实读文件、patch、测试或部署。汇报时要把“上下文记忆已修复”和“自动修复闭环未完成”分开。
