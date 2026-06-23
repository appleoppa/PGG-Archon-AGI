"""
Multi-LLM Audit MCP Server — reads provider config from Hermes config.yaml
Each provider (GPT-5.5, Claude, DeepSeek) becomes a callable MCP tool.

Source of truth for providers: ~/.hermes/config.yaml → custom_providers[]
Source of truth for API keys:  ~/.hermes/.env  → key_env field

No hardcoded URLs, models, or API keys.
No hermes subprocess spawning (conflicts with parent session).
"""
import json, sys, os, re, urllib.request, urllib.error
from pathlib import Path

HERMES = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
CONFIG = HERMES / "config.yaml"
ENV    = HERMES / ".env"

# ── Load API keys from .env ────────────────────────────────────────
def load_env():
    """Parse ~/.hermes/.env, return dict of KEY=VALUE."""
    if not ENV.exists():
        return {}
    env = {}
    for line in ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=["\']?(.*?)["\']?\s*(?:#.*)?$', line)
        if m:
            env[m.group(1)] = m.group(2).strip()
    return env

ENV_VARS = load_env()

# ── Load provider config from config.yaml ──────────────────────────
def load_custom_providers():
    """Read custom_providers[] from Hermes config.yaml.
    Returns dict mapping provider name to its config."""
    if not CONFIG.exists():
        return {}
    try:
        import yaml
        with open(CONFIG) as f:
            cfg = yaml.safe_load(f)
    except Exception:
        return {}

    providers = cfg.get("custom_providers") or cfg.get("providers", {}).get("custom_providers") or []
    if isinstance(providers, dict):
        providers = list(providers.values())

    result = {}
    for p in providers:
        name = p.get("name", "")
        if not name:
            continue
        result[name] = {
            "base_url": p.get("base_url", "").rstrip("/"),
            "model": p.get("model") or p.get("default_model", ""),
            "api_mode": p.get("api_mode", "chat_completions"),
            "key_env": p.get("key_env", ""),
            "description": f"{p.get('model') or p.get('default_model', '?')} 审计",
        }
    return result

CUSTOM_PROVIDERS = load_custom_providers()

# ── Map MCP tool names → provider name in config ──────────────────
PROVIDER_MAP = {
    "gpt55":    "gpt55_5yuantoken",
    "claude":   "claude_opus46_5yuantoken",
    "deepseek": "deepseek_v4_flash",
}

# ── Build MCP tools from resolved provider config ─────────────────
TOOLS = []
for tool_name, cfg_name in PROVIDER_MAP.items():
    cfg = CUSTOM_PROVIDERS.get(cfg_name)
    if not cfg:
        continue
    desc = cfg.get("description", f"{cfg_name} 审计")
    TOOLS.append({
        "name": f"audit_{tool_name}",
        "description": f"Call {cfg['model']} ({desc}) for audit/review",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Audit prompt"},
                "system": {"type": "string", "description": "System prompt (optional)"},
            },
            "required": ["prompt"],
        },
    })


