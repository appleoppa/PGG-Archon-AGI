# Hermes state.db Corruption Recovery

## Symptom

ARS sidecar or any session-DB read fails:
```
sqlite3.DatabaseError: database disk image is malformed
```
or
```
PRAGMA integrity_check: Tree X page Y cell Z: out of order / invalid page number
```

## One-shot recovery

```bash
cd ~/.hermes

# 1. Backup the corrupt DB
cp state.db state.db.corrupt_$(date +%Y%m%d_%H%M%S)

# 2. Recover via .recover command (handles most corruption)
sqlite3 state.db ".recover" 2>/dev/null | sqlite3 state.db.recovered

# 3. Rebuild FTS indexes (they often get malformed during recovery)
sqlite3 state.db.recovered "
INSERT INTO messages_fts(messages_fts) VALUES('rebuild');
INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('rebuild');
"

# 4. Verify
sqlite3 state.db.recovered "PRAGMA integrity_check;"
# Should output: ok

# 5. Swap in
mv state.db state.db.bak_original
mv state.db.recovered state.db
```

## Cron-side auto-repair

Add this to any shell script that reads `state.db`:

```bash
OUTPUT=$(command_that_reads_state_db 2>&1) || {
  EXIT_CODE=$?
  if echo "$OUTPUT" | grep -q "database disk image is malformed"; then
    echo "DB corruption detected. Attempting auto-repair..."
    sqlite3 ~/.hermes/state.db ".recover" | sqlite3 ~/.hermes/state.db.recovered
    sqlite3 ~/.hermes/state.db.recovered \
      "INSERT INTO messages_fts(messages_fts) VALUES('rebuild');" \
      "INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('rebuild');"
    mv ~/.hermes/state.db ~/.hermes/state.db.corrupt_auto
    mv ~/.hermes/state.db.recovered ~/.hermes/state.db
    echo "DB auto-repaired. Retrying..."
    command_that_reads_state_db
  else
    echo "$OUTPUT"
    exit $EXIT_CODE
  fi
}
```

## Prevention

- state.db is ~500MB+ and uses WAL mode. Large DBs are more prone to page corruption on unexpected shutdowns.
- If Hermes is killed (SIGKILL, system crash) while writing WAL, the DB can corrupt.
- The ARS sidecar cron script now includes auto-repair (see `~/.hermes/scripts/pgg_ultimate_evolution_phase3_ars_cycle.sh`).

## Cause

Hermes uses `PRAGMA journal_mode=WAL` for state.db. On macOS, if the process is force-killed during a write transaction, the WAL <-> main DB sync can leave page references in an inconsistent state. SQLite's `.recover` successfully extracts 99%+ of data from such corruptions.
