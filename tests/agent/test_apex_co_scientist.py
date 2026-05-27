from __future__ import annotations

import json
from pathlib import Path

from agent.apex_co_scientist import (
    build_debate_report,
    build_gene_candidate_from_debate,
    load_latest_debate_report,
    load_latest_gene_candidate,
    summarize_debate_report,
    summarize_gene_candidate,
    validate_debate_report,
    write_debate_report,
    write_gene_candidate,
)
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


def test_debate_report_summary_and_validation():
    report = build_debate_report(topic="co", reviewers=[{"status": "ok"}, {"status": "ok"}], decision="execute")
    validation = validate_debate_report(report)
    summary = summarize_debate_report(report)
    assert validation["valid"] is True
    assert summary["schema"] == "ApexCoScientistDebateSummary/v1"
    assert summary["status"] == "PASS"
    assert summary["reviewer_count"] == 2
    assert summary["promotion_required"] is True
    assert summary["applied_to_memory_or_skill"] is False


def test_load_latest_debate_report_under_workspace():
    workspace = Path.cwd() / "workspace" / "co_scientist_test"
    workspace.mkdir(parents=True, exist_ok=True)
    older = build_debate_report(topic="old", reviewers=[], decision="hold")
    newer = build_debate_report(topic="new", reviewers=[{"status": "ok"}, {"status": "ok"}], decision="execute")
    older_path = workspace / "old.json"
    newer_path = workspace / "new.json"
    write_debate_report(older_path, older)
    write_debate_report(newer_path, newer)
    older_path.touch()
    newer_path.touch()
    loaded = load_latest_debate_report(workspace)
    assert loaded is not None
    assert loaded["topic"] == "new"
    assert loaded["status"] == "PASS"


def test_load_latest_debate_report_rejects_outside_workspace(tmp_path):
    outside = tmp_path / "co_scientist"
    outside.mkdir()
    try:
        load_latest_debate_report(outside)
    except ValueError as exc:
        assert "repository workspace" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


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


def test_build_gene_candidate_from_debate_is_read_only():
    report = build_debate_report(topic="gene", reviewers=[{"status": "ok"}, {"status": "ok"}], decision="execute")
    candidate = build_gene_candidate_from_debate(report)
    summary = summarize_gene_candidate(candidate)
    assert candidate["schema"] == "ApexCoScientistGeneCandidate/v1"
    assert candidate["status"] == "READY"
    assert candidate["eligible"] is True
    assert candidate["promotion_required"] is True
    assert candidate["gene_library_written"] is False
    assert candidate["side_effects"] == "read_only_candidate"
    assert summary["eligible"] is True


def test_build_gene_candidate_holds_weak_debate():
    report = build_debate_report(topic="weak", reviewers=[{"status": "ok"}], decision="hold")
    candidate = build_gene_candidate_from_debate(report)
    assert candidate["status"] == "HOLD"
    assert candidate["eligible"] is False
    assert "insufficient_reviewers" in candidate["blockers"]
    assert candidate["gene_library_written"] is False


def test_write_and_load_latest_gene_candidate_under_workspace():
    workspace = Path.cwd() / "workspace" / "co_scientist_gene_candidate_test"
    workspace.mkdir(parents=True, exist_ok=True)
    report = build_debate_report(topic="gene-readback", reviewers=[{"status": "ok"}, {"status": "ok"}], decision="execute")
    candidate = build_gene_candidate_from_debate(report)
    out = workspace / "candidate.json"
    written = write_gene_candidate(out, candidate)
    loaded = load_latest_gene_candidate(workspace)
    assert written["written"] is True
    assert loaded is not None
    assert loaded["status"] == "READY"
    assert loaded["gene_library_written"] is False


def test_write_gene_candidate_rejects_outside_workspace(tmp_path):
    report = build_debate_report(topic="outside", reviewers=[{"status": "ok"}, {"status": "ok"}], decision="execute")
    candidate = build_gene_candidate_from_debate(report)
    try:
        write_gene_candidate(tmp_path / "candidate.json", candidate)
    except ValueError as exc:
        assert "repository workspace" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_cli_co_scientist_gene_json_report():
    workspace = Path.cwd() / "workspace" / "co_scientist_gene_cli_test"
    workspace.mkdir(parents=True, exist_ok=True)
    out = workspace / "candidate.json"
    payload = json.loads(run_apex_runtimeos_cli([
        "co-scientist-gene",
        "--topic", "APEX gene candidate test",
        "--reviewer", json.dumps({"provider": "gpt55_5yuantoken", "model": "gpt-5.5", "role": "reasoning", "status": "ok", "claim": "approve", "risk": "low", "verification": "pytest"}, ensure_ascii=False),
        "--reviewer", json.dumps({"provider": "claude_opus47_5yuantoken", "model": "claude-opus-4-7", "role": "coding", "status": "ok", "claim": "safe", "risk": "low", "verification": "readback"}, ensure_ascii=False),
        "--synthesis", "一致生成候选，但不写基因库",
        "--decision", "execute",
        "--output", str(out),
        "--json",
    ]))
    candidate = payload["result"]["candidate"]
    assert payload["object"] == "hermes.apex_runtimeos.co_scientist_gene"
    assert candidate["status"] == "READY"
    assert candidate["gene_library_written"] is False
    assert payload["result"]["written"]["written"] is True
    assert out.exists()
