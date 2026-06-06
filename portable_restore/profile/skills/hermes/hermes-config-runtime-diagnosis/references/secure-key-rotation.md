# Secure API Key Rotation

## When to Use

- User suspects a key has been leaked and wants to rotate it
- User asks "change my API key" or "update the key for provider X"
- Routine key rotation as a security maintenance step

## Principle

**Never expose the key in conversation history.** Use a temp file as a one-shot input vector ("向量输入口"), then atomically update, verify, and destroy.

## 4-Step Pipeline

### Step 1: Create Vector Input File

```bash
cat /dev/null > /tmp/new_PROVIDER_KEY.txt
chmod 600 /tmp/new_PROVIDER_KEY.txt
# Tell user: paste the key here, then say "done"
```

Key file permissions: 600 (owner-only). The user pastes their key by running in their own terminal:

```bash
echo -n 'sk-...newkey' > /tmp/new_PROVIDER_KEY.txt
```

**Edge case:** if the user pastes the echo command **in chat** instead of running it in terminal, you must handle it directly: write the key from the conversation to the temp file yourself, then proceed with the pipeline.

### Step 2: Update `.env`

Identify which `key_env` variable to update. Common Hermes variables:

| Provider | key_env |
|----------|---------|
| GPT (5yuantoken) | `GPT55_5YUANTOKEN_API_KEY` |
| Claude (5yuantoken) | `CLAUDE_OPUS47_5YUANTOKEN_API_KEY` |
| DeepSeek | `DEEPSEEK_V4_FLASH_API_KEY` |
| MiniMax | `MINIMAX_CN_API_KEY` |

**Read the new key from the temp file** (Python, to avoid terminal redaction issues):

```python
with open('/tmp/new_PROVIDER_KEY.txt') as f:
    new_key = f.read().strip()
```

**Update `.env`** — use Python regex to replace the line:

```python
import re
with open('/Users/appleoppa/.hermes/.env') as f:
    content = f.read()
old_pattern = rf'^{key_env}=.*$'
replacement = f'{key_env}={new_key}'
new_content = re.sub(old_pattern, replacement, content, count=1, flags=re.MULTILINE)
with open('/Users/appleoppa/.hermes/.env', 'w') as f:
    f.write(new_content)
```

**Error check:** if `new_content == content`, the pattern was not found — debug by listing `.env` lines with that variable name.

**Also check quantum-router:** if the router reads from the same env var at runtime (via `std::env::var` or `health.rs`), no config change needed. If it stores a hardcoded key, update that too.

### Step 3: Verify with Minimal Request

Make a real API call with the new key using Python (bypasses Hermes terminal redaction of `***`):

```python
import urllib.request, json

# Read key from .env
with open('/Users/appleoppa/.hermes/.env') as f:
    for line in f:
        if line.startswith(f'{key_env}='):
            key = line.strip().split('=', 1)[1]
            break

# Minimal test — use the provider's correct endpoint and auth scheme
data = json.dumps({"model": "MODEL_NAME", "input": "hi", "max_output_tokens": 5}).encode()
req = urllib.request.Request(
    "PROVIDER_BASE_URL",
    data=data,
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
)
try:
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())
    print(f"SUCCESS: {result.get(...)[:50]}")
except urllib.error.HTTPError as e:
    print(f"FAIL: HTTP {e.code} - {e.read().decode()[:200]}")
```

**Provider-specific endpoint and auth:**

| Provider | base_url | auth header | api_mode |
|----------|----------|-------------|----------|
| GPT (5yuantoken/chuanagent) | `https://chuangagent.eu.cc/v1/responses` | `Authorization: Bearer` | codex_responses |
| Claude (5yuantoken/chuanagent) | `https://chuangagent.eu.cc/v1/responses` | `Authorization: Bearer` | codex_responses |
| DeepSeek | `https://api.deepseek.com/v1/chat/completions` | `Authorization: Bearer` | chat_completions |
| MiniMax | `https://api.minimaxi.com/anthropic/v1/messages` | `x-api-key` | anthropic_messages |

### Step 4: Securely Destroy Temp File

macOS does not have `shred`. Use one of:

