# Local non-Hermes agent inventory

Use this reference when the user asks to inspect locally deployed agents besides Hermes.

## Goal

Produce a current-state inventory, not a memory-based architecture summary. The core distinction is:

- Hermes/PGG internal profile gateways are not external agents.
- A package, repo, plist, config file, or historical manifest is not proof of a currently running agent.
- Current online status requires live process, listening port, health endpoint, or equivalent runtime evidence.

## Bounded inspection sequence

1. Live processes
   - Search for likely agent runtimes and exclude the current Hermes inspection process where necessary.
   - Capture command line, profile/name, and whether the process is truly active.

2. launchd services and plist files on macOS
   - Check `launchctl list` and the matching plist in `~/Library/LaunchAgents`, `/Library/LaunchAgents`, `/Library/LaunchDaemons`.
   - Use `launchctl print gui/$(id -u)/<label>` for state, PID, last exit code, run count, stdout/stderr paths, and arguments.
   - Do not expose secrets from environment variables in the final report.

3. Ports and health endpoints
   - Check listeners before claiming a service is online.
   - If a historical manifest names a health URL, re-query it. Historical HTTP 200 is not current health.

4. Package manager / CLI presence
   - Check npm global packages, Homebrew services, known CLI locations, Docker containers, and app bundles.
   - Classify installed packages without running processes as `installed_not_running`, not online.

5. Workspace repos and binaries
   - For discovered repos, check git HEAD, dirty count, and whether the expected binary exists or can print help.
   - A repo/binary can support `installed_not_running` or `available_to_start`, but not `running` by itself.

6. Logs
   - Read tail/counts of relevant logs when a launchd service is failing.
   - Summarize repeating failure class without dumping long logs or secrets.

## Classification labels

- `running`: live process and/or listener/health proof exists.
- `installed_not_running`: repo/package/binary exists, but no process/listener/health.
- `residual_broken`: stale plist/native-host/plugin/config points to missing binary/package or repeatedly exits.
- `config_only`: credentials/config directories exist but no executable/runtime evidence.
- `Hermes_internal_not_external`: PGG department profiles, Hermes Web UI bridge, SE20/ARS sidecars, or other Hermes-owned runtime.

## Reporting format

Use concise Chinese, field lists, and explicit evidence status:

- 名称
- 类型
- 当前状态
- 证据
- 风险/异常
- 建议动作

End with a short grouped summary:

1. 正在运行
2. 外部 agent 当前在线
3. 外部 agent 已部署但未运行
4. 异常残留
5. 配置痕迹
6. 优先处理项

## Pitfalls

- Do not say an agent is deployed/online because a manifest says it once passed; re-check live state.
- Do not conflate Hermes internal PGG profiles with external agents when the user says “besides Hermes”.
- Do not quote gateway tokens or secrets from plists/logs.
- Do not turn transient local setup mismatches into durable negative claims about a tool; record only the inspection and classification method.
