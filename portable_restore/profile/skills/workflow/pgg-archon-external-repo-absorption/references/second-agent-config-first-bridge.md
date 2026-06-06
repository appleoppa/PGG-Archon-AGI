# Second-agent absorption: config-first bridge checklist

Use this when converting an external agent platform (for example PilotDeck) into a bounded second AGI-like node that learns from Hermes/PGG Archon.

## Durable lessons

1. **Configuration comes before evolution.** Do not push detailed evolution formulas, manifests, or AGI claims until the target agent's own UI, gateway, config loader, and model routing are stable and usable.
2. **Respect physical isolation.** Keep Hermes under `~/.hermes`, the auxiliary agent under its own hidden root (for example `~/.pilotdeck-agi`), and exchange material only through an independent hidden bridge directory (for example `~/.agent-bridge`). Do not create visible Home-root project folders.
3. **Bind runtime config explicitly.** If the target agent has both CLI/gateway and Web UI processes, start every process with the same explicit config variables, such as `PILOT_HOME` and `PILOTDECK_CONFIG_PATH`; otherwise the UI may read a default/old YAML even when the CLI loader validates the intended file.
4. **Validate with every relevant parser.** Check YAML syntax, the target agent's native config loader, the Web UI/server validator or config API, and the browser UI. A syntax-valid YAML can still fail if the running process reads a different file.
5. **Share LLMs through a local bridge, not by copying secrets.** Expose a localhost OpenAI-compatible bridge where appropriate; keep real API keys in Hermes/Bridge runtime and put only local placeholder credentials in the target agent config.
6. **Call all configured LLMs for high-risk fusion only after config works.** Multi-LLM review is useful for architecture/fusion, but it must not replace smoke tests of actual startup paths and UI operation.
7. **Report bounded status honestly.** Acceptable wording: bounded second AGI node / learning gate passed. Avoid full AGI, zero-risk, unsupervised production, or replacement claims.

## Verification evidence to collect

- Config path returned by the target UI/server API, not just the file you edited.
- Native loader result with diagnostics/errors.
- Gateway health endpoint.
- Web UI HTTP 200 and browser navigation into the relevant settings/config page.
- LLM bridge `/health` and `/v1/models` if model sharing is involved.
- Smoke test through every shared model when model routing changes.
- A hidden-bridge report summarizing paths, checks, and redacted config facts.

## Common fix pattern for PilotDeck-like systems

```bash
export PILOT_HOME=/path/to/.pilotdeck-agi/home/.pilotdeck
export PILOTDECK_CONFIG_PATH=/path/to/.pilotdeck-agi/home/.pilotdeck/pilotdeck.yaml
```

Then start both the gateway/server and Web UI with those variables, and verify the UI config API returns the same `PILOTDECK_CONFIG_PATH`.
