# Weixin/WeChat Channel Removal Reference

## Purpose

Concrete cleanup checklist for removing a configured Hermes Weixin/WeChat channel while preserving unrelated gateway platforms and core adapter code.

## Known state surfaces

A Weixin channel may be visible from several places:

- active credential keys such as `WEIXIN_TOKEN`, `WEIXIN_BASE_URL`, `WEIXIN_ACCOUNT_ID`
- pairing approval state such as `pairing/weixin-approved.json` and `pairing/weixin-pending.json`
- rate-limit or approval metadata containing `weixin`, `wechat`, or `im.wechat`
- local account cache under `weixin/accounts/`
- session directory entries whose origin platform is `weixin`
- `channel_directory.json` under `platforms.weixin`
- `gateway_state.json` under `platforms.weixin`
- historical logs/session transcripts, which should generally not be rewritten just to remove an active channel

## Safe cleanup sequence

1. Back up the active files/directories to a timestamped backup folder.
2. Remove only Weixin/WeChat credential keys from the active `.env`; do not print values.
3. Delete Weixin pairing files and clean Weixin-related rate-limit entries.
4. Remove Weixin local account cache when the user asked to delete, not merely pause.
5. Remove Weixin entries from the session directory source, otherwise channel discovery may repopulate `channel_directory.json`.
6. Clear `platforms.weixin` in `channel_directory.json`.
7. Restart the gateway so environment changes take effect.
8. If `gateway_state.json` still contains a stale disconnected `weixin` block after the channel is disabled, back up gateway state and remove that block.
9. Verify with a user-facing target list and state counts.

## Verification fields

Report concise verification, for example:

```json
{
  "env_weixin_keys_remaining": [],
  "pairing_weixin_files": [],
  "weixin_cache_exists": false,
  "sessions_weixin_entries": 0,
  "channel_directory_weixin_entries": 0,
  "gateway_state_has_weixin": false
}
```

Also verify that the messaging target list no longer contains a `Weixin:` section.

## Preserve

Do not delete these unless the user explicitly asks to modify Hermes source code:

- `gateway/platforms/weixin.py`
- Weixin documentation
- Weixin tests
- historical logs and session transcripts

These are product capability/history, not the live configured channel.
