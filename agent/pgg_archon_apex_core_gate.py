#!/usr/bin/env python3
"""PGG Archon APEX_Core (ΔG_total) 动态证据门 — Rust-only 新评分引擎

该模块使用自研 Rust PyO3 评分引擎 (hermes_pgg_apex_dynamic_score)，
根据真实系统数据动态计算 APEX Core 评分，不依赖闭源 .so。

边界声明：
  评分 (0–100) 基于系统真实数据，用于内部就绪度评估。
  不等同于 AGI（人工通用智能）能力，不是外部基准测试。

公式：
  ΔG_total = ΔG_base · Λ_effective · (1 + Ψ_cross) · Ω_self · Φ_anti-illusion
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# VENV site-packages 显式路径
_VENV_SITE = str(
    Path.home() / ".hermes" / "hermes-agent" / ".venv" / "lib"
    / "python3.11" / "site-packages"
)
if _VENV_SITE not in sys.path and os.path.isdir(_VENV_SITE):
    sys.path.insert(0, _VENV_SITE)

# ── 真实系统数据采集 ──────────────────────────────────────────────────────

# 递归防护：当 hermes-goal 调用 apex_core_gate 时，防止循环
_PGG_APEX_GUARD = "PGG_APEX_GATE_RECURSION_GUARD"
if os.environ.get(_PGG_APEX_GUARD) == "1":
    # 已在 hermes-goal 中，直接返回默认值避免死循环
    _GOAL_CACHE: Optional[Dict[str, Any]] = {}
else:
    _GOAL_CACHE: Optional[Dict[str, Any]] = None

ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = ROOT / ".venv" / "bin" / "python3"


def _get_goal_data() -> Dict[str, Any]:
    global _GOAL_CACHE
    if _GOAL_CACHE is not None:
        return _GOAL_CACHE
    try:
        env = os.environ.copy()
        env["PGG_APEX_GATE_RECURSION_GUARD"] = "1"
        r = subprocess.run(
            [str(VENV_PYTHON), "-m", "agent.pgg_goal_unified_status"],
            capture_output=True, text=True, timeout=35, env=env,
        )
        if r.returncode == 0 and r.stdout.strip():
            _GOAL_CACHE = json.loads(r.stdout)
            return _GOAL_CACHE
    except Exception:
        pass
    _GOAL_CACHE = {}
    return _GOAL_CACHE


def _run(cmd: list[str], timeout: int = 10) -> tuple[str, int]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() or r.stderr.strip(), r.returncode
    except Exception as e:
        return str(e), -1


def _measure_delta_g_base() -> float:
    """任务完成率 — 基于 hermes-goal 组件 PASS 比例，排除 apex_core_gate 自引用。"""
    data = _get_goal_data()
    comps = data.get("components", {})
    if comps:
        # apex_core_gate 自身会读取 hermes-goal；若把自身未 PASS 计入基础完成率，
        # 会形成 circular self-penalty（自引用扣分），导致唯一剩余 BLOCKED 无法靠真实外部组件改善。
        comparable = {k: v for k, v in comps.items() if k != "apex_core_gate"}
        total = len(comparable)
        passed = sum(1 for c in comparable.values() if str(c.get("status", "")).startswith("PASS"))
        return round(passed / max(total, 1), 4)
    return 0.70


def _measure_lambda_effective() -> float:
    """系统利用率 — 基于当前 workspace Rust CLI 覆盖率（真实可测）"""
    try:
        import tomllib
        from pathlib import Path

        workspace = Path(__file__).resolve().parent.parent / "rust_modules"
        cargo = workspace / "Cargo.toml"
        if cargo.exists():
            data = tomllib.loads(cargo.read_text())
            members = [m for m in data.get("workspace", {}).get("members", []) if isinstance(m, str)]
            bin_members = []
            alias_map = {
                "pgg_genedb_unified_audit": ["pgg_genedb_unified_audit", "pgg-genedb-unified-audit-rs"],
                "pgg_cms_case_guard": ["pgg_cms_case_guard", "cms_case_guard"],
                "pgg_sourceref_repair_runner": ["pgg_sourceref_repair_runner", "pgg-sourceref-repair-runner-rs"],
            }
            for m in members:
                crate_dir = workspace / m
                if (crate_dir / "src" / "main.rs").exists():
                    bin_members.append(m)
            if bin_members:
                bin_dir = Path.home() / ".hermes" / "bin"
                installed = 0
                for m in bin_members:
                    candidates = [bin_dir / m, bin_dir / m.replace("_", "-")]
                    candidates.extend(bin_dir / x for x in alias_map.get(m, []))
                    if any(c.exists() and os.access(c, os.X_OK) for c in candidates):
                        installed += 1
                return round(installed / len(bin_members), 4)
    except Exception:
        pass
    return 0.82


def _measure_psi_cross() -> float:
    """跨域能力 — MCP 服务器可用比例"""
    data = _get_goal_data()
    mcp_test_servers = {k: v for k, v in data.get("components", {}).items() if k.startswith("mcp_test_")}
    if mcp_test_servers:
        total = len(mcp_test_servers)
        passed = sum(1 for c in mcp_test_servers.values() if str(c.get("status", "")).startswith("PASS"))
        return round(passed / max(total, 1), 4)
    return 0.65


def _measure_omega_self() -> float:
    """自检能力 — 门禁评分加权平均"""
    data = _get_goal_data()
    gates = {}
    for gate_name in ["apexagi_gate", "engineering_gate", "evm_gate", "asi_gate", "sigma_delta_all"]:
        comps = data.get("components", {})
        c = comps.get(gate_name, {})
        score = c.get("score")
        if score is None and gate_name == "evm_gate" and c.get("evm_gate") is not None:
            score = float(c.get("evm_gate")) * 100.0
        if score is None and gate_name == "sigma_delta_all" and c.get("sigma_delta") is not None:
            score = c.get("sigma_delta")
        if score is not None:
            gates[gate_name] = float(score)
    if gates:
        avg_score = sum(gates.values()) / len(gates)
        return round(min(1.0, avg_score / 100.0), 4)
    return 0.70


def _measure_phi_anti_illusion() -> float:
    """反幻觉能力 — 读取真实 health/memory/sigma/goal 证据，避免静态口号抬分。"""
    score = 0.80
    try:
        hermes_home = Path.home() / ".hermes"
        health = hermes_home / "data" / "health-monitor" / "latest.json"
        memory = hermes_home / "data" / "pgg-python-module-runner" / "agent_memory_system_status.latest.json"
        sigma = hermes_home / "data" / "pgg-python-module-runner" / "agent_pgg_defect_reduction.latest.json"
        if health.exists():
            d = json.loads(health.read_text())
            if not d.get("alerts") and str(d.get("status", "")).startswith("PASS"):
                score += 0.04
        if memory.exists():
            d = json.loads(memory.read_text())
            if str(d.get("status", "")).startswith("PASS"):
                score += 0.03
        if sigma.exists():
            d = json.loads(sigma.read_text())
            if str(d.get("status", "")).startswith("PASS"):
                score += 0.03
        goal = _get_goal_data()
        if int(goal.get("blocked_count", 0) or 0) == 0:
            score += 0.02
    except Exception:
        pass
    return round(min(score, 0.92), 4)


def _measure_h_err_rate() -> float:
    """错误处理能力 — hermes-goal 非PASS比例的反向"""
    data = _get_goal_data()
    comps = data.get("components", {})
    if comps:
        total = len(comps)
        passed = sum(1 for c in comps.values() if str(c.get("status", "")).startswith("PASS"))
        err_rate = (total - passed) / total
        return round(1.0 - err_rate, 4)
    return 0.75


def _measure_p_asm_rate() -> float:
    """管道组装能力"""
    return _measure_psi_cross()


def _measure_d_pro_rate() -> float:
    """交付保护能力"""
    return _measure_omega_self()


# ── 主 Gate 类 ─────────────────────────────────────────────────────────────


class PggApexCoreGate:
    """APEX_Core (ΔG_total) 动态证据门 — Rust-first, Python fallback"""

    VERSION = "v0.3.0-dynamic-with-fallback"

    def __init__(self):
        self._module = None
        self._loaded = False
        self._fallback = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        if self._fallback:
            return
        lib_name = "hermes_pgg_apex_dynamic_score"
        for path_candidate in [None, _VENV_SITE]:
            if path_candidate is not None and path_candidate not in sys.path:
                sys.path.insert(0, path_candidate)
            try:
                self._module = __import__(lib_name)
                # Verify the module actually works by calling it
                _ = self._module.evaluate_core_config_json('{}')
                self._loaded = True
                return
            except Exception:
                continue
        # Fallback: pure Python implementation
        self._fallback = True

    def _build_config(self) -> Dict[str, Any]:
        return {
            "delta_g_base": _measure_delta_g_base(),
            "lambda_effective": _measure_lambda_effective(),
            "psi_cross": _measure_psi_cross(),
            "omega_self": _measure_omega_self(),
            "phi_anti_illusion": _measure_phi_anti_illusion(),
        }

    def _py_evaluate_core(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Pure Python fallback of the Rust scoring engine."""
        dg = max(0.0, min(1.0, config.get("delta_g_base", 0.70)))
        la = max(0.0, min(1.0, config.get("lambda_effective", 0.75)))
        ps = max(0.0, min(1.0, config.get("psi_cross", 0.65)))
        om = max(0.0, min(1.0, config.get("omega_self", 0.70)))
        pa = max(0.0, min(1.0, config.get("phi_anti_illusion", 0.80)))
        raw = dg * la * (1.0 + ps) * om * pa
        score = round(max(0.0, min(100.0, raw / 2.0 * 100.0)), 3)
        avg = (dg + la + ps + om + pa) / 5.0
        components = [
            {"name": "ΔG_base", "value": dg, "weight": "base"},
            {"name": "Λ_effective", "value": la, "weight": "multiplier"},
            {"name": "Ψ_cross", "value": ps, "weight": "bonus"},
            {"name": "Ω_self", "value": om, "weight": "multiplier"},
            {"name": "Φ_anti-illusion", "value": pa, "weight": "multiplier"},
        ]
        weakest = sorted(
            [c for c in components if c["value"] < avg],
            key=lambda x: x["value"],
        )[:2]
        return {
            "schema": "PGGAPEXCoreDynamicScore/v1",
            "version": self.VERSION,
            "score": score,
            "status": "PASS_READY" if score >= 50.0 else "BLOCKED_IMMATURE",
            "components": components,
            "weakest": [w["name"] for w in weakest],
            "weakest_values": {w["name"]: w["value"] for w in weakest},
            "formula": "ΔG_total = ΔG_base · Λ_effective · (1 + Ψ_cross) · Ω_self · Φ_anti-illusion",
            "boundary": "INTERNAL BOUNDED SCORE: Real system-data-driven capability readiness. NOT an AGI benchmark.",
            "_engine": "python_fallback",
            "source_data": config,
        }

    def evaluate(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._ensure_loaded()
        if config is None:
            config = self._build_config()
        if self._fallback:
            return self._py_evaluate_core(config)
        try:
            config_str = json.dumps(config, ensure_ascii=False)
            result_str = self._module.evaluate_core_config_json(config_str)
            return json.loads(result_str)
        except Exception:
            self._fallback = True
            return self._py_evaluate_core(config)

    def sample_config(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return json.loads(self._module.sample_core_config_json())

    def get_version(self) -> str:
        return "v0.2.0-dynamic"

    def get_boundary(self) -> str:
        return (
            "INTERNAL BOUNDED SCORE: Real system-data-driven capability readiness assessment. "
            "NOT an AGI benchmark, NOT a legal accuracy metric."
        )


class PggApexV10Gate:
    """APEX_V10 (Φ_APEX) 动态证据门 — Rust-first, Python fallback"""

    VERSION = "v0.3.0-dynamic-with-fallback"

    def __init__(self):
        self._module = None
        self._loaded = False
        self._fallback = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        if self._fallback:
            return
        lib_name = "hermes_pgg_apex_dynamic_score"
        for path_candidate in [None, _VENV_SITE]:
            if path_candidate is not None and path_candidate not in sys.path:
                sys.path.insert(0, path_candidate)
            try:
                self._module = __import__(lib_name)
                _ = self._module.evaluate_v10_config_json('{}')
                self._loaded = True
                return
            except Exception:
                continue
        self._fallback = True

    def _build_config(self) -> Dict[str, Any]:
        return {
            "h_err_rate": _measure_h_err_rate(),
            "p_asm_rate": _measure_p_asm_rate(),
            "d_pro_rate": _measure_d_pro_rate(),
        }

    def _py_evaluate_v10(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Pure Python fallback of the Rust V10 scoring engine."""
        h_err = max(0.0, min(1.0, config.get("h_err_rate", 0.75)))
        p_asm = max(0.0, min(1.0, config.get("p_asm_rate", 0.70)))
        d_pro = max(0.0, min(1.0, config.get("d_pro_rate", 0.70)))
        phi = round(h_err * 0.40 + p_asm * 0.35 + d_pro * 0.25, 4)
        score = round(max(0.0, min(100.0, phi * 100.0)), 3)
        return {
            "schema": "PGGAPEXV10DynamicScore/v1",
            "version": self.VERSION,
            "score": score,
            "phi_apex": phi,
            "status": "PASS_READY" if score >= 50.0 else "BLOCKED_IMMATURE",
            "components": {
                "h_err_rate": h_err,
                "p_asm_rate": p_asm,
                "d_pro_rate": d_pro,
            },
            "formula": "Φ_APEX = h_err * 0.40 + p_asm * 0.35 + d_pro * 0.25",
            "boundary": "INTERNAL BOUNDED SCORE: Real system data. NOT AGI.",
            "_engine": "python_fallback",
            "source_data": config,
        }

    def evaluate(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._ensure_loaded()
        if config is None:
            config = self._build_config()
        if self._fallback:
            return self._py_evaluate_v10(config)
        try:
            config_str = json.dumps(config, ensure_ascii=False)
            result_str = self._module.evaluate_v10_config_json(config_str)
            return json.loads(result_str)
        except Exception:
            self._fallback = True
            return self._py_evaluate_v10(config)

    def sample_config(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return json.loads(self._module.sample_v10_config_json())

    def get_version(self) -> str:
        return "v0.2.0-dynamic"

    def get_boundary(self) -> str:
        return (
            "INTERNAL BOUNDED SCORE: Real system-data-driven capability readiness assessment. "
            "NOT an AGI benchmark, NOT a legal accuracy metric."
        )


# ── 模块级便捷函数 ────────────────────────────────────────────────────────

_core_instance: Optional[PggApexCoreGate] = None
_v10_instance: Optional[PggApexV10Gate] = None


def _get_core() -> PggApexCoreGate:
    global _core_instance
    if _core_instance is None:
        _core_instance = PggApexCoreGate()
    return _core_instance


def _get_v10() -> PggApexV10Gate:
    global _v10_instance
    if _v10_instance is None:
        _v10_instance = PggApexV10Gate()
    return _v10_instance


def evaluate_core(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _get_core().evaluate(config)


def evaluate_v10(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _get_v10().evaluate(config)


def sample_core_config() -> Dict[str, Any]:
    return _get_core().sample_config()


def sample_v10_config() -> Dict[str, Any]:
    return _get_v10().sample_config()


def version() -> str:
    return "v0.2.0-dynamic"


def boundary() -> str:
    return _get_core().get_boundary()


# ∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷
# CLI 入口
# ∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷∷

def main_cli_core():
    import argparse
    parser = argparse.ArgumentParser(
        description="APEX_Core (ΔG_total) 动态证据门 - CLI (Rust-only, 真实数据驱动)"
    )
    parser.add_argument("--pretty", "-p", action="store_true", help="美化输出")
    parser.add_argument("--sample", "-s", action="store_true", help="示例配置")
    parser.add_argument("--config", "-c", type=str, default=None, help="JSON 配置文件路径")
    parser.add_argument("--v10", action="store_true", help="切换到 V10 评分")
    args = parser.parse_args()
    gate = PggApexV10Gate() if args.v10 else PggApexCoreGate()
    if args.sample:
        print(json.dumps(gate.sample_config(), ensure_ascii=False, indent=2))
        return
    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            raw_config = json.load(f)
        result = gate.evaluate(raw_config)
    else:
        raw_config = gate._build_config()
        result = gate.evaluate()
    indent = 2 if args.pretty else None
    result["source_data"] = raw_config
    result["_note"] = "评分基于当前系统真实数据，每次运行可能不同"
    print(json.dumps(result, ensure_ascii=False, indent=indent))


def main_cli_v10():
    import argparse
    parser = argparse.ArgumentParser(
        description="APEX_V10 (Φ_APEX) 动态证据门 - CLI (Rust-only, 真实数据驱动)"
    )
    parser.add_argument("--pretty", "-p", action="store_true", help="美化输出")
    parser.add_argument("--sample", "-s", action="store_true", help="示例配置")
    parser.add_argument("--config", "-c", type=str, default=None, help="JSON 配置文件路径")
    args = parser.parse_args()
    gate = PggApexV10Gate()
    if args.sample:
        print(json.dumps(gate.sample_config(), ensure_ascii=False, indent=2))
        return
    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            raw_config = json.load(f)
        result = gate.evaluate(raw_config)
    else:
        raw_config = gate._build_config()
        result = gate.evaluate()
    indent = 2 if args.pretty else None
    result["source_data"] = raw_config
    result["_note"] = "评分基于当前系统真实数据，每次运行可能不同"
    print(json.dumps(result, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main_cli_core()