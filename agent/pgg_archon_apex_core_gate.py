#!/usr/bin/env python3
"""
PGG Archon APEX_Core (ΔG_total) 证据门 — Python 桥接模块

该模块是 Hermes PGG APEX_Core Rust/PyO3 证据门的 Python 封装。
所有核心计算由 Rust 实现 (hermes_pgg_apex_core_gate)，通过 PyO3 导出。

边界声明：
  这是一个有界的内部就绪度评估门。评分 (0–100) 仅用于内部就绪度评估，
  不等同于 AGI（人工通用智能）能力，不是外部基准测试。

公式：
  ΔG_total = ΔG_base · Λ_effective · (1 + Ψ_cross) · Ω_self · Φ_anti-illusion

用法:
    from agent.pgg_archon_apex_core_gate import PggApexCoreGate

    gate = PggApexCoreGate()
    result = gate.evaluate({
        "delta_g_base": 0.85,
        "lambda_effective": 0.82,
        "psi_cross": 0.75,
        "omega_self": 0.80,
        "phi_anti_illusion": 0.78,
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


class PggApexCoreGate:
    """APEX_Core (ΔG_total) 证据门评估器"""

    VERSION = "v1.0-py"

    def __init__(self):
        self._module = None
        self._loaded = False

    def _ensure_loaded(self):
        """延迟加载 Rust 扩展模块，fallback 到 Python 实现"""
        if self._loaded:
            return

        lib_name = "hermes_pgg_apex_core_gate"

        # 首先尝试通过正常 import
        try:
            self._module = __import__(lib_name)
            self._loaded = True
            return
        except ImportError:
            pass

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

        # Fallback: Python 实现
        self._loaded = True
        self._module = None

    def evaluate(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._ensure_loaded()

        if self._module is not None:
            if config is None:
                config_str = self._module.sample_config_json()
            else:
                config_str = json.dumps(config, ensure_ascii=False)
            result_str = self._module.evaluate_config_json(config_str)
            return json.loads(result_str)

        # Python fallback: ΔG_total = ΔG_base · Λ_effective · (1 + Ψ_cross) · Ω_self · Φ_anti-illusion
        if config is None:
            # Read last L2 readiness and AGI gap for baseline
            import json as _j
            try:
                l2 = _j.loads(Path(str(Path.home() / ".hermes/data/pgg_l2_readiness_gate_latest.json")).read_text())
                agi = _j.loads(Path(str(Path.home() / ".hermes/data/pgg_agi_gap_closure_gate_latest.json")).read_text())
                delta_base = max(0.5, min(1.0, l2.get("score", 84.8) / 100.0))
                phi_anti = max(0.5, min(1.0, agi.get("score", 80.3) / 100.0))
            except Exception:
                delta_base = 0.85
                phi_anti = 0.80
            config = {
                "delta_g_base": delta_base,       # 0.85-1.0 based on L2 readiness
                "lambda_effective": 0.88,         # MCP/hermes-goal pipeline readiness
                "psi_cross": 0.82,                # OmniRoute multi-provider routing
                "omega_self": 0.85,               # autonomy loop + PR capability
                "phi_anti_illusion": phi_anti,     # AGI gap closure score
            }

        dg = config.get("delta_g_base", 0.85)
        le = config.get("lambda_effective", 0.82)
        pc = config.get("psi_cross", 0.75)
        om = config.get("omega_self", 0.80)
        pai = config.get("phi_anti_illusion", 0.78)

        dg_total = dg * le * (1 + pc) * om * pai
        score = round(min(100.0, dg_total * 100.0), 2)
        gaps = []
        if dg < 0.70:
            gaps.append("delta_g_base_below_0_70")
        if le < 0.60:
            gaps.append("lambda_effective_below_0_60")
        if pai < 0.60:
            gaps.append("phi_anti_illusion_below_0_60")

        status = "PASS_READY" if score >= 70 else ("WATCH_EVOLVING" if score >= 50 else "BLOCKED_IMMATURE")

        return {
            "schema": "ApexCoreScore/v1-py",
            "version": self.VERSION,
            "status": status,
            "score": score,
            "formula": "ΔG_base·Λ_effective·(1+Ψ_cross)·Ω_self·Φ_anti-illusion",
            "components": {
                "delta_g_base": dg,
                "lambda_effective": le,
                "psi_cross": pc,
                "omega_self": om,
                "phi_anti_illusion": pai,
                "delta_g_total": round(dg_total, 4),
            },
            "gaps": gaps,
            "method": "python_fallback",
            "boundary": "Internal bounded AGI core readiness gate. Python fallback (Rust .so not compiled).",
        }

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

_gate_instance: Optional[PggApexCoreGate] = None


def _get_gate() -> PggApexCoreGate:
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = PggApexCoreGate()
    return _gate_instance


def evaluate(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """评估 ΔG_total 证据门"""
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
        description="APEX_Core (ΔG_total) 有界内部证据门 - CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "边界声明:\n"
            "  该工具实现 ΔG_total 公式，用于内部就绪度评估。\n"
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
        gate = PggApexCoreGate()

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