def call_provider(cfg, prompt, system, timeout=120):
    """Direct HTTP POST using the provider's declared api_mode.

    Supported modes:
    - codex_responses: OpenAI-compatible Responses API at /responses
    - chat_completions: OpenAI-compatible Chat Completions API at /chat/completions
    - anthropic_messages: Anthropic Messages API at /messages

    Uses config from config.yaml (base_url, model, api_mode) and API key from .env.
    """
    api_key = ENV_VARS.get(cfg.get("key_env", ""), "")
    if not api_key:
        return f"ERROR: {cfg.get('key_env', '?')} not found in ~/.hermes/.env"

    api_mode = cfg.get("api_mode", "chat_completions")
    model = cfg.get("model", "")
    base_url = cfg.get("base_url", "")

    if api_mode == "anthropic_messages":
        # Anthropic Messages API
        url = f"{base_url}/messages"
        messages = []
        if system:
            messages.append({"role": "user", "content": f"[System]\n{system}\n\n{prompt}"})
        else:
            messages.append({"role": "user", "content": prompt})
        body = json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
    elif api_mode == "codex_responses":
        # OpenAI-compatible Responses API. Do not route this mode through
        # /chat/completions; GPT/Claude codex providers are configured to use
        # the Responses wire shape.
        url = f"{base_url}/responses"
        body = json.dumps({
            "model": model,
            "instructions": system or "You are a strict auditor.",
            "input": prompt,
            "max_output_tokens": 4096,
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
    elif api_mode == "chat_completions":
        # OpenAI-compatible Chat Completions API
        url = f"{base_url}/chat/completions"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.3,
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
    else:
        return f"ERROR: unsupported api_mode '{api_mode}' for model '{model}'"

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        return f"ERROR: HTTP {e.code} — {err_body}"
    except urllib.error.URLError as e:
        return f"ERROR: {e.reason}"
    except Exception as e:
        return f"ERROR: {str(e)}"

    if api_mode == "anthropic_messages":
        # Anthropic format
        content_blocks = data.get("content", [])
        text = " ".join(b.get("text", "") for b in content_blocks if isinstance(b, dict))
    elif api_mode == "codex_responses":
        # Responses API format; prefer output_text when present, then walk blocks.
        text = data.get("output_text", "")
        if not text:
            parts = []
            for item in data.get("output", []):
                if not isinstance(item, dict):
                    continue
                for block in item.get("content", []):
                    if isinstance(block, dict):
                        parts.append(block.get("text") or block.get("content") or "")
            text = " ".join(p for p in parts if p)
    else:
        # OpenAI-compatible chat completions format
        choices = data.get("choices", [])
        text = choices[0].get("message", {}).get("content", "") if choices else json.dumps(data)

    if len(text) > 8000:
        text = text[:8000] + "...[truncated]"
    return text or "No content in response"


def handle_list_tools(req):
    return {"jsonrpc": "2.0", "id": req.get("id"), "result": {"tools": TOOLS}}

def handle_call_tool(req):
    name = req["params"]["name"]
    args = req["params"].get("arguments", {})

    if not name.startswith("audit_") or name[6:] not in PROVIDER_MAP:
        return {"jsonrpc": "2.0", "id": req.get("id"),
                "error": {"code": -32601, "message": f"Unknown tool: {name}"}}

    cfg_name = PROVIDER_MAP[name[6:]]
    cfg = CUSTOM_PROVIDERS.get(cfg_name)
    if not cfg:
        return {"jsonrpc": "2.0", "id": req.get("id"),
                "error": {"code": -32603, "message": f"Provider '{cfg_name}' not found in config.yaml custom_providers"}}

    prompt = args.get("prompt", "")
    system = args.get("system", "You are a strict auditor. Be concise, specific, and evidence-based.")
    output = call_provider(cfg, prompt, system)

    return {
        "jsonrpc": "2.0", "id": req.get("id"),
        "result": {"content": [{"type": "text", "text": output}]},
    }


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--info":
        print(json.dumps({
            "name": "llm-audit",
            "version": "0.3.0",
            "providers": list(PROVIDER_MAP.keys()),
            "resolved_from_config": {
                tool_name: CUSTOM_PROVIDERS.get(cfg_name, {}).get("model", "not_found")
                for tool_name, cfg_name in PROVIDER_MAP.items()
            },
            "description": "Multi-LLM audit MCP server — reads provider config from config.yaml",
        }))
        return

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method", "")

            if method.startswith("notifications/"):
                continue
            elif method == "tools/list":
                resp = handle_list_tools(req)
            elif method == "tools/call":
                resp = handle_call_tool(req)
            elif method == "initialize":
                resp = {"jsonrpc": "2.0", "id": req.get("id"), "result": {
                    "protocolVersion": "2025-03-26",
                    "serverInfo": {"name": "llm-audit", "version": "0.3.0"},
                    "capabilities": {"tools": {}},
                }}
            else:
                resp = {"jsonrpc": "2.0", "id": req.get("id"),
                        "error": {"code": -32601, "message": f"Unknown method: {method}"}}

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            continue
        except Exception as e:
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)},
            }) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()