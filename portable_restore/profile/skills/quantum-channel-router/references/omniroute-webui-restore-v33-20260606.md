# OmniRoute WebUI restore + v3.2 cockpit v3.3 — 2026-06-06

## Status

`PASS_WEBUI_RESTORED_V32_VISIBLE`

## Discovery

Current launchd WebUI:

```text
label = ai.hermes.webui
pid = 86634
port = 8648
program = /usr/local/bin/node /Users/appleoppa/.hermes/webui/node_modules/hermes-web-ui/dist/server/index.js
static client = /Users/appleoppa/.hermes/webui/node_modules/hermes-web-ui/dist/client
```

The old `omniroute.html` existed only in backup:

```text
/Users/appleoppa/.hermes/workspace/config-backups/webui-final-unify-20260606-130812/hermes-web-ui.old-root.version-0.6.10/dist/client/omniroute.html
```

## Restored

Copied and upgraded to:

```text
/Users/appleoppa/.hermes/webui/node_modules/hermes-web-ui/dist/client/omniroute.html
```

Added v3.2 cockpit panel:

```text
OmniRoute v3.2 Fallback Window
Run fallback window
v32FallbackBox
```

## Runtime verification

HTTP:

```text
GET http://127.0.0.1:8648/omniroute.html -> 200 OK
```

Browser DOM:

```json
{
  "hasBox": true,
  "hasRun": "function",
  "text": {
    "status": "PASS",
    "sample_count": 20,
    "primary_http_502_count": 20,
    "fallback_success_count": 20,
    "cross_class_fallback_count": 20,
    "leakage_count": 0
  }
}
```

## Boundary

This restores visibility only. It does not change route-enforce, provider substitution, or legal/audit/AGI denial rules.
