# Session ledger expired cleanup — 2026-06-03

## Context

The user asked to clean all previously expired Hermes sessions. The relevant active-profile ledger was:

- `~/.hermes/sessions/sessions.json`

In this ledger, expired records were identifiable by:

- `expiry_finalized == true`

The active/current record had `expiry_finalized == false` and should be kept.

## Safe cleanup pattern

1. Load Hermes runtime/config skill first; this is Hermes Agent state, not generic JSON editing.
2. Locate active-profile session ledgers before modifying anything. Common files observed:
   - `~/.hermes/sessions/sessions.json` — JSON session routing/metadata ledger.
   - `~/.hermes/session.db` and `~/.hermes/sessions.db` may exist as 0-byte or stale files; do not treat them as canonical without inspecting.
   - For message transcript retrieval, canonical DB may be `~/.hermes/state.db`; do not conflate it with the JSON session routing ledger.
3. Read and summarize counts first:
   - total records
   - expired records where `expiry_finalized is true`
   - active/unfinalized records
   - session IDs and updated timestamps for deletion candidates
4. Create a reversible backup under workspace governance, e.g.:
   - `~/.hermes/workspace/治理/session_cleanup_<date>/sessions.json.backup_<timestamp>`
5. Rewrite the JSON atomically keeping only records where `expiry_finalized is not true`.
6. Write a compact cleanup report with removed session IDs and backup SHA256.
7. Read back the source JSON and verify:
   - count decreased as expected
   - `expired_count == 0`
   - active session(s) remain
   - backup exists and has nonzero size

## Pitfalls

- Do not delete session transcript databases just because the user says “expired sessions”; clarify by inspection whether they mean routing/session ledger vs historical searchable transcript DB.
- Do not edit other profiles unless explicitly requested.
- Do not skip the backup; session cleanup is low-risk only when immediately reversible.
- Do not claim cleanup completed from file existence alone; read back and count `expiry_finalized` after the write.

## Output evidence to report

- target path
- before count
- removed expired count
- kept count/session IDs
- backup path
- report path
- readback verification (`expired_count: 0`)
