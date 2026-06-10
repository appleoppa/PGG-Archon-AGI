from __future__ import annotations

from agent import pgg_autonomy_curve_collector as curve
from agent import pgg_high_risk_lane_gate as lanes
from agent import pgg_token_oauth_governance as token
from agent import pgg_external_benchmark_legal_smoke as bench
from agent import pgg_agi_gap_closure_gate as aggregate


def test_token_scope_parser_and_watch_boundary():
    scopes = token._parse_scopes("Token scopes: 'repo', 'workflow', 'delete_repo'")
    assert scopes == ["repo", "workflow", "delete_repo"]
    assert "delete_repo" in token.DANGEROUS_SCOPES


def test_high_risk_lane_receipts_are_guarded(monkeypatch, tmp_path):
    monkeypatch.setattr(lanes, "HOME", tmp_path)
    monkeypatch.setattr(lanes, "DATA", tmp_path / "data")
    monkeypatch.setattr(lanes, "LATEST", tmp_path / "data/latest.json")
    monkeypatch.setattr(lanes, "LEDGER", tmp_path / "data/ledger.jsonl")
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin/cms_case_guard").write_text("x")
    (tmp_path / "bin/case_trusted_workflow_gate").write_text("x")

    def fake_run(cmd, timeout=60):
        joined = " ".join(str(x) for x in cmd)
        if "hermes-goal" in joined:
            return {"returncode": 0, "stdout": '{"summary":"16/16 components PASS"}', "stderr": ""}
        if "hermes-evolve" in joined:
            return {"returncode": 0, "stdout": '{"status":"PASS_GITHUB_EVOLUTION_PIPELINE_BOUNDED"}', "stderr": ""}
        if "mcp" in joined:
            return {"returncode": 0, "stdout": "llm-audit enabled", "stderr": ""}
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(lanes, "_run", fake_run)
    rec = lanes.build_status()
    assert rec["status"] == "PASS_HIGH_RISK_LANES_GUARDED_READY"
    assert rec["lanes"]["legal"]["production_takeover"] is False
    assert "final_human_review" in rec["lanes"]["legal"]["requires_receipts"]


def test_autonomy_curve_does_not_claim_multi_day_from_one_sample(monkeypatch, tmp_path):
    monkeypatch.setattr(curve, "DATA", tmp_path)
    monkeypatch.setattr(curve, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(curve, "LATEST", tmp_path / "latest.json")
    (tmp_path / "pgg_github_evolution_pipeline_ledger.jsonl").write_text('{"status":"PASS_X"}\n')
    monkeypatch.setattr(curve, "_run", lambda cmd, timeout=30: {"returncode": 0, "stdout": "[]" if "gh" in cmd else "## main", "stderr": ""})
    rec = curve.collect()
    assert rec["multi_day_claim_allowed"] is False
    assert rec["pipeline_success_rate"] == 1.0


def test_benchmark_smoke_boundary(monkeypatch, tmp_path):
    monkeypatch.setattr(bench, "HOME", tmp_path)
    monkeypatch.setattr(bench, "DATA", tmp_path / "data")
    monkeypatch.setattr(bench, "LATEST", tmp_path / "data/latest.json")
    monkeypatch.setattr(bench, "LEDGER", tmp_path / "data/ledger.jsonl")
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin/cms_case_guard").write_text("x")
    monkeypatch.setattr(bench, "_run", lambda cmd, timeout=60: {"returncode": 0, "stdout": "16/16 components PASS" if "hermes-goal" in " ".join(map(str, cmd)) else "NEXT", "stderr": ""})
    rec = bench.build_status()
    assert rec["status"] == "PASS_BOUNDED_BENCHMARK_LEGAL_SMOKE"
    assert "not official" in rec["boundary"]


def test_aggregate_caps_score_when_token_oauth_watch(monkeypatch, tmp_path):
    monkeypatch.setattr(aggregate, "DATA", tmp_path)
    monkeypatch.setattr(aggregate, "LATEST", tmp_path / "latest.json")
    monkeypatch.setattr(aggregate, "LEDGER", tmp_path / "ledger.jsonl")

    def fake_run_module(module):
        if module.endswith("pgg_token_oauth_governance"):
            return {"status": "WATCH_TOKEN_OAUTH_REQUIRES_CREDENTIAL_ROTATION", "_returncode": 2}
        return {"status": "PASS_X", "_returncode": 0}

    monkeypatch.setattr(aggregate, "_run_module", fake_run_module)
    rec = aggregate.build_status()
    assert rec["status"] == "PASS_WITH_WATCH_AGI_GAP_CLOSURE_GATED"
    assert rec["strict_pass"]["token_oauth_min_privilege"] is False
    assert rec["score"] <= 84.9
    assert any("token/OAuth" in x for x in rec["score_cap_reasons"])
