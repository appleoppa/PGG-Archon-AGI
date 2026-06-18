#!/usr/bin/env python3
"""Phase 2: 总纲8吸收 — 侧录脚本
在每次 OmniRoute 调用旁路记录 query complexity + provider cost profile
写入 ledger 供后续分析和路由优化。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
BIN = HOME / "bin"
COMPLEXITY_GATE = BIN / "pgg_query_complexity_gate"
COST_PROFILE = BIN / "pgg_provider_cost_profile"
LEDGER = HOME / "data/omniroute_sidecar_ledger.jsonl"
LATEST = HOME / "data/omniroute_sidecar_latest.json"


def run_gate(bin_path: Path, input_text: str, timeout: int = 10) -> dict | None:
    try:
        r = subprocess.run(
            [str(bin_path)],
            input=input_text.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
        )
        if r.returncode != 0:
            return None
        return json.loads(r.stdout.decode("utf-8", "replace"))
    except Exception:
        return None


def main() -> int:
    # 从 stdin 或 args 获取 query
    input_text = sys.stdin.read() if not sys.stdin.isatty() else " ".join(sys.argv[1:])
    if not input_text.strip():
        # 无输入：只运行 cost profile（静态信息）
        cost = run_gate(COST_PROFILE, "static")
        if cost:
            record = {
                "schema": "pgg-omniroute-sidecar/v1",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "mode": "cost_only",
                "cost_profile": cost,
                "boundary": "sidecar ledger; shadow mode; does not alter routing.",
            }
        else:
            record = {"schema": "pgg-omniroute-sidecar/v1", "mode": "error", "error": "cost_profile_failed"}
    else:
        # 有 query：跑 complexity + cost
        complexity = run_gate(COMPLEXITY_GATE, input_text)
        cost = run_gate(COST_PROFILE, "static")

        record = {
            "schema": "pgg-omniroute-sidecar/v1",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "mode": "query_with_cost",
            "query_preview": input_text[:200],
            "complexity": complexity,
            "cost_profile": cost,
            "suggestion": _suggest(complexity, cost) if complexity and cost else None,
            "boundary": "sidecar ledger; shadow mode; does not alter routing.",
        }

    # 写入 ledger
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # 写入 latest.json
    with LATEST.open("w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    # stdout
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


def _suggest(complexity: dict | None, cost: dict | None) -> str | None:
    if not complexity or not cost:
        return None
    result = complexity.get("result", {})
    tier = result.get("tier_adjusted", "L")

    # 找到成本最低的 provider
    profiles = (cost.get("profiles") or []) if isinstance(cost, dict) else []
    if not profiles:
        return None

    cost_order = cost.get("global_cost_order", [])

    if tier == "L":
        # 低复杂度 → 推低成本 provider
        cheap = cost_order[0] if cost_order else "ark"
        return f"推荐低成本: {cheap} (Score_Q={result.get('score_q'):.2f}, Tier={tier})"
    elif tier == "M":
        # 中复杂度 → 推平衡 provider
        mid = cost_order[len(cost_order)//2] if len(cost_order) > 2 else "mimo"
        return f"推荐平衡: {mid} (Score_Q={result.get('score_q'):.2f}, Tier={tier})"
    else:
        # 高复杂度 → 推强模型
        return f"推荐强模型: gpt55/claude (Score_Q={result.get('score_q'):.2f}, Tier={tier})"


if __name__ == "__main__":
    raise SystemExit(main())