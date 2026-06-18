from __future__ import annotations

import json
from pathlib import Path

from agent import memory_system_status as mss


def test_memory_system_status_schema_and_score(monkeypatch, tmp_path):
    h = tmp_path / "hermes"
    (h / "memories").mkdir(parents=True)
    (h / "data").mkdir(parents=True)
    (h / "memories" / "MEMORY.md").write_text("A§B", encoding="utf-8")
    (h / "memories" / "USER.md").write_text("U§V", encoding="utf-8")
    (h / "SOUL.md").write_text("S", encoding="utf-8")
    (h / "config.yaml").write_text("memory:\n  provider: ''\n  memory_enabled: true\n  user_profile_enabled: true\n", encoding="utf-8")
    (h / "data" / "EVOLUTION_MANIFEST.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(mss, "_akashic_status", lambda home: {"status": "PASS", "audit": {"counts": {}}, "stats": {}, "code_markers": {"write_lock": True}})
    monkeypatch.setattr(mss, "_department_status", lambda home: {"status": "NOOP_BLOCKED_OR_EMPTY", "write_allowed": False, "apply_allowed": False, "counts": {}, "blockers": []})
    monkeypatch.setattr(mss, "_external_provider_status", lambda home: {"status": "PASS_READ_ONLY_AUDIT", "active_external_provider": "", "provider_count": 8, "recommended_next_step": {"provider": "holographic"}, "config_modified": False, "credential_values_printed": False})
    monkeypatch.setattr(mss, "_holographic_status", lambda home: {"status": "SANDBOX_PASS_DEFAULT_NOT_ENABLED", "active_in_default": False, "latest_sandbox_manifest_status": "PASS"})
    monkeypatch.setattr(mss, "_manifest_status", lambda home: {"tracked_memory_keys": {k: {"status": "PASS"} for k in mss.MEMORY_MANIFEST_KEYS}})

    status = mss.build_memory_system_status(h)

    assert status["schema"] == "PGGMemorySystemStatus/v1"
    assert status["command"] == "记忆系统"
    assert status["read_only"] is True
    assert status["config_modified"] is False
    assert status["curated"]["status"] == "PASS"
    assert status["overall"]["score_percent"] == 100.0


def test_memory_system_status_does_not_modify_core_files(monkeypatch, tmp_path):
    h = tmp_path / "hermes"
    (h / "memories").mkdir(parents=True)
    (h / "data").mkdir(parents=True)
    cfg = h / "config.yaml"
    mem = h / "memories" / "MEMORY.md"
    user = h / "memories" / "USER.md"
    cfg.write_text("memory:\n  provider: ''\n", encoding="utf-8")
    mem.write_text("stable memory", encoding="utf-8")
    user.write_text("stable user", encoding="utf-8")
    (h / "data" / "EVOLUTION_MANIFEST.json").write_text("{}", encoding="utf-8")
    before = {p: p.read_text(encoding="utf-8") for p in [cfg, mem, user]}

    monkeypatch.setattr(mss, "_akashic_status", lambda home: {"status": "PASS", "audit": {}, "stats": {}, "code_markers": {"write_lock": True}})
    monkeypatch.setattr(mss, "_department_status", lambda home: {"status": "NOOP_BLOCKED_OR_EMPTY", "write_allowed": False, "apply_allowed": False, "counts": {}, "blockers": []})
    monkeypatch.setattr(mss, "_external_provider_status", lambda home: {"status": "PASS_READ_ONLY_AUDIT", "active_external_provider": "", "recommended_next_step": {"provider": "holographic"}})
    monkeypatch.setattr(mss, "_holographic_status", lambda home: {"status": "SANDBOX_PASS_DEFAULT_NOT_ENABLED", "active_in_default": False})
    monkeypatch.setattr(mss, "_manifest_status", lambda home: {"tracked_memory_keys": {k: {"status": "PASS"} for k in mss.MEMORY_MANIFEST_KEYS}})

    mss.build_memory_system_status(h)

    after = {p: p.read_text(encoding="utf-8") for p in [cfg, mem, user]}
    assert before == after
