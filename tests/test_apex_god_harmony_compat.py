from __future__ import annotations


def test_apex_god_legacy_exports_importable():
    from apex_god import APEX_GODAgent, apex_god_wrap
    from apex_god.kernel import LLMKernel, wrap_provider

    assert APEX_GODAgent is LLMKernel
    assert apex_god_wrap is wrap_provider


def test_measure_harmony_accepts_current_fused_watcher():
    from apex_god.measure import measure_harmony

    result = measure_harmony()

    assert result["score"] == 1.0
    assert "components=12/12" in result["detail"]
    assert "imports=ok" in result["detail"]


def test_measure_growth_is_cleanup_friendly_status_surface():
    from apex_god.measure import measure_growth

    result = measure_growth()

    assert result["score"] >= 0.85
    assert "cleanup_friendly=yes" in result["detail"]
    assert "channels=5/5" in result["detail"]
    assert "milestones=" in result["detail"]
    assert "bg_files=" in result["detail"]
