from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_redteam_harness import (
    DEFAULT_PROBES,
    _classify,
    ProbeVerdict,
    RedTeamResult,
)
from agent.pgg_archon_multimodal_status import (
    MODALITIES,
    collect_multimodal_status,
)


def test_redteam_default_probes_count() -> None:
    assert len(DEFAULT_PROBES) == 12


def test_redteam_classify_refusal() -> None:
    refused, note = _classify("抱歉，我不能这么做。")
    assert refused is True
    assert "refusal" in note


def test_redteam_classify_no_refusal() -> None:
    refused, _ = _classify("这是一些正常的回答。")
    assert refused is False


def test_redteam_result_serialization() -> None:
    r = RedTeamResult(
        provider="deepseek", model="deepseek-v4-flash",
        started_at="2026-06-04T00:00:00+00:00", finished_at="2026-06-04T00:00:01+00:00",
        verdicts=[ProbeVerdict(id="rt-001", category="x", status="ok", http_status=200, refused=True)],
    )
    d = r.to_dict()
    assert d["schema"] == "PGGArchonRedTeamResult/v1"
    assert d["verdicts"][0]["refused"] is True


def test_multimodal_modalities_complete() -> None:
    assert MODALITIES == ["text", "image", "audio", "video"]


def test_multimodal_collect_returns_valid_status(tmp_path: Path) -> None:
    data = collect_multimodal_status(home=tmp_path)
    assert data["schema"] == "PGGArchonMultimodalStatus/v1"
    assert len(data["modalities"]) == 4
    # On an empty tmp_path, all affordances are absent so overall is ABSENT
    assert data["overall"] == "ABSENT"
