from __future__ import annotations

import json
from pathlib import Path

from agent import pgg_archon_apex_delta_e_health as health


def test_apex_delta_e_unified_health_passes_when_all_cards_pass(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    manifest = home / ".hermes/data/EVOLUTION_MANIFEST.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "latest_super_evolution13_apex_delta_e_gate_landing": {
                    "status": "completed_verified",
                    "timestamp": "2026-06-07T00:00:00Z",
                    "verification": {"gate_state": "PASS_BOUNDED_APEX_DELTA_E_GATE", "gate_score": 1.0},
                },
                "latest_super_evolution13_apex_delta_e_light_autorun_launchd_landing": {
                    "status": "completed_verified",
                    "timestamp": "2026-06-07T00:01:00Z",
                    "verification": {"light_launchd_label": "ai.hermes.pgg-apex-delta-e-light"},
                },
                "latest_super_evolution13_apex_delta_e_runtime_dashboard_integration": {
                    "status": "completed_verified",
                    "timestamp": "2026-06-07T00:02:00Z",
                    "verification": {
                        "card_status": "PASS",
                        "gate_state": "PASS_BOUNDED_APEX_DELTA_E_GATE",
                        "dashboard_smoke_sha256": "abc",
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    ledger = home / ".hermes/data/pgg_apex_delta_e_autorun_ledger.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "status": "PASS",
                "gate_state": "PASS_BOUNDED_APEX_DELTA_E_GATE",
                "gate_score": 1.0,
                "audit_hash": "sha256:test",
                "summary_sha256": "abc",
                "timestamp": "2026-06-07T00:03:00Z",
                "error": "",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    bin_dir = home / ".hermes/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "pgg_apex_delta_e_gate").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (bin_dir / "pgg-apex-delta-e-autorun").write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    monkeypatch.setattr(
        health,
        "_gate_smoke",
        lambda: {
            "status": "PASS",
            "state": "PASS_BOUNDED_APEX_DELTA_E_GATE",
            "score": 1.0,
            "audit_hash": "sha256:test",
        },
    )

    report = health.build_health_report(home=home, task="超级进化13 APEX ΔE")
    assert report["schema"] == "PGGApexDeltaEUnifiedHealth/v1"
    assert report["status"] == "PASS"
    assert report["checks"] == {
        "rust_gate_smoke": True,
        "light_ledger_pass": True,
        "runtime_dashboard_card_pass": True,
        "formula_panel_summary_pass": True,
    }
    assert report["formula_panel"]["apex_delta_e_gate"]["status"] == "PASS"
    assert "no full AGI" in report["boundary"]


def test_render_health_report_is_human_readable(monkeypatch) -> None:
    report = {
        "status": "PASS",
        "checks": {
            "rust_gate_smoke": True,
            "light_ledger_pass": True,
            "runtime_dashboard_card_pass": True,
            "formula_panel_summary_pass": True,
        },
        "boundary": "Read-only unified health report; no full AGI proof.",
    }
    text = health.render_health_report(report)
    assert "Super Evolution 13" in text
    assert "Runtime dashboard：PASS" in text
    assert "/goal 公式面板：PASS" in text
