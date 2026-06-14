"""Tests for PGG Archon P0 three-surface absorption in Hermes environment.

Verifies:
1. RiskPrediction scans correctly detect and miss patterns
2. CrossProjectPattern extracts and compares patterns
3. LifeHarness heartbeat/health/recovery constructors work
4. Unified p0 surface report aggregates all three correctly
5. Status surface integration accepts p0_surface_report param
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

# ── RiskPredictionSurface tests ──

from agent.pgg_archon_risk_prediction import (
    scan_content,
    scan_file,
    SURFACE_VERSION as RISK_VERSION,
)


def test_risk_detects_sql_injection():
    code = 'def get_user(uid):\n    cur.execute(f"SELECT * FROM users WHERE id = {uid}")'
    report = scan_content(code, "test.py")
    assert report.risk_score > 0.0, "Should detect SQL injection f-string"
    assert any("SQL Injection" in v.vulnerability_type for v in report.vulnerabilities)


def test_risk_detects_hardcoded_secret():
    code = 'api_key = "sk-abc123def456ghij"'
    report = scan_content(code)
    assert report.risk_score > 0.0
    assert any("Hardcoded" in v.vulnerability_type for v in report.vulnerabilities)


def test_risk_clean_code():
    code = 'def get_user(uid):\n    cur.execute("SELECT * FROM users WHERE id = ?", (uid,))'
    report = scan_content(code)
    assert len(report.vulnerabilities) == 0
    assert report.risk_score == 0.0


def test_risk_version():
    assert RISK_VERSION == "PGGArchonRiskPredictionSurface/v1"


def test_risk_to_dict():
    code = 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)'
    report = scan_content(code)
    d = report.to_dict()
    assert "scan_time" in d
    assert "risk_score" in d
    assert "summary" in d
    assert d["summary"]["total"] >= 1


# ── CrossProjectPatternSurface tests ──

from agent.pgg_archon_cross_project_pattern import (
    extract_patterns_from_file,
    compare_patterns,
    Pattern,
    SURFACE_VERSION as PATTERN_VERSION,
)


def test_pattern_extraction_python():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def hello(): pass\nasync def fetch_data(url): pass\n")
        tmp = f.name
    try:
        patterns = extract_patterns_from_file(tmp, "test_project")
        assert len(patterns) == 2
        assert any("hello" in p.code_snippet for p in patterns)
    finally:
        os.unlink(tmp)


def test_pattern_extraction_non_code():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Just docs\n")
        tmp = f.name
    try:
        patterns = extract_patterns_from_file(tmp)
        assert len(patterns) == 0
    finally:
        os.unlink(tmp)


def test_pattern_comparison():
    existing = [
        Pattern("e1", "code", "proj1", "a.py", "def login(): pass", "login func"),
        Pattern("e2", "code", "proj1", "b.py", "def logout(): pass", "logout func"),
    ]
    candidates = [
        Pattern("c1", "code", "proj2", "c.py", "def login(): pass", "login func"),
        Pattern("c2", "code", "proj2", "d.py", "def run_analysis_report(): pass", "analyze func"),
    ]
    results = compare_patterns(candidates, existing, threshold=0.9)
    assert len(results) == 2
    assert not results[0].should_promote  # login is similar to existing
    assert results[1].should_promote       # analysis is novel


def test_pattern_version():
    assert PATTERN_VERSION == "PGGArchonCrossProjectPatternSurface/v1"


# ── LifeHarnessSurface tests ──

from agent.pgg_archon_life_harness import (
    make_heartbeat,
    make_health_summary,
    make_recovery_entry,
    SystemStatus,
    SURFACE_VERSION as LH_VERSION,
)


def test_heartbeat_healthy():
    hb = make_heartbeat(successes=10, failures=0, max_failures=3, uptime=3600)
    assert hb.healthy is True
    assert hb.total_pings == 10
    assert hb.uptime_secs == 3600


def test_heartbeat_unhealthy():
    hb = make_heartbeat(successes=5, failures=4, max_failures=3, uptime=100)
    assert hb.healthy is False


def test_health_summary_healthy():
    hb = make_heartbeat(successes=10, failures=0)
    hs = make_health_summary(hb)
    assert hs.status == SystemStatus.HEALTHY.value
    assert hs.sessions_active == 0


def test_health_summary_critical():
    hb = make_heartbeat(successes=5, failures=0)
    hs = make_health_summary(hb, errors=["crash on startup"])
    assert hs.status == SystemStatus.CRITICAL.value


def test_recovery_entry():
    r = make_recovery_entry("restart_subsystem", "heartbeat timeout", 1)
    assert r.action == "restart_subsystem"
    assert r.count == 1


def test_life_harness_version():
    assert LH_VERSION == "PGGArchonLifeHarnessSurface/v1"


# ── Unified P0 surface tests ──

from agent.pgg_archon_p0_surface import build_pgg_archon_p0_surface, SURFACE_VERSION as P0_VERSION


def test_p0_surface_report_structure():
    report = build_pgg_archon_p0_surface()
    assert report["schema"] == P0_VERSION
    assert report["status"] in ("PASS", "WATCH", "BLOCK")
    assert "surfaces" in report
    assert set(report["surfaces"].keys()) == {"risk_prediction", "cross_project_pattern", "life_harness"}
    assert report.get("agi_completion_claim") is False


def test_p0_surface_all_pass():
    report = build_pgg_archon_p0_surface()
    # All three sub-surfaces should be importable and pass smoke tests
    for name, surface in report["surfaces"].items():
        assert surface.get("importable"), f"{name} should be importable"
        # Verify key smoke checks within each surface
        for key in surface:
            if key not in ("importable", "surface_version", "surface_source", "error"):
                assert surface[key] is not False, f"{name}.{key} should not be False"


def test_p0_surface_reuses_core_functions():
    """Verify that p0_surface re-exports allow direct usage."""
    from agent.pgg_archon_p0_surface import (
        scan_content as p0_scan,
        extract_patterns_from_file as p0_extract,
        compare_patterns as p0_compare,
        make_heartbeat as p0_heartbeat,
        make_health_summary as p0_summary,
    )

    # Risk scan via re-export
    r = p0_scan('api_key = "sk-abc123def456"')
    assert r.risk_score > 0

    # Heartbeat via re-export
    hb = p0_heartbeat(successes=3, failures=0)
    assert hb.healthy
    hs = p0_summary(hb)
    assert hs.status == SystemStatus.HEALTHY.value


# ── Status surface integration tests ──

from agent.pgg_archon_status_surface import build_pgg_archon_status_surface


def test_status_surface_accepts_p0_report():
    """Status surface should accept an explicit p0_surface_report."""
    status = build_pgg_archon_status_surface(
        unlock_report={},
        graph_replay_report={},
        eval_regression_report={},
        golden_regression_report={},
        promotion_guard_report={},
        evidence_loop_report={},
        apex_agi_absorption_report={},
        p0_surface_report={},  # empty dict → will be treated as BLOCK/ERROR
    )
    assert "p0_surfaces_ready" in status.get("signals", {}) or "signals" in status
    # Status should still produce a valid structure
    assert status.get("schema", "").startswith("PGGArchon")


def test_status_surface_p0_bottleneck():
    """When p0_surface is BLOCK, a P0/Srf bottleneck should appear."""
    fake_p0 = {
        "schema": "PGGArchonP0Surface/v1",
        "status": "BLOCK",
        "aggregate": {
            "surfaces_ok": 1,
            "surfaces_total": 3,
            "no_smoke_failures": False,
            "blocking_failures": ["life_harness: smoke test failure"],
        },
        "surfaces": {},
        "agi_completion_claim": False,
    }
    status = build_pgg_archon_status_surface(
        unlock_report={},
        graph_replay_report={},
        eval_regression_report={},
        golden_regression_report={},
        promotion_guard_report={},
        evidence_loop_report={},
        apex_agi_absorption_report={},
        p0_surface_report=fake_p0,
    )
    bottlenecks = status.get("small_bottlenecks", [])
    p0_bn = [b for b in bottlenecks if b.get("code") == "P0/Srf"]
    assert len(p0_bn) == 1, f"Expected P0/Srf bottleneck, got {bottlenecks}"
    assert p0_bn[0]["surfaces_ok"] == 1
    assert p0_bn[0]["surfaces_total"] == 3
