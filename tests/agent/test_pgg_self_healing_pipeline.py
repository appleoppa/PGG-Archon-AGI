from __future__ import annotations

from pathlib import Path

from agent import pgg_self_healing_pipeline as heal


def test_daily_learning_runtime_status_accepts_batch_scheduler_latest(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    data_dir = tmp_path / "data"
    cli = bin_dir / "pgg-daily-learning"
    latest = data_dir / "daily-learning" / "latest.json"
    cli.parent.mkdir(parents=True)
    cli.write_text("#!/bin/sh\n", encoding="utf-8")
    latest.parent.mkdir(parents=True)
    latest.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(heal, "BIN", bin_dir)
    monkeypatch.setattr(heal, "DATA", data_dir)
    monkeypatch.setattr(heal, "HOME", tmp_path)

    status = heal._daily_learning_runtime_status()

    assert status["action"] == "managed_by_batch_scheduler"
    assert status["cli"] == str(cli)
    assert status["latest"] == str(latest)


def test_daily_learning_runtime_status_only_reports_plist_missing_when_no_cli(tmp_path, monkeypatch):
    monkeypatch.setattr(heal, "BIN", tmp_path / "bin")
    monkeypatch.setattr(heal, "DATA", tmp_path / "data")
    monkeypatch.setattr(heal, "HOME", tmp_path)

    status = heal._daily_learning_runtime_status()

    assert status["action"] == "plist_missing"
