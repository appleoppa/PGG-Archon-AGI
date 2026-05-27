from __future__ import annotations

import json
from pathlib import Path

from agent.apex_era import (
    build_era_path_search_report,
    load_latest_era_report,
    summarize_era_report,
    write_era_report,
)
from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli


def _paths():
    return [
        {"id": "fast", "title": "快速直改", "summary": "直接修改", "risk": 0.4, "cost": 0.2, "reward": 0.6, "evidence": 0.5, "confidence": 0.6},
        {"id": "safe", "title": "只读门禁先行", "summary": "先做 schema 和测试", "risk": 0.1, "cost": 0.3, "reward": 0.8, "evidence": 0.9, "confidence": 0.8, "actions": ["schema", "tests"]},
        {"id": "risky", "title": "自动执行外部代码", "summary": "高风险", "risk": 0.9, "cost": 0.7, "reward": 0.9, "evidence": 0.2, "confidence": 0.2},
    ]


def test_build_era_path_search_report_selects_safe_path_and_is_read_only():
    report = build_era_path_search_report(task="ERA test", paths=_paths())
    assert report["schema"] == "ApexERAPathSearchReport/v1"
    assert report["status"] == "PASS"
    assert report["path_count"] == 3
    assert report["selected_path_id"] == "safe"
    assert report["executed"] is False
    assert report["side_effects"] == "read_only_report"
    assert all(item["side_effects"] == "not_executed" for item in report["paths"])


def test_era_report_sanitizes_sensitive_text():
    report = build_era_path_search_report(
        task="/Users/appleoppa/private api_key=secret",
        paths=[{"id": "x", "title": "authorization: bearer x", "risk": 0, "reward": 1, "evidence": 1, "confidence": 1}],
    )
    raw = json.dumps(report, ensure_ascii=False)
    assert "/Users/appleoppa" not in raw
    assert "api_key=secret" not in raw
    assert "authorization: bearer x" not in raw


def test_write_and_load_latest_era_report_under_workspace():
    workspace = Path.cwd() / "workspace" / "era_path_search_test"
    workspace.mkdir(parents=True, exist_ok=True)
    report = build_era_path_search_report(task="ERA readback", paths=_paths())
    out = workspace / "era.json"
    written = write_era_report(out, report)
    loaded = load_latest_era_report(workspace)
    assert written["written"] is True
    assert loaded is not None
    assert loaded["schema"] == "ApexERAPathSearchSummary/v1"
    assert loaded["selected_path_id"] == "safe"
    assert loaded["executed"] is False


def test_write_era_report_rejects_outside_workspace(tmp_path):
    report = build_era_path_search_report(task="outside", paths=_paths())
    try:
        write_era_report(tmp_path / "era.json", report)
    except ValueError as exc:
        assert "repository workspace" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_cli_era_json_report():
    workspace = Path.cwd() / "workspace" / "era_cli_test"
    workspace.mkdir(parents=True, exist_ok=True)
    out = workspace / "era.json"
    payload = json.loads(run_apex_runtimeos_cli([
        "era",
        "--topic", "ERA CLI test",
        "--path", json.dumps(_paths()[0], ensure_ascii=False),
        "--path", json.dumps(_paths()[1], ensure_ascii=False),
        "--path", json.dumps(_paths()[2], ensure_ascii=False),
        "--output", str(out),
        "--json",
    ]))
    report = payload["result"]["report"]
    assert payload["object"] == "hermes.apex_runtimeos.era"
    assert report["selected_path_id"] == "safe"
    assert report["executed"] is False
    assert payload["result"]["written"]["written"] is True


def test_summarize_era_report():
    report = build_era_path_search_report(task="sum", paths=_paths())
    summary = summarize_era_report(report)
    assert summary["valid"] is True
    assert summary["status"] == "PASS"
    assert summary["path_count"] == 3
