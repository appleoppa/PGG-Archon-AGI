# Noise/probe session archive filter — 2026-06-03

## Trigger

Use when the user complains that Desktop/TUI/Web UI shows sessions they did not intentionally create, especially short probes such as:

- `Return exactly: OK`
- `只回复：M3_OK`
- `只回复：...`
- provider/model smoke tests
- empty CLI/API/cron/compression sessions with `message_count=0`

## Durable approach

Do not hard-delete by default. Hermes may create a real `sessions` row for any agent turn or internal probe. Safer UX cleanup is to set `sessions.archived=1` for noise sessions so:

- Desktop/TUI visible history is decluttered.
- Raw transcript/audit data remains recoverable.
- `state.db` integrity and FK relationships are preserved.
- The user can undo by restoring the SQLite backup or clearing `archived` for selected ids.

Canonical DB:

- `~/.hermes/state.db`
- `sessions.archived` controls visibility in many session-history views.

## Preflight

Always create a reversible backup before updating `state.db`:

```bash
TS=$(date +%Y%m%d_%H%M%S)
OUT="$HOME/.hermes/workspace/治理/session_filter_$TS"
mkdir -p "$OUT"
sqlite3 "$HOME/.hermes/state.db" ".backup '$OUT/state_before_session_filter.db'"
cp "$HOME/.hermes/sessions/sessions.json" "$OUT/sessions_json_before.json" 2>/dev/null || true
sqlite3 "$HOME/.hermes/state.db" "PRAGMA integrity_check;"
```

Inspect candidate sessions with first user message, not only title, because short probe sessions may have empty title:

```sql
WITH first_user AS (
  SELECT session_id, MIN(id) AS mid FROM messages WHERE role='user' GROUP BY session_id
), first_msg AS (
  SELECT m.session_id, trim(m.content) AS first_user
  FROM messages m JOIN first_user f ON m.id=f.mid
)
SELECT s.id, datetime(s.started_at,'unixepoch','localtime') AS started,
       s.source, s.model, s.message_count, s.tool_call_count, s.archived,
       substr(coalesce(s.title,''),1,80) AS title,
       substr(coalesce(fm.first_user,''),1,100) AS first_user
FROM sessions s LEFT JOIN first_msg fm ON fm.session_id=s.id
ORDER BY s.started_at DESC;
```

## Candidate rule used successfully

Archive only already-unarchived rows matching one of these classes:

1. Empty stale sessions:
   - `message_count=0`
   - no business content
   - optionally require a minimum age such as 10 minutes for automation to avoid racing active turns.

2. Exact-reply / provider probe sessions:
   - `message_count <= 4`
   - `tool_call_count = 0`
   - first user message or title matches:
     - `Return exactly:*`
     - `return exactly *`
     - `只回复：*`
     - `只回复:*`
     - contains `M3_OK`

Do not archive larger/tool-using sessions solely because the first prompt includes `Return exactly`; a later troubleshooting conversation may have grown into a real business/debug session.

## Update pattern

```sql
BEGIN IMMEDIATE;
WITH first_user AS (
  SELECT session_id, MIN(id) AS mid FROM messages WHERE role='user' GROUP BY session_id
), first_msg AS (
  SELECT m.session_id, trim(m.content) AS first_user
  FROM messages m JOIN first_user f ON m.id=f.mid
), candidates AS (
  SELECT s.id
  FROM sessions s LEFT JOIN first_msg fm ON fm.session_id=s.id
  WHERE s.archived=0 AND (
    s.message_count=0
    OR (
      s.message_count <= 4 AND s.tool_call_count=0 AND (
        lower(coalesce(s.title,'')) LIKE '%return exactly%'
        OR lower(coalesce(fm.first_user,'')) LIKE 'return exactly:%'
        OR lower(coalesce(fm.first_user,'')) LIKE 'return exactly %'
        OR lower(coalesce(s.title,'')) LIKE '%m3_ok%'
        OR lower(coalesce(fm.first_user,'')) LIKE '%m3_ok%'
        OR coalesce(fm.first_user,'') LIKE '只回复：%'
        OR coalesce(fm.first_user,'') LIKE '只回复:%'
      )
    )
  )
)
UPDATE sessions SET archived=1 WHERE id IN (SELECT id FROM candidates);
COMMIT;
```

## Automation pattern

For ongoing cleanup, create a script under `~/.hermes/scripts/` that:

- connects to `~/.hermes/state.db`;
- applies a minimum age guard;
- sets `archived=1` only;
- appends a compact JSONL audit line under `~/.hermes/workspace/治理/`;
- prints nothing on success.

Then create a no-agent local cron job. Important: the cron `script` field must be relative to `~/.hermes/scripts/`, e.g. `archive_noise_sessions.py`, not an absolute path.

Example:

```text
schedule: every 5m
no_agent: true
deliver: local
script: archive_noise_sessions.py
```

## Verification

After cleanup, verify:

```sql
PRAGMA integrity_check;
SELECT archived, count(*) AS sessions, sum(message_count) AS messages_recorded
FROM sessions GROUP BY archived ORDER BY archived;
```

Also verify no unarchived noise remains under the same candidate rule.

## Reporting

Report counts and backup path. Be explicit that the cleanup hides/archives rather than deletes, and that Hermes may still create raw sessions internally for audit/state safety.
