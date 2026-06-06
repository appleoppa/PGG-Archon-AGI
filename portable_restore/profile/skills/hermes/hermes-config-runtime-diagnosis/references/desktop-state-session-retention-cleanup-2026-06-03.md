# Hermes Desktop state.db session retention cleanup (2026-06-03)

## Trigger

Use when Hermes Desktop/Web dashboard shows a large historical session count and the user asks to keep only a recent retention window, e.g. “保留最近4天，前面的清除”.

## Key distinction

There are at least two different session stores:

- `~/.hermes/sessions/sessions.json` — routing/session ledger for channel continuity; may contain `expiry_finalized` records.
- `~/.hermes/state.db` — canonical transcript/state database used by Hermes Desktop/TUI dashboard session history.

If Desktop shows a number like 1121, verify whether it corresponds to `state.db` with:

```bash
sqlite3 -readonly -separator ' | ' ~/.hermes/state.db "
select 'sessions_total', count(*) from sessions;
select 'desktop_display_count_message_count_gt0', count(*) from sessions where message_count>0;
select 'messages_total', count(*) from messages;
select 'by_source', source||'='||count(*) from sessions group by source order by count(*) desc;
"
```

## Safe retention cleanup workflow

1. Get the live cutoff with a real clock command, not mental date math:

```bash
date '+%Y-%m-%d %H:%M:%S %z %Z'
python3 - <<'PY'
import time, datetime
cut=time.time()-4*24*3600
print('cutoff_epoch', cut)
print('cutoff_local', datetime.datetime.fromtimestamp(cut).isoformat())
PY
```

2. Back up `state.db` with SQLite online backup, plus sidecars for rollback context:

```bash
mkdir -p ~/.hermes/workspace/治理/desktop_state_session_cleanup_$(date +%Y%m%d)
sqlite3 ~/.hermes/state.db ".backup ~/.hermes/workspace/治理/desktop_state_session_cleanup_$(date +%Y%m%d)/state.db.backup_$(date +%Y%m%d_%H%M%S).sqlite"
cp -p ~/.hermes/state.db-wal ~/.hermes/workspace/治理/desktop_state_session_cleanup_$(date +%Y%m%d)/ 2>/dev/null || true
cp -p ~/.hermes/state.db-shm ~/.hermes/workspace/治理/desktop_state_session_cleanup_$(date +%Y%m%d)/ 2>/dev/null || true
```

3. Preflight counts using the exact cutoff:

```sql
select count(*) from sessions where coalesce(started_at,0) < :cutoff;
select count(*) from messages where session_id in (select id from sessions where coalesce(started_at,0) < :cutoff);
select count(*) from sessions where coalesce(started_at,0) >= :cutoff;
```

4. Delete in a transaction. Important pitfall: `sessions.parent_session_id` can point from kept sessions to old sessions, causing `FOREIGN KEY constraint failed`. Null parent refs before deleting old sessions.

```sql
PRAGMA busy_timeout=30000;
PRAGMA foreign_keys=ON;
BEGIN IMMEDIATE;
CREATE TEMP TABLE _delete_sessions(id TEXT PRIMARY KEY);
INSERT INTO _delete_sessions(id)
  SELECT id FROM sessions WHERE coalesce(started_at,0) < :cutoff;
UPDATE sessions SET parent_session_id=NULL
  WHERE parent_session_id IN (SELECT id FROM _delete_sessions);
DELETE FROM auto_fix_log WHERE session_id IN (SELECT id FROM _delete_sessions);
DELETE FROM compression_locks WHERE session_id IN (SELECT id FROM _delete_sessions);
DELETE FROM messages WHERE session_id IN (SELECT id FROM _delete_sessions);
DELETE FROM sessions WHERE id IN (SELECT id FROM _delete_sessions);
DROP TABLE _delete_sessions;
COMMIT;
PRAGMA wal_checkpoint(TRUNCATE);
```

5. Rebuild FTS indexes after mass deletes, because raw row counts may otherwise not match expectations:

```sql
INSERT INTO messages_fts(messages_fts) VALUES('rebuild');
INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('rebuild');
INSERT INTO messages_fts(messages_fts) VALUES('optimize');
INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('optimize');
PRAGMA optimize;
PRAGMA wal_checkpoint(TRUNCATE);
```

6. Reclaim disk space. `DELETE` leaves freelist pages; run `VACUUM` after backup and verification when the DB is not heavily busy:

```bash
sqlite3 ~/.hermes/state.db "PRAGMA busy_timeout=30000; VACUUM; PRAGMA wal_checkpoint(TRUNCATE);"
```

## Verification checklist

Run all of these before reporting completion:

```sql
select 'sessions_total', count(*) from sessions;
select 'desktop_display_count_message_count_gt0', count(*) from sessions where message_count>0;
select 'sessions_before_cutoff', count(*) from sessions where started_at < :cutoff;
select 'messages_total', count(*) from messages;
select 'orphan_messages', count(*) from messages where session_id not in (select id from sessions);
select 'broken_parent_refs', count(*) from sessions where parent_session_id is not null and parent_session_id not in (select id from sessions);
select 'min_started_local', datetime(min(started_at),'unixepoch','localtime') from sessions;
select 'max_started_local', datetime(max(started_at),'unixepoch','localtime') from sessions;
select 'freelist_count', freelist_count from pragma_freelist_count;
```

Expected success shape: old sessions count is zero for the cutoff, orphan messages zero, broken parent refs zero, WAL checkpoint clean, freelist zero after `VACUUM`.

## Session-specific proof pattern

In the 2026-06-03 cleanup, Desktop showed 1121 sessions because `state.db` had `message_count>0` sessions = 1121, not because `~/.hermes/sessions/sessions.json` was uncleared. Keeping the last 4 days removed 1059 old sessions and 27333 old messages, leaving 138 total sessions / 104 Desktop-visible sessions / 3090 messages. Live `VACUUM` reduced `state.db` from about 657 MB to about 71 MB.
