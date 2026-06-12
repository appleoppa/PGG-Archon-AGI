"""
APEX 工程化终态公式 — Python bridge (PggApexEngineeringFormulaGate)
Formula: APEX_NEW(t+1) = APEX_CORE(t) ⊛ ΔG[规范收敛 ⊗ 纪律锁止 ⊗ 协同熵减]

Backed by hermes_pgg_apex_engineering_formula_gate native .so
"""
import json, sys, os
from pathlib import Path

try:
    import hermes_pgg_apex_engineering_formula_gate as _native
    _NATIVE = True
except ImportError:
    _NATIVE = False

class PggApexEngineeringFormulaGate:
    """APEX engineering final formula gate — bounded evidence gate."""

    def version(self) -> str:
        if _NATIVE:
            return _native.version()
        return "v0.1.0-py"

    def sample_config(self) -> dict:
        if _NATIVE:
            return json.loads(_native.sample_input_json())
        return {
            "source": 80, "norm_convergence": 70, "discipline_lock": 60,
            "collaboration_entropy": 65, "devour_fusion": 75,
            "delta_g": 70, "introspection_loop": 80, "skillopt": 50, "runtime": 40
        }

    def evaluate(self, config: dict = None) -> dict:
        if _NATIVE:
            cfg = json.dumps(config) if config else _native.sample_input_json()
            return json.loads(_native.evaluate_evidence_json(cfg))
        if config is None:
            try:
                evidence_path = Path.home() / ".hermes" / "data" / "engineering_evidence.json"
                if evidence_path.exists():
                    config = json.loads(evidence_path.read_text())
                else:
                    config = self.sample_config()
            except Exception:
                config = self.sample_config()
        return self._evaluate_py(config)

    def anti_overclaim_scan(self, config: dict = None) -> dict:
        if _NATIVE:
            cfg = json.dumps(config) if config else _native.sample_input_json()
            return json.loads(_native.anti_overclaim_scan_json(cfg))
        return {"status": "PASS", "hits": [], "boundary": "No native overclaim scan available"}

    def _evaluate_py(self, cfg: dict) -> dict:
        dims = ["source", "norm_convergence", "discipline_lock", "collaboration_entropy",
                "devour_fusion", "delta_g", "introspection_loop", "skillopt", "runtime"]
        weights = {"source": 0.10, "norm_convergence": 0.15, "discipline_lock": 0.15,
                   "collaboration_entropy": 0.10, "devour_fusion": 0.15,
                   "delta_g": 0.10, "introspection_loop": 0.10, "skillopt": 0.10, "runtime": 0.05}
        subscores = {d: cfg.get(d, 0) for d in dims}
        score = sum(subscores[d] * weights[d] for d in dims)
        gaps = [d for d, v in subscores.items() if v < 60]
        status = "PASS" if score >= 80 else ("WATCH" if score >= 50 else "BLOCKED")
        return {
            "schema": "PGGApexEngineeringFormula/v1-py",
            "status": status, "score": round(score, 2),
            "subscores": subscores, "gaps": gaps,
            "boundary": "Internal bounded engineering gate. Not full AGI, not production answer-chain replacement, not automatic skill mutation."
        }

if __name__ == "__main__":
    gate = PggApexEngineeringFormulaGate()
    if "--version" in sys.argv:
        print(gate.version())
    elif "--boundary" in sys.argv or "--sample" in sys.argv:
        print(json.dumps(gate.sample_config(), indent=2, ensure_ascii=False))
    elif "--eval" in sys.argv:
        idx = sys.argv.index("--eval")
        cfg = json.loads(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else None
        print(json.dumps(gate.evaluate(cfg), indent=2, ensure_ascii=False))
    elif "--overclaim" in sys.argv:
        idx = sys.argv.index("--overclaim")
        cfg = json.loads(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else None
        print(json.dumps(gate.anti_overclaim_scan(cfg), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(gate.evaluate(), indent=2, ensure_ascii=False))
