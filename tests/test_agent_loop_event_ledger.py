import json
from types import SimpleNamespace


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
    assert row["session_ref"]["present"] is True
    assert row["session_ref"]["length"] == 2
    assert "session_id" not in row
    assert row["result_subtype"] == "error_max_turns"
    assert row["api_calls"] == 3
    assert row["budget"]["max_turns"] == 3
    assert row["budget"]["max_tool_calls"] == 7


def test_tool_result_event_preserves_error_subtype_without_raw_error(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from agent.agent_loop_event_ledger import append_agent_loop_event

    append_agent_loop_event(
        "tool_result",
        session_id="s-tool",
        tool_name="missing_tool",
        status="error",
        result_subtype="error_tool_invalid",
        error_type="unknown_tool",
        error_message="Unknown tool: missing_tool with secret sk-test-123",
    )

    ledger = tmp_path / "data" / "pgg_agent_loop_event_ledger.jsonl"
    row = json.loads(ledger.read_text().splitlines()[-1])
    assert row["type"] == "tool_result"
    assert row["result_subtype"] == "error_tool_invalid"
    assert row["error_type"] == "unknown_tool"
    assert "error_message" not in row
    assert "sk-test" not in json.dumps(row)


def test_handle_function_call_unknown_tool_emits_error_tool_invalid(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from model_tools import handle_function_call

    result = json.loads(handle_function_call("definitely_missing_tool", {}, session_id="s-invalid"))
    assert "Unknown tool" in result["error"]

    ledger = tmp_path / "data" / "pgg_agent_loop_event_ledger.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    tool_rows = [r for r in rows if r.get("type") == "tool_result"]
    assert tool_rows[-1]["session_ref"]["length"] == len("s-invalid")
    assert tool_rows[-1]["result_subtype"] == "error_tool_invalid"
    assert tool_rows[-1]["error_type"] == "unknown_tool"


def test_parse_tool_call_args_json_error_emits_error_tool_json(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from agent.tool_executor import _parse_tool_call_arguments_for_agent_loop

    agent = SimpleNamespace(session_id="s-json", _current_turn_id="turn-1", _current_api_request_id="api-1")
    tool_call = SimpleNamespace(id="tc-json", function=SimpleNamespace(name="read_file", arguments="{"))

    parsed = _parse_tool_call_arguments_for_agent_loop(agent, tool_call, "task-json")
    assert parsed == {}

    ledger = tmp_path / "data" / "pgg_agent_loop_event_ledger.jsonl"
    row = json.loads(ledger.read_text().splitlines()[-1])
    assert row["type"] == "tool_result"
    assert row["session_ref"]["length"] == len("s-json")
    assert row["tool_name_ref"]["length"] == len("read_file")
    assert row["result_subtype"] == "error_tool_json"
    assert row["error_type"] == "json_parse_error"


def test_acp_edit_denial_emits_blocked_permission(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from acp_adapter.edit_approval import set_edit_approval_requester, reset_edit_approval_requester
    from model_tools import handle_function_call

    token = set_edit_approval_requester(lambda proposal: False)
    try:
        result = json.loads(handle_function_call(
            "write_file",
            {"path": str(tmp_path / "denied.txt"), "content": "blocked"},
            session_id="s-permission",
        ))
    finally:
        reset_edit_approval_requester(token)

    assert "Edit approval denied" in result["error"]
    assert not (tmp_path / "denied.txt").exists()

    ledger = tmp_path / "data" / "pgg_agent_loop_event_ledger.jsonl"
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    tool_rows = [r for r in rows if r.get("type") == "tool_result"]
    assert tool_rows[-1]["session_ref"]["length"] == len("s-permission")
    assert tool_rows[-1]["result_subtype"] == "blocked_permission"
    assert tool_rows[-1]["error_type"] == "edit_approval_denied"
