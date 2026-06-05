from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.pgg_archon_super_evolution_card import _strip_fence, _try_parse_json_obj, _has_required


def test_strip_fence() -> None:
    assert _strip_fence("```json\n{\"a\":1}\n```") == '{"a":1}'
    assert _strip_fence('{"a":1}') == '{"a":1}'


def test_try_parse_json_obj_window() -> None:
    out = _try_parse_json_obj("noise {\"a\":1} noise")
    assert out == {"a": 1}


def test_has_required() -> None:
    assert _has_required({"id": "x", "title": "t", "key_thesis": "kt", "mapped_skill": "ms", "status": "ok", "providers_seen": ["a"]})
    assert not _has_required({"id": "x"})
    assert not _has_required({"status": "ok"})
    assert not _has_required({"id": "x", "title": "t", "key_thesis": "kt", "mapped_skill": "ms", "status": "ok"})
