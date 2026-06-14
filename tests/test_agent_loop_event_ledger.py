import json


def test_append_loop_result_event_preserves_result_subtype_and_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from agent.agent_loop_event_ledger import append_agent_loop_event

    append_agent_loop_event(
        "loop_result",
        session_id="s1",
        status="completed",
        result_subtype="error_max_turns",
        api_calls=3,
        max_turns=3,
        budget={"max_turns": 3, "max_tool_calls": 7},
    )

    ledger = tmp_path / "data" / "pgg_agent_loop_event_ledger.jsonl"
    row = json.loads(ledger.read_text().splitlines()[-1])
    assert row["type"] == "loop_result"
    assert row["result_subtype"] == "error_max_turns"
    assert row["api_calls"] == 3
    assert row["budget"]["max_turns"] == 3
    assert row["budget"]["max_tool_calls"] == 7
