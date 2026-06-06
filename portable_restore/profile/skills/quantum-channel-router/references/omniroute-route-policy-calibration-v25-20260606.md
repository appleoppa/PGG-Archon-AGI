# OmniRoute route policy calibration v2.5 — 2026-06-06

## Problem fixed

`decide_omniroute_provider()` previously mirrored `dashboard_selected_provider=mimo`, so route-suggest recommended MiMo for nearly every core conversation.

## New policy

Auto mode now classifies task/prompt intent and uses provider preferences:

- Chinese legal: `deepseek -> gpt55 -> claude -> mimo`
- AGI / architecture / coding / evolution: `gpt55 -> claude -> deepseek -> mimo`
- audit / judge / benchmark: `mimo -> claude -> gpt55 -> deepseek`
- bounded exact/math: `gpt55 -> deepseek -> mimo -> claude`
- general: `gpt55 -> deepseek -> claude -> mimo`

Manual/request override still wins. Dashboard selected provider is fallback only.

## Verification

Offline smoke:

```text
legal -> deepseek
agi -> gpt55
audit -> mimo
exact -> gpt55
general -> gpt55
```

Real smoke:

```text
Prompt: Reply exactly: PGG_V25_POLICY_OK
suggested_provider = gpt55
actual_provider = custom:gpt55_5yuantoken
suggested_route_class = gpt
actual_route_class = gpt
class_match = true
latency_ms = 0.805
```

Rolling metrics still HOLD because old pre-calibration events dominate the window:

```text
suggested_route_class_counts = {mimo:149, gpt:1}
actual_route_class_counts = {gpt:104, deepseek:37, mimo:5, claude:4}
class_match_rate = 0.0133
```

## Decision

v2.5 fixed the root cause for new route suggestions, but route-enforce remains HOLD until a fresh calibrated rolling window shows stable class_match_rate.
