from __future__ import annotations

import pytest

from agent.pgg_archon_redteam_corpus_gen import _try_parse_json_obj


def test_try_parse_json_obj_raw() -> None:
    assert _try_parse_json_obj('{"a":1}') == {"a": 1}


def test_try_parse_json_obj_window() -> None:
    text = "noise before {\"a\":1} noise after"
    assert _try_parse_json_obj(text) == {"a": 1}


def test_try_parse_json_obj_balanced() -> None:
    # input is "prefix {{"inner":{"a":1}} suffix" — outermost wrap is unbalanced
    # and the innermost balanced window is {"a":1}.
    text = "prefix {{" + '"a":1' + "}} suffix"
    parsed = _try_parse_json_obj(text)
    assert parsed == {"a": 1}


def test_try_parse_json_obj_returns_none() -> None:
    assert _try_parse_json_obj("not json at all") is None
    assert _try_parse_json_obj("") is None
