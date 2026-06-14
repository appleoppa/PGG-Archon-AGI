from __future__ import annotations

import json
from pathlib import Path

from agent.department_memory_runtime import build_department_memory_runtime_state, write_runtime_state


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def test_department_memory_runtime_blocks_without_authorization(monkeypatch, tmp_path):
    h = tmp_path / "hermes"
    out = h / "workspace/pgg-archon-governance/team-memory-p3-20260606"
    _write_json(out / "department_memory_distillation_latest.json", {
        "schema": "PGGDepartmentMemoryDistillationPackage/v1",
        "generated_at": "2026-06-08T00:00:00+00:00",
        "candidate_count": 1,
        "distilled_count": 1,
        "archived_count": 0,
        "records": [{"department": "hub", "distillation_status": "distilled"}],
    })
    _write_json(out / "department_memory_review_desk_latest.json", {
        "schema": "PGGDepartmentMemoryReviewDesk/v1",
        "generated_at": "2026-06-08T00:00:00+00:00",
        "candidate_count": 0,
        "items": [],
        "write_allowed": False,
    })
    _write_json(out / "department_memory_apply_request_latest.json", {
        "schema": "PGGDepartmentMemoryApplyRequest/v1",
        "generated_at": "2026-06-08T00:00:00+00:00",
        "user_authorization": False,
        "authorization_scope": None,
        "items": [],
    })
    _write_json(out / "department_memory_rollback_package_latest.json", {
        "schema": "PGGDepartmentMemoryRollbackPackage/v1",
        "generated_at": "2026-06-08T00:00:00+00:00",
        "rollback_items": [],
    })
    _write_json(out / "department_memory_apply_gate_result.json", {
        "schema": "PGGDepartmentMemoryApplyGateResult/v1",
        "generated_at": "2026-06-08T00:00:00+00:00",
        "gate": {"status": "department_memory_apply_blocked", "apply_allowed": False, "score_percent": 40.0, "missing_checks": ["user_authorization_present"]},
    })

    monkeypatch.setenv("HERMES_HOME", str(h))
    state = build_department_memory_runtime_state()

    assert state["schema"] == "PGGDepartmentMemoryRuntime/v1"
    assert state["runtime_status"] == "NOOP_BLOCKED_OR_EMPTY"
    assert state["write_allowed"] is False
    assert state["apply_allowed"] is False
    assert state["curated_memory_authoritative"] is True
    assert "no_department_memory_apply_authorization" in state["gate"]["blockers"]
    assert state["counts"]["distilled_count"] == 1
    assert state["gate"]["readiness_checks"]["safe_targets"] is True


def test_department_memory_runtime_detects_unsafe_target_and_writes_state(monkeypatch, tmp_path):
    h = tmp_path / "hermes"
    out = h / "workspace/pgg-archon-governance/team-memory-p3-20260606"
    _write_json(out / "department_memory_distillation_latest.json", {"schema": "x", "generated_at": "2026-06-08T00:00:00+00:00", "records": []})
    _write_json(out / "department_memory_review_desk_latest.json", {"schema": "x", "generated_at": "2026-06-08T00:00:00+00:00", "items": []})
    _write_json(out / "department_memory_apply_request_latest.json", {
        "schema": "x",
        "generated_at": "2026-06-08T00:00:00+00:00",
        "user_authorization": True,
        "authorization_scope": "department_memory_apply",
        "items": [{
            "department": "hub",
            "distilled": True,
            "department_review": "PASS",
            "central_audit": "PASS",
            "target_path": "/tmp/unsafe-memory.md",
        }],
    })
    _write_json(out / "department_memory_rollback_package_latest.json", {"schema": "x", "generated_at": "2026-06-08T00:00:00+00:00", "rollback_items": [{"x": 1}]})
    _write_json(out / "department_memory_apply_gate_result.json", {"schema": "x", "generated_at": "2026-06-08T00:00:00+00:00", "gate": {"status": "blocked", "apply_allowed": False}})

    monkeypatch.setenv("HERMES_HOME", str(h))
    state = build_department_memory_runtime_state()
    assert state["gate"]["readiness_checks"]["safe_targets"] is False
    assert state["gate"]["unsafe_targets"] == ["/tmp/unsafe-memory.md"]
    out_file = write_runtime_state(state)
    readback = json.loads(out_file.read_text(encoding="utf-8"))
    assert readback["schema"] == "PGGDepartmentMemoryRuntime/v1"
    assert readback["gate"]["unsafe_targets"] == ["/tmp/unsafe-memory.md"]
