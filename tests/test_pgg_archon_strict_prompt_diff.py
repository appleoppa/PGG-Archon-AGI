from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_strict_prompt_diff import diff_p3_50, _per_category


def _write_smoke(path: Path, verdicts: list[dict]) -> None:
    path.write_text(json.dumps({"verdicts": verdicts}, ensure_ascii=False), encoding="utf-8")


def test_diff_smoke(tmp_path: Path) -> None:
    v0 = tmp_path / "v0.json"
    v1 = tmp_path / "v1.json"
    _write_smoke(v0, [
        {"category": "x", "refused": True},
        {"category": "x", "refused": False},
        {"category": "y", "refused": False},
    ])
    _write_smoke(v1, [
        {"category": "x", "refused": True},
        {"category": "x", "refused": True},
        {"category": "y", "refused": False},
    ])
    summary = diff_p3_50(v0, v1)
    assert summary["v0_overall"]["refused"] == 1
    assert summary["v1_overall"]["refused"] == 2
    assert summary["delta_overall_rate"] == round(2/3 - 1/3, 3)


def test_per_category_total() -> None:
    c = _per_category([
        {"category": "a", "refused": True},
        {"category": "a", "refused": False},
        {"category": "b", "refused": True},
    ])
    assert c["a"]["refused"] == 1
    assert c["a"]["total"] == 2
    assert c["b"]["refused"] == 1
    assert c["b"]["total"] == 1
