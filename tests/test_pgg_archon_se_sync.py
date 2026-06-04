from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_se_sync import sync, PATCHES


def test_sync_creates_output(tmp_path: Path) -> None:
    summary = sync()
    # only files present in source get patched; the 6 PATCHES include file 5.5 which may not be in source
    src = json.loads(Path(summary["source"]).read_text(encoding="utf-8"))
    src_ids = {r["card"]["id"] for r in src["results"]}
    expected = sum(1 for fid, _, _, _ in PATCHES if fid in src_ids)
    assert summary["patched_files"] == expected
    assert "SKELETON" in summary["status_distribution"]
    synced = Path(summary["synced_path"])
    assert synced.exists()
    data = json.loads(synced.read_text(encoding="utf-8"))
    by_id = {r["card"]["id"]: r["card"]["status"] for r in data["results"]}
    for fid, status, _, _ in PATCHES:
        if fid in src_ids:
            assert by_id.get(fid) == status


def test_sync_is_idempotent() -> None:
    s1 = sync()
    s2 = sync()
    assert s1["status_distribution"] == s2["status_distribution"]
