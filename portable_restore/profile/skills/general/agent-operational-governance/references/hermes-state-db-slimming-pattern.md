# Hermes State DB / Session Store Slimming Pattern

Use when `~/.hermes/state.db`, `state.db-wal`, or `~/.hermes/sessions/` grows large and the user asks to continue cleaning/token治理.

## Scope

This is for local Hermes hygiene. It is not a data-retention policy for legal case assets. Do not delete `state.db`, `sessions/`, `workspace/`, `skills/`, `memories/`, `.env`, or `config.yaml` outright.

## Safe sequence

1. Load `hermes-agent` and this governance skill before acting.
2. Stop the gateway before SQLite rewrite/VACUUM/checkpoint work; restart it after verification.
3. Audit first:
   - root/session/state DB sizes;
   - `messages` role counts and max content length;
   - FTS table sizes through `dbstat`;
   - large `state.db-wal`;
   - request dump count under `sessions/`.
4. Delete only regenerable debug dumps first, e.g. `sessions/request_dump*.json`, and verify count becomes zero.
5. For DB slimming, create a compressed row-level rollback file under `workspace/recovery/state-db-slim-<timestamp>/` before updating rows.
6. Prefer targeted trimming over deletion:
   - historical compression prompts over a threshold become short searchable placeholders;
   - historical tool outputs over a threshold keep head/tail plus a trim marker;
   - historical reasoning/codex blobs are nulled when current config already avoids persisting them;
   - old `sessions.system_prompt` may be replaced with a placeholder, but preserve recent sessions for resume friendliness.
7. Let SQLite FTS update via triggers, then run FTS optimize, `VACUUM`, and `PRAGMA wal_checkpoint(TRUNCATE)`.
8. Restart gateway and run `hermes doctor`; verify `session_search` still returns results.
9. Report exact before/after sizes, what was trimmed, where rollback rows live, and that no GitHub commit/push occurred unless explicitly authorized.

## Pitfalls

- `hermes doctor --fix` may not shrink a large WAL while the gateway keeps a live SQLite connection. Stop gateway, run `PRAGMA wal_checkpoint(TRUNCATE)`, then restart.
- A task/debug placeholder accidentally promoted in Kanban can be claimed by the dispatcher. Block template/non-case tasks immediately and state they are not worker completion evidence.
- Do not preserve full debug dumps by copying them into another permanent backup directory unless rollback genuinely requires it; that defeats cleanup.
- If JSON manifest writing fails after mutations, immediately reconstruct a recovery manifest from the recovery directory and live DB stats, then continue verification rather than rerunning the mutating script.
