# 5D Scoring Surface Drift Repair — Cleanup-Friendly Growth + Runtime-Aware Harmony (2026-06-06)

## Trigger

Use this when PGG/APEX 5D scores look wrong after session cleanup, runtime migration, or historical overlay rename.

## Problem

The historical 5D status surface drifted from live runtime state:

1. `measure_growth()` over-weighted raw `messages` / `sessions` counts and legacy `~/.hermes/data/apex_god_traces`, so legitimate user cleanup of historical sessions looked like capability loss.
2. `measure_harmony()` checked the historical plist path `apex_god/ops/launchd/com.appleoppa.apex-god.ars.plist`, but the active runtime is now Rust-native `ai.hermes.evol-watcher` running `apex13 fused-watch`.
3. Harmony import smoke expected legacy exports `APEX_GODAgent` and `apex_god_wrap`; current implementation exposes `LLMKernel` and `wrap_provider` from `apex_god.kernel`.
4. Internal 5D status scores can be mistaken for external AGI benchmark/capability scores.

## Landed fixes

Files:

- `~/.hermes/hermes-agent/apex_god/__init__.py`
  - Adds legacy compatibility aliases: `APEX_GODAgent = LLMKernel`, `apex_god_wrap = wrap_provider`.
  - Boundary: import-smoke compatibility only, not proof of provider routing or AGI capability.
- `~/.hermes/hermes-agent/apex_god/measure.py`
  - `measure_harmony()` accepts either legacy plist or current `~/Library/LaunchAgents/ai.hermes.evol-watcher.plist` + active Rust watcher.
  - `measure_growth()` is cleanup-friendly: Akashic 5-channel retrieval, graph, avg strength, benchmark artifact, Manifest milestones/growth signals, background-evolution files, and small live DB activity weight. Legacy traces are optional.
- `~/.hermes/hermes-agent/tests/test_apex_god_harmony_compat.py`
  - Regression tests for compatibility exports, current fused watcher Harmony, and cleanup-friendly Growth.

Evidence package:

- `~/.hermes/workspace/pgg-archon-governance/scoring_surface_fusion_20260606.json`

## Verification commands

```bash
cd ~/.hermes/hermes-agent
./venv/bin/python -m pytest tests/test_apex_god_harmony_compat.py -q
./venv/bin/python -m py_compile apex_god/measure.py apex_god/__init__.py tests/test_apex_god_harmony_compat.py
./venv/bin/python - <<'PY'
import json
from apex_god.measure import measure_all
print(json.dumps(measure_all(), ensure_ascii=False, indent=2))
PY
```

Expected verified result on 2026-06-06:

```text
pytest: 3 passed
Growth: 1.00 with cleanup_friendly=yes
Harmony: 1.00 with components=12/12, imports=ok
Overall: 1.00 under internal 5D status surface
```

## Boundary language

Always label this as:

> Internal 5D runtime/governance status surface.

Do **not** call it:

- external AGI benchmark score
- full AGI proof
- zero-risk proof
- legal correctness proof
- unsupervised production takeover proof

## Formula

```text
TrueScore_t = HarnessVerified(
    CleanupFriendlyGrowth
  + RuntimeAwareHarmony
  + LegacyCompatImport
  + BoundaryLabel
) - OverclaimPenalty
```

## Pitfalls

- Do not restore deleted sessions just to raise Growth.
- Do not add fake legacy plist files. Detect the live Rust fused watcher instead.
- Do not change import smoke into a capability claim.
- `apex_god/` is currently ignored by `.git/info/exclude`; treat it as runtime/historical overlay unless explicitly normalized into tracked source.
