from __future__ import annotations

from pathlib import Path

from agent.pgg_archon_quantum_channel_router import run_quantum_channel_router


def test_quantum_router_exposes_rust_omniroute_dashboard_bridge() -> None:
    out = run_quantum_channel_router()
    assert out["schema"] == "PGGArchonQuantumChannelRouter/v1"
    probes = out["probe"]["probes"]
    assert probes["rust_omniroute_crate"] == "present"
    assert probes["rust_omniroute_binary"] == "present"
    assert probes["rust_omniroute_dashboard"] == "present"
    assert probes["rust_omniroute_order_source"] == "python_evm_engine+live_provider_health"
    assert probes["rust_omniroute_evm_report"] == "present"
    assert probes["rust_omniroute_provider_health"] == "present"
    assert probes["rust_omniroute_provider_cache_status"] in {"hit", "refresh_miss_or_expired", "refresh_forced"}
    assert float(probes["rust_omniroute_provider_cache_age_sec"]) >= 0.0
    assert float(probes["rust_omniroute_provider_cache_ttl_sec"]) > 0.0
    assert int(probes["rust_omniroute_provider_healthy_count"]) >= 1
    assert int(probes["rust_omniroute_provider_unhealthy_count"]) >= 0
    assert probes["rust_omniroute_order_status"] == "PASS"

    dashboard = out["dashboard"]
    assert dashboard["schema"] == "PGGArchonOmniRouteDashboard/v1"
    assert dashboard["selected_provider"]
    assert dashboard["order_source"] == "python_evm_engine+live_provider_health"
    assert dashboard["evm_final_score"]
    assert dashboard["order_strength"]
    assert dashboard["provider_health_cache_status"] in {"hit", "refresh_miss_or_expired", "refresh_forced"}
    assert float(dashboard["provider_health_age_sec"]) >= 0.0
    assert float(dashboard["provider_health_ttl_sec"]) > 0.0
    assert int(dashboard["provider_healthy_count"]) >= 1

    dashboard_path = Path(dashboard["dashboard_path"])
    evm_report_path = Path(dashboard["evm_report_path"])
    provider_health_path = Path(dashboard["provider_health_path"])
    assert dashboard_path.exists()
    assert evm_report_path.exists()
    assert provider_health_path.exists()
    assert "does not prove upstream provider participation" in out["boundary"]
