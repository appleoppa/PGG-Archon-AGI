# Custom Provider: OpenAI SDK Header Blocking

Some API gateways (e.g. 5yuantoken.eu.cc) block requests from the OpenAI Python SDK because of headers the SDK auto-injects. This document explains the root cause and the fix.

## Root Cause

The OpenAI Python SDK's `_build_headers()` method (in `openai._base_client.SyncAPIClient`) injects two classes of headers that certain gateways/WAFs block:

1. **x-stainless-*** headers — The SDK adds up to 9 headers: `x-stainless-lang`, `x-stainless-package-version`, `x-stainless-os`, `x-stainless-arch`, `x-stainless-runtime`, `x-stainless-runtime-version`, `x-stainless-async`, `x-stainless-retry-count`, `x-stainless-read-timeout`. These are set in `_build_headers()` after `default_headers` are processed, so they **cannot be removed via `default_headers` alone**.

2. **User-Agent: OpenAI/Python** — Many non-OpenAI gateways (including 5yuantoken) block or rate-limit this User-Agent string.

## Key Debugging Insight

The `x-stainless-retry-count` and `x-stainless-read-timeout` headers are set at lines ~452-459 of `_build_headers()`:

```python
lower_custom_headers = [header.lower() for header in custom_headers]
if "x-stainless-retry-count" not in lower_custom_headers:
    headers["x-stainless-retry-count"] = str(retries_taken)
if "x-stainless-read-timeout" not in lower_custom_headers:
    ...
    headers["x-stainless-read-timeout"] = str(timeout)
```

The guard checks `custom_headers` (from `options.headers`, the per-request headers), NOT `self.default_headers`. So setting them to empty string in `default_headers` has no effect — they get overwritten by these two lines.

## Fix: Monkey-patch `_build_headers`

The cleanest fix is to patch `SyncAPIClient._build_headers` before the OpenAI client is created, stripping x-stainless headers and rewriting User-Agent only for the target API:

```python
from openai._base_client import SyncAPIClient

_orig_bh = SyncAPIClient._build_headers
if not getattr(_orig_bh, "_patched_for_5yuantoken", False):
    def _patched_headers(self, options, *, retries_taken=0):
        result = _orig_bh(self, options, retries_taken=retries_taken)
        keys_to_del = [k for k in result if k.lower().startswith("x-stainless-")]
        for k in keys_to_del:
            del result[k]
        result["user-agent"] = "python-requests/2.32.3"
        result["accept"] = "*/*"
        return result
    _patched_headers._patched_for_5yuantoken = True
    SyncAPIClient._build_headers = _patched_headers
```

The `_patched_for_5yuantoken` sentinel ensures the patch is applied only once (since `_create_openai_client` may be called multiple times per session for credential rotation, client rebuilds, etc.).

## Where to Apply the Patch

In Hermes Agent, the patch goes in `_create_openai_client()` in `run_agent.py`, inside the code block that detects the target API base_url:

```python
_base_url = str(client_kwargs.get("base_url", ""))
if "5yuantoken.eu.cc" in _base_url:
    # apply monkey-patch here (with sentinel guard)
```

This keeps the patch scoped: it only activates when Hermes connects to a provider whose base_url matches the target pattern.

## Why Other Approaches Fail

| Approach | Result | Why |
|----------|--------|-----|
| `default_headers={"X-Stainless-...": ""}` | Fails | `_build_headers` overwrites retry-count and read-timeout after default_headers |
| httpx event_hooks on custom http_client | Fails (for this case) | Event hooks fire and strip headers, but the gateway also blocks on User-Agent |
| Direct `requests.post` with clean headers | Works | No SDK header injection at all |
| `max_retries=0` | Works for retry-count but not read-timeout | Doesn't fix User-Agent or other x-stainless headers |

## Testing the Fix

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-...",
    base_url="https://5yuantoken.eu.cc/v1",
    max_retries=0,
)
resp = client.chat.completions.create(
    model="gpt-5.5",
    messages=[{"role": "user", "content": "say ok"}],
    max_tokens=10
)
print(resp.choices[0].message.content)
```

If patched correctly, this returns `ok` instead of 403.
