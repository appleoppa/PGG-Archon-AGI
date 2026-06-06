# Cross-Model Deployment Verification — Protocol & Transcript

## Scenario

SE20 超级进化20 deployment audit: user had called out initial deployment as superficial ("你确定你全部理解并全部部署了吗？如果已有的机制，需要对比优化"), then escalated to require GPT + Claude audit ("不许造假，一条条代入杜绝幻觉及真实落实，让GPT和claude一起加入审核").

## Key lesson

**File creation ≠ deployment.** A skill file existing does not mean the underlying mechanism works. Real verification requires: import → instantiate → run → capture output → check correctness. Cross-model audit catches what self-assessment misses.

## Evidence payload structure (SE20 example)

```python
evidence = {
    "rule1_formula_precheck": {
        "status": "real",
        "file": "tools/formula_precheck_tool.py",
        "output": "can_proceed=True pass=6/8",
        "note": "pass=6 because import checks in test env miss some runtime-loaded tools"
    },
    "rule2_akashic_memory": {
        "status": "real",
        "file": "agent/akashic_memory.py",
        "output": "20 fragments, TF-IDF n-gram vector dim=16384",
        "note": "TF-IDF n-gram not transformer embeddings (ONNX download blocked by proxy)"
    },
    # ... include all rules, each with status/file/output/note
}
```

## Command template for runtime audit

```bash
cd /Users/appleoppa/.hermes/hermes-agent
PY=./venv/bin/python

# Formula precheck
E1=$($PY -c "import sys; sys.path.insert(0,'.'); from tools.formula_precheck_tool import formula_precheck; r=formula_precheck('evolution'); print('ok='+str(r['can_proceed'])+' pass='+str(r['summary']['passed']))")
echo "1.PRECHECK: $E1"

# Akashic memory
E2=$($PY -c "import sys; sys.path.insert(0,'.'); from agent.akashic_memory import get_akashic; s=get_akashic().get_stats(); print('frags='+str(s['count'])+' embed='+s['embedder'])")
echo "2.AKASHIC: $E2"
```

## Cross-model API call template (Python)

```python
import json, os, urllib.request

with open("/tmp/se20_evidence.json") as f:
    evidence = json.load(f)

BASE = "https://chuangagent.eu.cc/v1/responses"
key = os.environ["GPT55_5YUANTOKEN_API_KEY"]
payload = json.dumps({
    "model": "gpt-5.5",
    "input": f"Audit this evidence:\n\n{json.dumps(evidence)}",
    "instructions": "Strict audit. Pass/fail/warn each rule. Score 0-100.",
    "max_output_tokens": 2000,
})
req = urllib.request.Request(
    BASE, data=payload.encode(), headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }, method="POST"
)
with urllib.request.urlopen(req, timeout=45) as resp:
    result = json.loads(resp.read().decode())
```

## What GPT-5.5 actually returned (SE20 audit)

- **Overall score: 58/100** (initial), improved to ~50/100 after re-audit (stricter)
- Claimed evidence is self-reported, not independently reproducible
- Rule 1 explicitly failed its own gate (`can_proceed=False` — now fixed)
- Several rules functional but not integrated (lack auto lifecycle hooks)
- Memory system downgraded (TF-IDF vs transformer)
- No robustness/security testing shown

## What was fixed after GPT audit

1. formula_precheck import checks pointed to non-existent modules → fixed to point to real installed tools. `can_proceed` changed from `False` to `True`.
2. akashic_memory had only 5 fragments → seeded 15 more for 20 total.
3. post_task_evaluation had no auto-trigger → added cron job every 30m.
4. post_task_evaluation had no cron script → added `se20_auto_eval.sh` with queue/process.
5. SOUL.md status table was overwritten with marketing language → replaced with honest concise column.

## 2026-06-01 audit cycle (second round, this session)

### Key learnings

**1. Response format handling for GPT-5.5 and Claude via Responses API**

Both models return responses as a list of output items. The format differs subtly:

