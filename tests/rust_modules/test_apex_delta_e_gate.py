import json


def test_apex_delta_e_gate_sample_passes():
    import hermes_pgg_apex_delta_e_gate as gate

    assert "Super Evolution 13" in gate.version()
    sample = gate.sample_input_json()
    out = json.loads(gate.evaluate_json(sample))
    assert out["schema"] == "HermesPGGApexDeltaEGate/v1"
    assert out["formula"] == "APEX_{ΔE}=αΨ+βΩ+λΦ+∇Θ+Evol_{code}"
    assert out["state"] == "PASS_BOUNDED_APEX_DELTA_E_GATE"
    assert out["score"] >= 0.99
    assert out["safety_flags"] == []
    assert "no self-awareness" in out["boundary"]


def test_apex_delta_e_gate_blocks_unsafe_external_code():
    import hermes_pgg_apex_delta_e_gate as gate

    sample = json.loads(gate.sample_input_json())
    sample["lambda"]["external_code_imported"] = True
    out = json.loads(gate.evaluate_json(json.dumps(sample)))
    assert out["state"] == "BLOCKED_BY_SAFETY_BOUNDARY"
    assert any("external_code_imported" in x for x in out["safety_flags"])


def test_apex_delta_e_gate_missing_compile_is_not_pass():
    import hermes_pgg_apex_delta_e_gate as gate

    sample = json.loads(gate.sample_input_json())
    sample["beta"]["compile_gate_passed"] = False
    out = json.loads(gate.evaluate_json(json.dumps(sample)))
    assert out["state"] != "PASS_BOUNDED_APEX_DELTA_E_GATE"
    assert any(c["name"].startswith("beta") and c["gaps"] for c in out["components"])
