# Rust CLI Feishu/Lark Context + Error Triage Pattern

Use this when a Rust CLI/daemon sidecar has a Feishu/Lark webhook that feels “dumb”: it replies to each message as an isolated prompt, loses context on “继续/修复/还是报错”, or only echoes raw errors.

## Durable lesson

A working webhook + real LLM provider chain is not the same as agent learning or context competence. Treat these as separate layers:

1. **Transport layer**: Feishu event reaches local webhook and ACKs quickly.
2. **Model layer**: webhook can call real providers.
3. **Conversation layer**: chat_id-scoped context is persisted and injected.
4. **Triage layer**: error/follow-up messages are classified and recorded.
5. **Learning/sync layer**: curated knowledge packs or skill summaries are imported with boundaries.
6. **Execution/escalation layer**: tasks beyond sidecar capability are escalated to Hermes/main agent; do not imply the sidecar can patch/test/deploy unless it really has that tool path.

Do not tell the user “the chain is open, so the sidecar will automatically learn everything.” That is false unless a real knowledge sync/import job exists and has been verified.

## Minimal implementation shape

### 1. Persist chat context by chat_id

Add a SQLite table, normally under the sidecar data dir:

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

At message handling time:

1. record current user message;
2. query recent messages for the same `chat_id` (bounded, e.g. 12–40);
3. build prompt with recent history + current message;
4. record assistant answer back into the same store.

Prompt rules should explicitly say:

- user follow-ups like “继续 / 修复 / 还是报错 / 不对” refer to the same chat_id’s recent context;
- do not fabricate actions that the sidecar cannot perform;
- if actual execution is needed, say what evidence/logs or escalation is required.

### 2. Add error triage before prompt construction

Classify current text plus the most recent error-like context. Useful categories:

- `provider_auth`: 401, unauthorized, invalid API key/token, authentication.
- `provider_rate_limit`: 429, rate limit, too many requests.
- `provider_timeout`: timeout, timed out, 超时.
- `feishu_config`: verification token, app_id/app_secret, tenant access token.
- `feishu_encrypt`: encrypt/encrypted event not supported.
- `webhook_payload`: JSON/payload/message_type/content parsing.
- `runtime_panic`: panic, killed, byte index, crash.
- `unknown_error`.

Persist incidents separately:

```sql
CREATE TABLE IF NOT EXISTS feishu_error_incidents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id TEXT NOT NULL,
  message_id TEXT NOT NULL,
  category TEXT NOT NULL,
  evidence TEXT NOT NULL,
  user_text TEXT NOT NULL,
  status TEXT NOT NULL,
  timestamp INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feishu_error_incidents_chat_ts
  ON feishu_error_incidents(chat_id, timestamp DESC);
```

Inject triage fields into the prompt:

```text
triage_mode: true/false
category: provider_timeout
 evidence: request timeout
last_error_context: ...
suggested_actions: retry; check provider/network/proxy; reduce prompt/output length
```

When `triage_mode=true`, require a fielded reply:

```text
状态：...
分类：...
依据：...
修复步骤：...
需要用户提供：...
```

### 3. Handle real provider failures gracefully

If the model call itself fails, return a structured fallback, not a raw stack dump:

```text
状态：模型调用或消息处理报错
用户消息：...
错误摘要：...
可继续发：重试上一条 / 修复这个报错 / 贴完整日志
```

Also persist the failure context so the next “继续修复” can refer to it.

### 4. Verify with a webhook simulation

Use two synthetic Feishu events for the same `chat_id`:

1. `刚才模型调用报错：request timeout，帮我修复`
2. `继续修复`

Expected evidence:

- webhook replies `accepted` to both events;
- `feishu_chat_messages` contains user and assistant rows;
- `feishu_error_incidents` contains `provider_timeout` rows;
- second assistant answer references the prior timeout rather than treating “继续修复” as standalone.

### 5. Deployment gate for macOS Rust CLI daemon

After code changes:

```bash
cargo fmt
cargo check --all-targets --message-format=short
cargo test
cargo build --release
install -m 755 target/release/<bin> ~/.local/bin/<bin>
codesign --remove-signature ~/.local/bin/<bin> 2>/dev/null || true
codesign --force --sign - ~/.local/bin/<bin>
launchctl kickstart -k gui/$(id -u)/<launchd-label>
<bin> status
curl -sS http://127.0.0.1:<port>/healthz
```

Do not commit runtime DBs, WAL files, or `target/.rustc_info.json`.

## Boundary: learning vs sync

If the user asks why the sidecar does not “automatically learn from Hermes/main agent,” explain the layers honestly:

- Context memory lets it remember local chat history.
- Evolution ledger records runs, not skills.
- A real knowledge sync must be built: curate SOUL/USER/skill summaries, write a knowledge pack, import it into the sidecar store, inject relevant rules at prompt time, and define escalation.
- Do not copy raw Hermes memory/secrets/session context wholesale into the sidecar.

## Suggested next class-level step

Build a `knowledge_sync` surface only after context + triage work:

1. extract safe identity/style rules;
2. summarize skills into trigger/capability/boundary records;
3. import to SQLite/JSON pack;
4. inject only relevant entries by route/category;
5. record and test escalation requests for tasks beyond the sidecar’s permissions.
