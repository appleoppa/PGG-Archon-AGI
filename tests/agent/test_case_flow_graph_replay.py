from pathlib import Path

from agent.case_flow_graph_replay import build_case_flow_graph_replay, summarize_case_flow_graph_replays
from agent.case_flow_orchestrator_ledger import build_case_flow_orchestrator_ledger


def test_graph_replay_blocks_at_intake_when_preflight_blocked(tmp_path):
    ledger = build_case_flow_orchestrator_ledger(
        "启动办案程序",
        {
            "case_id": "TEMP-001",
            "case_id_generated_by": "苹果中枢",
            "formal_workflow_started": False,
            "evidence_gate_status": "HOLD",
            "intended_output": "正式律师函",
            "internal_report_generated": False,
            "department_results": [],
        },
    )

    replay = build_case_flow_graph_replay(ledger, write_replay=True, replay_dir=tmp_path)

    assert replay["schema"] == "PGGCaseFlowGraphReplay/v1"
    assert replay["replay_status"] == "BLOCK"
    assert replay["next_node"] == "intake"
    assert replay["allows_external_delivery"] is False
    assert len(replay["nodes"]) == 9
    assert len(replay["edges"]) == 8
    assert replay["agi_completion_claim"] is False
    assert Path(replay["replay_path"]).exists()


def test_graph_replay_maps_unlabeled_department_timeout_to_block():
    ledger = build_case_flow_orchestrator_ledger(
        "开始办案",
        {
            "case_id": "PGG-MS-20260528-001",
            "case_id_generated_by": "案件管理中心",
            "formal_workflow_started": True,
            "evidence_gate_status": "PASS",
            "intended_output": "内部分析",
            "internal_report_generated": True,
            "department_results": [
                {"department": "案件管理中心", "status": "PASS"},
                {"department": "证据管理部", "status": "TIMEOUT", "exception_labeled": False},
            ],
        },
    )

    replay = build_case_flow_graph_replay(ledger)
    nodes = {node["node_id"]: node for node in replay["nodes"]}

    assert replay["replay_status"] == "BLOCK"
    assert replay["next_node"] == "evidence_gate"
    assert nodes["case_management"]["status"] == "PASS"
    assert nodes["evidence_gate"]["status"] == "BLOCK"
    assert nodes["evidence_gate"]["reason"] == "department_events=1"


def test_graph_replay_passes_when_all_departments_and_delivery_gate_pass():
    departments = [
        {"department": name, "status": "PASS", "evidence_hash": f"h-{idx}"}
        for idx, name in enumerate(("案件管理中心", "证据管理部", "主办部门", "律法支持部", "案件推演部", "智脑知识部"), 1)
    ]
    ledger = build_case_flow_orchestrator_ledger(
        "启动办案程序",
        {
            "case_id": "PGG-MS-20260528-001",
            "case_id_generated_by": "案件管理中心",
            "formal_workflow_started": True,
            "evidence_gate_status": "PASS",
            "intended_output": "正式法律意见书",
            "internal_report_generated": True,
            "department_results": departments,
        },
    )

    replay = build_case_flow_graph_replay(ledger)

    assert ledger["allows_external_delivery"] is True
    assert replay["replay_status"] == "PASS"
    assert replay["next_node"] is None
    assert replay["allows_external_delivery"] is True
    assert replay["status_counts"] == {"PASS": 9}


def test_graph_replay_summary_counts_statuses_and_next_nodes():
    summary = summarize_case_flow_graph_replays(
        [
            {"replay_status": "BLOCK", "next_node": "intake"},
            {"replay_status": "ACTION_REQUIRED", "next_node": "case_management"},
            {"replay_status": "PASS", "next_node": None},
        ]
    )

    assert summary["replay_count"] == 3
    assert summary["blocked_count"] == 1
    assert summary["action_required_count"] == 1
    assert summary["pass_count"] == 1
    assert summary["next_node_counts"]["intake"] == 1
    assert summary["next_node_counts"]["NONE"] == 1
    assert summary["agi_completion_claim"] is False


def _evidence_gate_packet(status: str, label: str = "") -> dict:
    return {
        "evidence_gate_status": status,
        "missing_evidence_or_exception_label": label or f"evidence_gate_packet_{status.lower()}",
    }


def test_graph_replay_evidence_gate_packet_pass_unblocks_evidence_gate(tmp_path):
    """A PASS packet overrides a BLOCK evidence_gate node to PASS."""
    ledger = build_case_flow_orchestrator_ledger(
        "开车",
        {
            "case_id": "TEMP-002",
            "case_id_generated_by": "苹果中枢",
            "formal_workflow_started": True,
            "evidence_gate_status": "HOLD",
            "intended_output": "法律意见书",
            "internal_report_generated": True,
            "department_results": [
                {"department": "证据管理部", "status": "TIMEOUT", "exception_labeled": False},
            ],
        },
    )
    packet = _evidence_gate_packet("PASS", "evidence_resolved")
    replay = build_case_flow_graph_replay(ledger, evidence_gate_packet=packet,
                                          write_replay=True, replay_dir=tmp_path)
    nodes = {n["node_id"]: n for n in replay["nodes"]}
    assert nodes["evidence_gate"]["status"] == "PASS"
    assert nodes["evidence_gate"]["reason"] == "evidence_gate_packet_pass"


def test_graph_replay_evidence_gate_packet_block_keeps_block():
    """A BLOCK packet keeps evidence_gate as BLOCK."""
    ledger = build_case_flow_orchestrator_ledger(
        "开车",
        {
            "case_id": "TEMP-002",
            "case_id_generated_by": "苹果中枢",
            "formal_workflow_started": True,
            "evidence_gate_status": "HOLD",
            "intended_output": "法律意见书",
            "internal_report_generated": True,
            "department_results": [
                {"department": "证据管理部", "status": "TIMEOUT", "exception_labeled": False},
            ],
        },
    )
    packet = _evidence_gate_packet("BLOCK", "still_missing")
    replay = build_case_flow_graph_replay(ledger, evidence_gate_packet=packet)
    nodes = {n["node_id"]: n for n in replay["nodes"]}
    assert nodes["evidence_gate"]["status"] == "BLOCK"
    assert nodes["evidence_gate"]["reason"] == "evidence_gate_packet_block"


def test_graph_replay_evidence_gate_packet_hold_sets_action_required():
    """A HOLD packet sets evidence_gate to ACTION_REQUIRED with the label as reason."""
    ledger = build_case_flow_orchestrator_ledger(
        "开车",
        {
            "case_id": "TEMP-002",
            "case_id_generated_by": "苹果中枢",
            "formal_workflow_started": True,
            "evidence_gate_status": "HOLD",
            "intended_output": "法律意见书",
            "internal_report_generated": True,
            "department_results": [
                {"department": "证据管理部", "status": "TIMEOUT", "exception_labeled": False},
            ],
        },
    )
    packet = _evidence_gate_packet("HOLD", "waiting_for_original")
    replay = build_case_flow_graph_replay(ledger, evidence_gate_packet=packet)
    nodes = {n["node_id"]: n for n in replay["nodes"]}
    assert nodes["evidence_gate"]["status"] == "ACTION_REQUIRED"
    assert nodes["evidence_gate"]["reason"] == "waiting_for_original"
