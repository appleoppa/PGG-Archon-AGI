from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_se_sync import sync, PATCHES


def test_sync_creates_output(tmp_path: Path) -> None:
    summary = sync()
    assert summary["patched_files"] >= 6
    assert "SKELETON" in summary["status_distribution"]
    synced = Path(summary["synced_path"])
    assert synced.exists()
    data = json.loads(synced.read_text(encoding="utf-8"))
    by_id = {r["card"]["id"]: r["card"]["status"] for r in data["results"]}
    for fid, status, _, _ in PATCHES:
        assert by_id.get(fid) == status


def test_sync_is_idempotent() -> None:
    s1 = sync()
    s2 = sync()
    assert s1["status_distribution"] == s2["status_distribution"]
