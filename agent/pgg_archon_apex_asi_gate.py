#!/usr/bin/env python3
"""
PGG Archon APEX-ASI (Ψ_ASI) 证据门 — Rust PyO3 纯桥

所有核心计算由 Rust 实现 (hermes_pgg_apex_asi_gate)，通过 PyO3 导出。
Rust .so 不可用时只返回 BLOCKED，不提供 Python 实现。
"""

import json
import sys
from typing import Any, Dict, Optional

try:
    import hermes_pgg_apex_asi_gate as _native  # type: ignore[import-untyped]
    _MODULE = _native
except ImportError:
    _MODULE = None


class PggApexAsiGate:
    """Ψ_ASI 证据门评估器 — 纯 Rust 桥，无 Python 实现。"""

    def evaluate(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if _MODULE is None:
            return {"status": "BLOCKED", "score": 0.0, "detail": "Rust native .so not available"}
        if config is None:
            config = json.loads(_MODULE.sample_config_json())
        return json.loads(_MODULE.evaluate_config_json(json.dumps(config, ensure_ascii=False)))

    def sample_config(self) -> Dict[str, Any]:
        if _MODULE is None:
            return {"status": "BLOCKED", "score": 0.0, "detail": "Rust native .so not available"}
        return json.loads(_MODULE.sample_config_json())

    def get_version(self) -> str:
        return _MODULE.version() if _MODULE else "v0.0.0-no-rust"

    def get_boundary(self) -> str:
        return _MODULE.boundary_statement() if _MODULE else "Rust native .so not available"


def evaluate(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return PggApexAsiGate().evaluate(config)


def sample_config() -> Dict[str, Any]:
    return PggApexAsiGate().sample_config()


def version() -> str:
    return PggApexAsiGate().get_version()


def boundary() -> str:
    return PggApexAsiGate().get_boundary()


def main_cli():
    """CLI 入口点 — 只依赖 Rust native 计算"""
    import argparse
    parser = argparse.ArgumentParser(description="Ψ_ASI APEX-ASI 有界内部证据门")
    parser.add_argument("--config", "-c", type=str, default=None, help="JSON 配置文件路径")
    parser.add_argument("--sample", "-s", action="store_true", help="输出示例配置")
    parser.add_argument("--version", "-v", action="store_true", help="输出版本信息")
    parser.add_argument("--boundary", "-b", action="store_true", help="输出边界声明")
    parser.add_argument("--pretty", "-p", action="store_true", help="美化输出 JSON")
    args = parser.parse_args()
    gate = PggApexAsiGate()
    if args.version:     print(gate.get_version()); return
    if args.boundary:    print(gate.get_boundary()); return
    if args.sample:      indent = 2 if args.pretty else None; print(json.dumps(gate.sample_config(), ensure_ascii=False, indent=indent)); return
    config = None
    if args.config:
        with open(args.config, "r") as f:
            config = json.load(f)
    result = gate.evaluate(config)
    indent = 2 if args.pretty else None
    print(json.dumps(result, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main_cli()
