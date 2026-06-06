# AutoLoop Daemon — Continuous Self-Evolution

Designed 2026-06-01. Registered as macOS launchd daemon running every 30 minutes.

## Pattern

Inspired by external AGI reference: AutoLoop registered as daemon → auto-evolution every N minutes → measured across 5 dimensions.

The core loop:

```
[AutoLoop Daemon] ──→ [Measure 5 dimensions] ──→ [ARS Phase3+4 cycle]
                         ↓                          ↓
                    [Scorecard history]      [Post-eval queue]
                         ↓                          ↓
                    [Report/Feedback] ←── [Daemon ⇄ Evolution glue]
```

## Three services running

| Service | PID | Type | Interval |
|---------|-----|------|----------|
| ARS daemon | 5285 | `launchd` | Phase3+4 on demand |
| AutoLoop daemon | 5462 | `launchd` | Every 30 min |
| DB maintenance | cron | `cronjob` | Daily 03:00 |

## Five-dimension measurement (`se20/measure.py`)

Real measurements based on code existence, runtime import, and actual usage data — not claimed scores.

| Dimension | What it measures | Scoring |
|-----------|-----------------|---------|
| **Autonomy** | Can the system start evolution without human trigger? | ARS cron last_ok + SE20Agent existence |
| **Evolution** | Is there scheduled trigger + auto iteration? | Phase3/Phase4 reports + launchd script + feedback script |
| **Growth** | Is data accumulating 24/7? | DB message count + akashic fragment count + trace count |
| **Decision** | Does it decide "time to evolve" without human? | Auto-cron jobs count + middleware existence + launchd |
| **Harmony** | Do components work together? | Component existence (8/8) + import test |

## Daemon ⇄ Evolution feedback loop (`se20/feedback.py`)

The feedback loop is the "glue" between daemon and evolution layers:

```
ARS Phase3 report ──→ Extract ars_score (84.867) ──→ Write to se20_feedback.json
                      ↓
              SE20Agent reads config on next cycle ──→ Adjusts behavior
```

## Files

| Path | Role |
|------|------|
| `se20/workers/autoloop_daemon.py` | AutoLoop continuous daemon — measure → evolve → feedback → sleep → repeat |
| `se20/measure.py` | Five-dimension measurement tool with honest verification |
| `se20/feedback.py` | Daemon⇄Evolution feedback — extracts ARS scores → writes config |
| `se20/ops/launchd/com.appleoppa.se20.autoloop.plist` | macOS launchd config — auto-start at boot, crash restart |

## Scorecard persistence

Every AutoLoop cycle appends a JSONL entry to `~/.hermes/data/se20_autoloop/scorecard_history.jsonl`:

```json
{"ts": "2026-06-01T10:27:24.813589+00:00", "scores": {"Autonomy": 0.9, "Evolution": 0.95, "Growth": 0.87, "Decision": 0.95, "Harmony": 1.0}, "overall": 0.93}
```

Heartbeat file: `~/.hermes/data/se20_autoloop/autoloop_heartbeat.json`

## Real-world constraints

- Current baseline (2026-06-01): Overall 0.93. Growth limited (0.87) because auto-logging hasn't accumulated in production.
- Scores are file/usage-based, not runtime-behavior-based. SE20Agent exists but is not yet the Hermes default handler.
- To improve: wire `se20_wrap` as the Hermes tool dispatch wrapper → every agent call auto-measured → Growth rises over time.
