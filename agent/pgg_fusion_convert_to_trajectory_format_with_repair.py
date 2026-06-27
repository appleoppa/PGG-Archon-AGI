import json
from typing import Any, Dict, List


def convert_to_trajectory_format_with_repair(
    agent,
    messages: List[Dict[str, Any]],
    user_query: str,
    completed: bool,
) -> Dict[str, Any]:
    """Repair malformed message ordering, then convert into trajectory format."""
    def _normalize_for_trajectory(msg: Any) -> Any:
        if not isinstance(msg, dict):
            return msg
        normalized = dict(msg)
        content = normalized.get("content")
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    if item_type == "text":
                        parts.append(str(item.get("text", "")))
                    elif "text" in item:
                        parts.append(str(item.get("text", "")))
                    elif "content" in item:
                        parts.append(str(item.get("content", "")))
                    else:
                        parts.append(json.dumps(item, ensure_ascii=False))
                else:
                    parts.append(str(item))
            normalized["content"] = "\n".join(p for p in parts if p is not None)
        elif content is None:
            normalized["content"] = ""
        elif not isinstance(content, str):
            normalized["content"] = json.dumps(content, ensure_ascii=False)
        return normalized

    def _scratchpad_to_thinking(text: str) -> str:
        converter = globals().get("convert_scratchpad_to_think")
        if callable(converter):
            return converter(text)
        return text or ""

    def _tool_arguments(raw_args: Any) -> Any:
        if isinstance(raw_args, str):
            try:
                return json.loads(raw_args)
            except json.JSONDecodeError:
                return {}
        return raw_args if raw_args is not None else {}

    def _maybe_json_content(tool_content: Any) -> Any:
        if not isinstance(tool_content, str):
            return tool_content
        stripped = tool_content.strip()
        if stripped.startswith(("{", "[")):
            try:
                return json.loads(stripped)
            except Exception:
                return tool_content
        return tool_content

    repairs = 0
    if not messages:
        repaired_messages: List[Dict[str, Any]] = []
    else:
        known_tool_ids = set()
        filtered: List[Dict[str, Any]] = []
        for msg in messages:
            if not isinstance(msg, dict):
                filtered.append(msg); continue
            role = msg.get("role")
            if role == "assistant":
                known_tool_ids = set()
                for tool_call in msg.get("tool_calls") or []:
                    if isinstance(tool_call, dict) and tool_call.get("id"):
                        known_tool_ids.add(tool_call["id"])
                filtered.append(msg)
            elif role == "tool":
                tc_id = msg.get("tool_call_id")
                if tc_id and tc_id in known_tool_ids:
                    filtered.append(msg)
                else:
                    repairs += 1
            else:
                if role == "user":
                    known_tool_ids = set()
                filtered.append(msg)
        repaired_messages = []
        for msg in filtered:
            if (repaired_messages and isinstance(msg, dict) and msg.get("role") == "user"
                and isinstance(repaired_messages[-1], dict) and repaired_messages[-1].get("role") == "user"):
                prev = repaired_messages[-1]
                prev_c = prev.get("content", "")
                cur_c = msg.get("content", "")
                if isinstance(prev_c, str) and isinstance(cur_c, str):
                    prev["content"] = (f"{prev_c}\n\n{cur_c}" if prev_c and cur_c else prev_c or cur_c)
                    repairs += 1; continue
            repaired_messages.append(msg)
        if repairs > 0:
            messages[:] = repaired_messages

    repaired_messages = [_normalize_for_trajectory(m) for m in repaired_messages]
    trajectory = []
    tool_formatter = getattr(agent, "_format_tools_for_system_message", None)
    formatted_tools = tool_formatter() if callable(tool_formatter) else ""
    system_msg = "You are a function calling AI model..."
    trajectory.append({"from": "system", "value": system_msg})
    trajectory.append({"from": "human", "value": user_query})
    i = 1
    while i < len(repaired_messages):
        msg = repaired_messages[i]
        if not isinstance(msg, dict):
            i += 1; continue
        role = msg.get("role")
        if role == "assistant":
            tool_calls = msg.get("tool_calls") or []
            if tool_calls:
                content = ""
                reasoning = msg.get("reasoning")
                if isinstance(reasoning, str) and reasoning.strip():
                    content += f"<thinking>\n{reasoning}\n</thinking>\n"
                if msg.get("content"):
                    content += str(msg.get("content")) + "\n"
                for tool_call in tool_calls:
                    if not isinstance(tool_call, dict):
                        continue
                    function = tool_call.get("function") or {}
                    tcj = {"name": function.get("name", ""), "arguments": _tool_arguments(function.get("arguments"))}
                    content += f"<tool_call>\n{json.dumps(tcj, ensure_ascii=False)}\n</tool_call>\n"
                if "<thinking>" not in content:
                    content = "<thinking>\n</thinking>\n" + content
                trajectory.append({"from": "gpt", "value": content.rstrip()})
                tool_responses = []
                j = i + 1
                while j < len(repaired_messages):
                    tool_msg = repaired_messages[j]
                    if not isinstance(tool_msg, dict) or tool_msg.get("role") != "tool":
                        break
                    ri = len(tool_responses)
                    tool_name = "unknown"
                    if ri < len(tool_calls) and isinstance(tool_calls[ri], dict):
                        tool_name = (tool_calls[ri].get("function") or {}).get("name", "unknown")
                    payload = {"tool_call_id": tool_msg.get("tool_call_id", ""), "name": tool_name,
                               "content": _maybe_json_content(tool_msg.get("content", ""))}
                    tool_responses.append(f"<tool_response>\n{json.dumps(payload, ensure_ascii=False)}\n</tool_response>")
                    j += 1
                if tool_responses:
                    trajectory.append({"from": "tool", "value": "\n".join(tool_responses)})
                    i = j - 1
            else:
                content = ""
                reasoning = msg.get("reasoning")
                if isinstance(reasoning, str) and reasoning.strip():
                    content += f"<thinking>\n{reasoning}\n</thinking>\n"
                content += _scratchpad_to_thinking(str(msg.get("content", "") or ""))
                if "<thinking>" not in content:
                    content = "<thinking>\n</thinking>\n" + content
                trajectory.append({"from": "gpt", "value": content.strip()})
        elif role == "user":
            trajectory.append({"from": "human", "value": msg.get("content", "")})
        i += 1

    tool_formatter2 = getattr(agent, "_format_tools_for_system_message", None)
    if callable(tool_formatter2):
        formatted_tools_final = tool_formatter2()
        trajectory[0] = {"from": "system", "value": (
            "You are a function calling AI model..."
            f"<tools>\n{formatted_tools_final}\n</tools>\n"
            "For each function call return a JSON object..."
        )}

    return {"trajectory": trajectory, "repairs": repairs}
