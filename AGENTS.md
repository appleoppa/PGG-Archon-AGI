# Hermes Agent - Development Guide

Compact instructions for AI coding assistants working in this repository. Full archived/reference version: `website/docs/developer-guide/agents-full-reference.md`. Load that file only when exact legacy detail is needed.

## Prime Directive

- Verify with real files/tests/logs before claiming completion.
- Keep prompt/context small: search/read targeted sections; avoid dumping large files.
- Do not expose secrets. Config stores key env names; `.env` stores actual secrets.
- Do not mix unrelated working-tree changes into commits. Stage only the files for the current task.

## Development Environment

```bash
source .venv/bin/activate   # or: source venv/bin/activate
```

`scripts/run_tests.sh` probes `.venv`, then `venv`, then `$HOME/.hermes/hermes-agent/venv`.

## High-Value Entry Points

- `run_agent.py` — `AIAgent`, conversation loop, session persistence, prompt/cache lifecycle.
- `agent/` — provider adapters, prompt assembly, context compression, memory, transports.
- `model_tools.py` + `tools/registry.py` — tool discovery, schemas, dispatch.
- `tools/` — built-in tool implementations; each top-level tool registers itself.
- `toolsets.py` — toolset definitions and core tool bundle.
- `hermes_state.py` — SQLite session store and FTS5 search.
- `gateway/run.py` + `gateway/platforms/` — messaging gateway and adapters.
- `hermes_cli/` + `cli.py` — CLI, slash commands, setup/config/profile commands.
- `plugins/` — plugin surfaces: memory, model providers, context engines, image providers.
- `cron/` — scheduled jobs and scheduler runtime.
- `tests/` — pytest suite; prefer targeted tests plus relevant integration tests.

Dependency chain:

```text
tools/registry.py -> tools/*.py -> model_tools.py -> run_agent.py/cli.py/gateway/batch
```

## AIAgent / Prompt / Context Rules

- `AIAgent.__init__` has many runtime parameters; inspect `run_agent.py` before changing signatures.
- `run_conversation()` is the core synchronous loop: build prompt -> call model -> execute tool calls -> append tool results -> persist/trajectory/cleanup.
- Prompt caching must not break. Do not mutate past context, toolsets, memories, or system prompt mid-conversation except through the established compression path.
- Slash commands that change system-prompt state should default to next-session/deferred invalidation; provide an explicit immediate option if needed.
- Context files (`SOUL.md`, `AGENTS.md`, `.cursorrules`) are loaded by `agent/prompt_builder.py`; keep them compact. Move long detail to docs/references.

## Tools

When adding or modifying tools:

1. Implement in `tools/<name>_tool.py`.
2. Register with `tools.registry.registry.register(...)` at module level.
3. Add to `toolsets.py`; auto-discovery imports tools, but exposure is deliberate.
4. Handlers return JSON strings unless the tool framework explicitly documents otherwise.
5. Use `get_hermes_home()` for persistent state; use `display_hermes_home()` in user-facing text.
6. Keep schema descriptions self-contained. Do not mention tools from other toolsets unless dynamically gated in `model_tools.py`.
7. Set/verify result-size behavior for high-output tools; large outputs must be paginated, summarized, or persisted rather than injected wholesale.

## Configuration and Profiles

- User config: `~/.hermes/config.yaml`.
- Secrets: `~/.hermes/.env` only. Do not print or commit secret values.
- Use config loaders appropriate to the layer being changed; do not invent parallel config paths.
- Profiles isolate `HERMES_HOME`. Code that reads/writes Hermes state must use `get_hermes_home()`.
- User-facing paths should use `display_hermes_home()`.
- Profile operations that enumerate all profiles are HOME-anchored by design; do not accidentally scope them to the active profile.

## Plugins

