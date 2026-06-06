# launchd plist env injection — verified 2026-06-04

## Symptom

- `~/.hermes/.env` already declares the key (e.g. `MINIMAX_API_KEY=***`).
- A state-card audit reports `env_keys_missing: [MINIMAX_API_KEY]` or a per-gateway provider audit returns 401/403.
- `launchctl getenv <KEY>` returns empty.
- `echo $<KEY>` in the current shell is empty (terminal shells do not auto-source `.env`).

All four observations are simultaneously possible and normal. They are not contradictory.

## Why all three look "empty"

- `.env` is sourced by the CLI subprocess path only; it is **not** inherited by launchd-spawned daemons.
- `launchctl getenv` only shows variables that have been **explicitly set on the launchd domain** via `launchctl setenv`. It does **not** see per-plist `EnvironmentVariables` blocks; that block lives in the plist file on disk and is only consumed when a daemon is launched.
- Each `~/Library/LaunchAgents/ai.hermes.*.plist` is its own small environment; the gateway / Web UI / 12 pgg-* gateways / evol-watcher each start with their plist's `EnvironmentVariables` and nothing else.

The correct fix is **inject the key into each plist's `EnvironmentVariables` block** and let launchd re-bootstrap the daemon.

## Procedure

1. Extract the value once, never echo it in the report:

   ```bash
   APIK=$(grep '^MINIMAX_API_KEY=*** ~/.hermes/.env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
   ```

2. Back up the plists before editing. Keep the backup under `~/.hermes/workspace/config-backups/launchd/<ts>/`:

   ```bash
   TS=$(date +%Y%m%d-%H%M%S)
   BACKUP="$HOME/.hermes/workspace/config-backups/launchd/$TS"
   mkdir -p "$BACKUP"
   for plist in ~/Library/LaunchAgents/ai.hermes.*.plist; do
     cp "$plist" "$BACKUP/$(basename $plist).bak"
   done
   ```

3. Iterate the glob, insert idempotently. Existing values are preserved:

   ```bash
   for plist in ~/Library/LaunchAgents/ai.hermes.*.plist; do
     if plutil -extract EnvironmentVariables.MINIMAX_API_KEY raw "$plist" >/dev/null 2>&1; then
       echo "HAVE $(basename $plist)"
     else
       plutil -insert EnvironmentVariables.MINIMAX_API_KEY -string "$APIK" "$plist"
       echo "INJECT $(basename $plist)"
     fi
   done
   ```

4. Force launchd to re-read the plists:

   ```bash
   for plist in ~/Library/LaunchAgents/ai.hermes.*.plist; do
     launchctl unload "$plist" 2>/dev/null || true
     launchctl load   "$plist" 2>/dev/null || true
   done
   ```

5. Verify. Do not stop at `launchctl getenv` — that command cannot see plist-injected envs:

   ```bash
   plutil -p "$HOME/Library/LaunchAgents/ai.hermes.gateway.plist" | grep MINIMAX_API_KEY
   plutil -p "$HOME/Library/LaunchAgents/ai.hermes.gateway-pgg-zhixing.plist" | grep MINIMAX_API_KEY
   launchctl list | grep 'ai\.hermes\.' | awk '$1 == "0" || $1 == "-" {print "DEAD " $0}'
   ```

   Every `ai.hermes.*` label must show a non-zero PID. PID 0 / `-` means the daemon exited on startup; read `StandardErrorPath` from the same plist to see the first real failure.

6. Optional: prove the env is visible to a child process (not a substitute for step 5, just a smoke test):

   ```bash
   launchctl asuser $UID python3 -c "import os; print((os.environ.get('MINIMAX_API_KEY') or '')[:6])"
   ```

## Pitfalls observed in this deployment

- **15 plists, not 4.** The glob `ai.hermes.*.plist` catches the gateway, the Web UI, the evol-watcher, AND 12 pgg-* profile gateways. Hardcoding the list silently skips the pgg-* gateways and the env fix only "works" for default-profile requests.
- **`launchctl getenv` lies about plist envs.** Use `plutil -p` to read the actual on-disk injection; use the live provider call (or a real `launchctl asuser` smoke) to confirm the child sees it.
- **Do not stop at "edit .env".** `.env` is CLI-only; launchd-spawned daemons never see it.
- **Do not rely on `plutil -extract` exit code alone.** Always also `plutil -p` and grep; the extract subcommand can return success for missing keys with some plist encodings.
- **Back up first, every time.** A `plutil -insert` on a plist with bad encoding or wrong value silently breaks the daemon; the only rollback is the backup file.

## Verified evidence (2026-06-04)

- 15/15 plists (`ai.hermes.gateway`, `ai.hermes.webui`, `ai.hermes.evol-watcher`, 12 pgg-* gateways) injected.
- `plutil -p` on `ai.hermes.gateway.plist` and `ai.hermes.gateway-pgg-zhixing.plist` both show `"MINIMAX_API_KEY" => "sk-cp-...g7Kc"`.
- `launchctl list | grep ai.hermes` shows 15 non-zero PIDs after `unload`+`load` cycle.
- Subsequent per-profile provider audit calls return 200/visible, not 401/403.

## Rollback

```bash
TS=<original_timestamp>
cp -r "$HOME/.hermes/workspace/config-backups/launchd/$TS/"*.bak ~/Library/LaunchAgents/
for plist in ~/Library/LaunchAgents/ai.hermes.*.plist; do
  launchctl unload "$plist" 2>/dev/null || true
  launchctl load   "$plist" 2>/dev/null || true
done
```

Or remove the env block surgically per plist:

```bash
plutil -remove EnvironmentVariables.MINIMAX_API_KEY ~/Library/LaunchAgents/ai.hermes.gateway.plist
```

## Related

- `hermes-config-runtime-diagnosis` SKILL.md — main "Provider pitfalls" section for `MINIMAX_API_KEY` config row.
- `references/profile-bootstrap-scripts-2026-06-04.md` — sibling pattern for AGENTS.md / MEMORY.md / skills sync.
- `references/multi-model-provider-health-check-2026-06-03.md` — post-injection provider smoke test.
