from __future__ import annotations

from agent import pgg_legal_e2e_benchmark_gate as legal
from agent import pgg_l2_readiness_gate as l2


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
    token_latest = tmp_path / "pgg_token_oauth_governance_latest.json"
    token_latest.write_text('{"status":"PASS_TOKEN_OAUTH_MIN_PRIVILEGE"}', encoding="utf-8")

    def fake_json(cmd, timeout=120):
        joined = " ".join(map(str, cmd))
        if "hermes-goal" in joined:
            return {"summary": "16/16 components PASS", "watch_count": 0, "blocked_count": 0}
        if "hermes-evolve" in joined:
            return {"status": "PASS_GITHUB_EVOLUTION_PIPELINE_BOUNDED", "blockers": []}
        if "pgg_agi_gap" in joined:
            return {"status": "PASS_WITH_WATCH_AGI_GAP_CLOSURE_GATED", "score": 83.2}
        if "pgg_legal_e2e" in joined:
            return {"status": "PASS_BOUNDED_LEGAL_E2E_RETRIEVAL_BENCHMARK", "pass_rate": 1.0}
        if "pgg_autonomy" in joined:
            return {"status": "PASS_AUTONOMY_CURVE_BASELINE_COLLECTING", "pipeline_success_rate": 0.93}
        return {"status": "PASS"}

    def fake_run(cmd, timeout=120):
        joined = " ".join(map(str, cmd))
        if "gh pr list" in joined:
            return {"returncode": 0, "stdout": "[]", "stderr": ""}
        return {"returncode": 0, "stdout": "{}", "stderr": ""}

    monkeypatch.setattr(l2, "_json_from_run", fake_json)
    monkeypatch.setattr(l2, "_run", fake_run)
    rec = l2.build_status()
    assert rec["status"] == "PASS_INTERNAL_L2_CANDIDATE_READINESS"
    assert rec["score"] >= 85
    assert "external AGI L2" in rec["must_not_claim"]
