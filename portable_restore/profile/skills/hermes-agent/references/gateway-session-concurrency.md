# Gateway session concurrency and busy-turn behavior

Use when diagnosing reports like: “same desktop/user has multiple conversations but only one runs”, “messages get queued/interrupted”, or “why can’t three Feishu/Lark chats run simultaneously?”

## Durable model

Hermes Gateway concurrency is session-key based, not UI-window based and not simply username based.

- Gateway tracks active turns in `GatewayRunner._running_agents[session_key]`.
- If a new inbound event maps to an existing running `session_key`, it enters the busy path: queue, steer, interrupt, reject mid-turn slash commands, or require `/stop` depending on command and `ui.busy_input_mode`.
- Distinct session keys can run independently; same session key is intentionally serialized to protect transcript/tool state.

## Session-key construction highlights

Core source: `gateway/session.py::build_session_key()`.

- DM: includes platform + `chat_id`; `thread_id` further isolates threaded DMs.
- Group/channel: includes platform + chat type + `chat_id`; appends `thread_id` when present.
- `group_sessions_per_user: true` appends participant identity for non-thread group/channel sessions.
- Threads default shared across users unless `thread_sessions_per_user` is enabled.

## Feishu/Lark-specific notes

Source: `gateway/platforms/feishu.py`.

- Feishu normalizes inbound messages into `SessionSource` using `chat_id`, resolved `chat_type`, `user_id`, `user_id_alt`/`union_id`, and `thread_id` from `message.thread_id` or `message.root_id`.
- A desktop user opening multiple visible conversations does not guarantee multiple Hermes sessions; the deciding evidence is the backend `chat_id/thread_id` passed to Hermes.
- Feishu adapter also maintains per-chat locks (`_chat_locks: Dict[str, asyncio.Lock]`) for per-chat serial processing, so same `chat_id` may be serialized even before session-key-level concurrency is considered.

## Web UI profile/model/session boundary

Hermes Web UI adds a separate three-layer concept on top of gateway session concurrency:

- `profile` = user/environment context.
- `model` = the actual model chosen for that session.
- `session` = the concrete instance that stores the chosen profile, model, and provider together.

Important implications:

- A profile's default model is only a default, not a restriction.
- A profile can create sessions with other visible models if the UI exposes them.
- Do not infer routing decisions from Web UI profile names.
- Do not treat a profile gateway with empty `platforms` as residual just because it has no messaging platforms; it may still be serving an active Web UI conversation.
- When investigating “why did this conversation stop”, distinguish UI/session identity from backend gateway health and upstream provider health.

## Routing boundary

- `qr route` is a task-routing aid, not a Web UI session classifier.
- Use `qr route` for deciding what model family to assign to a task.
- Use Web UI `sessions` / `model_context` / visible-model config to understand what a specific conversation was actually using.
- If `qr` output and current conversation model disagree, treat the route as a suggestion unless the task is explicitly being moved to a different execution lane.

1. State the distinction: “parallelism is by Hermes session_key, not by desktop window or username.”
2. Explain likely cases:
   - Different private chats / different `chat_id`: can run concurrently.
   - Same chat/thread/session: cannot run concurrently; follow-ups are busy-handled.
   - Same Feishu `chat_id`: may be serialized by Feishu per-chat lock.
3. Mention safe controls:
   - `/queue <prompt>` for ordered follow-up turns.
   - `/steer <prompt>` to inject into the running task when appropriate.
   - `/stop` before replacing a running task.
4. If exact proof is needed, inspect session keys/logs rather than guessing from UI labels.

## Do not overclaim

- Do not say “same username can never run three tasks.” That is false.
- Do not say “three windows can run” unless verified they map to distinct `chat_id/thread_id`/session keys.
- Prefer evidence language: “if these three entries share the same session_key, they serialize.”
