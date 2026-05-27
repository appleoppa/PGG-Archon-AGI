from __future__ import annotations

import json
from pathlib import Path

from agent.apex_co_scientist import build_debate_report, write_debate_report
from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli


def test_build_debate_report_sanitizes_and_scores():
    report = build_debate_report(
        topic="APEX Co_Scientist 固化",
        reviewers=[
            {"provider": "gpt55_5yuantoken", "model": "gpt-5.5", "role": "reasoning", "status": "ok", "claim": "execute", "risk": "low", "verification": "tests"},
            {"provider": "claude_opus47_5yuantoken", "model": "claude-opus-4-7", "role": "coding", "status": "ok", "claim": "implement", "risk": "api_key=secret", "verification": "/Users/appleoppa/private"},
        ],
        synthesis="两方一致：只读结构化审查先落地",
        decision="execute",
    )
    assert report["schema"] == "ApexCoScientistDebateReport/v1"
    assert report["status"] == "PASS"
    assert report["reviewer_count"] == 2
    assert report["ok_count"] == 2
    assert report["promotion_required"] is True
    raw = json.dumps(report, ensure_ascii=False)
    assert "api_key=secret" not in raw
    assert "/Users/appleoppa" not in raw


def test_write_debate_report(tmp_path):
    report = build_debate_report(topic="x", reviewers=[], decision="hold")
    out = tmp_path / "debate.json"
    result = write_debate_report(out, report)
    assert result["written"] is True
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8"))["schema"] == "ApexCoScientistDebateReport/v1"


def test_cli_co_scientist_json_report(tmp_path):
    out = tmp_path / "co_scientist.json"
    payload = json.loads(run_apex_runtimeos_cli([
        "co-scientist",
        "--topic", "APEX RuntimeOS test",
        "--reviewer", json.dumps({"provider": "gpt55_5yuantoken", "model": "gpt-5.5", "role": "reasoning", "status": "ok", "claim": "approve", "risk": "low", "verification": "pytest"}, ensure_ascii=False),
        "--reviewer", json.dumps({"provider": "claude_opus47_5yuantoken", "model": "claude-opus-4-7", "role": "coding", "status": "ok", "claim": "safe", "risk": "low", "verification": "readback"}, ensure_ascii=False),
        "--synthesis", "一致执行",
        "--decision", "execute",
        "--output", str(out),
        "--json",
    ]))
    report = payload["result"]["report"]
    assert payload["object"] == "hermes.apex_runtimeos.co_scientist"
    assert report["status"] == "PASS"
    assert report["reviewer_count"] == 2
    assert payload["result"]["written"]["written"] is True
    assert out.exists()
