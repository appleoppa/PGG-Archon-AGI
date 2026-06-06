from __future__ import annotations

import json

import pytest


def test_ralph_pyo3_import_and_json_surface() -> None:
    mod = pytest.importorskip(
        "hermes_pgg_ralph",
        reason="installed PyO3 artifact required; run rust_modules/build_and_install.sh first",
    )
    assert "hermes_pgg_ralph" in mod.version()
    state = mod.sample_state_json()
    out = json.loads(mod.evaluate_state_json(state, None))
    assert out["schema"] == "HermesPGGRalphCore/v1"
    assert out["audit_hash"].startswith("sha256:")
    assert "no full AGI claim" in out["boundary"]


def test_pilotdeck_pyo3_import_and_sample_watch_surface() -> None:
    mod = pytest.importorskip(
        "hermes_pgg_pilotdeck",
        reason="installed PyO3 artifact required; run rust_modules/build_and_install.sh first",
    )
    assert "hermes_pgg_pilotdeck" in mod.version()
    out = json.loads(mod.evaluate_default_json())
    assert out["schema"] == "HermesPGGPilotDeckAbsorption/v1"
    assert out["pass"] == 0
    assert out["watch"] == 14
    assert out["blocked"] == 1
    assert "sample declared-source" in out["evidence_semantics"]
    assert "prove runtime integration" in out["boundary"]
