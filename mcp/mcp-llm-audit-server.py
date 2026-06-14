"""
Multi-LLM Audit MCP Server — wraps existing Hermes providers as MCP tools
Each provider (GPT-5.5, Claude, DeepSeek, MiMo, Agnes) becomes a callable MCP tool
for multi-model audit chains.

Usage via Hermes CLI (after config): 
  hermes mcp add llm-audit --command python3 --args /path/to/mcp-llm-audit-server.py

Then available as MCP tools: audit_gpt55, audit_claude, audit_deepseek, audit_mimo, audit_agnes
"""
import json, sys, os, subprocess
from pathlib import Path

HERMES = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
AGENT = HERMES / "hermes-agent"
VENV = AGENT / "venv" / "bin" / "python"

# MCP protocol: read a JSON-RPC request from stdin, write response to stdout
PROVIDERS = {
    "gpt55": {"provider": "custom:gpt55_5yuantoken", "model": "gpt-5.5", "desc": "GPT-5.5 主力审计"},
    "claude": {"provider": "custom:claude_opus46_5yuantoken", "model": "claude-opus-4-6", "desc": "Claude Opus 4-6 深度审计"},
    "deepseek": {"provider": "custom:deepseek_v4_flash", "model": "deepseek-v4-flash", "desc": "DeepSeek V4 快速审计"},
    "mimo": {"provider": "custom:mimo_v25_pro_auditor", "model": "mimo-v2.5-pro", "desc": "MiMo V2.5 Pro 第三方审计"},
    "agnes": {"provider": "custom:agnes_20_flash", "model": "agnes-2.0-flash", "desc": "Agnes 2.0 Flash 辅助审计"},
}

TOOLS = []
for name, cfg in PROVIDERS.items():
    TOOLS.append({
        "name": f"audit_{name}",
        "description": f"Call {cfg['model']} ({cfg['desc']}) for audit/review",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Audit prompt"},
                "system": {"type": "string", "description": "System prompt (optional)"},
            },
            "required": ["prompt"]
        }
    })

def handle_list_tools(req):
    return {"jsonrpc": "2.0", "id": req.get("id"), "result": {"tools": TOOLS}}

def handle_call_tool(req):
    name = req["params"]["name"]
    args = req["params"].get("arguments", {})

    if not name.startswith("audit_") or name[6:] not in PROVIDERS:
        return {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32601, "message": f"Unknown tool: {name}"}}

    provider_name = name[6:]
    cfg = PROVIDERS[provider_name]
    prompt = args.get("prompt", "")
    system = args.get("system", "You are a strict auditor. Be concise, specific, and evidence-based.")

    # Call the provider via subprocess using the hermes CLI entry point
    hermes_bin = VENV.parent / "hermes"
    cmd = [
        str(hermes_bin),
        "chat",
        "--model", cfg["model"],
        "--provider", cfg["provider"],
        "-Q",
        "-q", f"{system}\n\n---\n\n{prompt}"
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output = r.stdout.strip() or r.stderr.strip() or "No output"
        if len(output) > 8000:
            output = output[:8000] + "...[truncated]"
    except subprocess.TimeoutExpired:
        output = "ERROR: Provider timed out (120s)"
    except Exception as e:
        output = f"ERROR: {str(e)}"

    return {
        "jsonrpc": "2.0", "id": req.get("id"),
        "result": {
            "content": [{"type": "text", "text": output}]
        }
    }

def main():
    """Run MCP server loop — read JSON-RPC from stdin, write to stdout."""
    # Respond to server info (for hermes mcp add)
    if len(sys.argv) > 1 and sys.argv[1] == "--info":
        print(json.dumps({
            "name": "llm-audit",
            "version": "0.1.0",
            "providers": list(PROVIDERS.keys()),
            "description": "Multi-LLM audit MCP server — GPT-5.5/Claude/DeepSeek/MiMo/Agnes"
        }))
        return
    
    # MCP protocol: read lines from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method", "")
            
            if method.startswith("notifications/"):
                # JSON-RPC/MCP notifications MUST NOT receive a response. Responding
                # with id=None makes the Hermes MCP client reject our stdout as an
                # invalid JSONRPCMessage and triggers reconnect noise.
                continue
            if method == "tools/list":
                resp = handle_list_tools(req)
            elif method == "tools/call":
                resp = handle_call_tool(req)
            elif method == "initialize":
                resp = {"jsonrpc": "2.0", "id": req.get("id"), "result": {
                    "protocolVersion": "2025-03-26",
                    "serverInfo": {"name": "llm-audit", "version": "0.1.0"},
                    "capabilities": {"tools": {}}
                }}
            elif method == "notifications/tools/list_changed":
                resp = {"jsonrpc": "2.0", "id": req.get("id"), "result": {}}
            else:
                resp = {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32601, "message": f"Unknown method: {method}"}}
            
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except json.JSONDecodeError:
            continue
        except Exception as e:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
