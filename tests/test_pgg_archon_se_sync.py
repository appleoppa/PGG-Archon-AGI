from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_se_sync import sync, PATCHES


def test_sync_creates_output(tmp_path: Path) -> None:
    summary = sync()
    # only files present in source get patched; the 6 PATCHES include file 5.5 which may not be in source
    src = json.loads(Path(summary["source"]).read_text(encoding="utf-8"))
    def _norm(raw: object) -> set[str]:
        s = str(raw)
        out = {s}
        if s.startswith("file_"):
            out.add(s.removeprefix("file_"))
        return out

    src_norm_ids = set()
    for r in src["results"]:
        src_norm_ids.update(_norm(r["card"]["id"]))
    expected = sum(1 for fid, _, _, _ in PATCHES if str(fid) in src_norm_ids)
    assert summary["patched_files"] == expected
    assert summary["status_distribution"] == {"SKELETON": 0, "ABSENT": 0, "PARTIAL": 0, "ACTIVE": 33}
    synced = Path(summary["synced_path"])
    assert synced.exists()
    data = json.loads(synced.read_text(encoding="utf-8"))
    by_norm_id = {}
    for r in data["results"]:
        for nid in _norm(r["card"]["id"]):
            by_norm_id[nid] = r["card"]["status"]
    for fid, status, _, _ in PATCHES:
        if str(fid) in src_norm_ids:
            assert by_norm_id.get(str(fid)) == status


def test_sync_is_idempotent() -> None:
    s1 = sync()
    s2 = sync()
    assert s1["status_distribution"] == s2["status_distribution"]
