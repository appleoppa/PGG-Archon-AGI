from __future__ import annotations

from agent.pgg_archon_minimax_structured_adapter import parse_structured_json, strip_think


def test_strip_think_removes_minimax_reasoning_block() -> None:
    text = '<think>hidden reasoning</think>{"verdict":"PASS"}'
    assert strip_think(text) == '{"verdict":"PASS"}'


def test_parse_direct_json() -> None:
    r = parse_structured_json('{"updated_score": 41, "level": "L1"}')
    assert r.ok is True
    assert r.data == {"updated_score": 41, "level": "L1"}
    assert "does not validate truth" in r.boundary


def test_parse_minimax_think_plus_json() -> None:
    r = parse_structured_json('<think>analysis</think>\n{"verdict":"WATCH","score":38}')
    assert r.ok is True
    assert r.data and r.data["verdict"] == "WATCH"


def test_parse_json_inside_markdown_like_text() -> None:
    r = parse_structured_json('prefix text\n```json\n{"a":1,"b":{"c":2}}\n```\nsuffix')
    assert r.ok is True
    assert r.data == {"a": 1, "b": {"c": 2}}


def test_parse_failure_is_preserved() -> None:
    r = parse_structured_json('<think>x</think> no json here')
    assert r.ok is False
    assert r.error == "json_parse_failed"
    assert "do not count as PASS" in r.boundary
