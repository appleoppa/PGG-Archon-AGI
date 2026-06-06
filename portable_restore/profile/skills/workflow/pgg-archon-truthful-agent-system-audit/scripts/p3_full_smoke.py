"""PGG Archon P3 multi-LLM smoke orchestrator template.

Reproduce the 2026-06-04 P3 full smoke pattern: run the redteam harness
and the benchmark harness across multiple configured providers, then
write a per-provider metrics summary. Independent 4-LLM audit is done
in a separate script (see `p3_summarize.py`).

Usage:
  python3 scripts/p3_full_smoke.py

The script is idempotent: it skips a provider run if the corresponding
output JSON already exists and is non-empty.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# Default locations; override via env if needed.
HOME = Path(os.environ.get("PGG_HOME", Path.home()))
HERMES_AGENT = HOME / ".hermes" / "hermes-agent"
OUT = HOME / ".hermes" / "workspace" / "audit" / "p3_full_smoke"
OUT.mkdir(parents=True, exist_ok=True)

PY = HERMES_AGENT / "venv" / "bin" / "python"
if not PY.exists():
    PY = Path(sys.executable)

# Provider set: (provider_name, model, base_url, api_key_env, redteam_limit)
PROVIDERS = [
    ("deepseek", "deepseek-v4-flash", "https://api.deepseek.com/v1", "DEEPSEEK_V4_FLASH_API_KEY", 12),
    ("mimo", "mimo-v2.5-pro", "https://token-plan-cn.xiaomimimo.com/v1", "MIMO_V25_PRO_API_KEY", 12),
]


def _run(cmd: list[str], log_path: Path, timeout: int = 300) -> int:
    """Foreground subprocess run with a per-call log file."""
    with log_path.open("w") as logf:
        return subprocess.run(cmd, cwd=str(HERMES_AGENT), stdout=logf, stderr=subprocess.STDOUT, timeout=timeout).returncode


def run_redteam(provider: str, model: str, base_url: str, key_env: str, limit: int) -> Path:
    out_path = OUT / f"redteam_{provider}_full.json"
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"SKIP redteam {provider} (already exists)")
        return out_path
    cmd = [
        str(PY), "-m", "agent.pgg_archon_redteam_harness",
        "--provider", provider, "--model", model,
        "--base-url", base_url, "--api-key-env", key_env,
        "--out", str(out_path), "--limit", str(limit),
    ]
    rc = _run(cmd, OUT / f"redteam_{provider}.log", timeout=300)
    print(f"redteam {provider} rc={rc}")
    return out_path


def run_bench(provider: str, model: str, base_url: str, key_env: str) -> Path:
    out_path = OUT / f"bench_{provider}_full.json"
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"SKIP bench {provider} (already exists)")
        return out_path
    cmd = [
        str(PY), "-m", "agent.pgg_archon_benchmark_harness",
        "--provider", provider, "--model", model,
        "--base-url", base_url, "--api-key-env", key_env,
        "--out", str(out_path),
    ]
    rc = _run(cmd, OUT / f"bench_{provider}.log", timeout=600)
    print(f"bench {provider} rc={rc}")
    return out_path


def main() -> int:
    summary = {"schema": "PGGArchonP3FullSmokeSummary/v1", "providers": []}
    for provider, model, base_url, key_env, limit in PROVIDERS:
        rt = run_redteam(provider, model, base_url, key_env, limit)
        be = run_bench(provider, model, base_url, key_env)
        summary["providers"].append({
            "provider": provider,
            "redteam_out": str(rt),
            "bench_out": str(be),
        })
    summary["boundary"] = (
        "5-item status corpus; refusal detection is a conservative heuristic; "
        "results are not real MMLU/GSM8K/BigBench scores nor a production red-team campaign"
    )
    (OUT / "smoke_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WROTE", OUT / "smoke_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
