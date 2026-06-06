# APEX-GOD API Discovery Pattern

## Problem

When auditing or testing APEX-GOD components, `import` succeeds for 28/29 modules — but you don't know the **actual** class names, method signatures, or call patterns until you probe. Guessing (e.g. `AGIKernel` → actually `LLMKernel`, `verify_chain()` → actually `verify()`) leads to wasted iterations and flakey test runs.

## The pattern: module → dir → inspect → call

### Step 1: Import and list public attrs

```python
import apex_god.kernel
print([x for x in dir(apex_god.kernel) if not x.startswith("_")])
# → ['Any', 'Callable', 'LLMKernel', 'Optional', ...]
```

This tells you the actual exported names. **Never assume class/function names** from domain knowledge alone.

### Step 2: Check method signatures

```python
import inspect
from apex_god.audit_trail import get_audit_trail
at = get_audit_trail()
sig = inspect.signature(at.append)
print(sig)  # → (**kwargs) -> 'str'
```

This avoids 3-4 wasted iterations trying positional args. Key findings from actual probing:

| Component | My assumption | Actual API |
|-----------|---------------|------------|
| `audit_trail.append()` | `(event_type, detail)` positional | `(**kwargs)` with `event_type="...", detail="..."` |
| `audit_trail.verify()` | `verify_chain()` | `verify()` returns dict `{'valid': bool, 'total_entries': int, 'breaks': []}` |
| `fail_closed` | `fc.closed` | `fc._closed` |
| `AuditEventType` | `.PROBE` | `.HEALTH_PROBE` |
| `kernel` | `AGIKernel` | `LLMKernel` |
| `force_inherit` | `ForceInherit` class | `FormulaCalculator` + `get_calculator()` function |
| `auto_bootstrap` | `auto_bootstrap_components()` | `bootstrap()` function (module-level) |
| `health` | `is_healthy()` | Not exported |

### Step 3: Write test scripts to files, not inline

**Don't do this** (quoting errors, backslash-in-fstring errors):
```bash
python3 -c '
import sys; sys.path.insert(0,".")
from apex_god.fail_closed import FailClosed
fc = FailClosed()
print(f"closed={fc.closed}")
'
```

**Do this** (write + execute — single-quote safe, patchable, syntax-checked):
```bash
python3 /tmp/test_probe.py
```

The `write_file` tool lints Python automatically, catching syntax issues before execution.

**Why**: f-strings work fine inside files. No shell escaping needed. Patching is one `patch()` call. The build-execute-fix cycle is 5-10x faster than inline.

### Step 4: Test call patterns with minimal examples

After discovering signatures, validate with minimal calls:

```python
# After discovering append(**kwargs):
e = at.append(event_type="health_probe", detail="functional_test")
print(type(e))  # → str (hash)
v = at.verify()
print(v.get("valid"), v.get("total_entries"))  # → True, 29
```

### Step 5: Aggregate scores from complementary sources

APEX-GOD has three independent scoring systems — use all three for an honest picture:

| Source | What it measures | How to access |
|--------|-----------------|---------------|
| `health_check()` | Binary pass/fail per component | `health_check()['healthy_count']` out of `total_checks` |
| `measure_all()` | 5-dimensional capability score (0-1) | `measure_all()['overall']` + per-dimension scores |
| `EVOLUTION_MANIFEST.json` | Structural completeness (0-100) | `summary.overall_5d_score` field |
| Background evolution watcher | Infrastructure readiness (0-100) | `summary.latest_background_evolution_score.score` |

**Never use only one score.** A module can be `health=24/24 ✅` but `measure=0.51` — the first checks existence, the second checks actual capability.

## Example: Complete probe pattern

```python
# 1. Module import test (broad)
import importlib
modules = ["apex_god.kernel", "apex_god.fail_closed", ...]
for m in modules:
    try:
        importlib.import_module(m)
        passed += 1
    except Exception as e:
        failed += 1

# 2. API discovery (narrow)
import apex_god.kernel
print(dir(apex_god.kernel))  # find actual class names

# 3. Functional test
from apex_god.health import health_check
hc = health_check()
print(hc['healthy_count'], hc['overall_healthy'])

# 4. Score from manifest
import json
with open("/Users/appleoppa/.hermes/data/EVOLUTION_MANIFEST.json") as f:
    m = json.load(f)
print(m['summary']['overall_5d_score'])
```

## When to use this pattern

- First time testing a component you haven't called before
- After a system repair/restore (APIs may have changed)
- When the manifest claims `importable=true` but you need to know what to import
- Anytime a class/function name feels like a guess — probe it
