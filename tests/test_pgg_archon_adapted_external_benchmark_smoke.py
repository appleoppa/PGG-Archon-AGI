from __future__ import annotations

import json

from agent import pgg_archon_adapted_external_benchmark_smoke as mod


def test_extract_expected_and_prediction() -> None:
    assert mod.extract_expected("reasoning\n#### 1,234") == "1234"
    assert mod.extract_prediction("work\nFINAL_ANSWER: 42") == "42"
    assert mod.extract_prediction("numbers 1 then 2.5") == "2.5"


def test_run_smoke_requires_successful_returncode_for_pass(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        mod,
        "fetch_gsm8k_sample",
        lambda limit: [{"question": "1+1?", "answer": "#### 2"}],
    )
    monkeypatch.setattr(
        mod,
        "ask_hermes",
        lambda provider, model, question, timeout: ("FINAL_ANSWER: 2", 0.01, 1, "provider error"),
    )
    result = mod.run_smoke(
        provider="gpt55_5yuantoken",
        model="gpt-5.5",
        limit=1,
        timeout=1,
        out_dir=tmp_path,
    )
    report = json.loads((tmp_path / "adapted_gsm8k_smoke_report.json").read_text(encoding="utf-8"))
    assert result["passed_count"] == 0
    assert result["status"] == "WATCH"
    assert result["run_status"] == "COMPLETED"
    assert report["items"][0]["passed"] is False
    assert report["raw_calls"][0]["returncode"] == 1
    assert "not official GSM8K score" in report["boundary"]