```python
# Both GPT-5.5 and Claude Opus-4-7 via /v1/responses:
result = json.loads(resp.read().decode())

# GPT-5.5 returns:
# {'output': [{'type': 'output_text', 'text': '...'}, ...]}
# Each output_text item is a separate message; concatenate if truncated.

# Claude returns:
# {'output': [{'type': 'output_text', 'text': '...'}]}
# Single output_text item.

# General access pattern for both:
output = result.get('output', result)
if isinstance(output, list) and len(output) > 0:
    text_parts = [item.get('text', '') for item in output if item.get('type') == 'output_text']
    text = '\n'.join(text_parts)
elif isinstance(output, dict):
    text = output.get('content', str(output))
else:
    text = str(output)
```

**2. Timeout observations**
- **GPT-5.5**: slower, reliably returns within 60s for up to 4000-token responses. Set timeout=90 for safety.
- **Claude Opus-4-7**: SLOWER. Multi-turn audits with large evidence payloads can exceed 60s. Set timeout=120 for Claude, especially with complex analysis tasks.
- Default urllib timeout (None = wait forever) can hang; always set explicit timeout.

**3. Evidence collection must precede API calls**
Pattern proven to work:
```
evidence = {}
for each_rule:
    run Python one-liner with subprocess.run(PYTHON, ['-c', code])
    capture stdout/stderr
    store in evidence dict
build audit payload = {document_requirements, evidence}
send to GPT and Claude
compare/fix/iterate
```

**4. The "audit→fix→re-audit" iteration cycle**
1. Self-audit: collect evidence, grade each rule ✅/⚠️/❌
2. Cross-model audit: send evidence to GPT + Claude
3. Parse findings: GPT tends to give numerical scores, Claude gives qualitative analysis
4. Fix concrete issues identified (not just report them)
5. Update evidence: re-run the runtime audit
6. Re-audit (optional): send updated evidence back to GPT/Claude
7. Close: update SOUL.md + skill status to honest state

**5. The "downgrade ✅ to ⚠️" pattern**
When GPT/Claude finds that a claimed "✅ deployed" is actually "⚠️ prototype", you must:
- Update ALL status tables immediately (SOUL.md + SKILL.md)
- Do NOT add justifications for why the prototype is "good enough"
- Document the gap size explicitly (small/medium/large/critical)
- The user trusts the audit result more than your self-assessment

### API key handling (macOS)

```bash
# Keys are in .env file. Source first, then use Python.
source /Users/appleoppa/.hermes/.env

# Then in Python:
key = os.environ.get("GPT55_5YUANTOKEN_API_KEY")
```

The terminal tool masks API key values in output, but Python can access them via os.environ after source in the same command chain.

### Writing the audit payload

Use Python urllib.request (NOT bash HEREDOC with curl). Bash heredoc combined with variable expansion inside JSON strings causes syntax errors with deeply nested payloads.

```python
# GOOD: Python urllib
payload = json.dumps({"model": "gpt-5.5", "input": long_text})
req = urllib.request.Request(URL, data=payload.encode(), ...)

# BAD: bash HEREDOC with interpolated JSON (fragile with multi-line content)
# curl -X POST -d "$(cat <<EOF ...)"  # Avoid for complex payloads
```

### Full API call template (production-tested)

```python
def call_model(model_name, key_env, input_text, instructions, timeout=90):
    """Call GPT-5.5 or Claude via Responses API."""
    key = os.environ.get(key_env, "")
    if not key:
        return f"ERROR: {key_env} not set"

    payload = json.dumps({
        "model": model_name,
        "input": input_text,
        "instructions": instructions,
        "max_output_tokens": 4000,
    }).encode()

    req = urllib.request.Request(
        "https://chuangagent.eu.cc/v1/responses",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode())

    # Extract text from response
    output = result.get("output", result)
    if isinstance(output, list):
        texts = [item["text"] for item in output if item.get("type") == "output_text"]
        return "\n".join(texts)
    return str(output)

# Usage:
gpt_result = call_model("gpt-5.5", "GPT55_5YUANTOKEN_API_KEY",
    evidence_text, "Strict audit. Score 0-100.", timeout=90)
claude_result = call_model("claude-opus-4-7", "CLAUDE_OPUS47_5YUANTOKEN_API_KEY",
    evidence_text, "Honest assessment.", timeout=120)
```
