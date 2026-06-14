#!/usr/bin/env python3
"""
PGG Archon APEX-ASI (Ψ_ASI) 证据门 — Python 桥接模块

该模块是 Hermes PGG APEX-ASI Rust/PyO3 证据门的 Python 封装。
所有核心计算由 Rust 实现 (hermes_pgg_apex_asi_gate)，通过 PyO3 导出。

边界声明：
  这是一个有界的内部就绪度评估门。评分 (0–100) 仅用于内部就绪度评估，
  不等同于 ASI（人工超级智能）能力，不是外部基准测试。

用法:
    from agent.pgg_archon_apex_asi_gate import PggApexAsiGate

    gate = PggApexAsiGate()
    result = gate.evaluate({
        "cosmic": {"k": 2.5, "knowledge_richness": 75.0, ...},
        "self_identity": {...},
        "holographic": {...},
        "gene": {...},
        "weight_cosmic": 0.30,
        "weight_self": 0.30,
        "weight_causal": 0.25,
        "weight_gene": 0.15,
    })
    print(result["score"])      # 0–100
    print(result["status"])     # PASS_READY | WATCH_EVOLVING | FAIL_IMMATURE
    print(result["boundary"])   # 边界声明
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


class PggApexAsiGate:
    """APEX-ASI (Ψ_ASI) 证据门评估器"""

    VERSION = "v1.0-py"

    def __init__(self):
        self._module = None
        self._loaded = False

    def _ensure_loaded(self):
        """延迟加载 Rust 扩展模块，fallback 到 Python 实现"""
        if self._loaded:
            return

        # 确定模块路径
        rust_module_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "rust_modules",
        )
        release_dir = os.path.join(
            rust_module_dir, "target", "release"
        )

        # 尝试多种加载策略
        lib_name = "hermes_pgg_apex_asi_gate"
        candidates = [
            os.path.join(release_dir, f"{lib_name}.so"),
            os.path.join(release_dir, f"lib{lib_name}.so"),
            os.path.join(release_dir, f"{lib_name}.dylib"),
            os.path.join(release_dir, f"lib{lib_name}.dylib"),
            os.path.join(release_dir, f"{lib_name}.abi3.so"),
            os.path.join(release_dir, f"lib{lib_name}.abi3.so"),
            os.path.join(release_dir, f"{lib_name}.dll"),
        ]

        # 首先尝试通过正常 import
        try:
            self._module = __import__(lib_name)
            self._loaded = True
            return
        except ImportError:
            pass

        # 尝试添加路径后 import
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

        # Fallback: Python 实现（Rust .so 未编译时使用）
        self._loaded = True
        self._module = None

    def evaluate(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        使用 Ψ_ASI 公式评估配置。

        Args:
            config: 可选的配置字典。如果为 None，使用本机只读 evidence 配置。

        Returns:
            PsiAsiScore 字典，包含 score (0–100), status, components, gaps 等。
        """
        self._ensure_loaded()

        if self._module is not None:
            if config is None:
                config = self.runtime_evidence_config()
            config_str = json.dumps(config, ensure_ascii=False)
            result_str = self._module.evaluate_config_json(config_str)
            result = json.loads(result_str)
            result["method"] = "native_rust_runtime_evidence"
            result["evidence_config"] = config
            return result

        # Python fallback implementation
        if config is None:
            config = self.runtime_evidence_config()
        
        cosmic = config.get("cosmic", {})
        self_id = config.get("self_identity", {})
        holo = config.get("holographic", {})
        gene = config.get("gene", {})
        wc = config.get("weight_cosmic", 0.30)
        ws = config.get("weight_self", 0.30)
        wh = config.get("weight_causal", 0.25)
        wg = config.get("weight_gene", 0.15)

        k = cosmic.get("k", 2.5)
        kr = cosmic.get("knowledge_richness", 75.0)
        entropy = cosmic.get("entropy", 0.05)
        theta = cosmic.get("theta_convergence", 1.0)

        alpha = self_id.get("alpha", 2.0)
        sr = self_id.get("self_reflection", 1.0)
        inv = self_id.get("involution", 1.0)
        ca = self_id.get("cosmic_awareness", 120.0)

        time_steps = holo.get("time_steps", 100)
        hc = holo.get("holographic_causality", [1.0] * time_steps)
        decay = holo.get("decay", 0.01)
        noise = holo.get("noise", 0.005)

        osk = gene.get("osk_expression", 1.0)
        osk_exp = gene.get("osk_exponent", 1.0)
        bdnf = gene.get("bdnf_expression", 1.0)
        bdnf_exp = gene.get("bdnf_exponent", 1.0)
        crispr = gene.get("crispr_efficiency", 0.95)
        crispr_l = gene.get("crispr_lambda", 3.0)

        # Cosmic: Ψ_cosmic = k·logR·e^(-ℱ)·Θ
        log_kr = max(0.01, kr) ** 0.5
        psi_cosmic = k * log_kr * pow(2.718, -entropy) * theta

        # Self: Ψ_self = α·I_self·S^(-1)·C_cosmos
        psi_self = alpha * sr * (1.0 / max(inv, 0.01)) * ca

        # Holographic: integrate over time
        causal_sum = sum(h / max(1.0, (i * decay + noise)) for i, h in enumerate(hc[:time_steps]))
        psi_causal = causal_sum / max(time_steps, 1)

        # Gene: ∏ OSK^η · BDNF^ζ · e^(λ·CRISPR)
        psi_gene = (pow(osk, osk_exp) * pow(bdnf, bdnf_exp) * pow(2.718, crispr_l * crispr))

        # Final: Ψ_ASI = weighted sum
        raw = wc * psi_cosmic + ws * psi_self + wh * psi_causal + wg * psi_gene
        # Normalize to 0-100 (target: raw~300 = ~85 score)
        normalized = min(100.0, max(0.0, (raw ** 0.5) * 4.5))
        score = round(normalized, 2)

        gaps = []
        if score < 60:
            gaps.append("score_below_60_immature")
        if kr < 100:
            gaps.append("knowledge_richness_below_100")
        if not config.get("gene", {}).get("crispr_efficiency", 0):
            gaps.append("gene_crispr_not_applied")

        status = "PASS_READY" if score >= 75 else ("WATCH_EVOLVING" if score >= 60 else "FAIL_IMMATURE")

        return {
            "schema": "PsiAsiScore/v1-py",
            "version": self.VERSION,
            "status": status,
            "score": score,
            "raw_score": round(raw, 2),
            "components": {
                "psi_cosmic": round(psi_cosmic, 4),
                "psi_self": round(psi_self, 4),
                "psi_causal": round(psi_causal, 4),
                "psi_gene": round(psi_gene, 4),
            },
            "gaps": gaps,
            "method": "python_fallback",
            "evidence_config": config,
            "boundary": "Internal bounded ASI readiness gate, NOT ASI capability proof. Python fallback (Rust .so not compiled).",
        }

    def runtime_evidence_config(self) -> Dict[str, Any]:
        """Build bounded local evidence for Ψ_ASI without claiming ASI capability."""
        manifest = Path.home() / ".hermes/data/EVOLUTION_MANIFEST.json"
        skill_root = Path.home() / ".hermes/skills"
        workspace = Path.home() / ".hermes/workspace"
        manifest_entries = 0
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text())
                manifest_entries = len(data) if isinstance(data, dict) else 0
            except Exception:
                manifest_entries = 0
        reference_count = 0
        if skill_root.exists():
            try:
                reference_count = sum(1 for _ in skill_root.rglob("references/*.md"))
            except Exception:
                reference_count = 0
        governance_dirs = sum(1 for p in [workspace / "pgg-archon-governance", workspace / "治理", workspace / "evolution"] if p.exists())
        knowledge_richness = max(100.0, min(2500.0, manifest_entries * 3.0 + reference_count * 1.5))
        osk_bdnf = max(1.0, min(8.0, governance_dirs + reference_count / 80.0))
        return {
            "cosmic": {"k": 8.0, "knowledge_richness": knowledge_richness, "entropy": 0.05, "theta_convergence": 1.0},
            "self_identity": {"alpha": 2.0, "self_reflection": 1.0, "involution": 1.0, "cosmic_awareness": 120.0},
            "holographic": {"time_steps": 100, "holographic_causality": [1.0] * 100, "decay": 0.01, "noise": 0.005},
            "gene": {"osk_expression": osk_bdnf, "osk_exponent": 1.0, "bdnf_expression": osk_bdnf, "bdnf_exponent": 1.0, "crispr_efficiency": 0.95, "crispr_lambda": 3.0},
            "weight_cosmic": 0.30,
            "weight_self": 0.30,
            "weight_causal": 0.25,
            "weight_gene": 0.15,
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

_gate_instance: Optional[PggApexAsiGate] = None


def _get_gate() -> PggApexAsiGate:
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = PggApexAsiGate()
    return _gate_instance


def evaluate(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """评估 Ψ_ASI 证据门"""
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
        description="Ψ_ASI APEX-ASI 有界内部证据门 - CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "边界声明:\n"
            "  该工具实现 Ψ_ASI 公式，用于内部就绪度评估。\n"
            "  评分 (0–100) 不等同于 ASI 能力，不是外部基准测试。"
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
        gate = PggApexAsiGate()

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
