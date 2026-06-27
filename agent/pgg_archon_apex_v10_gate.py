#!/usr/bin/env python3
"""
PGG Archon APEX_V10 (Φ_APEX) 证据门 — Rust-only Python 桥接模块

该模块是 Hermes PGG APEX_V10 Rust/PyO3 证据门的 Python 封装。
所有核心计算由 Rust 实现 (hermes_pgg_apex_v10_gate)，通过 PyO3 导出。
无 Python fallback。Rust .so 未加载时直接报错，不自欺。

边界声明：
  这是一个有界的内部就绪度评估门。评分 (0–100) 仅用于内部就绪度评估，
  不等同于 AGI（人工通用智能）能力，不是外部基准测试。

公式：
  Φ_APEX = H_err × P_asm × D_pro

用法:
    from agent.pgg_archon_apex_v10_gate import PggApexV10Gate

    gate = PggApexV10Gate()
    result = gate.evaluate({
        "h_err_rate": 0.85,
        "p_asm_rate": 0.82,
        "d_pro_rate": 0.88,
    })
    print(result["score"])      # 0–100
    print(result["status"])     # PASS_READY | WATCH_EVOLVING | BLOCKED_IMMATURE
    print(result["boundary"])   # 边界声明
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# VENV site-packages 显式路径（确保系统 python3 也能加载 .so）
# .abi3.so 在 VENV (Python 3.11) 下编译。系统 python3 可能是 3.9，所以硬编码 3.11
_VENV_SITE = str(
    Path.home() / ".hermes" / "hermes-agent" / ".venv" / "lib"
    / "python3.11" / "site-packages"
)
if _VENV_SITE not in sys.path and os.path.isdir(_VENV_SITE):
    sys.path.insert(0, _VENV_SITE)


class PggApexV10Gate:
    """APEX_V10 (Φ_APEX) 证据门评估器 — Rust-only"""

    VERSION = "v1.0-rust-only"

    def __init__(self):
        self._module = None
        self._loaded = False

    def _ensure_loaded(self):
        """延迟加载 Rust 扩展模块。无 Python fallback。"""
        if self._loaded:
            return

        lib_name = "hermes_pgg_apex_v10_gate"

        # 尝试正常 import（VENV 下的 direct import 路径）
        for path_candidate in [None, _VENV_SITE]:
            if path_candidate is not None and path_candidate not in sys.path:
                sys.path.insert(0, path_candidate)
            try:
                self._module = __import__(lib_name)
                self._loaded = True
                return
            except ImportError:
                continue

        # 尝试从 release 目录加载
        rust_module_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "rust_modules",
        )
        release_dir = os.path.join(rust_module_dir, "target", "release")
        candidates = [
            os.path.join(release_dir, f"{lib_name}.so"),
            os.path.join(release_dir, f"lib{lib_name}.so"),
            os.path.join(release_dir, f"{lib_name}.dylib"),
            os.path.join(release_dir, f"lib{lib_name}.dylib"),
            os.path.join(release_dir, f"{lib_name}.abi3.so"),
        ]

        for candidate in candidates:
            if os.path.exists(candidate):
                lib_dir = os.path.dirname(candidate)
                if lib_dir not in sys.path:
                    sys.path.insert(0, lib_dir)
                try:
                    self._module = __import__(lib_name)
                    self._loaded = True
                    return
                except ImportError:
                    continue

        # Rust .so 不存在 — 直接报错，不自欺
        raise RuntimeError(
            f"Rust .so 未加载: {lib_name} 在 sys.path={sys.path[:5]} 中找不到。"
            "请运行 'cd rust_modules && cargo build --release' 编译 Rust 核心。"
        )

    def evaluate(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """评估 Φ_APEX。只走 Rust。"""
        self._ensure_loaded()

        if config is None:
            config_str = self._module.sample_config_json()
        else:
            config_str = json.dumps(config, ensure_ascii=False)
        result_str = self._module.evaluate_config_json(config_str)
        return json.loads(result_str)

    def sample_config(self) -> Dict[str, Any]:
        """返回示例配置"""
        self._ensure_loaded()
        return json.loads(self._module.sample_config_json())

    def get_version(self) -> str:
        """返回模块版本"""
        self._ensure_loaded()
        return self._module.version()

    def get_boundary(self) -> str:
        """返回边界声明"""
        self._ensure_loaded()
        return self._module.boundary_statement()


# ∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷
# 便捷函数（模块级调用）
# ∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷

_gate_instance: Optional[PggApexV10Gate] = None


def _get_gate() -> PggApexV10Gate:
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = PggApexV10Gate()
    return _gate_instance


def evaluate(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """评估 Φ_APEX 证据门"""
    return _get_gate().evaluate(config)


def sample_config() -> Dict[str, Any]:
    """返回示例配置"""
    return _get_gate().sample_config()


def version() -> str:
    """返回版本信息"""
    return _get_gate().get_version()


def boundary() -> str:
    """返回边界声明"""
    return _get_gate().get_boundary()


# ∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷
# CLI 入口
# ∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷

def main_cli():
    """CLI 入口点"""
    import argparse

    parser = argparse.ArgumentParser(
        description="APEX_V10 (Φ_APEX) 有界内部证据门 - CLI (Rust-only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "边界声明:\n"
            "  该工具实现 Φ_APEX 公式，用于内部就绪度评估。\n"
            "  评分 (0–100) 不等同于 AGI 能力，不是外部基准测试。"
        ),
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="JSON 配置文件路径（可选，默认使用示例配置）",
    )
    parser.add_argument(
        "--sample", "-s",
        action="store_true",
        help="输出示例配置",
    )
    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="输出版本信息",
    )
    parser.add_argument(
        "--boundary", "-b",
        action="store_true",
        help="输出边界声明",
    )
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        help="美化输出 JSON",
    )

    args = parser.parse_args()

    try:
        gate = PggApexV10Gate()

        if args.version:
            print(gate.get_version())
            return

        if args.boundary:
            print(gate.get_boundary())
            return

        if args.sample:
            config = gate.sample_config()
            indent = 2 if args.pretty else None
            print(json.dumps(config, ensure_ascii=False, indent=indent))
            return

        if args.config:
            with open(args.config, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = None

        result = gate.evaluate(config)
        indent = 2 if args.pretty else None
        print(json.dumps(result, ensure_ascii=False, indent=indent))

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main_cli()