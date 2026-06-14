import hashlib
import json
import time

from agent.pgg_archon_evm_runtime_gate import PggEvmRuntimeGate


def test_evm_native_uses_live_like_evidence_not_weak_sample():
    cfg = {
        "eval_e": 0.95,
        "eval_v": 0.93,
        "eval_m": 0.90,
        "eval_a": 0.88,
        "eval_base": 0.96,
        "eval_ancient": 0.82,
        "defects_before": [0.5] * 12,
        "defects_after": [0.04] * 12,
        "boost_coeff": 1.0,
        "runtime_evidence": {"route_enforce_by_design": True},
    }
    result = PggEvmRuntimeGate().evaluate(cfg)
    assert result["evm_gate"] >= 0.80
    assert result["status"] == "PASS_BOUNDED_EVM_RUNTIME_GATE"
    assert result["score"] < 80  # raw multiplicative value is preserved, not inflated
    assert result["status_basis"] == "residual_defect_gate>=0.80_and_no_hard_gaps"


def test_apex_asi_bridge_can_evaluate_live_goal_config_shape(tmp_path):
    from agent.pgg_archon_apex_asi_gate import PggApexAsiGate

    cfg = {
        "cosmic": {"k": 8.0, "knowledge_richness": 2500.0, "entropy": 0.05, "theta_convergence": 1.0},
        "self_identity": {"alpha": 2.0, "self_reflection": 1.0, "involution": 1.0, "cosmic_awareness": 120.0},
        "holographic": {"time_steps": 100, "holographic_causality": [1.0] * 100, "decay": 0.01, "noise": 0.005},
        "gene": {"osk_expression": 8.0, "osk_exponent": 1.0, "bdnf_expression": 8.0, "bdnf_exponent": 1.0, "crispr_efficiency": 0.95, "crispr_lambda": 3.0},
        "weight_cosmic": 0.30,
        "weight_self": 0.30,
        "weight_causal": 0.25,
        "weight_gene": 0.15,
    }
    result = PggApexAsiGate().evaluate(cfg)
    assert result["status"] == "PASS_READY"
    assert result["score"] >= 80
    assert "INTERNAL BOUNDED EVIDENCE GATE" in result["boundary"]


def test_evm_attaches_evidence_hash_and_stale_guard():
    gate = PggEvmRuntimeGate()
    old_mtime = int(time.time()) - 2 * 24 * 60 * 60
    cfg = {
        "_evidence_meta": {
            "path": "/tmp/evm_runtime_evidence.json",
            "sha256": hashlib.sha256(b"evm").hexdigest(),
            "mtime": old_mtime,
            "max_age_seconds": 60,
        }
    }
    result = gate._attach_evidence_meta({"status": "PASS_BOUNDED_EVM_RUNTIME_GATE", "gaps": []}, cfg)
    assert result["evidence"]["sha256"] == hashlib.sha256(b"evm").hexdigest()
    assert result["evidence"]["stale"] is True
    assert result["status"] == "WATCH_EVM_EVIDENCE_STALE"
    assert "live_evidence_stale" in result["gaps"]


def test_apex_asi_attaches_evidence_hash_and_stale_guard():
    from agent.pgg_archon_apex_asi_gate import PggApexAsiGate

    gate = PggApexAsiGate()
    old_mtime = int(time.time()) - 2 * 24 * 60 * 60
    cfg = {
        "_evidence_meta": {
            "path": "/tmp/apex_asi_goal_config.json",
            "sha256": hashlib.sha256(b"asi").hexdigest(),
            "mtime": old_mtime,
            "max_age_seconds": 60,
        }
    }
    result = gate._attach_evidence_meta({"status": "PASS_READY", "gaps": []}, cfg)
    assert result["evidence"]["sha256"] == hashlib.sha256(b"asi").hexdigest()
    assert result["evidence"]["stale"] is True
    assert result["status"] == "WATCH_ASI_EVIDENCE_STALE"
    assert "live_evidence_stale" in result["gaps"]