- General plugins live under `plugins/<name>/` or user plugin dirs and register hooks/tools/CLI commands through the plugin context.
- Plugins must not patch core files for plugin-specific behavior. If a plugin needs a new capability, expand the generic plugin API/hook surface.
- New memory providers should be standalone plugin repos, not new in-tree `plugins/memory/<name>/` directories.
- Model providers register through `plugins/model-providers/<name>/` and `providers.register_provider(...)`; user plugins can override bundled providers.

## Skills

- Built-in skills: `skills/`; heavier/niche official skills: `optional-skills/`.
- `SKILL.md` frontmatter should include `name`, short `description`, `version`, `author`, `license`, platform gating when needed, tags/category/related skills.
- Description should be concise and capability-focused; avoid marketing wording.
- Skill prose should reference Hermes tools (`read_file`, `search_files`, `patch`, `terminal`, etc.) rather than raw shell equivalents when those wrappers exist.
- Put helper scripts in `scripts/`, references in `references/`, templates in `templates/`; keep main `SKILL.md` procedural and bounded.
- Tests for skills belong under `tests/skills/` and should avoid live network calls.

## Delegation / Cron / Kanban

- `delegate_task` creates isolated subagents and is synchronous from the parent’s perspective. If the parent is interrupted, child work is cancelled.
- Cron jobs must be self-contained. Future runs do not inherit current chat context. Do not let cron sessions recursively schedule more cron jobs.
- Cron success means the tick ran, not that business output is correct; verify side effects.
- Kanban coordinates multi-agent work; each card should have explicit objective, evidence, and completion criteria.

## Gateway and Background Processes

- Gateway has adapter-level and runner-level message guards. Control/approval commands that must interrupt a running agent must bypass both guards.
- Gateway platform adapters using unique credentials should use scoped token locks to avoid two profiles using the same bot/app credential.
- For `terminal(background=true)`, use `notify_on_complete=true` for bounded jobs. Use watch patterns only for rare one-shot signals in long-lived processes.

## Testing

Preferred command:

```bash
scripts/run_tests.sh tests/path_or_file.py::test_name -q
```

In this local macOS checkout, `venv/bin/python -m pytest ...` is acceptable for quick targeted verification when wrapper overhead is unnecessary; still run the relevant targeted suites before committing.

Testing rules:

- Do not write tests that depend on live secrets, real `~/.hermes`, current time zone, external network, or exact changing catalog counts.
- Prefer behavior/invariant tests over change-detector snapshots.
- If mocking `Path.home()`, set `HERMES_HOME` too when code uses Hermes paths.
- Always run `git diff --check` and at least syntax/targeted tests for edited Python files.

## Known Pitfalls

- Never hardcode `~/.hermes` / `Path.home() / ".hermes"` in runtime state paths.
- Do not introduce new `simple_term_menu` usage; prefer the curses UI helpers.
- Do not use raw ANSI erase-to-EOL `\033[K` in spinner/display code; use space-padding.
- `model_tools._last_resolved_tool_names` is process-global; subagents save/restore it.
- Stale squash merges can silently revert unrelated fixes; inspect diffs after merging.
- Do not wire dead code into active paths without E2E validation.
- Tests must not write into the real Hermes home; use temp homes/fixtures.

## Reference Map

Use targeted docs instead of expanding this file:

- Agent loop: `website/docs/developer-guide/agent-loop.md`
- Prompt assembly/cache: `website/docs/developer-guide/prompt-assembly.md`
- Tools runtime: `website/docs/developer-guide/tools-runtime.md`
- CLI extension: `website/docs/developer-guide/extending-the-cli.md`
- Cron internals: `website/docs/developer-guide/cron-internals.md`
- Memory provider plugins: `website/docs/developer-guide/memory-provider-plugin.md`
- Model provider plugins: `website/docs/developer-guide/model-provider-plugin.md`
- Platform adapters: `website/docs/developer-guide/adding-platform-adapters.md`
- Full previous AGENTS reference: `website/docs/developer-guide/agents-full-reference.md`
