from __future__ import annotations

import sys
from pathlib import Path

import hermes_cli.main as main


def test_project_venv_dir_prefers_live_dotvenv(monkeypatch, tmp_path):
    project = tmp_path / "hermes-agent"
    dotvenv = project / ".venv"
    legacy = project / "venv"
    (dotvenv / "bin").mkdir(parents=True)
    (dotvenv / "pyvenv.cfg").write_text("prompt = hermes-agent\n")
    legacy.mkdir(parents=True)

    monkeypatch.setattr(main, "PROJECT_ROOT", project)
    monkeypatch.setattr(sys, "prefix", str(dotvenv))
    monkeypatch.setattr(sys, "base_prefix", str(tmp_path / "python"))
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    assert main._project_venv_dir() == dotvenv.resolve()


def test_project_venv_dir_falls_back_to_dotvenv_before_legacy(monkeypatch, tmp_path):
    project = tmp_path / "hermes-agent"
    dotvenv = project / ".venv"
    legacy = project / "venv"
    dotvenv.mkdir(parents=True)
    legacy.mkdir(parents=True)

    monkeypatch.setattr(main, "PROJECT_ROOT", project)
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "system"))
    monkeypatch.setattr(sys, "base_prefix", str(tmp_path / "system"))
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)

    assert main._project_venv_dir() == dotvenv


def test_ensure_legacy_venv_compat_creates_symlink(monkeypatch, tmp_path):
    project = tmp_path / "hermes-agent"
    dotvenv = project / ".venv"
    (dotvenv / "bin").mkdir(parents=True)

    monkeypatch.setattr(main, "PROJECT_ROOT", project)
    monkeypatch.setattr(main, "_is_windows", lambda: False)

    main._ensure_legacy_venv_compat(dotvenv)

    legacy = project / "venv"
    assert legacy.is_symlink()
    assert legacy.readlink() == Path(".venv")
