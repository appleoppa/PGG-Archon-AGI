# Launchd restart race and RTK plugin activation — 2026-06-02

## When this matters

Use this note when Hermes Web UI dialogs stop continuing tasks, the UI appears alive, but bridge/logs show intermittent socket closes or port conflicts, especially on macOS where Web UI is managed by launchd.

## Durable lesson

A running Web UI process is not enough. For launchd-managed Web UI, plain stop/start or PID-based restarts can race with KeepAlive and create stale bridge state or `EADDRINUSE` on the Web UI port. Prefer launchd kickstart when the service is registered.

Also verify plugin configuration as structured YAML. A plugin list written as a string can look visually correct but leave the plugin disabled.

## Diagnosis pattern

1. Check Web UI process and port.
2. Check whether `ai.hermes.webui` exists under `launchctl print gui/$(id -u)/ai.hermes.webui`.
3. Inspect Web UI and bridge logs for:
   - `EADDRINUSE` on the Web UI port;
   - `Agent bridge socket closed without a response`;
   - bridge socket mode/broker startup messages.
4. Inspect `~/.hermes/config.yaml` plugin shape, not just displayed text:
   - correct: `plugins.enabled` is a YAML list containing `rtk-rewrite`;
   - wrong: `plugins.enabled` is a single string like `'[rtk-rewrite]'`.
5. Verify with a tiny bridge request, not only HTTP homepage availability.

## Repair pattern

1. Back up config before editing.
2. Set RTK plugin as a real list:

```yaml
plugins:
  enabled:
    - rtk-rewrite
```

3. Restart Web UI with launchd kickstart when launchd-managed:

```bash
launchctl kickstart -k gui/$(id -u)/ai.hermes.webui
```

4. If the local `hermes-web-ui restart` command ignores launchd and continues to plain stop/start, patch its restart path to:
   - detect `launchctl print gui/$uid/ai.hermes.webui`;
   - call `launchctl kickstart -k gui/$uid/ai.hermes.webui`;
   - fall back to stop/start only when launchd service is absent.

## Verification pattern

Pass only after all of these are true:

- Web UI status reports running and expected port is listening.
- HTTP homepage returns HTML.
- Bridge ping returns `ok: true` and expected mode/socket.
- A tiny async chat request returns a run id, then `get_output` reaches `done: true` with expected output and no error.
- `hermes plugins list` shows `rtk-rewrite` enabled if RTK activation was part of the task.

## Reporting

Use fields: `status`, `root_cause`, `fix_applied`, `rtk_activation`, `verification`, `backup`, `notes`.

Do not claim the dialog is fixed from port/process checks alone; require bridge-level chat smoke evidence.
