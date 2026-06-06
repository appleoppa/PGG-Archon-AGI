---
name: messaging-channel-governance
description: Disable, remove, or clean up Hermes messaging gateway channels without leaving stale directory/session targets.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, gateway, messaging, channels, configuration]
    related_skills: [hermes-agent, hermes-config-runtime-diagnosis]
---

# Messaging Channel Governance

## Trigger

Use this when the user asks to close, disable, remove, delete, or clean up a messaging channel in Hermes Gateway, including Weixin/WeChat, Feishu/Lark, Telegram, Discord, Slack, or similar platform adapters.

Do not treat channel deletion as only removing one credential. A channel can survive through credentials, pairing files, account caches, session directory discovery, channel directory cache, and gateway state.

## Workflow

1. Scope the active profile first.
   - Default profile changes affect the live gateway used by the user.
   - Do not edit other profile credential stores unless the user explicitly asks.

2. Classify the request before changing anything.
   - If the user asks to remove/disable a channel, continue with credential/runtime cleanup below.
   - If the user only asks to hide tool-call/progress chatter in a platform chat, do **not** remove credentials, adapters, sessions, or channel state. Treat it as a display configuration change.
   - For platform-specific tool progress, set `display.platforms.<platform>.tool_progress: off` in the active profile `config.yaml` after backing it up, then restart the live gateway and verify the effective platform value is `off`. Leave global `display.tool_progress` and other platforms unchanged unless the user asks for a global change.
   - Keep `runtime_footer.enabled: false` checked separately when the complaint is about metadata footers; tool progress and runtime footer are different controls.

3. Discover the live target list.
   - Use the messaging target listing tool when available.
   - Confirm which platform entries are visible before changing anything.

4. Back up before destructive cleanup or display config edits.
   - Store backups under a timestamped directory in the active Hermes home backup area.
   - Do not print secrets from `.env` or credential stores.

5. Disable credentials/config minimally.
   - Remove only the platform-specific keys requested, e.g. `WEIXIN_*` / `WECHAT_*` for Weixin.
   - Leave unrelated platforms untouched.

5. Remove platform runtime identity state.
   - Delete or clean platform-specific pairing/approval files.
   - Delete platform-specific local account caches if the user asked to delete the channel, not merely pause it.
   - Remove platform entries from the session directory source when that source is used for channel discovery.

6. Clear stale discovery output.
   - Clear the platform entry in `channel_directory.json`.
   - If gateway state still shows a disconnected stale platform after successful disablement, remove the stale platform block from gateway state after backing it up.

7. Restart or reload the gateway.
   - Restart the relevant launchd/systemd/service-managed gateway so environment changes take effect.
   - Do not claim the channel is gone before restart/readback.

8. Verify from user-facing output.
   - Re-run target listing and confirm the removed platform no longer appears.
   - Check active config/state counts: remaining platform env keys, pairing files, account cache, session source entries, channel directory entries, and gateway state platform presence.

## Pitfalls

- `channel_directory.json` may be repopulated from session history even after credentials are removed. Clean the session directory source for the platform before final verification.
- A disconnected stale platform block in `gateway_state.json` is not an active connection, but it confuses status reporting. Back it up and remove the stale block when the user asked to delete the channel.
- Do not delete adapter source code, documentation, or tests when the user asks to delete a configured channel. Source code is product capability; credentials and runtime state are the configured channel.
- Do not expose token values while auditing `.env`; report key names and counts only.

## References

- `references/weixin-channel-removal.md` — concrete Weixin/WeChat cleanup checklist and verification fields from a live Hermes Gateway removal.
