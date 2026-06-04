from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_super_evolution_lane import run_lane
from agent.pgg_archon_redteam_corpus_gen import collect_corpus


def test_super_evolution_lane_emits_snap(tmp_path: Path) -> None:
    result = run_lane(tmp_path, run_id="test")
    assert result["schema"] == "PGGArchonSuperEvolutionLaneResult/v1"
    snap = json.loads(Path(result["snap_path"]).read_text(encoding="utf-8"))
    assert snap["schema"] == "PGGArchonSuperEvolutionLaneSnap/v1"
    assert "tiangong" in snap
    assert "multimodal" in snap
    assert "research_engine" in snap


def test_redteam_corpus_gen_shape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Bypass real provider calls by stubbing _ask via monkeypatch.
    # collect_corpus iterates over 4 providers; set fake API keys so every
    # provider is exercised, then assert probes came back.
    from agent import pgg_archon_redteam_corpus_gen as mod

    for env in ("DEEPSEEK_V4_FLASH_API_KEY", "MIMO_V25_PRO_API_KEY", "AGNES_AI_API_KEY", "MINIMAX_API_KEY"):
        monkeypatch.setenv(env, "test-key")

    def fake_ask(url, model, key, prompt, mx, timeout=120):
        return '{"probes":[{"prompt":"a"},{"prompt":"b"}]}'

    monkeypatch.setattr(mod, "_ask", fake_ask)
    data = collect_corpus(categories=["credential_exfil"], per_provider=2)
    assert data["schema"] == "PGGArchonRedteamCorpusGen/v1"
    # 4 providers × 1 category = 4 items
    assert len(data["items"]) == 4
    # Each item's probes list reflects the mocked pair (since all 4 keys are present)
    for item in data["items"]:
        assert item["probes"] == [{"prompt": "a"}, {"prompt": "b"}]
