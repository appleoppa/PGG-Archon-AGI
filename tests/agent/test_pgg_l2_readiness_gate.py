from __future__ import annotations

from agent import pgg_legal_e2e_benchmark_gate as legal
from agent import pgg_l2_readiness_gate as l2
from agent import pgg_historical_evidence_backfill_gate as hist


def test_legal_e2e_scores_local_corpus(monkeypatch, tmp_path):
    root = tmp_path / "法律法规库"
    root.mkdir()
    (root / "最高人民法院关于审理劳动争议案件适用法律问题的解释（一）_20201229.txt").write_text("劳动争议 解释（一）", encoding="utf-8")
    (root / "最高法关于审理道路交通事故损害赔偿案件适用法律若干问题的解释二_法释〔2026〕9号.txt").write_text("道路交通事故 损害赔偿 解释二", encoding="utf-8")
    (root / "最高人民法院关于审理拒不执行判决、裁定刑事案件适用法律若干问题的解释.txt").write_text("拒不执行判决 裁定 刑事案件", encoding="utf-8")
    (root / "最高人民法院关于执行程序中计算迟延履行期间的债务利息适用法律若干问题的解释.txt").write_text("执行程序 迟延履行 债务利息", encoding="utf-8")
    (root / "最高人民法院关于审理物业服务纠纷案件具体应用法律若干问题的解释.txt").write_text("物业服务 纠纷 解释", encoding="utf-8")
    monkeypatch.setattr(legal, "CORPUS_ROOT", root)
    monkeypatch.setattr(legal, "DATA", tmp_path / "data")
    monkeypatch.setattr(legal, "LATEST", tmp_path / "data/latest.json")
    monkeypatch.setattr(legal, "LEDGER", tmp_path / "data/ledger.jsonl")
    rec = legal.run_benchmark()
    assert rec["status"] == "PASS_BOUNDED_LEGAL_E2E_RETRIEVAL_BENCHMARK"
    assert rec["pass_rate"] == 1.0
    assert "not LegalBench" in rec["boundary"]


def test_l2_readiness_is_internal_not_external(monkeypatch, tmp_path):
    monkeypatch.setattr(l2, "DATA", tmp_path)
    monkeypatch.setattr(l2, "LATEST", tmp_path / "latest.json")
    monkeypatch.setattr(l2, "LEDGER", tmp_path / "ledger.jsonl")
    (tmp_path / "pgg_token_oauth_governance_latest.json").write_text('{"status":"PASS_TOKEN_OAUTH_MIN_PRIVILEGE"}', encoding="utf-8")
    (tmp_path / "pgg_agi_gap_closure_gate_latest.json").write_text('{"status":"PASS_WITH_WATCH_AGI_GAP_CLOSURE_GATED","score":83.2}', encoding="utf-8")
    (tmp_path / "pgg_legal_e2e_benchmark_latest.json").write_text('{"status":"PASS_BOUNDED_LEGAL_E2E_RETRIEVAL_BENCHMARK","pass_rate":1.0}', encoding="utf-8")
    (tmp_path / "pgg_autonomy_curve_latest.json").write_text('{"status":"PASS_AUTONOMY_CURVE_BASELINE_COLLECTING","pipeline_success_rate":0.93}', encoding="utf-8")
    (tmp_path / "pgg_historical_evidence_backfill_latest.json").write_text('{"status":"PASS_HISTORICAL_EVIDENCE_BACKFILL_INTERNAL_ONLY","summary":{"evolution_pass_days":["2026-06-08","2026-06-09","2026-06-10"]}}', encoding="utf-8")
    (tmp_path / "pgg_github_evolution_pipeline_latest.json").write_text('{"status":"PASS_GITHUB_EVOLUTION_PIPELINE_BOUNDED","blockers":[]}', encoding="utf-8")

    def fake_run(cmd, timeout=120):
        joined = " ".join(map(str, cmd))
        if "gh pr list" in joined:
            return {"returncode": 0, "stdout": "[]", "stderr": ""}
        if "hermes-goal" in joined:
            return {"returncode": 0, "stdout": '{"summary":"16/16 components PASS","watch_count":0,"blocked_count":0}', "stderr": ""}
        if "hermes-evolve" in joined:
            return {"returncode": 0, "stdout": '{"status":"PASS_GITHUB_EVOLUTION_PIPELINE_BOUNDED","blockers":[]}', "stderr": ""}
        return {"returncode": 0, "stdout": "{}", "stderr": ""}

    monkeypatch.setattr(l2, "_run", fake_run)
    rec = l2.build_status()
    assert rec["status"] == "PASS_INTERNAL_L2_CANDIDATE_READINESS"
    assert rec["score"] >= 85
    assert rec["checks"]["historical_backfill_internal_pass"] is True
    assert rec["dimensions"]["自主行动"] == 88
    assert "external AGI L2" in rec["must_not_claim"]

def test_historical_backfill_classifies_internal_only(monkeypatch, tmp_path):
    monkeypatch.setattr(hist, "DATA", tmp_path / "data")
    monkeypatch.setattr(hist, "LATEST", tmp_path / "data/latest.json")
    monkeypatch.setattr(hist, "LEDGER", tmp_path / "data/ledger.jsonl")
    monkeypatch.setattr(hist, "EVOLUTION_LEDGER", tmp_path / "evolution.jsonl")
    monkeypatch.setattr(hist, "AUTONOMY_LEDGER", tmp_path / "autonomy.jsonl")
    monkeypatch.setattr(hist, "LEGAL_LEDGER", tmp_path / "legal.jsonl")
    monkeypatch.setattr(hist, "L2_LEDGER", tmp_path / "l2.jsonl")
    rows = []
    for day in ["2026-06-08", "2026-06-09", "2026-06-10"]:
        for _ in range(40):
            rows.append('{"generated_at":"' + day + 'T00:00:00+00:00","status":"PASS_A"}')
    hist.EVOLUTION_LEDGER.write_text('\n'.join(rows) + '\n', encoding="utf-8")
    hist.AUTONOMY_LEDGER.write_text('{"generated_at":"2026-06-10T00:00:00+00:00","status":"PASS_AUTONOMY_CURVE_BASELINE_COLLECTING","multi_day_claim_allowed":false}\n', encoding="utf-8")
    hist.LEGAL_LEDGER.write_text('{"generated_at":"2026-06-10T00:00:00+00:00","status":"PASS_BOUNDED_LEGAL_E2E_RETRIEVAL_BENCHMARK","pass_rate":1.0}\n', encoding="utf-8")
    hist.L2_LEDGER.write_text('{"generated_at":"2026-06-10T00:00:00+00:00","status":"PASS_INTERNAL_L2_CANDIDATE_READINESS","score":86.2}\n', encoding="utf-8")
    rec = hist.build_status()
    assert rec["status"] == "PASS_HISTORICAL_EVIDENCE_BACKFILL_INTERNAL_ONLY"
    assert rec["checks"]["multi_day_github_evolution_telemetry"] is True
    assert rec["checks"]["autonomy_collector_multiday_not_claimed"] is True
    assert "external AGI L2" in rec["not_usable_for_external_claims"]