```bash
# Option A: overwrite then delete
dd if=/dev/urandom of=/tmp/new_PROVIDER_KEY.txt bs=1K count=1 2>/dev/null
rm /tmp/new_PROVIDER_KEY.txt

# Option B: rm -P (3-pass overwrite on macOS)
rm -P /tmp/new_PROVIDER_KEY.txt 2>/dev/null

# Option C: srm (Secure Remove, macOS)
srm /tmp/new_PROVIDER_KEY.txt 2>/dev/null
```

**Verify deletion:**
```bash
ls /tmp/new_PROVIDER_KEY.txt 2>&1 | head -1
# Should print: ls: /tmp/new_PROVIDER_KEY.txt: No such file or directory
```

## Multi-Key Rotation

When rotating multiple keys (e.g. all 4 providers after a suspected mass leak), repeat the pipeline for each. Create separate temp files or reuse the same file with user confirmation.

## Step 5: Post-rotation Security Confirmation

After the key is rotated, the user will often ask whether the old key or the new key was exposed during the process. Run a security trace to give a concrete answer.

### Check Session Recording Status

```bash
python3 << 'PYEOF'
import subprocess, os, glob

# 1. Check record_sessions config
with open(os.path.expanduser('~/.hermes/config.yaml')) as f:
    for line in f:
        if 'record_sessions' in line:
            print(f"Session recording: {line.strip()}")

# 2. Check for active session databases
session_dbs = glob.glob(os.path.expanduser('~/.hermes/sessions/*.db'))
print(f"Session DBs found: {len(session_dbs)}")

# 3. Check for remote sync/export
with open(os.path.expanduser('~/.hermes/config.yaml')) as f:
    for line in f:
        if any(k in line.lower() for k in ['export', 'sync', 'upload', 'remote']):
            print(f"Remote config: {line.strip()}")

# 4. Check for any other DB files containing session data
other_dbs = glob.glob(os.path.expanduser('~/.hermes/*.db'))
session_relevant = [d for d in other_dbs
    if not any(x in d for x in ['skill_bank', 'state', 'genome'])]
print(f"Other relevant DBs: {session_relevant if session_relevant else 'none'}")
PYEOF
```

### Report Template

When the user asks "did it leak?", structure the answer as a table:

| Risk Path | Verdict | Evidence |
|-----------|---------|----------|
| Session log on disk | Safe / At risk | `record_sessions: <true/false>`, session DB existence |
| Tool output masking | Safe | Terminal tool replaces secrets with `***` |
| Remote sync/upload | Safe / At risk | Sync/export config status |
| `.env` file | ✅ Correct location | Where secrets belong |
| Temp file | ✅ Destroyed | Overwrite method + deletion confirmation |

## Pitfalls

| Pitfall | Symptom | Resolution |
|---------|---------|------------|
| **User pastes command in chat, not terminal** | Temp file is empty (0 bytes) when you read it | The key is already exposed in the conversation. Write it from the chat to the temp file yourself, then proceed with the pipeline. Do NOT ask the user to repeat themselves. |
| **Terminal tool masks secrets as `***`** | `grep`, `cat`, `source .env` all return `***` instead of the key | Use Python `with open(...)` and `.read()` to get raw file content — bypasses the terminal-level redaction completely. |
| **write_file truncation from mental redaction** | You accidentally write `sk-db9...81c3` instead of the full 67-char key | Copy the exact string from the user's message. Do not abbreviate or redact when writing to the temp file — the key is already in the conversation. Focus on processing it quickly and destroying the file. |
| **`shred` not found on macOS** | `shred: command not found` | Use `dd if=/dev/urandom` + `rm`, or `rm -P`, or `srm` instead. |
| **`.env` sourcing fails in subprocesses** | `source ~/.hermes/.env` then `$KEY_VAR` is empty | Herited env vars are not exported to subprocess children. Use `export KEY=$(grep ...)` or Python file read. |

## Verification Checklist

- [ ] New key written to `.env` — Python readback confirms length > variable name length
- [ ] Test request returns 200 with expected response content
- [ ] Quantum router (if applicable) reads the same env var at runtime — no config change needed
- [ ] Temp file securely destroyed (overwrite + rm on macOS)
- [ ] Post-rotation security confirmation completed — session recording checked, no stale DBs
- [ ] User told to start a new session (gateway restart) for env var to take effect in running processes
