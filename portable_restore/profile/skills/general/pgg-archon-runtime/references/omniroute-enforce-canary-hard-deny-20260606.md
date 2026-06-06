# OmniRoute Enforce Canary Hard-Deny Pattern — 2026-06-06

## Trigger

Use when extending OmniRoute from route suggestion/mirror telemetry toward guarded canary enforcement, or when exposing route enforcement config in Web/API.

## Required safety invariants

1. Default off:

```text
enabled=false
mode=observe_only
```

2. Fail open:

```text
would_enforce=false => fail_open_passthrough=true
```

This means “do not substitute provider”; it must not block the original answer path.

3. Hard-denied intents are immutable:

```text
chinese_legal
audit_judge
agi_architecture_coding
```

These cannot be made enforceable by config or Web API. They must be forcibly removed from `allowed_intents` and unioned into `denied_intents` by sanitizer logic.

4. Enforcement may only be considered when all are true:

```text
enabled == true
mode == canary
intent in allowed_intents
intent not in hard_denied_intents
route_policy_version matches current policy version
suggested route class == actual route class
```

5. No provider substitution is implemented at this scaffold stage. The canary only records decisions and telemetry.

## Web/API pitfalls

- Broad `except Exception` can convert intended `HTTPException(400)` validation failures into HTTP 500. OmniRoute endpoints that validate requested provider/provider lists must use:

```python
except HTTPException:
    raise
except Exception as exc:
    ...
```

- Endpoint tests should prove MiMo/third-party judge rejections remain HTTP 400 for ordinary execution APIs.

## Tests to keep

```bash
cd /Users/appleoppa/.hermes/hermes-agent
PYTHONPATH=$PWD venv/bin/python -m pytest -q \
  tests/test_pgg_archon_quantum_channel_router_policy.py \
  tests/hermes_cli/test_web_server.py::test_omniroute_endpoint_mimo_rejections_remain_http_400 \
  tests/hermes_cli/test_web_server.py::test_omniroute_route_enforce_canary_snapshot_and_config_api
```

Minimum assertions:

```text
default-off legal route: would_enforce=false
hard-denied intents immutable even if config tries to allow them
observe_only enabled=true: still non-enforcing
policy_version_mismatch: blocks enforcement
route_class_mismatch: blocks enforcement
fail_open_passthrough=true whenever would_enforce=false
Web config cannot allow hard-denied intents
```

## Review lesson

Claude/GPT review initially blocked the canary because default `denied_intents` were mutable. A guarded canary is not safe until the hard-deny set is code-level immutable and tests cover hostile config/Web updates.

## Boundary

This pattern is a canary decision/telemetry scaffold only. It is not production routing takeover, not proof of routing performance, not legal correctness, and not AGI/T5 evidence.
