"""
EVM Runtime Gate — Python bridge (PggEvmRuntimeGate)
EVM = E×V×M×A×Base × Ancient × (1 - defect_rate)
EVM_Gate = 1 - weighted_residual_defect_rate

Backed by hermes_pgg_evm_runtime_gate native .so
"""
import json, sys
from pathlib import Path

try:
    import hermes_pgg_evm_runtime_gate as _native
    _NATIVE = True
except ImportError:
    _NATIVE = False

class PggEvmRuntimeGate:
    """EVM runtime defect governance gate."""

    def version(self) -> str:
        if _NATIVE:
            return _native.version()
        return "v0.1.0-py"

    def sample_config(self) -> dict:
        if _NATIVE:
            return json.loads(_native.sample_evidence_json())
        return {
            "e": 0.8, "v": 0.7, "m": 0.6, "a": 0.5, "base": 0.9,
            "ancient": 0.5,
            "defects_before": [0.3, 0.2, 0.4, 0.1, 0.3, 0.2, 0.1, 0.4, 0.2, 0.3, 0.1, 0.2],
            "defects_after": [0.2, 0.1, 0.3, 0.05, 0.2, 0.1, 0.05, 0.3, 0.1, 0.2, 0.05, 0.1],
            "boost_coeff": 1.5,
            "epsilon": 0.001,
            "runtime_evidence": {"skillflow_route_enforce": False, "skillflow_live_window": 7}
        }

    def evaluate(self, config: dict = None) -> dict:
        if _NATIVE:
            cfg = json.dumps(config) if config else _native.sample_evidence_json()
            return json.loads(_native.evaluate_evidence_json(cfg))
        if config is None:
            try:
                evidence_path = Path.home() / ".hermes" / "data" / "evm_runtime_evidence.json"
                if evidence_path.exists():
                    config = json.loads(evidence_path.read_text())
                    # map evidence fields to EVM params
                    config["e"] = config.get("eval_e", 0.8)
                    config["v"] = config.get("eval_v", 0.7)
                    config["m"] = config.get("eval_m", 0.6)
                    config["a"] = config.get("eval_a", 0.5)
                    config["base"] = config.get("eval_base", 0.9)
                    config["ancient"] = config.get("eval_ancient", 0.5)
                    config["runtime_evidence"] = config.get("runtime_evidence", {})
                else:
                    config = self.sample_config()
            except Exception:
                config = self.sample_config()
        return self._evaluate_py(config)

    def _evaluate_py(self, cfg: dict) -> dict:
        e, v, m, a, base, ancient = cfg["e"], cfg["v"], cfg["m"], cfg["a"], cfg["base"], cfg["ancient"]
        modern = e * v * m * a * base
        defect_before = sum(cfg.get("defects_before", [0.3]*12)) / 12
        defect_after = sum(cfg.get("defects_after", [0.2]*12)) / 12
        bc = cfg.get("boost_coeff", 1.5)
        defect_rate = defect_after * 0.5 + bc * (defect_after ** 1.5)
        residual = defect_after / max(defect_before, 1e-6)
        evm_gate = 1.0 - residual
        score = modern * ancient * (1 - defect_rate) * 100
        gaps = ["evm_gate_below_0_80"] if evm_gate < 0.80 else []
        if not cfg.get("runtime_evidence", {}).get("skillflow_route_enforce"):
            # route_enforce not active can be by-design (SkillFlow HOLD)
            if not cfg.get("runtime_evidence", {}).get("route_enforce_by_design", False):
                gaps.append("route_enforce_not_active")
        else:
            pass  # route_enforce active
        status = "PASS" if score >= 80 and not gaps else ("WATCH" if score >= 50 else "BLOCKED")
        return {
            "schema": "HermesPggEvmRuntimeGate/v1-py",
            "status": status, "evm_gate": round(evm_gate, 4),
            "evm_value": round(modern, 4), "score": round(score, 2),
            "gaps": gaps,
            "boundary": "Internal bounded EVM runtime gate. Not full AGI, not external benchmark."
        }

if __name__ == "__main__":
    gate = PggEvmRuntimeGate()
    if "--version" in sys.argv:
        print(gate.version())
    elif "--boundary" in sys.argv or "--sample" in sys.argv:
        print(json.dumps(gate.sample_config(), indent=2, ensure_ascii=False))
    elif "--eval" in sys.argv:
        idx = sys.argv.index("--eval")
        cfg = json.loads(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else None
        print(json.dumps(gate.evaluate(cfg), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(gate.evaluate(), indent=2, ensure_ascii=False))
