"""Graph replay for PGG case-flow ledgers.

This module turns a sanitized case-flow ledger into a deterministic graph/state
replay. It is intentionally read-only: it does not call departments, create case
numbers, read raw legal materials, or generate legal deliverables.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

DEFAULT_REPLAY_DIR = Path("/Users/appleoppa/.hermes/workspace/agi-routing/case-flow-graph-replays")

_NODE_ORDER = (
    "intake",
    "case_management",
    "evidence_gate",
    "lead_department",
    "legal_support",
    "case_simulation",
    "knowledge_support",
    "internal_report",
    "external_delivery_gate",
)

_DEPARTMENT_TO_NODE = {
    "案件管理中心": "case_management",
    "证据管理部": "evidence_gate",
    "主办部门": "lead_department",
    "律法支持部": "legal_support",
    "案件推演部": "case_simulation",
    "智脑知识部": "knowledge_support",
}

_NODE_LABELS = {
    "intake": "收案入口",
    "case_management": "案件管理中心",
    "evidence_gate": "证据门禁",
    "lead_department": "主办部门",
    "legal_support": "律法支持部",
    "case_simulation": "案件推演部",
    "knowledge_support": "智脑知识部",
    "internal_report": "内部报告",
    "external_delivery_gate": "对外交付门禁",
}

_PASS_STATUSES = {"PASS", "DONE", "COMPLETED", "OK"}
_BLOCK_STATUSES = {"BLOCK", "FAILED", "ERROR", "TIMEOUT"}


def _sha256_obj(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _safe_text(value: Any, limit: int = 300) -> str:
    return str(value or "")[:limit]


@dataclass(frozen=True)
class CaseFlowGraphNode:
    node_id: str
    label: str
    status: str
    reason: str
    source_event_count: int = 0
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "status": self.status,
            "reason": self.reason,
            "source_event_count": self.source_event_count,
            "required": self.required,
        }


def _initial_nodes() -> dict[str, CaseFlowGraphNode]:
    return {
        node_id: CaseFlowGraphNode(
            node_id=node_id,
            label=_NODE_LABELS[node_id],
            status="PENDING",
            reason="awaiting_replay_input",
        )
        for node_id in _NODE_ORDER
    }


def _replace_node(nodes: dict[str, CaseFlowGraphNode], node_id: str, *, status: str, reason: str, source_event_count: int = 0, required: bool = True) -> None:
    nodes[node_id] = CaseFlowGraphNode(
        node_id=node_id,
        label=_NODE_LABELS[node_id],
        status=status,
        reason=reason,
        source_event_count=source_event_count,
        required=required,
    )


def _status_from_department_event(event: Mapping[str, Any]) -> str:
    raw_status = _safe_text(event.get("status")).upper()
    if raw_status in _PASS_STATUSES:
        return "PASS"
    if raw_status in _BLOCK_STATUSES and not bool(event.get("exception_labeled")):
        return "BLOCK"
    if raw_status in _BLOCK_STATUSES:
        return "ACTION_REQUIRED"
    return "ACTION_REQUIRED"


def _build_edges() -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for idx, source in enumerate(_NODE_ORDER[:-1]):
        edges.append({"from": source, "to": _NODE_ORDER[idx + 1], "type": "sequential_gate"})
    return edges


def build_case_flow_graph_replay(
    ledger: Mapping[str, Any],
    *,
    evidence_gate_packet: Mapping[str, Any] | None = None,
    write_replay: bool = False,
    replay_dir: str | Path = DEFAULT_REPLAY_DIR,
) -> dict[str, Any]:
    """Build a deterministic replay graph from a sanitized case-flow ledger.

    When *evidence_gate_packet* is provided and carries a valid
    ``evidence_gate_status``, the ``evidence_gate`` node is overridden with the
    packet's resolution — allowing the packet builder (e.g. a human reviewer or
    bounded repair plan) to unblock a previously-stuck replay without changing
    the root ledger.

    Packet-driven override rules:
    - ``PASS`` → evidence_gate node becomes PASS.
    - ``BLOCK`` → evidence_gate node stays BLOCK.
    - ``HOLD`` / others → evidence_gate node becomes ACTION_REQUIRED.
    - ``None`` (default) → pure ledger-driven replay, unchanged.
    """
    nodes = _initial_nodes()
    ledger_status = _safe_text(ledger.get("status") or "UNKNOWN").upper()
    preflight_status = _safe_text(ledger.get("preflight_status") or "UNKNOWN").upper()
    events = [dict(item) for item in _as_sequence(ledger.get("events")) if isinstance(item, Mapping)]

    department_events_by_node: dict[str, list[Mapping[str, Any]]] = {node_id: [] for node_id in _NODE_ORDER}
    required_actions_by_node: dict[str, list[Mapping[str, Any]]] = {node_id: [] for node_id in _NODE_ORDER}
    for event in events:
        if event.get("event_type") == "department_status":
            node_id = _DEPARTMENT_TO_NODE.get(_safe_text(event.get("owner")))
            if node_id:
                department_events_by_node[node_id].append(event)
        elif event.get("event_type") == "required_action":
            action = _safe_text(event.get("action"))
            owner = _safe_text(event.get("owner"))
            if "案号" in action or "案件管理" in owner or "formal_case_number" in action:
                required_actions_by_node["case_management"].append(event)
            elif "证据" in action or "evidence" in action:
                required_actions_by_node["evidence_gate"].append(event)
            elif "内部报告" in action or "internal_report" in action:
                required_actions_by_node["internal_report"].append(event)
            elif "交付" in action or "external" in action:
                required_actions_by_node["external_delivery_gate"].append(event)
            else:
                required_actions_by_node["lead_department"].append(event)

    intake_blocked = preflight_status == "BLOCK" and not any(department_events_by_node.values())
    _replace_node(
        nodes,
        "intake",
        status="BLOCK" if intake_blocked else "PASS",
        reason=f"preflight_status={preflight_status}" if intake_blocked else f"case_entered_replay; preflight_status={preflight_status}",
        source_event_count=1,
    )

    for department, node_id in _DEPARTMENT_TO_NODE.items():
        dept_events = department_events_by_node[node_id]
        action_events = required_actions_by_node[node_id]
        if dept_events:
            statuses = [_status_from_department_event(item) for item in dept_events]
            if "BLOCK" in statuses:
                status = "BLOCK"
            elif "ACTION_REQUIRED" in statuses:
                status = "ACTION_REQUIRED"
            else:
                status = "PASS"
            reason = f"department_events={len(dept_events)}"
        elif department in set(_as_sequence(ledger.get("missing_departments"))):
            status = "ACTION_REQUIRED"
            reason = "missing_department_event"
        elif action_events:
            status = "ACTION_REQUIRED"
            reason = f"required_actions={len(action_events)}"
        else:
            status = "PENDING"
            reason = "no_department_event"
        _replace_node(nodes, node_id, status=status, reason=reason, source_event_count=len(dept_events) + len(action_events))

    # -- evidence_gate packet override (after department loop, before downstream nodes) --
    if evidence_gate_packet is not None and isinstance(evidence_gate_packet, Mapping):
        pkt_status = _safe_text(evidence_gate_packet.get("evidence_gate_status")).upper()
        if pkt_status in _PASS_STATUSES:
            _replace_node(nodes, "evidence_gate", status="PASS", reason="evidence_gate_packet_pass", source_event_count=nodes["evidence_gate"].source_event_count)
        elif pkt_status in _BLOCK_STATUSES:
            _replace_node(nodes, "evidence_gate", status="BLOCK", reason="evidence_gate_packet_block", source_event_count=nodes["evidence_gate"].source_event_count)
        elif pkt_status:
            label = _safe_text(evidence_gate_packet.get("missing_evidence_or_exception_label") or "evidence_gate_packet_hold")
            _replace_node(nodes, "evidence_gate", status="ACTION_REQUIRED", reason=label, source_event_count=nodes["evidence_gate"].source_event_count)

    internal_actions = required_actions_by_node["internal_report"]
    if ledger.get("safe_to_continue_internal_work") and not internal_actions:
        internal_status = "PASS" if ledger_status == "PASS" else "ACTION_REQUIRED"
        internal_reason = f"ledger_status={ledger_status}"
    elif internal_actions:
        internal_status = "ACTION_REQUIRED"
        internal_reason = f"required_actions={len(internal_actions)}"
    else:
        internal_status = "ACTION_REQUIRED"
        internal_reason = "internal_work_not_cleared"
    _replace_node(nodes, "internal_report", status=internal_status, reason=internal_reason, source_event_count=len(internal_actions))

    if bool(ledger.get("allows_external_delivery")) and ledger_status == "PASS":
        delivery_status = "PASS"
        delivery_reason = "ledger_allows_external_delivery"
    elif ledger_status == "BLOCK":
        delivery_status = "BLOCK"
        delivery_reason = "ledger_blocked"
    else:
        delivery_status = "ACTION_REQUIRED"
        delivery_reason = "external_delivery_not_cleared"
    _replace_node(nodes, "external_delivery_gate", status=delivery_status, reason=delivery_reason, source_event_count=len(required_actions_by_node["external_delivery_gate"]))

    node_list = [nodes[node_id].to_dict() for node_id in _NODE_ORDER]
    status_counts: dict[str, int] = {}
    for node in node_list:
        status_counts[node["status"]] = status_counts.get(node["status"], 0) + 1

    first_blocker = next((node for node in node_list if node["status"] == "BLOCK"), None)
    first_action = next((node for node in node_list if node["status"] == "ACTION_REQUIRED"), None)
    if first_blocker:
        replay_status = "BLOCK"
        next_node = first_blocker["node_id"]
    elif first_action:
        replay_status = "ACTION_REQUIRED"
        next_node = first_action["node_id"]
    elif all(node["status"] == "PASS" for node in node_list):
        replay_status = "PASS"
        next_node = None
    else:
        replay_status = "ACTION_REQUIRED"
        next_node = next((node["node_id"] for node in node_list if node["status"] != "PASS"), None)

    replay = {
        "schema": "PGGCaseFlowGraphReplay/v1",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "case_id": ledger.get("case_id") or "UNKNOWN-CASE",
        "source_ledger_hash": ledger.get("ledger_hash") or _sha256_obj(dict(ledger)),
        "source_ledger_status": ledger_status,
        "replay_status": replay_status,
        "next_node": next_node,
        "nodes": node_list,
        "edges": _build_edges(),
        "status_counts": dict(sorted(status_counts.items())),
        "allows_external_delivery": bool(ledger.get("allows_external_delivery")) and replay_status == "PASS",
        "side_effects": "replay_write" if write_replay else "read_only_replay",
        "boundary": "Graph replay uses sanitized ledger fields only; it does not call departments or generate legal deliverables.",
        "agi_completion_claim": False,
    }
    replay["replay_hash"] = _sha256_obj(replay)
    if write_replay:
        out_dir = Path(replay_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        case_id = str(replay["case_id"]).replace("/", "_")[:80]
        out = out_dir / f"{int(time.time())}_{case_id}_case_flow_graph_replay.json"
        out.write_text(json.dumps(replay, ensure_ascii=False, indent=2), encoding="utf-8")
        replay["replay_path"] = str(out)
    return replay


def summarize_case_flow_graph_replays(replays: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = [dict(item) for item in replays]
    status_counts: dict[str, int] = {}
    next_node_counts: dict[str, int] = {}
    for item in items:
        status = _safe_text(item.get("replay_status") or "UNKNOWN").upper()
        status_counts[status] = status_counts.get(status, 0) + 1
        next_node = _safe_text(item.get("next_node") or "NONE")
        next_node_counts[next_node] = next_node_counts.get(next_node, 0) + 1
    return {
        "schema": "PGGCaseFlowGraphReplaySummary/v1",
        "replay_count": len(items),
        "status_counts": dict(sorted(status_counts.items())),
        "next_node_counts": dict(sorted(next_node_counts.items())),
        "blocked_count": status_counts.get("BLOCK", 0),
        "action_required_count": status_counts.get("ACTION_REQUIRED", 0),
        "pass_count": status_counts.get("PASS", 0),
        "agi_completion_claim": False,
    }


__all__ = ["build_case_flow_graph_replay", "summarize_case_flow_graph_replays"]
