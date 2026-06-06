# SQLite state.db corruption recovery

The ARS sidecar cron (SE20 Rule 8) reads `~/.hermes/state.db` for session message counting. If the DB gets corrupted (`sqlite3.DatabaseError: database disk image is malformed`), the cron fails silently.

## Symptoms

- ARS cron job status shows "error"
- Script exits with `sqlite3.DatabaseError: database disk image is malformed`
- `sqlite3 state.db "SELECT count(*) FROM messages;"` fails on stepping

## Detection

```bash
sqlite3 ~/.hermes/state.db "PRAGMA integrity_check;"
```

If it returns anything other than `ok`, the DB needs recovery.

## Recovery procedure

```bash
# 1. Backup the corrupt file
cp ~/.hermes/state.db ~/.hermes/state.db.corrupt_bak

# 2. Recover via .recover command (creates clean copy)
sqlite3 ~/.hermes/state.db.corrupt_bak ".recover" | sqlite3 ~/.hermes/state.db.recovered

# 3. Rebuild FTS5 indexes (common post-recovery issue)
sqlite3 ~/.hermes/state.db.recovered "
INSERT INTO messages_fts(messages_fts) VALUES('rebuild');
INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('rebuild');
"

# 4. Verify
sqlite3 ~/.hermes/state.db.recovered "PRAGMA integrity_check;"
# Should return: ok

sqlite3 ~/.hermes/state.db.recovered "SELECT count(*) FROM messages;"
# Should return a number (e.g. 28634)

# 5. Swap
mv ~/.hermes/state.db ~/.hermes/state.db.original_bak
mv ~/.hermes/state.db.recovered ~/.hermes/state.db
```

## Cron script resilience

The ARS cron script (`scripts/pgg_ultimate_evolution_phase3_ars_cycle.sh`) now includes auto-detection + recovery:

```bash
if ! sqlite3 "$STATE_DB" "PRAGMA quick_check;" 2>/dev/null | grep -q "^ok$"; then
    sqlite3 "$STATE_DB" ".recover" | sqlite3 "$STATE_DB.recovered"
    sqlite3 "$STATE_DB.recovered" "INSERT INTO messages_fts(messages_fts) VALUES('rebuild');"
    mv "$STATE_DB" "$STATE_DB.bad" 2>/dev/null
    mv "$STATE_DB.recovered" "$STATE_DB"
fi
```

## Root cause

The corruption is likely caused by concurrent writes when Hermes is running and the ARS cron tries to read the same sqlite DB at the same time. Ensuring the cron script handles this gracefully prevents recurrence.
