# SE20 Middleware Architecture

Designed 2026-06-01 via three-model consultation (DeepSeek V4 Flash + GPT-5.5 + Claude Opus-4-7).

## Core insight

The original SE20 document described 8 independent "kernel-level axioms" that should govern all LLM behavior. The three models independently agreed: you cannot control third-party LLM internals, but you CAN build a middleware stack that wraps every call with pre/post hooks — achieving the *behavioral* effect without the *system-level* claim.

## Architecture

### Central dispatcher (`se20/SE20Agent`)

```
User input → SE20Agent.execute()
              │
              ├─ [PRE] R1: precheck_gates() → block if fails
              │
              ├─ LLM/model call (handler function)
              │
              ├─ [POST] R6: measure_response() → EVM metrics
              ├─ [POST] R2: log_interaction() → akashic memory
              ├─ [POST] R3: enqueue_eval() → evaluation queue
              └─ [POST] R4: check_and_rewrite() → gate/block
                            │ if contradiction:
                            │   → rewrite_fn() once
                            │   → recheck
                            │   → if still bad: SE20ConvergenceError
              │
              └─ _persist_trace() → ~/.hermes/data/se20_traces/
```

### Hook ordering rationale (Claude Opus-4-7's recommendation)

> "The post-call hook is doing a lot (R2, R3, R4, R6). Keep it ordered: R6 measure → R2 log → R3 enqueue → R4 gate. R4 must be last because it can trigger a rewrite that re-enters the pipeline; guard with a recursion counter."

**Why this order**:
- **R6 first**: Captures raw model output metrics before any modification
- **R2 second**: Persists interaction before transformations
- **R3 third**: Non-blocking queue, safe to run before gate
- **R4 last**: Can trigger rewrite → re-enters the stack. Recursion counter (`rewrite_count`) prevents infinite loops

### Decorator pattern (`se20_wrap`)

For simple cases where you don't need the full SE20Agent:

```python
from se20 import se20_wrap

@se20_wrap
def my_handler(text: str) -> str:
    return f"Processed: {text}"

# Now my_handler runs through full pre/post middleware stack
result = my_handler("user input")
```

## How it was designed

1. **Problem**: GPT-5.5 audited the 8 prototypes at 50/100, calling R1-R3 "critical gaps". The core issue: scripts exist but nothing enforces them at runtime.
2. **Consultation**: Sent current state + constraints to GPT-5.5 and Claude Opus-4-7, asking for a "realistic deployment plan" with 3 lines per rule.
3. **Convergence**: Both models independently proposed the same architecture:
   - Central dispatcher wrapping all calls
   - Pre-call (R1) and post-call (R2-R6) hooks
   - Ordered middleware stack
4. **Implementation**: Built `se20/SE20Agent` + 5 middleware modules + `se20_wrap` decorator in ~1000 lines.
5. **Verification**: Full end-to-end test through all 5 middleware hooks, running on actual Hermes Python environment.

## Files

| Path | Role |
|------|------|
| `se20/__init__.py` | SE20Agent, SE20Context, se20_wrap, SE20BlockedError, SE20ConvergenceError |
| `se20/middleware/precheck.py` | R1: precheck_gates() |
| `se20/middleware/akashic.py` | R2: log_interaction() |
| `se20/middleware/post_eval.py` | R3: enqueue_eval() |
| `se20/middleware/convergence_check.py` | R4: check_and_rewrite() |
| `se20/middleware/evm_runtime.py` | R6: measure_response() |
| `se20/workers/ars_daemon.py` | R8: continuous evolution loop |
| `se20/ops/launchd/com.appleoppa.se20.ars.plist` | macOS launchd config |

## Verification (run after any changes)

```python
from se20 import SE20Agent
agent = SE20Agent()
result = agent.execute("test", lambda t: f"response to {t}")
# Check: no error, trace file created at ~/.hermes/data/se20_traces/
# Check: EVM metrics in trace dict
# Check: convergence gate verdict
```
