#!/usr/bin/env python3
"""PGG Archon 本地确定性 mini-benchmark CLI。

用法:
    python agent/pgg_local_mini_benchmark_cli.py [--json] [--verbose]

选项:
    --json      输出原始 JSON
    --verbose   详细输出每个测试细节
"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PGG Archon 本地确定性 mini-benchmark CLI",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出原始 JSON",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="详细输出每个测试细节",
    )
    args = parser.parse_args()

    # 延迟导入，避免循环 import
    from agent.pgg_local_mini_benchmark import run_mini_benchmark

    result = run_mini_benchmark()

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # 人类可读输出
    print("=" * 60)
    print("  PGG Archon 本地确定性 mini-benchmark")
    print("=" * 60)
    print()
    print(f"  Schema:  {result['schema']}")
    print(f"  Status:  {result['status']}")
    print(f"  Score:   {result['pass_count']}/{result['total_count']}")
    print(f"  Border:  {result['boundary']}")
    print()
    print("-" * 60)

    for r in result["results"]:
        status_icon = "✅" if r["status"] == "PASS" else "⚠️ " if r["status"] == "WATCH" else "❌"
        print(f"\n  {status_icon}  {r['name']}")
        print(f"     {r['pass_count']}/{r['total']} passed")
        if args.verbose and "details" in r:
            for k, v in r["details"].items():
                print(f"     {k}: {v}")

    print()
    print("-" * 60)
    print(f"\n  Overall: {result['pass_count']}/{result['total_count']} — {result['status']}")
    print()

    # 非零退出码表示失败
    if result["status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
