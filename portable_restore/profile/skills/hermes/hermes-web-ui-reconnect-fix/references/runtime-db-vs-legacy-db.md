# Runtime DB vs Legacy DB Recovery Pattern

Use when Hermes Web UI chats are present in a SQLite DB but still do not appear in the UI.

## Key lesson

Do not assume `~/.hermes-web-ui/hermes-web-ui.db` is the live database. Confirm the actual DB file held open by the running Web UI node process:

```bash
lsof -nP | grep 'hermes-web-ui.db'
```

Observed live path example:

```text
/Users/appleoppa/packages/server/data/hermes-web-ui.db
```

A restored legacy DB can look correct while the UI continues reading a different runtime DB.

## Diagnosis sequence

1. Confirm core process and DB handle:

```bash
ps aux | egrep 'hermes-web-ui|hermes_bridge.py|hermes_cli.main gateway run' | egrep -v egrep
lsof -nP | grep 'hermes-web-ui.db'
```

2. Inspect the actual runtime DB:

```bash
sqlite3 "$RUNTIME_DB" "PRAGMA integrity_check;"
sqlite3 -header -column "$RUNTIME_DB" \
  "SELECT id,title,profile,source,model,provider,datetime(last_active,'unixepoch','localtime') AS last_active,message_count FROM sessions ORDER BY last_active DESC LIMIT 20;"
```

3. Compare with candidate backup/legacy DBs. If a backup path contains Chinese characters and SQLite URI opening fails, copy it to a timestamped ASCII-safe temp/backup path before attaching.

4. Check what the UI can actually see through the authenticated API. Read the token locally but never print it:

```bash
TOKEN=$(cat ~/.hermes-web-ui/.token)
curl -s -H "Authorization: Bearer $TOKEN" \
  'http://127.0.0.1:8648/api/hermes/sessions?limit=20'
```

## Low-risk merge pattern

Before writing, copy the actual runtime DB:

```bash
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p ~/.hermes/workspace/存档/webui-runtime-db-restore-$TS
cp -p "$RUNTIME_DB" ~/.hermes/workspace/存档/webui-runtime-db-restore-$TS/runtime-hermes-web-ui.db.before-merge
```

Attach the source DB and `INSERT OR IGNORE` missing rows. Prefer additive merge over full replacement so newer live chats survive. Tables that are normally safe to merge additively:

- `sessions`
- `messages`
- `session_usage`
- `model_context`
- `chat_compression_snapshots`

After commit, verify:

```sql
PRAGMA integrity_check;
SELECT id,title,profile,source,model,provider,datetime(last_active,'unixepoch','localtime'),message_count
FROM sessions ORDER BY last_active DESC LIMIT 20;
```

Then verify API visibility, not just DB existence.

## Profile-filter pitfall

The Web UI session endpoint filters to known/current profiles when no explicit profile is requested. If a restored session still uses a retired profile name, it may remain hidden even after being merged into the correct runtime DB.

Safe handling:

1. Confirm the row is present and has meaningful non-empty user/assistant messages.
2. Confirm the old profile is retired and the current replacement profile is known.
3. Back up the runtime DB.
4. Update only the affected restored session row's `profile` to the current replacement profile.
5. Recheck `/api/hermes/sessions?limit=20`.

Do not bulk-remap profiles without evidence; profile names may encode intentional chat separation.
