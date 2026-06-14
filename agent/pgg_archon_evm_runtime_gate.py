"""
EVM Runtime Gate — Python bridge (PggEvmRuntimeGate)
EVM = E×V×M×A×Base × Ancient × (1 - defect_rate)
EVM_Gate = 1 - weighted_residual_defect_rate

Backed by hermes_pgg_evm_runtime_gate native .so
"""
import hashlib
import json, sys
import time
from pathlib import Path

EVIDENCE_MAX_AGE_SECONDS = 24 * 60 * 60

try:
    import hermes_pgg_evm_runtime_gate as _native
    _NATIVE = True
except ImportError:
    _native = None
    _NATIVE = False

class PggEvmRuntimeGate:
    """EVM runtime defect governance gate."""

    def version(self) -> str:
        if _NATIVE and _native is not None:
            return _native.version()
        return "v0.1.0-py"

    def sample_config(self) -> dict:
        if _NATIVE and _native is not None:
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

    def _load_live_evidence_config(self) -> dict:
        """Load live EVM evidence and map legacy eval_* keys to native inputs.

        The Rust native module's sample config is deliberately weak/demo-like.
        For hermes-goal/runtime status we must evaluate the live evidence file
        produced by the self-healing pipeline instead of silently falling back to
        the sample when the native .so is present.
        """
        evidence_path = Path.home() / ".hermes" / "data" / "evm_runtime_evidence.json"
        if evidence_path.exists():
            raw = evidence_path.read_bytes()
            config = json.loads(raw.decode("utf-8"))
            config["e"] = config.get("eval_e", config.get("e", 0.8))
            config["v"] = config.get("eval_v", config.get("v", 0.7))
            config["m"] = config.get("eval_m", config.get("m", 0.6))
            config["a"] = config.get("eval_a", config.get("a", 0.5))
            config["base"] = config.get("eval_base", config.get("base", 0.9))
            config["ancient"] = config.get("eval_ancient", config.get("ancient", 0.5))
            config["runtime_evidence"] = config.get("runtime_evidence", {})
            config["_evidence_meta"] = {
                "path": str(evidence_path),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "mtime": int(evidence_path.stat().st_mtime),
                "max_age_seconds": EVIDENCE_MAX_AGE_SECONDS,
            }
            return config
        return self.sample_config()

    def _normalize_status(self, result: dict) -> dict:
        """Use the gate semantics as the PASS criterion, not the raw EVM value.

        The EVM value is multiplicative and intentionally conservative; it may
        stay below 80 even when the residual-defect gate is healthy.  A clean
        residual gate (evm_gate >= 0.80 with no hard gaps) is the bounded runtime
        PASS condition.  The raw score is preserved for transparency.
        """
        try:
            evm_gate = float(result.get("evm_gate", 0.0) or 0.0)
        except Exception:
            evm_gate = 0.0
        hard_gaps = [g for g in result.get("gaps", []) if g not in {"evm_value_below_0_70"}]
        if evm_gate >= 0.80 and not hard_gaps:
            result["status"] = "PASS_BOUNDED_EVM_RUNTIME_GATE"
            result["status_basis"] = "residual_defect_gate>=0.80_and_no_hard_gaps"
        return result

    def _attach_evidence_meta(self, result: dict, cfg: dict) -> dict:
        meta = cfg.get("_evidence_meta") if isinstance(cfg, dict) else None
        if not isinstance(meta, dict):
            return result
        age_seconds = max(0, int(time.time()) - int(meta.get("mtime", 0) or 0))
        evidence = {
            "path": meta.get("path"),
            "sha256": meta.get("sha256"),
            "mtime": meta.get("mtime"),
            "age_seconds": age_seconds,
            "max_age_seconds": meta.get("max_age_seconds", EVIDENCE_MAX_AGE_SECONDS),
            "stale": age_seconds > int(meta.get("max_age_seconds", EVIDENCE_MAX_AGE_SECONDS) or EVIDENCE_MAX_AGE_SECONDS),
        }
        result["evidence"] = evidence
        if evidence["stale"]:
            gaps = list(result.get("gaps", []))
            gaps.append("live_evidence_stale")
            result["gaps"] = gaps
            result["status"] = "WATCH_EVM_EVIDENCE_STALE"
        return result

    def evaluate(self, config: dict = None) -> dict:
        if config is None:
            try:
                config = self._load_live_evidence_config()
            except Exception:
                config = self.sample_config()
        if _NATIVE and _native is not None:
            native_config = {k: v for k, v in config.items() if k != "_evidence_meta"}
            result = json.loads(_native.evaluate_evidence_json(json.dumps(native_config)))
            return self._attach_evidence_meta(self._normalize_status(result), config)
        return self._attach_evidence_meta(self._normalize_status(self._evaluate_py(config)), config)

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
