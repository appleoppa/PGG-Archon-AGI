# Hermes state.db Optimization Guide

> Created: 2026-06-01 | Source: SE20 全量部署后的 GPT + Claude 联合审计优化

## Overview

`state.db` is the Hermes SQLite session store (~549MB, 28K messages, 1.1K sessions). It uses WAL journal mode. This reference covers prevention-focused optimization — keeping the DB healthy, fast, and corruption-resistant.

## 1. Connection-Level PRAGMAs (Critical)

PRAGMAs are **per-connection**, not persistent. Every process that opens state.db must set these **immediately after connect**, before any query:

```python
import sqlite3
con = sqlite3.connect("/path/to/state.db")
con.execute("PRAGMA busy_timeout = 5000")     # 5s retry on concurrent writes
con.execute("PRAGMA foreign_keys = ON")        # prevent orphaned messages
con.execute("PRAGMA cache_size = -64000")      # 64 MB cache (default is ~8MB)
con.execute("PRAGMA temp_store = MEMORY")      # temp tables in RAM
con.execute("PRAGMA mmap_size = 268435456")    # 256 MB memory-mapped I/O
con.execute("PRAGMA synchronous = NORMAL")     # safe for WAL mode
```

| PRAGMA | Problem if unset | Fix |
|--------|-----------------|-----|
| `busy_timeout=0` | Concurrent cron + Hermes write → `SQLITE_BUSY` → corruption risk | Set to 5000+ |
| `foreign_keys=OFF` | Orphaned messages when sessions are deleted | Set ON |
| `cache_size=2000` (~8MB) | Planner starved on 549MB DB | Set to -64000 (64MB) |
| `temp_store=FILE` (default) | Temp tables hit slow disk I/O | Set to MEMORY |

## 2. Index Strategy

### Required indexes (11 total)

Current indexes on `state.db`:

| Index | Table | Coverage | Purpose |
|-------|-------|----------|---------|
| `idx_messages_session` | messages | `(session_id, timestamp)` | Session context build |
| `idx_messages_timestamp` | messages | `(timestamp)` | ARS sidecar 24h queries |
| `idx_messages_role_timestamp` | messages | `(role, timestamp)` | Role-based session search |
| `idx_messages_platform_msg_id` | messages | `(session_id, platform_message_id)` WHERE NOT NULL | Platform message dedup |
| `idx_sessions_source` | sessions | `(source)` | Gateway routing |
| `idx_sessions_parent` | sessions | `(parent_session_id)` | Session tree queries |
| `idx_sessions_started` | sessions | `(started_at DESC)` | Recent sessions |
| `idx_sessions_model` | sessions | `(model)` | Model filter queries |
| `idx_sessions_user_id` | sessions | `(user_id)` | User filter queries |
| `idx_sessions_title_unique` | sessions | `(title)` UNIQUE WHERE NOT NULL | Title uniqueness |
| `idx_compression_locks_expires` | compression_locks | `(expires_at)` | Lock expiration |

### Verify with EXPLAIN QUERY PLAN

```sql
-- Timestamp-only query → should show COVERING INDEX
EXPLAIN QUERY PLAN SELECT count(*) FROM messages WHERE timestamp >= 1780000000;

-- Role + timestamp query → should show COVERING INDEX
EXPLAIN QUERY PLAN SELECT count(*) FROM messages WHERE role='user' AND timestamp >= 1780000000;
```

Expected output (COVERING = no table access needed):
```
QUERY PLAN
`--SEARCH messages USING COVERING INDEX idx_messages_timestamp (timestamp>?)
```

### Adding indexes (write lock required)

```sql
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_role_timestamp ON messages(role, timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_model ON sessions(model);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
```

Each `CREATE INDEX` takes a brief write lock. Run during a quiet window.

## 3. Schema Details

### messages table
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content TEXT,
    tool_call_id TEXT,
    tool_calls TEXT,
    tool_name TEXT,
    timestamp REAL NOT NULL,
    token_count INTEGER,
    finish_reason TEXT,
    reasoning TEXT,
    reasoning_content TEXT,
    reasoning_details TEXT,
    codex_reasoning_items TEXT,
    codex_message_items TEXT,
    "platform_message_id" TEXT,
    "observed" INTEGER DEFAULT 0
);
```

### sessions table
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    user_id TEXT,
    model TEXT,
    model_config TEXT,
    system_prompt TEXT,
    parent_session_id TEXT,
    started_at REAL NOT NULL,
    ended_at REAL,
    end_reason TEXT,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    reasoning_tokens INTEGER DEFAULT 0,
    billing_provider TEXT,
    billing_base_url TEXT,
    billing_mode TEXT,
    estimated_cost_usd REAL,
    actual_cost_usd REAL,
    cost_status TEXT,
    cost_source TEXT,
    pricing_version TEXT,
    title TEXT,
    api_call_count INTEGER DEFAULT 0,
    handoff_state TEXT,
    handoff_platform TEXT,
);
```

## 4. WAL Management

WAL file grows unbounded without checkpointing. Default auto-checkpoint is 1000 pages.

### Nightly checkpoint cron

```bash
# ~/.hermes/scripts/se20_db_maintenance.sh
sqlite3 ~/.hermes/state.db <<'SQL'
PRAGMA busy_timeout = 10000;
PRAGMA wal_checkpoint(TRUNCATE);
PRAGMA incremental_vacuum(500);
INSERT INTO messages_fts(messages_fts) VALUES('optimize');
INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('optimize');
ANALYZE;
SQL
```

| Step | Purpose | Frequency |
|------|---------|-----------|
| `wal_checkpoint(TRUNCATE)` | Flush WAL → main DB, truncate to 0 | Daily (03:00) |
| `incremental_vacuum(500)` | Reclaim up to 500 free pages | Daily |
| FTS optimize | Defragment FTS indexes | Monthly |
| ANALYZE | Refresh query planner stats | Daily |

### WAL file health check

```bash
ls -lh ~/.hermes/state.db-wal
```
If > 50MB during normal operation, the auto-checkpoint may be failing under contention.

## 5. Corruption Prevention Checklist

- [ ] `busy_timeout=5000` on every connection (not just cron)
- [ ] `foreign_keys=ON` on every connection
- [ ] WAL checkpoint cron running (check with `cronjob action=list`)
- [ ] `integrity_check` monthly
- [ ] No SIGKILL while state.db is open (use SIGTERM with cleanup handler)
- [ ] Minimum 1.1GB free disk (for VACUUM)

## 6. Per-Connection Code Update Pattern

Find all `sqlite3.connect("state.db")` calls and add the PRAGMA block:

```python
con = sqlite3.connect(path)
con.execute("PRAGMA busy_timeout = 5000")
con.execute("PRAGMA foreign_keys = ON")
con.execute("PRAGMA cache_size = -64000")
con.execute("PRAGMA temp_store = MEMORY")
```

Key files to check: `hermes_state.py`, `pgg_archon_ultimate_evolution_ars_cycle.py`, `tools/post_task_evaluation_tool.py`, `tools/ecc_audit_tool.py`.

## 7. Related References

- `state-db-corruption-recovery.md` — one-shot recovery procedure for existing corruptions
- `evolution-systems-governance/SKILL.md` — evolution system governance including DB interactions
